"""Capa de despachos FYS: chofer y fecha de salida por factura.

Cada PDF de facturación tiene en el encabezado (líneas 1-4 de la página 1) el
chofer y la fecha de salida del despacho, en 3 formatos detectados:

  A) "CHOFER HEINNER G. SALIDA JUEVES 20-08-26"     (fecha explícita junto al chofer)
  B) "CHOFER WILLIANS T." + "17/8/2026 01:56 p. m. 18-08-26"  (fecha al final de
     la línea de fecha/hora de impresión)
  C) "CHOFER CARLOS M. FACTURACION VIERNES SALIDA LUNES" +
     "1 de 2 15/5/2026 4:47 p. m. 18-05-26"          (ídem, con prefijo "N de M")

La asociación factura → chofer/salida se hace por (fecha_emision, documento)
re-extraído de cada PDF, de modo que dos PDFs del mismo día con distinto
chofer (caso real: 07-01-26 y 07-01-26 2) quedan bien asignados.

Salida: data/despachos.csv con
  fecha_facturacion, documento, nombre_cliente, rif, total_operacion, cajas,
  chofer, fecha_salida, dias_espera
Los nombres de chofer se normalizan con data/choferes.csv (editable):
primera columna = alias encontrado, segunda = nombre canónico.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

sys.path.insert(0, str(ROOT / "src"))
from facturas import RE_DOC  # noqa: E402

RE_CHOFER = re.compile(
    r"CHOFER\s+(?P<nombre>.*?)(?:\s+FACTURACION\b|\s+SALIDA\b|\s*$)"
)
RE_SALIDA_EN_CHOFER = re.compile(r"SALIDA\s+[A-ZÁÉÍÓÚÑ]+\s+(?P<fecha>\d{1,2}-\d{2}-\d{2})$")
# Línea de fecha/hora de impresión: "... 20/8/2026 04:18 p. m. 21-08-26"
RE_LINEA_IMPRESION = re.compile(
    r"^(?:\d+\s+de\s+\d+\s+)?\d{1,2}/\d{1,2}/\d{4}\s+.*\s(?P<fecha>\d{1,2}-\d{2}-\d{2})$"
)
# Formato D: "SALIDA MIERCOLES 27-05 26/5/2026 27-05-26" (salida con fecha corta + impresión)
RE_SALIDA_EXTENDIDA = re.compile(
    r"SALIDA\s+\w+\s+(?:\d{1,2}-\d{2})?\s*\d{1,2}/\d{1,2}/\d{4}.*\s(?P<fecha>\d{1,2}-\d{2}-\d{2})$"
)
RE_FECHA_EXT = re.compile(r"\b(\d{1,2})-(\d{2})-(\d{2})$")


def normalizar_fecha(f: str) -> str:
    """'18-08-26' -> '18/08/2026'."""
    m = re.match(r"^(\d{1,2})-(\d{2})-(\d{2})$", f.strip())
    if not m:
        return ""
    d, mo, y = m.groups()
    return f"{int(d):02d}/{int(mo):02d}/20{y}"


def cargar_normalizacion() -> dict[str, str]:
    """Alias -> nombre canónico desde data/choferes.csv (editable)."""
    out: dict[str, str] = {}
    p = DATA / "choferes.csv"
    if p.is_file():
        with open(p, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                alias = (row.get("alias") or "").strip().upper()
                canon = (row.get("canonico") or "").strip()
                if alias and canon:
                    out[alias] = canon
    return out


def guardar_normalizacion(nuevos: dict[str, str]) -> None:
    """Agrega alias nuevos sin pisar los existentes."""
    actual = cargar_normalizacion()
    actual.update({k: v for k, v in nuevos.items() if k not in actual})
    with open(DATA / "choferes.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["alias", "canonico"])
        for alias, canon in sorted(actual.items()):
            w.writerow([alias, canon])


def extraer_encabezado_de_texto(lineas: list[str]) -> tuple[str, str]:
    """Devuelve (chofer_bruto, fecha_salida) desde las primeras líneas del PDF."""
    cabeza = [l.strip() for l in lineas[:6] if l.strip()]

    chofer_bruto = ""
    fecha_salida = ""
    for l in cabeza:
        # Formato A: chofer con SALIDA + fecha explícita
        m = RE_SALIDA_EN_CHOFER.search(l)
        if m and "CHOFER" in l.upper():
            fecha_salida = normalizar_fecha(m.group("fecha"))
        # Nombre del chofer
        m2 = RE_CHOFER.search(l)
        if m2 and m2.group("nombre") and m2.group("nombre").strip(" ."):
            chofer_bruto = m2.group("nombre").strip(" .")
    # Formato B/C: fecha de salida al final de la línea de impresión
    if not fecha_salida:
        for l in cabeza:
            m = RE_LINEA_IMPRESION.search(l) or RE_SALIDA_EXTENDIDA.search(l)
            if m:
                fecha_salida = normalizar_fecha(m.group("fecha"))
                break
    return chofer_bruto, fecha_salida


def _hash_archivo(img: Path) -> str:
    """SHA-256 del archivo para el caché incremental (solo cambia si el archivo cambió)."""
    import hashlib

    h = hashlib.sha256()
    with open(img, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


DESPACHOS_CACHE_VERSION = "1"  # subir si cambia la lógica de extracción


def procesar(pdfs_glob: list[Path], normalizacion: dict[str, str],
             out_dir: Path | None = None) -> list[dict]:
    """Extrae (fecha, documento) de cada PDF y les asigna chofer + salida.

    Caché incremental por hash de PDF (data/despachos_cache.json): solo se
    re-leen los PDFs nuevos/cambiados; el resto se reutiliza.
    """
    cache_path = (out_dir or ROOT / "data") / "despachos_cache.json"
    cache: dict[str, dict] = {}
    if cache_path.is_file():
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            if data.get("version") == DESPACHOS_CACHE_VERSION:
                cache = data.get("pdfs", {})
        except Exception:
            cache = {}

    filas: list[dict] = []
    aliases_nuevos: dict[str, str] = {}
    nuevos = 0
    for pdf_path in sorted(pdfs_glob):
        h = _hash_archivo(pdf_path)
        if h in cache:
            filas.extend(cache[h]["filas"])
            continue
        try:
            with pdfplumber.open(pdf_path) as pdf:
                paginas = [pg.extract_text() or "" for pg in pdf.pages]
        except Exception:
            continue
        texto = "\n".join(paginas)
        chofer_bruto, fecha_salida = extraer_encabezado_de_texto(texto.split("\n"))
        canon = normalizacion.get(chofer_bruto.upper(), chofer_bruto)
        if canon and canon not in normalizacion.values():
            aliases_nuevos[chofer_bruto.upper()] = canon
        # Re-extraer facturas de este PDF (fecha + documento)
        pdf_filas: list[dict] = []
        for l in texto.split("\n"):
            m = RE_DOC.match(l.strip())
            if m:
                fecha = m.group(1)  # dd/mm/yyyy
                doc = m.group(2) or m.group(5)  # doc-tipo o tipo-doc
                pdf_filas.append({
                    "fecha_facturacion": fecha,
                    "documento": doc,
                    "chofer": canon,
                    "fecha_salida": fecha_salida,
                })
        cache[h] = {"filas": pdf_filas}
        filas.extend(pdf_filas)
        nuevos += 1

    if nuevos:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache_path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps({"version": DESPACHOS_CACHE_VERSION, "pdfs": cache},
                       ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(cache_path)
        print(f"   [cache] {nuevos} PDF(s) nuevo(s) procesados; resto desde caché")
    if aliases_nuevos:
        guardar_normalizacion(aliases_nuevos)
    return filas


def sanear_fecha_salida(fecha_salida: str, fecha_facturacion: str) -> str:
    """Corrige errores de impresión de mes en la fecha de salida.

    Caso real: PDF del 10-01-26 imprime 'SALIDA MIERCOLES 14-10-26' (octubre)
    cuando debió ser 14-01-26. Si la salida queda a más de 30 días de la
    facturación, se asume typo de mes: se usa el mes de la facturación (o el
    siguiente si el día es anterior al de facturación).
    """
    from datetime import datetime
    try:
        d_fac = datetime.strptime(fecha_facturacion, "%d/%m/%Y")
        d_sal = datetime.strptime(fecha_salida, "%d/%m/%Y")
    except ValueError:
        return fecha_salida
    if abs((d_sal - d_fac).days) <= 30:
        return fecha_salida
    # typo de mes: conservar día, corregir mes/año
    if d_sal.day >= d_fac.day:
        mes = d_fac.month
    else:
        mes = d_fac.month + 1 if d_fac.month < 12 else 1
        if mes == 1:
            return fecha_salida  # no corregir cruce de año
    corregida = datetime(d_fac.year, mes, d_sal.day)
    return corregida.strftime("%d/%m/%Y")


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--facturas", default=str(ROOT.parent / "Facturas"))
    args = ap.parse_args()

    base = Path(args.facturas)
    pdfs = sorted(base.glob("2026-*/FACT*.pdf"))
    print(f"PDFs de facturación encontrados: {len(pdfs)}")

    normalizacion = cargar_normalizacion()
    filas = procesar(pdfs, normalizacion, DATA)

    # Cruzar con facturas.csv (deduplicado) para traer cliente/rif/monto/cajas
    facturas = {}
    with open(DATA / "facturas.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            facturas[(r["fecha_emision"], r["documento"])] = r

    seen: set[tuple[str, str]] = set()
    salida: list[dict] = []
    sin_chofer = sin_salida = 0
    for f in filas:
        clave = (f["fecha_facturacion"], f["documento"])
        if clave in seen:
            continue
        seen.add(clave)
        fac = facturas.get(clave)
        if not fac:
            continue
        chofer = f["chofer"] or "SIN DATO"
        fecha_salida = f["fecha_salida"] or ""
        if fecha_salida:
            fecha_salida = sanear_fecha_salida(fecha_salida, clave[0])
        if chofer == "SIN DATO":
            sin_chofer += 1
        if not fecha_salida:
            sin_salida += 1
        dias = ""
        if fecha_salida:
            from datetime import datetime
            try:
                d_fac = datetime.strptime(clave[0], "%d/%m/%Y")
                d_sal = datetime.strptime(fecha_salida, "%d/%m/%Y")
                dias = (d_sal - d_fac).days
            except ValueError:
                dias = ""
        salida.append({
            "fecha_facturacion": clave[0],
            "documento": clave[1],
            "nombre_cliente": fac.get("nombre_cliente", ""),
            "rif": fac.get("rif", ""),
            "total_operacion": fac.get("total_operacion", ""),
            "cajas": fac.get("cajas", ""),
            "chofer": chofer,
            "fecha_salida": fecha_salida,
            "dias_espera": dias,
        })

    salida.sort(key=lambda x: (x["fecha_facturacion"], x["documento"]))
    with open(DATA / "despachos.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "fecha_facturacion", "documento", "nombre_cliente", "rif",
            "total_operacion", "cajas", "chofer", "fecha_salida", "dias_espera",
        ])
        w.writeheader()
        w.writerows(salida)

    print(f"Despachos: {len(salida)} facturas asociadas "
          f"({sin_chofer} sin chofer, {sin_salida} sin fecha de salida)")
    print(f"Choferes: {sorted(set(x['chofer'] for x in salida))}")
    print(f"Salida en: {DATA / 'despachos.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
