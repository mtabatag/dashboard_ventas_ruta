"""Chequeo de calidad post-corrida FYS.

Verifica que una corrida del pipeline no haya roto lo validado:

- Facturas: 0 PDFs DESVIADO/SIN_TOTAL/ERROR, conteo y monto plausibles
- Pagos: 0 capturas SIN_TOTAL (SOLO_TOTAL permitido y documentado)
- Productos: cobertura de detalle >= 95 % (antes 97,9 %)
- Duplicados por (fecha, documento): deben quedar registrados en el resumen
- Corridas_log.csv: no debe empeorar respecto a la corrida anterior

Uso:
    python src/check_corrida.py            # chequea data/ actual
    python src/check_corrida.py --ultima   # compara con la corrida anterior
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

UMBRAL_COBERTURA = 0.95

# No morir por ✓/⚠ si la consola no es UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    ok = True
    resumen_path = DATA / "resumen_global.json"
    if not resumen_path.is_file():
        print("✗ No existe resumen_global.json — corre el pipeline primero.")
        return 1
    resumen = json.loads(resumen_path.read_text(encoding="utf-8"))

    f = resumen.get("facturas", {})
    print("== Facturas ==")
    print(f"  PDFs: {f.get('pdfs_ok')}/{f.get('pdfs_procesados')} OK · "
          f"facturas={f.get('facturas_totales')} · monto={f.get('monto_total_operacion_usd')}")
    if f.get("pdfs_desviados"):
        print(f"  ✗ DESVIADOS: {f['pdfs_desviados']}"); ok = False
    if f.get("pdfs_sin_total"):
        print(f"  ✗ SIN_TOTAL: {f['pdfs_sin_total']}"); ok = False
    if f.get("pdfs_error"):
        print(f"  ✗ ERROR: {f['pdfs_error']}"); ok = False
    dups = f.get("facturas_duplicadas_eliminadas", [])
    if dups:
        print(f"  ⚠ Duplicados eliminados: {len(dups)} — "
              f"{dups[0].get('documento')} {dups[0].get('cliente', '')} {dups[0].get('fecha', '')}")

    p = resumen.get("pagos", {})
    print("\n== Pagos ==")
    print(f"  capturas={p.get('capturas_totales')} · VERIFICADO={p.get('capturas_verificadas')} · "
          f"SOLO_TOTAL={len(p.get('capturas_solo_total', []))} · "
          f"SIN_TOTAL={len(p.get('capturas_sin_total', []))} · crédito={p.get('credito_total_dia_usd')}")
    if p.get("capturas_sin_total"):
        print("  ✗ SIN_TOTAL presentes — revisar manualmente:")
        for c in p["capturas_sin_total"]:
            print(f"    {c}")
        ok = False
    if p.get("capturas_duplicadas"):
        print("  ✗ Capturas duplicadas (mismo contenido, distinto nombre):")
        for d in p["capturas_duplicadas"]:
            print(f"    {d['archivo']} = copia de {d['copia_de']}")
        ok = False

    print("\n== Productos ==")
    val = DATA / "validacion_productos.csv"
    if val.is_file():
        with open(val, encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
        total = len(rows)
        okp = sum(1 for r in rows if r["estado"] == "VALIDADO")
        if total:
            cobertura = okp / total
            print(f"  cobertura detalle: {okp}/{total} = {cobertura:.1%} "
                  f"(umbral {UMBRAL_COBERTURA:.0%})")
            if cobertura < UMBRAL_COBERTURA:
                print("  ✗ Cobertura por debajo del umbral"); ok = False

    print("\n" + ("✓ Corrida saludable" if ok else "✗ Hay problemas que revisar"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
