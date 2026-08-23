"""Capa adicional: líneas de producto por factura (sin precios ni totales).

Extrae de cada PDF, por cada factura ya validada, las líneas de producto con
SOLO:
  - CODIGO_PRODUCTO
  - NOMBRE_PRODUCTO
  - CANTIDAD (unidades/cajas según el reporte)

No se extraen precios ni totales de línea (fuente de los errores históricos).
La validación usa la capa ya validada: la suma de cantidades de las líneas de
una factura debe coincidir con las CAJAS de esa factura en data/facturas.csv
(que ya pasó el checksum del total general del PDF).

Salidas:
  data/factura_lineas.csv        una fila por línea de producto
  data/validacion_productos.csv  validación por factura (estado y cobertura)
  data/productos.csv             catálogo único de productos (codigo, nombre, marca)
  data/marcas.csv                catálogo de marcas EDITABLE (clave -> marca)
"""
from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

RE_DOC = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+"
    r"(?:(\d{8,10})\s+([A-Z/]+)|([A-Z/]+)\s+(\d{8,10}))\s+"
    r"([A-Z0-9\-]+)\s+(.+?)\s+([\d.,]+)$"
)
RE_CODIGO = re.compile(r"^[A-Z0-9][A-Z0-9-]{1,13}$")  # admite guiones (20007-, CV1498-)
RE_CANTIDAD = re.compile(r"^\d+[.,]\d{1,2}$")
# Token numérico del sufijo final: cantidad/precio llevan decimales, el total
# de línea puede ser entero (p. ej. "423") o con 1-2 decimales ("58,1", "21,01").
RE_NUM_FINAL = re.compile(r"^\d+(?:[.,]\d{1,2})?$")
RE_CHECK = re.compile(r"^\d{2}/\d{2}/\d{4}$")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s or "").upper())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_cantidad(s: str) -> float:
    return float(s.replace(",", "."))


def parse_linea_producto(linea: str) -> dict | None:
    toks = linea.split()
    if not toks or RE_DOC.match(linea):
        return None
    if not RE_CODIGO.match(toks[0]):
        return None
    # La cantidad es el PRIMER token del sufijo numérico final de la línea.
    # El sufijo (2-3 tokens: cantidad, precio, [total]) admite totales enteros
    # ("423") además de decimales ("21,01"); la cantidad siempre lleva
    # decimales. Esto evita confundir tamaños del nombre ("GALON 3.7 LT")
    # con la cantidad real.
    idx_cant = None
    for i in range(1, len(toks)):
        if RE_CANTIDAD.match(toks[i]) and all(
            RE_NUM_FINAL.match(t) for t in toks[i:]
        ):
            idx_cant = i
            break
    if idx_cant is None:
        return None
    nombre = re.sub(r"\s*\(E\)\s*$", "", " ".join(toks[1:idx_cant])).strip()
    if not nombre:
        return None
    return {
        "codigo": toks[0],
        "nombre": nombre,
        "cantidad": parse_cantidad(toks[idx_cant]),
    }


