"""Respaldo previo a cada corrida (paso 1 del Actualizar_Dashboard.bat).

Copia data/*.csv y data/*.json a data/backup/<YYYY-MM-DD_HHMM>/ antes de
regenerar nada, y poda respaldos viejos conservando los últimos MAX_BACKUPS.

Si el respaldo falla, la corrida se aborta: nunca se regenera sin red de
seguridad.

Uso:
    python src/backup_data.py
"""
from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BACKUPS = DATA / "backup"
MAX_BACKUPS = 15

# No morir por ✓/⚠ si la consola no es UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    if not DATA.is_dir():
        print(f"✗ No existe {DATA}")
        return 1

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    dest = BACKUPS / stamp
    dest.mkdir(parents=True, exist_ok=True)

    copiados = 0
    try:
        for f in sorted(DATA.iterdir()):
            if f.is_file() and f.suffix.lower() in (".csv", ".json"):
                shutil.copy2(f, dest / f.name)
                copiados += 1
    except Exception as e:  # noqa: BLE001
        print(f"✗ Respaldo falló: {e} — corrida abortada.")
        return 1

    # Podar respaldos viejos (los nombres ordenan cronológicamente)
    pods = sorted(p for p in BACKUPS.iterdir() if p.is_dir())
    eliminados = 0
    for viejo in pods[:-MAX_BACKUPS] if len(pods) > MAX_BACKUPS else []:
        shutil.rmtree(viejo, ignore_errors=True)
        eliminados += 1

    print(f"✓ Respaldo en {dest.relative_to(ROOT)} ({copiados} archivos"
          + (f", {eliminados} respaldos viejos podados)" if eliminados else ")"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
