"""Genera el master de clientes actualizado.

Unión (por RIF y por nombre normalizado) de:
  1. MASTER TABATA MARCOS 13-05-26.pdf   (último master publicado)
  2. Clientes nuevos detectados en las facturas (enero–agosto 2026)

Salidas:
  data/master_clientes.csv   master completo con origen y ventas
  data/clientes.csv          mismo listado (rif, nombre) para el dashboard
  data/Master de Clientes FYS 2026-08.xlsx  copia para Excel (si hay openpyxl)
"""
from __future__ import annotations

import csv
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import facturas as facturas_mod  # noqa: E402

MASTER_PDF = Path(
    r"C:\Users\Marcos\Mi unidad\FYS\Master\MASTER TABATA MARCOS 13-05-26.pdf"
)
BASE_FACTURAS = ROOT.parent / "Facturas"

RE_MASTER = re.compile(
    r"^([A-Z]\d{6,10}|\d{6,10})\s+(.+?)\s+(\d{1,2}/\d{1,2}/\d{4})"
)

ORDEN_ORIGEN = {"MASTER PDF": 0, "FACTURAS": 1}

_CYR = str.maketrans(
    {
        "С": "C", "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M",
        "О": "O", "Р": "P", "Т": "T", "Х": "X", "Н": "H", "І": "I",
        "Є": "E", "Г": "F",
    }
)


def limpiar_nombre(s: str) -> str:
    return str(s or "").translate(_CYR).strip()


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s or "").upper())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    toks = [t for t in s.split() if t]
    out: list[str] = []
    i = 0
    while i < len(toks):
        if len(toks[i]) == 1 and i + 1 < len(toks) and len(toks[i + 1]) == 1:
            j = i
            while j < len(toks) and len(toks[j]) == 1:
                j += 1
            out.append("".join(toks[i:j]))
            i = j
        else:
            out.append(toks[i])
            i += 1
    return " ".join(out)


def rif_digitos(s) -> str:
    return re.sub(r"\D", "", str(s or ""))


def fecha_iso(valor) -> str:
    """Convierte dd/mm/yyyy o datetime.date a YYYY-MM-DD (o '')."""
    if valor is None:
        return ""
    if hasattr(valor, "isoformat") and not isinstance(valor, str):
        return str(valor.isoformat())[:10]
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", str(valor).strip())
    if m:
        d, mo, y = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    return ""


def leer_master_pdf() -> list[dict]:
    import pdfplumber

    clientes: list[dict] = []
    vistos: set[str] = set()
    with pdfplumber.open(MASTER_PDF) as pdf:
        for page in pdf.pages:
            for linea in (page.extract_text() or "").split("\n"):
                m = RE_MASTER.match(linea.strip())
                if not m:
                    continue
                rif, nombre, fecha = m.groups()
                clave = rif_digitos(rif)
                n = norm(nombre)
                if clave in vistos or n in vistos:
                    continue
                vistos.add(clave)
                vistos.add(n)
                clientes.append(
                    {
                        "rif": rif.strip(),
                        "nombre": limpiar_nombre(nombre),
                        "ultima_master": fecha_iso(fecha),
                    }
                )
    return clientes


def leer_facturas() -> list[dict]:
    clientes: dict[str, dict] = {}
    for r in facturas_mod.procesar_todo(BASE_FACTURAS):
        for f in r.get("facturas", []):
            nombre = limpiar_nombre(f.get("nombre_cliente"))
            if not nombre:
                continue
            n = norm(nombre)
            clave = rif_digitos(f.get("rif_cliente")) or n
            c = clientes.get(clave)
            if c is None:
                c = {"rif": f.get("rif_cliente") or "", "nombre": nombre, "fechas": []}
                clientes[clave] = c
            fechas: list[str] = []
            if f.get("fecha_emision"):
                d, m, y = f["fecha_emision"].split("/")
                fechas.append(f"{y}-{m}-{d}")
            c["fechas"].extend(fechas)
    return list(clientes.values())


