"""Orquesta la extracción completa: facturas + pagos -> data/.

Uso:
    python src/run_all.py
    python src/run_all.py --facturas <ruta> --pagos <ruta>

Salidas en data/:
    facturas.csv                     784 facturas (ene-jul): fecha, documento,
                                     cliente, total operacion, cajas
    validacion_facturas_por_pdf.csv  checksum por PDF (117 PDFs)
    pagos_diarios.csv                total del día por captura (129 capturas)
    pagos_detalle.csv                filas de pago extraídas (936)
    resumen_global.json              totales globales validados
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import facturas as facturas_mod  # noqa: E402
import pagos as pagos_mod  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Extractores mínimos FYS")
    ap.add_argument("--facturas", default=str(ROOT.parent / "Facturas"))
    ap.add_argument("--pagos", default=str(ROOT.parent / "Pagos_procesados"))
    ap.add_argument("--out", default=str(ROOT / "data"))
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print("== Facturas ==")
    resultados_facturas = facturas_mod.procesar_todo(Path(args.facturas), out)
    _, res_facturas = facturas_mod.escribir_resultados(resultados_facturas, out)
    print(
        f"PDFs={res_facturas['pdfs_procesados']} OK={res_facturas['pdfs_ok']} "
        f"facturas={res_facturas['facturas_totales']} "
        f"monto={res_facturas['monto_total_operacion_usd']} "
        f"cajas={res_facturas['cajas_totales']}"
    )

    print("== Pagos ==")
    capturas = pagos_mod.procesar_todo(Path(args.pagos), out)
    res_pagos = pagos_mod.escribir_resultados(capturas, out)
    print(
        f"capturas={res_pagos['capturas_totales']} "
        f"VERIFICADO={res_pagos['capturas_verificadas']} "
        f"SOLO_TOTAL={len(res_pagos['capturas_solo_total'])} "
        f"SIN_TOTAL={len(res_pagos['capturas_sin_total'])} "
        f"filas={res_pagos['pagos_filas_extraidas']} "
        f"credito={res_pagos['credito_total_dia_usd']}"
    )

    resumen = {"facturas": res_facturas, "pagos": res_pagos}
    (out / "resumen_global.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"OK. Resultados en {out}")


if __name__ == "__main__":
    main()
