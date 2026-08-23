"""Extractor mínimo y validado de pagos procesados FYS (capturas WhatsApp).

Por cada captura (una por día de cobranza) se hace OCR con Tesseract y se
obtienen TODAS las filas de pago:
  - DOCUMENTO (PAG-...)
  - NOMBRE DEL CLIENTE
  - EFECTIVO / TRANSFERENCIA BANCARIA / CUPON
más la fila de TOTALES impresa al pie de la captura.

Validación por captura:
  suma(filas por columna) == total impreso por columna  (tolerancia 0.01 USD)

Respaldo (regla del usuario): si no se logran extraer/validar las filas
completas, se usa ÚNICAMENTE la sumatoria impresa como total del día
(estado SOLO_TOTAL). Si ni siquiera la sumatoria se puede leer, la captura
queda SIN_TOTAL para revisión manual.

Detalles técnicos:
  - El OCR pierde comas/puntos con frecuencia ('62547' en vez de 625,47).
    Cada token numérico recibe interpretaciones y se resuelve por sección
    buscando la combinación que sume exactamente el total impreso.
  - Si la fila de totales no se detecta en la primera pasada, se reintenta
    con --psm 6 (recupera filas que el psm 4 omite).
  - Si el total impreso queda en una columna equivocada (p. ej. transferencia
    leída como cupón) pero las filas coinciden, se alinean las columnas.
"""
from __future__ import annotations

import csv
import io
import itertools
import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image, ImageEnhance, ImageOps

    _HAVE_PIL = True
except ImportError:  # pragma: no cover
    _HAVE_PIL = False