def unir(listas: list[tuple[str, list[dict]]]) -> list[dict]:
    """Agrupa por RIF (dígitos) y, si no hay coincidencia, por nombre."""
    clusters: list[dict] = []
    rif_index: dict[str, int] = {}
    name_index: dict[str, int] = {}

    def idx_cluster(entry: dict, origen: str) -> int:
        clave = rif_digitos(entry.get("rif"))
        n = norm(entry.get("nombre", ""))
        if clave and clave in rif_index:
            return rif_index[clave]
        if n and n in name_index:
            return name_index[n]
        idx = len(clusters)
        clusters.append(
            {
                "rif": entry.get("rif", ""),
                "nombre": entry["nombre"],
                "nombres": {n},
                "origen": set(),
                "fechas": [],
                "name_rank": ORDEN_ORIGEN[origen],
                "ultima_master": "",
            }
        )
        if clave:
            rif_index[clave] = idx
        if n:
            name_index[n] = idx
        return idx

    for origen, items in listas:
        for it in items:
            idx = idx_cluster(it, origen)
            c = clusters[idx]
            c["origen"].add(origen)
            c["fechas"].extend(it.get("fechas", []))
            c["ultima_master"] = max(c["ultima_master"], it.get("ultima_master", ""))
            n = norm(it["nombre"])
            c["nombres"].add(n)
            if n not in name_index:
                name_index[n] = idx
            clave = rif_digitos(it.get("rif"))
            if clave and clave not in rif_index:
                rif_index[clave] = idx
            # El RIF con letra (formato real) tiene prioridad
            if re.match(r"^[A-Z]", str(it.get("rif", ""))) and not re.match(
                r"^[A-Z]", c["rif"]
            ):
                c["rif"] = it["rif"]
            # Preferir el nombre según el origen de mayor prioridad
            if ORDEN_ORIGEN[origen] < c["name_rank"]:
                c["nombre"] = it["nombre"]
                c["name_rank"] = ORDEN_ORIGEN[origen]

    return clusters


def main():
    unidos = unir(
        [
            ("MASTER PDF", leer_master_pdf()),
            ("FACTURAS", leer_facturas()),
        ]
    )

    filas = []
    for u in unidos:
        fechas = sorted(set(u["fechas"]))
        filas.append(
            {
                "rif": u["rif"],
                "nombre": u["nombre"],
                "origen": "; ".join(sorted(u["origen"])),
                "primera_venta": fechas[0] if fechas else "",
                "ultima_venta": fechas[-1] if fechas else "",
                "ultima_master": u["ultima_master"],
                "facturas": len(fechas),
            }
        )
    filas.sort(key=lambda x: norm(x["nombre"]))

    with open(ROOT / "data" / "master_clientes.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            ["rif", "nombre", "origen", "primera_venta", "ultima_venta",
             "ultima_master", "facturas"]
        )
        for f in filas:
            w.writerow(
                [f["rif"], f["nombre"], f["origen"],
                 f["primera_venta"], f["ultima_venta"],
                 f["ultima_master"], f["facturas"]]
            )

    with open(ROOT / "data" / "clientes.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["rif", "nombre", "ultima_venta"])
        for f in filas:
            fechas_venta = [x for x in (f["ultima_venta"], f["ultima_master"]) if x]
            w.writerow([f["rif"], f["nombre"], max(fechas_venta) if fechas_venta else ""])

    xlsx_path = ROOT / "data" / "Master de Clientes FYS 2026-08.xlsx"
    xlsx_ok = False
    try:
        import openpyxl  # noqa: PLC0415
        from openpyxl.styles import Font  # noqa: PLC0415

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Clientes"
        enc = ["RIF", "Nombre", "Origen", "Primera venta", "Última venta",
               "Última venta master", "Facturas"]
        ws.append(enc)
        for i, c in enumerate(enc, start=1):
            ws.cell(row=1, column=i).font = Font(bold=True)
        for f in filas:
            ws.append(
                [f["rif"], f["nombre"], f["origen"],
                 f["primera_venta"], f["ultima_venta"],
                 f["ultima_master"], f["facturas"]]
            )
        wb.save(xlsx_path)
        xlsx_ok = True
    except Exception:  # noqa: BLE001
        pass

    origen_counts: dict[str, int] = {}
    for f in filas:
        for o in f["origen"].split("; "):
            origen_counts[o] = origen_counts.get(o, 0) + 1
    print(f"Total clientes en master: {len(filas)}")
    for o in ("MASTER PDF", "FACTURAS"):
        print(f"  {o}: {origen_counts.get(o, 0)}")
    nuevos = sum(1 for f in filas if "MASTER PDF" not in f["origen"])
    print(f"Clientes nuevos (no presentes en el MASTER PDF): {nuevos}")
    print(f"Master escrito en: {ROOT / 'data' / 'master_clientes.csv'}")
    print(f"Excel {'generado' if xlsx_ok else 'no disponible'}: {xlsx_path}")


if __name__ == "__main__":
    main()
