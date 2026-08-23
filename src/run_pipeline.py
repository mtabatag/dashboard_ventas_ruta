"""Orquesta el pipeline completo de FYS y registra cada corrida.

Ejecuta en orden:
  1. src/run_all.py           (facturas + pagos -> data/)
  2. src/productos.py         (capa de productos por factura)
  3. src/despachos.py         (chofer + fecha de salida por factura)
  4. src/generar_master.py    (master de clientes)
  5. src/build_dashboard.py   (dashboard/index.html)

Al final escribe un registro en data/corridas_log.csv con fecha, duración,
conteos y estado. El log permite detectar regresiones entre corridas.

Uso:
    python src/run_pipeline.py            # todo, con log
    python src/run_pipeline.py --skip dashboard
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CODEX_PY = Path(
    r"C:\Users\Marcos\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
)

STEPS = ["run_all", "productos", "despachos", "generar_master", "build_dashboard"]


def _correr(step: str) -> tuple[bool, str]:
    cmd = [str(CODEX_PY), f"src/{step}.py"]
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)  # PIL roto del venv Hermes si no se limpia
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, env=env)
    ok = r.returncode == 0
    resumen = (r.stdout or "").strip().splitlines()
    ultimas = resumen[-6:] if resumen else []
    return ok, "\n".join(ultimas) + (f"\n[stderr] {r.stderr[-800:]}" if not ok and r.stderr else "")


def _leer_resumen() -> dict:
    path = DATA / "resumen_global.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Pipeline completo FYS con log")
    ap.add_argument("--skip", choices=STEPS, action="append", default=[])
    args = ap.parse_args()

    inicio = time.time()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    resultados: dict[str, str] = {}
    fallo = False

    for step in STEPS:
        if step in args.skip:
            resultados[step] = "SKIP"
            continue
        print(f"== {step} ==")
        ok, out = _correr(step)
        print(out)
        resultados[step] = "OK" if ok else "ERROR"
        if not ok:
            fallo = True

    duracion = round(time.time() - inicio, 1)
    resumen = _leer_resumen()

    log_path = DATA / "corridas_log.csv"
    nuevo = not log_path.is_file()
    with open(log_path, "a", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        if nuevo:
            w.writerow(["fecha", "duracion_s", "facturas", "monto_usd", "cajas",
                        "capturas", "verificadas", "solo_total", "sin_total",
                        "credito_usd", "pasos", "estado"])
        w.writerow([
            fecha, duracion,
            resumen.get("facturas", {}).get("facturas_totales", ""),
            resumen.get("facturas", {}).get("monto_total_operacion_usd", ""),
            resumen.get("facturas", {}).get("cajas_totales", ""),
            resumen.get("pagos", {}).get("capturas_totales", ""),
            resumen.get("pagos", {}).get("capturas_verificadas", ""),
            len(resumen.get("pagos", {}).get("capturas_solo_total", [])),
            len(resumen.get("pagos", {}).get("capturas_sin_total", [])),
            resumen.get("pagos", {}).get("credito_total_dia_usd", ""),
            "|".join(f"{k}={v}" for k, v in resultados.items()),
            "ERROR" if fallo else "OK",
        ])

    print(f"\n{'⚠ FALLÓ ALGÚN PASO' if fallo else '✓ Pipeline completo'} "
          f"({duracion}s) — log en {log_path}")
    return 1 if fallo else 0


if __name__ == "__main__":
    raise SystemExit(main())