TESSERACT = Path(
    os.environ.get("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
)

DOC_RE = re.compile(r"^(?:PAG-)?\d{7,12}$", re.IGNORECASE)
NUM_RE = re.compile(r"^[\d.,]+$")
PAYMENT_COLUMNS = ("efectivo", "transferencia_bancaria", "cupon")


def interpretaciones(s: str) -> list[float]:
    """Conjunto de valores posibles de un token numérico del OCR."""
    s = s.strip().replace("|", "")
    if not NUM_RE.match(s):
        return []

    m1 = re.match(r"^(\d{1,3}(?:[.,]\d{3})+)[.,](\d{2})$", s)
    if m1:
        entero = m1.group(1).replace(",", "").replace(".", "")
        return [float(f"{entero}.{m1.group(2)}")]

    m2 = re.match(r"^(\d+)[.,](\d{2})$", s)
    if m2:
        return [float(f"{m2.group(1)}.{m2.group(2)}")]

    m3 = re.match(r"^(\d+)\.(\d+)$", s)
    if m3:
        if len(m3.group(2)) <= 2:
            return [float(f"{m3.group(1)}.{m3.group(2)}")]
        unido = m3.group(1) + m3.group(2)
        opciones = {float(f"{unido[:-2]}.{unido[-2:]}"), float(f"{m3.group(1)}.{m3.group(2)}")}
        return sorted(opciones, key=lambda v: (v != float(f"{unido[:-2]}.{unido[-2:]}"), v))

    digits = re.sub(r"\D", "", s)
    if not digits or len(digits) > 9:
        return []
    opciones: set[float] = set()
    for n in (2, 3):
        if len(digits) > n:
            opciones.add(float(f"{digits[:-n]}.{digits[-n:]}"))
    opciones.add(float(digits))
    return sorted(opciones, key=lambda v: (round(v, 2) != v, len(str(int(v))), v))


def _preprocesar(image: Path) -> bytes:
    """Escala 2x + contraste: recupera filas de total y comas/puntos perdidos."""
    im = Image.open(image)
    w, h = im.size
    w2, h2 = w * 2, h * 2
    while w2 * h2 > 40_000_000 and w2 > w:  # sin reventar la memoria
        w2, h2 = int(w2 * 0.8), int(h2 * 0.8)
    im = im.resize((w2, h2), Image.BICUBIC)
    im = im.convert("L")
    im = ImageOps.autocontrast(im, cutoff=2)
    im = ImageEnhance.Sharpness(im).enhance(1.5)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    im.close()
    return buf.getvalue()


def _text(image: Path, psm: str = "4") -> list[str]:
    if _HAVE_PIL:
        result = subprocess.run(
            [str(TESSERACT), "-", "stdout", "-l", "spa+eng", "--psm", psm],
            input=_preprocesar(image), capture_output=True, check=True,
        )
        return [line.strip(" |") for line in result.stdout.decode("utf-8", errors="replace").splitlines() if line.strip()]
    result = subprocess.run(
        [str(TESSERACT), str(image), "stdout", "-l", "spa+eng", "--psm", psm],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=True,
    )
    return [line.strip(" |") for line in result.stdout.splitlines() if line.strip()]


def _docs6(image: Path) -> list[str]:
    """Documentos PAG leídos con psm 6 (donde se conservan los PAG-...)."""
    docs: list[str] = []
    try:
        for line in _text(image, "6"):
            for m in re.finditer(r"\d{10}", line):
                docs.append(m.group(0))
    except Exception:  # noqa: BLE001
        pass
    return docs


def _fila_pago(line: str, doc_default: str | None = None) -> dict | None:
    """Interpreta una línea de pago (sin resolver montos aún)."""
    m = re.search(r"(?:PAG-)?(\d{7,12})", line)
    tiene_doc = m is not None and m.start() <= 20
    if tiene_doc:
        doc = m.group(1)
    elif doc_default:
        doc = doc_default
    else:
        return None
    montos = []
    for t in reversed(line.split()):
        limpio = _limpiar_monto(t)
        if limpio and NUM_RE.match(limpio):
            montos.insert(0, limpio)
        elif re.fullmatch(r"[-——–•·|,:;]+", t):
            continue
        else:
            break
    if not montos:
        return None
    if len(montos) >= 3:
        efectivo, tf, cp = montos[-3], montos[-2], montos[-1]
    elif len(montos) == 2:
        efectivo, tf, cp = montos[0], montos[1], "0,00"
    else:
        efectivo, tf, cp = montos[0], "0,00", "0,00"
    nombre = line[m.end():] if m else line
    for tok in montos:
        idx = nombre.find(tok)
        if idx >= 0:
            nombre = nombre[:idx].strip(" |·:;")
            break
    nombre = re.sub(r"^[^A-ZÀ-Ý0-9]*", "", nombre).rstrip(" |·:;")
    nombre = re.sub(r"\s+", " ", nombre).strip()
    return {
        "documento": doc,
        "cliente": nombre,
        "efectivo": efectivo,
        "transferencia_bancaria": tf,
        "cupon": cp,
    }


def _limpiar_monto(w: str) -> str:
    """Quita basura del OCR pegada a un monto: '0,00:' -> '0,00'."""
    w = w.strip(" |·:;!_€©é)(").rstrip(".,")
    return w if NUM_RE.match(w) else ""


def _es_fila_posible(line: str) -> bool:
    """Línea con nombre (letras) y al menos 2 montos: candidata a fila sin doc."""
    if not re.search(r"[A-Za-zÀ-Ý]", line):
        return False
    n = sum(1 for w in line.split() if NUM_RE.match(_limpiar_monto(w)))
    return n >= 2


def _fila_total(line: str) -> list[str] | None:
    """Línea sin documento formada por montos: total de la sección."""
    if not line.strip():
        return None
    if re.match(r"^[A-ZÀ-Ý]{2,}", line.split()[0]):
        return None
    montos = [w for w in line.split() if NUM_RE.match(w.strip("|"))]
    if len(montos) in (2, 3):
        return montos
    return None


def _fecha(lines: list[str]) -> list[str]:
    fechas: list[str] = []
    for line in lines:
        for m in re.finditer(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", line):
            d, mo, y = m.groups()
            if 1 <= int(d) <= 31 and 1 <= int(mo) <= 12:
                fechas.append(f"{y}-{int(mo):02d}-{int(d):02d}")
    return list(dict.fromkeys(fechas))


def _fecha_archivo(nombre: str) -> str:
    m = re.search(r"(20\d{2})-(\d{2})-(\d{2})", nombre)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return ""


def _vendedor(lines: list[str]) -> str | None:
    for line in lines:
        if "Vendedor" in line and ":" in line:
            return line.split(":", 1)[-1].strip() or None
    return None


def _resolver_seccion(filas: list[dict], total_raw: list[str] | None) -> tuple[list[dict], list[str], list[str]]:
    """Resuelve los montos ambiguos de las filas contra el total impreso."""
    motivos: list[str] = []
    notas: list[str] = []

    def row_values(fila: dict, col: str) -> list[float] | None:
        return interpretaciones(str(fila[col]))

    valores: dict[str, list[list[float]]] = {c: [] for c in PAYMENT_COLUMNS}
    for c in PAYMENT_COLUMNS:
        for f in filas:
            valores[c].append(row_values(f, c) or [0.0])

    resueltos: dict[str, list[float]] = {c: [] for c in PAYMENT_COLUMNS}
    if total_raw:
        for idx, c in enumerate(PAYMENT_COLUMNS):
            if idx >= len(total_raw):
                resueltos[c] = [v[0] for v in valores[c]]
                suma = round(sum(v[0] for v in valores[c]), 2)
                if suma != 0.0:
                    motivos.append(f"{c}: filas {suma:.2f} sin posición en el total impreso")
                continue
            total_opts = interpretaciones(total_raw[idx])
            if not total_opts:
                motivos.append(f"{c}: total impreso ilegible ({total_raw[idx]})")
                resueltos[c] = [v[0] for v in valores[c]]
                continue
            if total_opts and abs(total_opts[0]) < 0.005:
                valores[c] = [v + [0.0] if max(v) < 10.0 else v for v in valores[c]]
            prod = 1
            for opc in valores[c]:
                prod *= len(opc)
                if prod > 2_000_000:
                    prod = 0
                    break
            if prod:
                combos = itertools.product(*valores[c])
            else:
                combos = [tuple(opc[0] for opc in valores[c])]
            target = total_opts[0]
            mejor = None
            for combo in combos:
                suma = round(sum(combo), 2)
                for t in total_opts:
                    if abs(suma - t) < 0.01:
                        mejor, target = combo, t
                        break
                if mejor is not None:
                    break
            if mejor is None:
                mejor = tuple(v[0] for v in valores[c])
                suma = round(sum(mejor), 2)
                if abs(suma - target) <= 1.00:
                    notas.append(f"{c}: error OCR leve ({suma:.2f} vs total {target:.2f})")
                else:
                    motivos.append(f"{c}: filas {suma:.2f} vs total impreso {target:.2f}")
            resueltos[c] = list(mejor)
    else:
        for c in PAYMENT_COLUMNS:
            motivos.append(f"{c}: sin total impreso en la sección")
            resueltos[c] = [v[0] for v in valores[c]]

    filas_out = []
    for i, f in enumerate(filas):
        filas_out.append({
            "documento": f["documento"],
            "cliente": f["cliente"],
            "efectivo": round(resueltos["efectivo"][i], 2),
            "transferencia_bancaria": round(resueltos["transferencia_bancaria"][i], 2),
            "cupon": round(resueltos["cupon"][i], 2),
        })
    return filas_out, motivos, notas


def _estructura_base(archivo: str, motivos: list[str]) -> dict:
    return {
        "archivo": archivo,
        "error": "; ".join(motivos),
        "fecha": None,
        "vendedor": None,
        "n_filas": 0,
        "filas": [],
        "suma_filas": {"efectivo": 0.0, "transferencia_bancaria": 0.0, "cupon": 0.0},
        "totales_impresos": None,
        "estado": "ERROR",
        "motivos": motivos,
        "notas": [],
    }


def _sumar(filas: list[dict]) -> dict:
    suma = {c: 0.0 for c in PAYMENT_COLUMNS}
    for f in filas:
        for c in PAYMENT_COLUMNS:
            suma[c] += f.get(c, 0.0)
    return {c: round(v, 2) for c, v in suma.items()}


def procesar_imagen(image: Path) -> dict:
    try:
        lineas = _text(image)
    except Exception as e:  # noqa: BLE001
        return _estructura_base(image.name, [str(e)])
    docs6 = _docs6(image)

    def segmentar(lines: list[str], doc_src: list[str]) -> tuple[list[dict], dict]:
        secciones_loc: list[dict] = []
        grupo: list[dict | tuple[int, str]] = []
        contador = 0
        total_grupo: list[str] | None = None
        fechas_tmp: list[str] = []
        vendedor_tmp: str | None = None
        for line in lines:
            fechas_tmp.extend(_fecha([line]))
            v = _vendedor([line])
            if v:
                vendedor_tmp = v
            fila = _fila_pago(line)
            if fila:
                grupo.append(fila)
                contador += 1
                continue
            if _es_fila_posible(line):
                grupo.append((contador, line))
                contador += 1
                continue
            total = _fila_total(line)
            if total is not None and grupo:
                secciones_loc.append({"filas": grupo, "total_linea": line, "totales_raw": total})
                grupo = []
                continue
            if total is not None and not grupo and line.strip():
                total_grupo = total
                continue
        if grupo or total_grupo:
            secciones_loc.append({"filas": grupo, "total_linea": None, "totales_raw": total_grupo})

        for s in secciones_loc:
            nuevas: list[dict] = []
            for item in s["filas"]:
                if isinstance(item, dict):
                    nuevas.append(item)
                else:
                    idx, linea = item
                    doc = doc_src[idx] if doc_src and idx < len(doc_src) else None
                    cand = _fila_pago(linea, doc) if doc else None
                    if cand:
                        nuevas.append(cand)
            s["filas"] = nuevas
        return secciones_loc, {"fechas": fechas_tmp, "vendedor": vendedor_tmp}

    secciones, ctx = segmentar(lineas, docs6)
    if not secciones or not any(s["filas"] for s in secciones):
        try:
            lineas6 = _text(image, "6")
        except Exception:  # noqa: BLE001
            lineas6 = []
        secciones, ctx = segmentar(lineas6, [])
        if not secciones or not any(s["filas"] for s in secciones):
            return _estructura_base(image.name, ["No se encontraron filas de pago (PAG-) en la captura"])

    fechas_ocr = ctx["fechas"]
    vendedor = ctx["vendedor"]
    motivos: list[str] = []
    fecha = _fecha_archivo(image.name)
    if not fecha:
        fecha = fechas_ocr[0] if fechas_ocr else None
        if not fecha:
            motivos.append("No se identifico fecha")
    if not vendedor:
        motivos.append("No se identifico vendedor")

    filas_totales: list[dict] = []
    docs: list[str] = []
    notas: list[str] = []
    for s in secciones:
        filas_resueltas, mot, nts = _resolver_seccion(s["filas"], s["totales_raw"])
        motivos.extend(mot)
        notas.extend(nts)
        for f in filas_resueltas:
            docs.append(f["documento"])
            if not f["cliente"]:
                motivos.append(f"Fila {f['documento']}: cliente vacio")
        filas_totales.extend(filas_resueltas)

    dups = sorted({d for d in docs if docs.count(d) > 1})
    if dups:
        motivos.append(f"Docs duplicados: {', '.join(dups[:5])}")

    ultimo_total = None
    for s in reversed(secciones):
        if s["totales_raw"]:
            opts = [interpretaciones(t) for t in s["totales_raw"]]
            ultimo_total = [o[0] if o else 0.0 for o in opts]
            break

    estado = "VERIFICADO" if not motivos else "REVISAR"
    return {
        "archivo": image.name,
        "fecha": fecha,
        "fechas_ocr": fechas_ocr,
        "vendedor": vendedor,
        "n_filas": len(filas_totales),
        "filas": filas_totales,
        "suma_filas": _sumar(filas_totales),
        "totales_impresos": ultimo_total,
        "estado": estado,
        "motivos": motivos,
        "notas": notas,
    }


def _normalizar_totales(raw: list[float] | None) -> list[float] | None:
    if not raw:
        return None
    out = [round(v, 2) for v in raw]
    while len(out) < 3:
        out.append(0.0)
    return out[:3]


def _totales_con_psm6(img: Path) -> list[float] | None:
    """Reintento OCR (psm 6): busca la fila de sumatoria al pie de la captura."""
    try:
        lineas = _text(img, "6")
    except Exception:  # noqa: BLE001
        return None
    ETIQUETAS = {"TOTAL", "TOTALES", "TOTALA", "TOTALS", "SUMA", "GENERAL"}
    candidatos: list[list[float]] = []
    ultima_fila_pago = -1
    for i, ln in enumerate(lineas):
        if re.search(r"PAG-?\d{7,12}", ln, re.IGNORECASE):
            ultima_fila_pago = i
    for i, ln in enumerate(lineas):
        if i <= ultima_fila_pago:
            continue
        if re.search(r"PAG-?\d{7,12}", ln, re.IGNORECASE):
            continue
        toks = [w.strip(" |") for w in ln.split()]
        if not toks:
            continue
        numericos = [w for w in toks if NUM_RE.match(w)]
        if len(numericos) == 4 and "." not in numericos[0] and "," not in numericos[0]:
            numericos = numericos[1:]
        if len(numericos) not in (2, 3):
            continue
        primero_no_num = next((t for t in toks if not NUM_RE.match(t)), None)
        if (
            primero_no_num
            and len(primero_no_num) >= 2
            and primero_no_num.upper() not in ETIQUETAS
        ):
            continue
        vals: list[float] = []
        for n in numericos:
            opciones = interpretaciones(n)
            if not opciones:
                vals = []
                break
            vals.append(opciones[0])
        if not vals:
            continue
        while len(vals) < 3:
            vals.append(0.0)
        candidatos.append(vals[:3])
    return candidatos[-1] if candidatos else None


def _alinear_totales(totales: list[float], suma_filas: dict) -> tuple[float, list[float]]:
    mejor_diff = float("inf")
    mejor = list(totales)
    for perm in itertools.permutations(range(3)):
        candidato = [totales[perm[0]], totales[perm[1]], totales[perm[2]]]
        diff = sum(
            abs(round(candidato[i], 2) - round(suma_filas.get(c, 0.0), 2))
            for i, c in enumerate(PAYMENT_COLUMNS)
        )
        if diff < mejor_diff:
            mejor_diff = diff
            mejor = candidato
    return round(mejor_diff, 2), mejor


def procesar_captura(img: Path, mes: str) -> dict:
    r = procesar_imagen(img)
    r["mes"] = mes
    r["ruta_imagen"] = str(img)

    totales_impresos = _normalizar_totales(r.get("totales_impresos"))
    if r["estado"] != "VERIFICADO" and (
        totales_impresos is None or all(v == 0.0 for v in totales_impresos)
    ):
        recuperado = _totales_con_psm6(img)
        if recuperado is not None:
            totales_impresos = recuperado
            r["notas"] = (r.get("notas") or []) + ["total recuperado con OCR psm 6"]
            sumf = r["suma_filas"]
            diff = sum(
                abs(round(sumf.get(c, 0.0), 2) - round(recuperado[i], 2))
                for i, c in enumerate(PAYMENT_COLUMNS)
            )
            if diff < 0.03:
                r["estado"] = "VERIFICADO"
                r["motivos"] = []
            else:
                r["motivos"] = (r.get("motivos") or []) + [
                    f"filas no concilian con total recuperado (diff {diff:.2f})"
                ]
    if totales_impresos is not None and r["estado"] != "VERIFICADO":
        diff_mejor, alineado = _alinear_totales(totales_impresos, r["suma_filas"])
        if diff_mejor < 0.03:
            totales_impresos = alineado
            r["notas"] = (r.get("notas") or []) + [
                "columnas del total alineadas con las filas"
            ]

    usa_solo_total = False
    total_dia: list[float] | None = None
    if r["estado"] == "VERIFICADO":
        total_dia = _normalizar_totales(
            [r["suma_filas"].get(c, 0.0) for c in PAYMENT_COLUMNS]
        )
    elif totales_impresos is not None:
        usa_solo_total = True
        total_dia = totales_impresos
    r["totales_impresos"] = totales_impresos
    r["usa_solo_total"] = usa_solo_total
    r["total_dia"] = total_dia
    return r


def _hash_archivo(img: Path) -> str:
    """SHA-256 del archivo para el caché incremental (solo cambia si el archivo cambió)."""
    import hashlib

    h = hashlib.sha256()
    with open(img, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


CACHE_VERSION = "1"  # subir si cambia la lógica de OCR (invalida el caché viejo)


def procesar_todo(base_pagos: Path, out_dir: Path | None = None) -> list[dict]:
    """Procesa las capturas con caché incremental por hash.

    Las imágenes cuyo hash ya está en data/pagos_cache.json se reutilizan
    (sin re-OCR); solo las nuevas/cambiadas se procesan con Tesseract.
    """
    cache_path = (out_dir or Path(__file__).resolve().parent.parent / "data") / "pagos_cache.json"
    cache: dict[str, dict] = {}
    if cache_path.is_file():
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            if data.get("version") == CACHE_VERSION:
                cache = data.get("capturas", {})
        except Exception:
            cache = {}

    capturas: list[dict] = []
    nuevas = 0
    for mes_dir in sorted(base_pagos.glob("2026-*")):
        if not mes_dir.is_dir():
            continue
        imagenes = sorted(
            list(mes_dir.glob("*.jpeg"))
            + list(mes_dir.glob("*.jpg"))
            + list(mes_dir.glob("*.png"))
        )
        for img in imagenes:
            h = _hash_archivo(img)
            if h in cache:
                r = dict(cache[h])
                r["mes"] = mes_dir.name
                r["ruta_imagen"] = str(img)
                r["sha256"] = h
                capturas.append(r)
                continue
            r = procesar_captura(img, mes_dir.name)
            r["sha256"] = h
            # solo cachear lo serializable; filas pueden tener listas de dicts
            cache[h] = {k: v for k, v in r.items() if k not in ("mes", "ruta_imagen")}
            capturas.append(r)
            nuevas += 1

    if nuevas:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache_path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps({"version": CACHE_VERSION, "capturas": cache}, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(cache_path)
        print(f"   [cache] {nuevas} captura(s) nueva(s) procesadas; resto desde caché")
    return capturas


def escribir_resultados(capturas: list[dict], out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)

    # Guardia anti-duplicados: con la ingesta manual puede copiarse dos veces
    # la misma captura (mismo contenido, distinto nombre) y el crédito se
    # contaría doble. Se avisa y se registra; la eliminación es manual.
    vistos_sha: dict[str, str] = {}
    duplicadas: list[dict] = []
    for c in sorted(capturas, key=lambda x: x["archivo"]):
        sha = c.get("sha256")
        if not sha:
            continue
        if sha in vistos_sha:
            duplicadas.append({"archivo": c["archivo"], "copia_de": vistos_sha[sha]})
            print(
                f"  ⚠ Captura duplicada: {c['archivo']} es idéntica a "
                f"{vistos_sha[sha]} — eliminar una copia y re-correr."
            )
        else:
            vistos_sha[sha] = c["archivo"]

    with open(out_dir / "pagos_diarios.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            ["mes", "fecha", "archivo", "efectivo", "transferencia_bancaria",
             "cupon", "total_dia", "estado", "usa_solo_total"]
        )
        for c in sorted(capturas, key=lambda x: (str(x.get("fecha")), x["archivo"])):
            t = c["total_dia"] or [0.0, 0.0, 0.0]
            estado_csv = "SOLO_TOTAL" if c["usa_solo_total"] else c["estado"]
            w.writerow(
                [c["mes"], c.get("fecha"), c["archivo"], t[0], t[1], t[2],
                 round(sum(t), 2), estado_csv, c["usa_solo_total"]]
            )

    with open(out_dir / "pagos_detalle.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            ["mes", "archivo", "fecha", "documento", "cliente", "efectivo",
             "transferencia_bancaria", "cupon", "total_pago", "estado_captura",
             "ruta_imagen"]
        )
        for c in capturas:
            estado_csv = "SOLO_TOTAL" if c["usa_solo_total"] else c["estado"]
            for f in c.get("filas", []):
                w.writerow(
                    [c["mes"], c["archivo"], c.get("fecha"), f["documento"], f["cliente"],
                     f["efectivo"], f["transferencia_bancaria"], f["cupon"],
                     round(f["efectivo"] + f["transferencia_bancaria"] + f["cupon"], 2),
                     estado_csv, c.get("ruta_imagen", "")]
                )

    credito_mes: dict[str, float] = {}
    for c in capturas:
        if c["total_dia"] is not None:
            credito_mes[c["mes"]] = round(
                credito_mes.get(c["mes"], 0.0) + sum(c["total_dia"]), 2
            )
    resumen = {
        "capturas_totales": len(capturas),
        "capturas_verificadas": sum(1 for c in capturas if c["estado"] == "VERIFICADO"),
        "capturas_solo_total": [c["archivo"] for c in capturas if c["usa_solo_total"]],
        "capturas_sin_total": [c["archivo"] for c in capturas if c["total_dia"] is None],
        "capturas_error": [c["archivo"] for c in capturas if c["estado"] == "ERROR"],
        "capturas_duplicadas": duplicadas,
        "pagos_filas_extraidas": sum(c["n_filas"] for c in capturas),
        "credito_total_dia_usd": round(sum(credito_mes.values()), 2),
        "credito_por_mes_usd": {m: credito_mes[m] for m in sorted(credito_mes)},
    }
    return resumen


if __name__ == "__main__":
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\Users\Marcos\Mi unidad\FYS\Pagos_procesados")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent / "data"
    capturas = procesar_todo(base, out)
    resumen = escribir_resultados(capturas, out)
    print(json.dumps(resumen, ensure_ascii=False, indent=1))