def procesar_pdf(pdf_path: Path, cajas_por_factura: dict,
                 lineas_cache: dict[str, dict] | None = None) -> dict:
    """Extrae las líneas de producto del PDF; usa caché por hash si está disponible.

    lineas_cache: dict hash_pdf -> {"lineas_raw": {clave: [lineas]}} con las
    líneas extraídas (sin validar) para no re-leer los PDFs ya procesados.
    Devuelve el resultado YA validado contra cajas_por_factura.
    """
    import pdfplumber

    h = _hash_archivo(pdf_path)
    if lineas_cache is not None and h in lineas_cache:
        facturas = lineas_cache[h]["lineas_raw"]
    else:
        facturas: dict[str, dict] = {}  # clave (fecha|documento) -> lineas
        actual = None
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                for linea in (page.extract_text() or "").split("\n"):
                    linea = linea.strip()
                    if not linea:
                        continue
                    m = RE_DOC.match(linea)
                    if m:
                        if actual is not None:
                            facturas[actual["clave"]] = actual
                        fecha = m.group(1)
                        doc = m.group(2) or m.group(5)
                        nombre_cliente = m.group(7).strip()
                        if not RE_CHECK.match(fecha):
                            fecha = ""
                        actual = {
                            "clave": f"{fecha}|{doc}",
                            "fecha": fecha,
                            "documento": doc,
                            "cliente": nombre_cliente,
                            "lineas": [],
                        }
                        continue
                    if actual is not None:
                        p = parse_linea_producto(linea)
                        if p:
                            actual["lineas"].append(p)
        if actual is not None:
            facturas[actual["clave"]] = actual
        if lineas_cache is not None:
            lineas_cache[h] = {"lineas_raw": facturas}

    resultado = []
    for f in facturas.values():
        cajas_esp = cajas_por_factura.get(f["clave"])
        suma = round(sum(l["cantidad"] for l in f["lineas"]), 2)
        if cajas_esp is None:
            estado = "SIN_REFERENCIA"
            diff = None
        elif abs(suma - cajas_esp) <= 0.10:
            estado = "VALIDADO"
            diff = round(suma - cajas_esp, 2)
        else:
            estado = "PENDIENTE"
            diff = round(suma - cajas_esp, 2)
        resultado.append(
            {
                "archivo": pdf_path.name,
                "fecha": f["fecha"],
                "documento": f["documento"],
                "cliente": f["cliente"],
                "n_lineas": len(f["lineas"]),
                "suma_cantidad": suma,
                "cajas_esperada": cajas_esp,
                "diff": diff,
                "estado": estado,
                "lineas": f["lineas"],
            }
        )
    return resultado


