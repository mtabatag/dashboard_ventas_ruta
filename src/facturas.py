"""Extractor mínimo y validado de facturas FYS (TABATA MARCOS).

Por cada factura extrae únicamente:
  - FECHA DE EMISION
  - DOCUMENTO
  - NOMBRE DE CLIENTE
  - TOTAL OPERACION (USD)
  - CANTIDAD DE CAJAS (sumatoria de cantidades que el propio reporte
    imprime debajo de cada factura, en la columna Cantidad)

Validación por PDF: se lee el documento completo (el monto total general en
USD a veces solo está en la última hoja) y se exige que
    suma(total_operacion de cada factura) == total_general_pdf
Cada PDF se clasifica OK / DESVIADO / SIN_TOTAL / ERROR.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

RE_DOC = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+"
    r"(?:(\d{8,10})\s+([A-Z/]+)|([A-Z/]+)\s+(\d{8,10}))\s+"
    r"([A-Z0-9\-]+)\s+(.+?)\s+([\d.,]+)$"
)
RE_NUM = re.compile(r"^\d{1,3}(?:[.,]\d{3})*[.,]\d{2}$")
RE_CHECK = re.compile(r"^\d{2}/\d{2}/\d{4}$")


def parse_amount(s: str) -> float:
    """Convierte '1.080,03' o '1,940.65' o '123.45' a float."""
    s = s.strip()
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            return float(s.replace(".", "").replace(",", "."))
        return float(s.replace(",", ""))
    if "," in s:
        return float(s.replace(",", "."))
    return float(s)


def num_tokens(text: str) -> list[str]:
    return [t for t in text.split() if RE_NUM.match(t)]


def solo_numeros(text: str) -> bool:
    toks = text.split()
    return bool(toks) and all(RE_NUM.match(t) for t in toks)


@dataclass
class FacturaResumen:
    fecha_emision: str | None
    nro_documento: str
    tipo_doc: str | None
    rif_cliente: str | None
    nombre_cliente: str | None
    total_operacion: float | None
    cajas: float | None


def extract_pdf_text(pdf_path: Path) -> list[str]:
    import pdfplumber

    lineas: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.split("\n"):
                line = line.strip()
                if line:
                    lineas.append(line)
    return lineas


def parse_documento(lineas: list[str], filename: str) -> dict:
    """Recorre las líneas del PDF y extrae las facturas + el total general."""
    facturas: list[FacturaResumen] = []
    bloque = None
    total_general: float | None = None
    total_general_linea: str | None = None

    for linea in lineas:
        m = RE_DOC.match(linea)
        if m:
            if bloque is not None:
                facturas.append(_factura_desde_bloque(bloque))
            fecha, nro_a, tipo_a, tipo_b, nro_b, rif, nombre, total_s = m.groups()
            try:
                total = parse_amount(total_s)
            except ValueError:
                total = None
            bloque = {
                "fecha": fecha if RE_CHECK.match(fecha) else None,
                "nro": nro_a or nro_b,
                "tipo": (tipo_a or tipo_b).upper(),
                "rif": rif,
                "nombre": nombre.strip(),
                "total": total,
                "cajas": None,
                "hay_sumatoria": False,
            }
            continue

        if bloque is not None:
            if solo_numeros(linea):
                toks = num_tokens(linea)
                if len(toks) == 2:
                    # sumatoria de cajas (última fila de solo 2 números del bloque)
                    try:
                        bloque["cajas"] = parse_amount(toks[0])
                        bloque["hay_sumatoria"] = True
                    except ValueError:
                        pass
                elif len(toks) == 1 and bloque["hay_sumatoria"]:
                    # número suelto tras la sumatoria => candidato a total general
                    try:
                        total_general = parse_amount(toks[0])
                        total_general_linea = linea
                    except ValueError:
                        pass
                continue
            # las líneas de detalle (con texto) se ignoran
            continue

        # fuera de cualquier factura: candidato a total general
        if solo_numeros(linea) and len(num_tokens(linea)) == 1:
            try:
                total_general = parse_amount(num_tokens(linea)[0])
                total_general_linea = linea
            except ValueError:
                pass

    if bloque is not None:
        facturas.append(_factura_desde_bloque(bloque))

    suma = round(sum(f.total_operacion or 0 for f in facturas), 2)
    if total_general is None:
        estado = "SIN_TOTAL"
    else:
        estado = "OK" if abs(round(total_general, 2) - suma) < 0.01 else "DESVIADO"

    return {
        "archivo": filename,
        "facturas": [
            {
                "fecha_emision": f.fecha_emision,
                "nro_documento": f.nro_documento,
                "tipo_doc": f.tipo_doc,
                "rif_cliente": f.rif_cliente,
                "nombre_cliente": f.nombre_cliente,
                "total_operacion": f.total_operacion,
                "cajas": f.cajas,
            }
            for f in facturas
        ],
        "n_facturas": len(facturas),
        "suma_extraida": suma,
        "total_general_pdf": total_general,
        "total_general_linea": total_general_linea,
        "validacion": estado,
        "diff": round((total_general or 0) - suma, 2),
    }


def _factura_desde_bloque(b: dict) -> FacturaResumen:
    return FacturaResumen(
        fecha_emision=b["fecha"],
        nro_documento=b["nro"],
        tipo_doc=b["tipo"],
        rif_cliente=b["rif"],
        nombre_cliente=b["nombre"],
        total_operacion=b["total"],
        cajas=b["cajas"],
    )


def procesar_pdf(pdf_path: Path) -> dict:
    try:
        lineas = extract_pdf_text(pdf_path)
        res = parse_documento(lineas, pdf_path.name)
    except Exception as e:  # noqa: BLE001
        res = {
            "archivo": pdf_path.name,
            "error": str(e),
            "facturas": [],
            "n_facturas": 0,
            "suma_extraida": 0.0,
            "total_general_pdf": None,
            "validacion": "ERROR",
            "diff": None,
        }
    return res


def _es_reporte_ventas(pdf: Path) -> bool:
    nombre = pdf.name.upper()
    # Se excluyen reportes que no son el listado diario de ventas
    # (CXC = cuentas por cobrar, MASTER = catálogo de clientes, etc.)
    return not (nombre.startswith("CXC") or "MASTER" in nombre)


def procesar_carpeta(pdfs_dir: Path) -> list[dict]:
    return [
        procesar_pdf(pdf)
        for pdf in sorted(pdfs_dir.glob("*.pdf"))
        if _es_reporte_ventas(pdf)
    ]


def _hash_archivo(img: Path) -> str:
    """SHA-256 del archivo para el caché incremental (solo cambia si el archivo cambió)."""
    import hashlib

    h = hashlib.sha256()
    with open(img, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


FACTURAS_CACHE_VERSION = "1"  # subir si cambia la lógica de extracción


def procesar_todo(base_facturas: Path, out_dir: Path | None = None) -> list[dict]:
    """Procesa todas las carpetas 2026-* con caché incremental por hash.

    Los PDFs cuyo hash ya está en data/facturas_cache.json se reutilizan;
    solo los nuevos/cambiados se re-extraen con pdfplumber.
    """
    cache_path = (out_dir or Path(__file__).resolve().parent.parent / "data") / "facturas_cache.json"
    cache: dict[str, dict] = {}
    if cache_path.is_file():
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            if data.get("version") == FACTURAS_CACHE_VERSION:
                cache = data.get("pdfs", {})
        except Exception:
            cache = {}

    resultados: list[dict] = []
    nuevos = 0
    for mes_dir in sorted(base_facturas.glob("2026-*")):
        if not mes_dir.is_dir():
            continue
        for pdf in sorted(mes_dir.glob("*.pdf")):
            if not _es_reporte_ventas(pdf):
                continue
            h = _hash_archivo(pdf)
            if h in cache:
                r = dict(cache[h])
                r["mes"] = mes_dir.name
                r["ruta_pdf"] = str(pdf)
                resultados.append(r)
                continue
            r = procesar_pdf(pdf)
            r["mes"] = mes_dir.name
            r["ruta_pdf"] = str(pdf)
            # solo cachear lo serializable (sin mes/ruta que dependen de la corrida)
            cache[h] = {k: v for k, v in r.items() if k not in ("mes", "ruta_pdf")}
            resultados.append(r)
            nuevos += 1

    if nuevos:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache_path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps({"version": FACTURAS_CACHE_VERSION, "pdfs": cache}, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(cache_path)
        print(f"   [cache] {nuevos} PDF(s) nuevo(s) procesados; resto desde caché")
    return resultados


def escribir_resultados(resultados: list[dict], out_dir: Path) -> tuple[list[dict], dict]:
    """Escribe facturas.csv (5 campos) y validacion_facturas_por_pdf.csv."""
    out_dir.mkdir(parents=True, exist_ok=True)

    facturas = [
        {
            "fecha_emision": f["fecha_emision"],
            "documento": f["nro_documento"],
            "nombre_cliente": f["nombre_cliente"],
            "total_operacion": f["total_operacion"],
            "cajas": f["cajas"],
            "rif": f.get("rif_cliente") or "",
        }
        for r in resultados
        for f in r.get("facturas", [])
    ]

    # Deduplicación por (fecha, documento): un mismo número de documento es
    # UNA sola venta. La oficina a veces imprime la misma factura en dos
    # listados del mismo día (p. ej. 07-01-2026 doc 0000000128 INSIEME), y
    # cada listado la incluye en su total general — el checksum por PDF
    # sigue validando (refleja lo impreso), pero el total global no debe
    # contarla dos veces. Se conserva la primera aparición.
    vistos: dict[tuple, dict] = {}
    duplicados_eliminados: list[dict] = []
    for f in facturas:
        clave = (str(f["fecha_emision"]), str(f["documento"]))
        if clave in vistos:
            duplicados_eliminados.append(f)
            continue
        vistos[clave] = f
    facturas = list(vistos.values())
    if duplicados_eliminados:
        print(
            f"  ⚠ Deduplicadas {len(duplicados_eliminados)} factura(s) por "
            f"(fecha, documento): "
            + ", ".join(
                f"{d['documento']} {d['nombre_cliente']} {d['fecha_emision']}"
                for d in duplicados_eliminados
            )
        )
    def _clave_fecha(f: dict) -> tuple:
        try:
            d, m, y = str(f["fecha_emision"]).split("/")
            return (int(y), int(m), int(d), str(f["documento"]))
        except ValueError:
            return (9999, 99, 99, str(f["documento"]))

    facturas.sort(key=_clave_fecha)

    with open(out_dir / "facturas.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            ["fecha_emision", "documento", "nombre_cliente", "rif", "total_operacion", "cajas"]
        )
        for f in facturas:
            w.writerow(
                [
                    f["fecha_emision"],
                    f["documento"],
                    f["nombre_cliente"],
                    f["rif"],
                    f["total_operacion"],
                    f["cajas"],
                ]
            )

    # Mapeo único cliente -> RIF (para unir variantes de nombre en el dashboard)
    rif_unicos: dict[str, dict] = {}
    for f in facturas:
        clave_rif = re.sub(r"\D", "", f["rif"])
        clave_nombre = re.sub(r"[^A-Z0-9]", "", (f["nombre_cliente"] or "").upper())
        # conservar todas las variantes de nombre por RIF
        clave = f"{clave_rif}|{clave_nombre}" if clave_rif else clave_nombre
        if not clave:
            continue
        c = rif_unicos.setdefault(clave, {"rif": f["rif"], "nombre": f["nombre_cliente"], "ultima": ""})
        try:
            d, m, y = f["fecha_emision"].split("/")
            iso = f"{y}-{m}-{d}"
            if iso > c["ultima"]:
                c["ultima"] = iso
        except ValueError:
            pass
    with open(
        out_dir / "facturas_rif.csv", "w", encoding="utf-8-sig", newline=""
    ) as fh:
        w = csv.writer(fh)
        w.writerow(["rif", "nombre", "ultima_fecha"])
        for c in sorted(rif_unicos.values(), key=lambda x: x["nombre"].upper()):
            w.writerow([c["rif"], c["nombre"], c["ultima"]])

    with open(
        out_dir / "validacion_facturas_por_pdf.csv", "w", encoding="utf-8-sig", newline=""
    ) as fh:
        w = csv.writer(fh)
        w.writerow(
            ["mes", "archivo", "n_facturas", "suma_extraida", "total_general_pdf",
             "diff", "validacion", "ruta_pdf"]
        )
        for r in resultados:
            w.writerow(
                [r.get("mes"), r["archivo"], r["n_facturas"], r["suma_extraida"],
                 r["total_general_pdf"], r["diff"], r["validacion"], r.get("ruta_pdf", "")]
            )

    resumen = {
        "pdfs_procesados": len(resultados),
        "pdfs_ok": sum(1 for r in resultados if r["validacion"] == "OK"),
        "pdfs_desviados": [r["archivo"] for r in resultados if r["validacion"] == "DESVIADO"],
        "pdfs_sin_total": [r["archivo"] for r in resultados if r["validacion"] == "SIN_TOTAL"],
        "pdfs_error": [r["archivo"] for r in resultados if r.get("error")],
        "facturas_totales": len(facturas),
        "facturas_duplicadas_eliminadas": [
            {"fecha": d["fecha_emision"], "documento": d["documento"],
             "cliente": d["nombre_cliente"], "total_operacion": d["total_operacion"]}
            for d in duplicados_eliminados
        ],
        "monto_total_operacion_usd": round(
            sum(f["total_operacion"] or 0 for f in facturas), 2
        ),
        "cajas_totales": round(sum(f["cajas"] or 0 for f in facturas), 2),
    }
    return facturas, resumen


if __name__ == "__main__":
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\Users\Marcos\Mi unidad\FYS\Facturas")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent / "data"
    res = procesar_todo(base)
    _, resumen = escribir_resultados(res, out)
    print(json.dumps(resumen, ensure_ascii=False, indent=1))
