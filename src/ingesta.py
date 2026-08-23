"""Ingesta automática FYS (Fase A).

Vigila la carpeta de entrada y procesa archivos nuevos:

1. Detecta PDFs de facturas y capturas de pago (jpeg/jpg/png) en Entrada/
2. Los clasifica en la carpeta mensual correcta (Facturas\\2026-MM /
   Pagos_procesados\\2026-MM) según la fecha del nombre del archivo
   (formato YYYY-MM-DD o DD-MM-YY) o del mes por defecto
3. Evita duplicados (mismo nombre o mismo hash ya procesado)
4. Ejecuta el pipeline completo: run_all.py + productos.py + generar_master.py
   + build_dashboard.py
5. Escribe un log de la corrida en FYS_DATOS_VALIDADOS\\data\\ingesta_log.csv

Uso:
    python src/ingesta.py              # procesa Entrada/ y regenera todo
    python src/ingesta.py --check      # solo reporta qué hay en Entrada/
    python src/ingesta.py --entrada <ruta>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # FYS_DATOS_VALIDADOS
FYS_ROOT = ROOT.parent                                  # .../Mi unidad/FYS
ENTRADA_DEFAULT = FYS_ROOT / "Entrada"
FACTURAS_DIR = FYS_ROOT / "Facturas"
PAGOS_DIR = FYS_ROOT / "Pagos_procesados"
CODEX_PY = Path(
    r"C:\Users\Marcos\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
)

EXT_FACTURA = {".pdf"}
EXT_PAGO = {".jpeg", ".jpg", ".png"}

RE_FECHA_ARCHIVO = re.compile(
    r"(20\d{2})[-/._](\d{1,2})[-/._](\d{1,2})|(\d{1,2})[-/._](\d{1,2})[-/._](\d{2})"
)


def fecha_desde_nombre(nombre: str) -> str | None:
    """Devuelve 'YYYY-MM' desde el nombre del archivo, o None si no detecta."""
    m = RE_FECHA_ARCHIVO.search(nombre)
    if not m:
        return None
    if m.group(1):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        d, mo, y = int(m.group(4)), int(m.group(5)), int(m.group(6))
        y = 2000 + y
    if not (1 <= mo <= 12 and 1 <= d <= 31):
        return None
    return f"{y}-{mo:02d}"


def hash_archivo(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def hashes_procesados(log_path: Path) -> set[str]:
    """SHA-256 de los archivos ya registrados en el log de ingesta."""
    if not log_path.is_file():
        return set()
    with open(log_path, encoding="utf-8-sig") as fh:
        return {r["sha256"] for r in csv.DictReader(fh) if r.get("sha256")}


def clasificar_y_mover(path: Path, dest_dir: Path, log_path: Path,
                       ya_vistos: set[str]) -> tuple[str, str]:
    """Mueve un archivo a su carpeta mensual. Devuelve (estado, detalle)."""
    nombre = path.name
    if nombre.lower().startswith(("cxc", "master")) or "master" in nombre.lower():
        return "IGNORADO", "reporte excluido (CXC/MASTER)"
    h = hash_archivo(path)
    if h in ya_vistos:
        return "DUPLICADO", "hash ya procesado"
    mes = fecha_desde_nombre(nombre)
    if not mes:
        mes = datetime.now().strftime("%Y-%m")
    carpeta = dest_dir / mes
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / nombre
    if destino.exists():
        # mismo nombre ya presente: si es idéntico, es duplicado; si no, sufijar
        if hash_archivo(destino) == h:
            return "DUPLICADO", "nombre y contenido ya presentes"
        destino = carpeta / f"{path.stem}_{datetime.now():%H%M%S}{path.suffix}"
    shutil.move(str(path), str(destino))
    return "PROCESADO", str(destino)


def correr_pipeline() -> tuple[bool, str]:
    """Ejecuta el pipeline completo (con log de corrida). Devuelve (ok, resumen)."""
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)  # PIL roto del venv Hermes si no se limpia
    cmd = [str(CODEX_PY), "src/run_pipeline.py"]
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, env=env)
    if r.returncode != 0:
        return False, f"FALLÓ pipeline\n{r.stderr[-2000:]}"
    return True, (r.stdout or "").strip().splitlines()[-1]


def main() -> int:
    ap = argparse.ArgumentParser(description="Ingesta automática FYS")
    ap.add_argument("--entrada", default=str(ENTRADA_DEFAULT))
    ap.add_argument("--check", action="store_true",
                    help="solo listar lo que hay en Entrada/ sin procesar")
    args = ap.parse_args()

    entrada = Path(args.entrada)
    entrada.mkdir(parents=True, exist_ok=True)
    log_path = ROOT / "data" / "ingesta_log.csv"

    pendientes = sorted(
        [p for p in entrada.iterdir() if p.is_file()],
        key=lambda p: p.stat().st_mtime,
    )
    if args.check:
        if not pendientes:
            print("Entrada vacía.")
        for p in pendientes:
            print(f"  {p.name} ({p.stat().st_size} bytes)")
        return 0

    if not pendientes:
        print("Sin archivos nuevos en Entrada/.")
        return 0

    ya_vistos = hashes_procesados(log_path)
    movidos: list[dict] = []
    for p in pendientes:
        ext = p.suffix.lower()
        if ext in EXT_FACTURA:
            estado, detalle = clasificar_y_mover(p, FACTURAS_DIR, log_path, ya_vistos)
            destino_tipo = "factura"
        elif ext in EXT_PAGO:
            estado, detalle = clasificar_y_mover(p, PAGOS_DIR, log_path, ya_vistos)
            destino_tipo = "pago"
        else:
            estado, detalle = "IGNORADO", "extensión no reconocida"
            destino_tipo = ""
        if estado in ("PROCESADO", "DUPLICADO"):
            movidos.append({
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "archivo": p.name,
                "tipo": destino_tipo,
                "estado": estado,
                "detalle": detalle,
                "sha256": hash_archivo(p) if p.exists() else "",
            })
        elif estado == "IGNORADO" and detalle == "extensión no reconocida":
            print(f"  ⚠ {p.name}: {detalle}")
        else:
            print(f"  {estado}: {p.name} ({detalle})")

    # Escribir log (append)
    nuevo_log = not log_path.is_file()
    with open(log_path, "a", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["fecha", "archivo", "tipo", "estado",
                                           "detalle", "sha256"])
        if nuevo_log:
            w.writeheader()
        for m in movidos:
            w.writerow(m)

    if any(m["estado"] == "PROCESADO" for m in movidos):
        ok, resumen = correr_pipeline()
        print(resumen)
        if not ok:
            print("⚠ Pipeline falló — revisar.", file=sys.stderr)
            return 1
    else:
        print("Nada nuevo que procesar (solo duplicados/ignorados).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