def cargar_cajas() -> dict[str, float]:
    mapa: dict[str, float] = {}
    with open(DATA / "facturas.csv", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            clave = f"{r['fecha_emision']}|{r['documento']}"
            try:
                mapa[clave] = round(float(r["cajas"] or 0), 2)
            except ValueError:
                pass
    return mapa


def escribir_resultados(resultados: list[dict], out: Path):
    out.mkdir(parents=True, exist_ok=True)

    with open(out / "factura_lineas.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            ["fecha", "documento", "cliente", "codigo_producto",
             "nombre_producto", "cantidad", "estado_linea"]
        )
        for r in resultados:
            estado = r["estado"]
            for l in r["lineas"]:
                w.writerow(
                    [r["fecha"], r["documento"], r["cliente"],
                     l["codigo"], l["nombre"], l["cantidad"], estado]
                )

    with open(out / "validacion_productos.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            ["archivo", "fecha", "documento", "cliente", "n_lineas",
             "suma_cantidad", "cajas_esperada", "diff", "estado"]
        )
        for r in resultados:
            w.writerow(
                [r["archivo"], r["fecha"], r["documento"], r["cliente"],
                 r["n_lineas"], r["suma_cantidad"], r["cajas_esperada"],
                 r["diff"], r["estado"]]
            )

    # Catálogo de productos (código único -> nombre + marca)
    productos: dict[str, dict] = {}
    for r in resultados:
        if r["estado"] != "VALIDADO":
            continue
        for l in r["lineas"]:
            p = productos.setdefault(
                l["codigo"], {"codigo": l["codigo"], "nombre": l["nombre"], "n": 0}
            )
            p["n"] += 1
    marcas = cargar_marcas(out)
    for p in productos.values():
        p["marca"] = marca_de_producto(p["codigo"], p["nombre"], marcas)
    with open(out / "productos.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["codigo", "nombre", "marca", "lineas"])
        for p in sorted(productos.values(), key=lambda x: x["codigo"]):
            w.writerow([p["codigo"], p["nombre"], p["marca"], p["n"]])

    return productos


def clave_marca(nombre: str) -> str:
    toks = norm(nombre).split()
    if not toks:
        return ""
    if len(toks) >= 2 and toks[1] in ("DE", "DEL", "LA", "EL", "Y", "SAN", "SANTA"):
        return " ".join(toks[:2])
    return toks[0]


def cargar_marcas(out: Path) -> dict[str, str]:
    marcas: dict[str, str] = {}
    path = out / "marcas.csv"
    if path.is_file():
        with open(path, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                if r["clave"]:
                    marcas[r["clave"].strip().upper()] = r["marca"].strip()
    return marcas


def marca_de_producto(codigo: str, nombre: str, marcas: dict[str, str]) -> str:
    clave = clave_marca(nombre)
    if clave in marcas:
        return marcas[clave]
    return clave


def seed_marcas(productos: dict, out: Path):
    """Crea/actualiza marcas.csv editable con las claves detectadas."""
    contador: Counter = Counter()
    for p in productos.values():
        contador[clave_marca(p["nombre"])] += 1
    path = out / "marcas.csv"
    existentes = {}
    if path.is_file():
        with open(path, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                existentes[r["clave"].strip().upper()] = r["marca"].strip()
    filas = []
    for clave, n in contador.most_common():
        filas.append(
            {"clave": clave, "marca": existentes.get(clave, clave), "productos": n}
        )
    filas.sort(key=lambda x: x["clave"])
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["clave", "marca", "productos"])
        w.writeheader()
        w.writerows(filas)


def _hash_archivo(img: Path) -> str:
    """SHA-256 del archivo para el caché incremental (solo cambia si el archivo cambió)."""
    import hashlib

    h = hashlib.sha256()
    with open(img, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


PRODUCTOS_CACHE_VERSION = "1"  # subir si cambia el parser de líneas


def main(base_facturas: Path, out: Path):
    cajas = cargar_cajas()
    resultados = []
    # Caché de líneas extraídas por hash de PDF (no re-leer PDFs ya procesados)
    cache_path = out / "productos_cache.json"
    lineas_cache: dict[str, dict] = {}
    if cache_path.is_file():
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            if data.get("version") == PRODUCTOS_CACHE_VERSION:
                lineas_cache = data.get("pdfs", {})
        except Exception:
            lineas_cache = {}
    nuevos = 0
    for mes_dir in sorted(base_facturas.glob("2026-*")):
        if not mes_dir.is_dir():
            continue
        for pdf in sorted(mes_dir.glob("*.pdf")):
            nombre = pdf.name.upper()
            if nombre.startswith("CXC") or "MASTER" in nombre:
                continue
            h = _hash_archivo(pdf)
            if h not in lineas_cache:
                nuevos += 1
            resultados.extend(procesar_pdf(pdf, cajas, lineas_cache))
    if nuevos:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache_path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps({"version": PRODUCTOS_CACHE_VERSION, "pdfs": lineas_cache},
                       ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(cache_path)
        print(f"   [cache] {nuevos} PDF(s) nuevo(s) procesados; resto desde caché")

    productos = escribir_resultados(resultados, out)
    seed_marcas(productos, out)

    total = len(resultados)
    ok = sum(1 for r in resultados if r["estado"] == "VALIDADO")
    pend = sum(1 for r in resultados if r["estado"] == "PENDIENTE")
    sinref = sum(1 for r in resultados if r["estado"] == "SIN_REFERENCIA")
    lineas_ok = sum(r["n_lineas"] for r in resultados if r["estado"] == "VALIDADO")
    print(f"Facturas con detalle: {total} | VALIDADO: {ok} ({ok/total*100:.1f}%) | "
          f"PENDIENTE: {pend} | SIN_REFERENCIA: {sinref}")
    print(f"Líneas de producto en facturas validadas: {lineas_ok}")
    print(f"Productos únicos: {len(productos)}")
    print(f"Salidas en: {out}")


if __name__ == "__main__":
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "Facturas"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else DATA
    main(base, out)
