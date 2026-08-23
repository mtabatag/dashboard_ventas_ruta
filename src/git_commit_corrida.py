"""Commit automático de la corrida (paso 4 del Actualizar_Dashboard.bat).

Construye el mensaje a partir de resumen_global.json + última fila de
corridas_log.csv y registra el estado en git. Solo se invoca si el pipeline
terminó OK; si el chequeo de calidad detectó problemas, el commit se hace
igualmente pero queda marcado en el mensaje (traza auditable).

Uso:
    python src/git_commit_corrida.py --check 0
    python src/git_commit_corrida.py --check 1
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# No morir por ✓/⚠ si la consola no es UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _resumen() -> dict:
    p = DATA / "resumen_global.json"
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _ultima_corrida() -> dict:
    p = DATA / "corridas_log.csv"
    if not p.is_file():
        return {}
    with open(p, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    return rows[-1] if rows else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Commit automático de corrida FYS")
    ap.add_argument("--check", type=int, default=0,
                    help="código de salida de check_corrida.py (0=OK)")
    args = ap.parse_args()

    r = _resumen()
    f = r.get("facturas", {})
    p = r.get("pagos", {})
    cor = _ultima_corrida()
    fecha = cor.get("fecha", "")
    check_txt = "OK" if args.check == 0 else "PROBLEMAS"

    msg = (
        f"Corrida {fecha}: facturas={f.get('facturas_totales', '?')} "
        f"monto={f.get('monto_total_operacion_usd', '?')} "
        f"cajas={f.get('cajas_totales', '?')} · "
        f"capturas={p.get('capturas_totales', '?')} "
        f"credito={p.get('credito_total_dia_usd', '?')} · check={check_txt}"
    )

    def git(*argv: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", *argv], cwd=str(ROOT),
                              capture_output=True, text=True)

    if git("rev-parse", "--is-inside-work-tree").returncode != 0:
        print("⚠ No hay repositorio git — se omite el registro.")
        return 0

    git("add", "-A")
    status = git("status", "--porcelain")
    if not status.stdout.strip():
        print("Sin cambios que registrar en git.")
        return 0

    c = git("commit", "-m", msg)
    if c.returncode != 0:
        print(f"✗ git commit falló:\n{c.stderr.strip()}")
        return 1
    print(f"✓ Registrado en git: {msg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
