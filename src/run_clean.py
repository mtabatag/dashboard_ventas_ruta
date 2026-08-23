"""Wrapper de arranque: ejecuta el pipeline FYS con el entorno limpio.

El PYTHONPATH de la sesión Hermes apunta a un PIL roto (venv de hermes-agent,
compilado para CPython 3.11, mientras el runtime de Codex es 3.12). Sin
limpiarlo, el OCR de pagos corre sin preprocesamiento y produce SIN_TOTAL.

Este wrapper fuerza `unset PYTHONPATH` antes de ejecutar cualquier comando.

Uso:
    python src\run_clean.py src\run_pipeline.py [--skip run_all]
    python src\run_clean.py src\fys_consulta.py resumen
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

CODEX_PY = Path(
    r"C:\Users\Marcos\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
)


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python src/run_clean.py <script> [args...]")
        return 2
    script = sys.argv[1]
    args = sys.argv[2:]

    env = dict(os.environ)
    env.pop("PYTHONPATH", None)  # ← clave: eliminar el PYTHONPATH contaminado

    cmd = [str(CODEX_PY), script, *args]
    print(f"[run_clean] PYTHONPATH limpio · {' '.join(cmd)}")
    return subprocess.call(cmd, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
