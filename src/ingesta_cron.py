"""Ingesta FYS + notificación por WhatsApp (para cron de Hermes).

Corre src/ingesta.py y, según el resultado, emite a stdout el mensaje que
el cron de Hermes debe entregar por WhatsApp al home channel:

- Si no hay archivos nuevos: stdout VACÍO → el cron no molesta (silencioso).
- Si procesó archivos y el pipeline quedó OK: mensaje de éxito con conteos.
- Si el pipeline falló o hay SIN_TOTAL: alerta para revisión.

Uso (desde el cron):
    python src/ingesta_cron.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODEX_PY = Path(
    r"C:\Users\Marcos\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
)


def main() -> int:
    import os
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)

    r = subprocess.run(
        [str(CODEX_PY), "src/ingesta.py"],
        cwd=str(ROOT), capture_output=True, text=True, env=env,
    )
    out = (r.stdout or "").strip()
    err = (r.stderr or "").strip()

    # Sin archivos nuevos → silencio (el cron no entrega nada)
    if "Sin archivos nuevos" in out:
        return 0
    if "Nada nuevo que procesar" in out:
        return 0

    if r.returncode != 0:
        print(f"⚠ *FYS · Ingesta FALLÓ*\n\n{out[-1500:]}\n\n{err[-500:]}")
        return 0

    # Éxito: resumir el resultado de la ingesta
    print("✅ *FYS · Ingesta completada*\n")
    print(out[-1500:])
    # Chequeo de calidad rápido
    chk = subprocess.run(
        [str(CODEX_PY), "src/check_corrida.py"],
        cwd=str(ROOT), capture_output=True, text=True, env=env,
    )
    if chk.returncode != 0:
        print("\n⚠ *Revisar:* el chequeo de calidad detectó problemas.")
        print((chk.stdout or "")[-800:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
