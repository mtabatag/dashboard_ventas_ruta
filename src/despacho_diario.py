"""Mensaje diario FYS por WhatsApp: despachos de hoy + recordatorios de pago.

Corre por la mañana (cron de Hermes). Genera a stdout el texto del mensaje:

1. 📦 DESPACHOS DE HOY: facturas cuya fecha de salida es hoy, agrupadas por
   chofer, con cliente, documento y monto.
2. 💰 RECORDATORIOS: clientes cuyo despacho cumple 5 días (vence en 2 días) o 6 días (vence mañana)
   (pago a los 7 días del despacho) — aviso para llamarlos/escribirles.

Si no hay nada que reportar, stdout queda vacío → el cron no envía nada.

Uso: python src/despacho_diario.py
"""
from __future__ import annotations

import csv
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def parse_fecha(f: str) -> date | None:
    try:
        return datetime.strptime(f, "%d/%m/%Y").date()
    except (ValueError, TypeError):
        return None


def cargar_despachos() -> list[dict]:
    p = DATA / "despachos.csv"
    if not p.is_file():
        return []
    with open(p, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main() -> int:
    hoy = date.today()
    despachos = cargar_despachos()
    if not despachos:
        return 0

    # ── Despachos de hoy ──
    de_hoy = [d for d in despachos if parse_fecha(d.get("fecha_salida", "")) == hoy]
    # ── Recordatorios: despachado hace 5 días (vence en 2 días) y hace 6 días (vence mañana) ──
    hace5 = hoy - timedelta(days=5)
    hace6 = hoy - timedelta(days=6)
    recordatorios = [
        d for d in despachos
        if parse_fecha(d.get("fecha_salida", "")) == hace5 or parse_fecha(d.get("fecha_salida", "")) == hace6
    ]

    if not de_hoy and not recordatorios:
        return 0  # silencio: el cron no envía nada

    partes: list[str] = []
    partes.append("⚕ *FYS · Resumen del día*")

    if de_hoy:
        total_hoy = sum(float(d["total_operacion"] or 0) for d in de_hoy)
        partes.append(f"\n📦 *Despachos de hoy ({len(de_hoy)} facturas · USD {total_hoy:,.2f})*")
        por_chofer: dict[str, list[dict]] = {}
        for d in de_hoy:
            por_chofer.setdefault(d.get("chofer") or "SIN DATO", []).append(d)
        for chofer, docs in sorted(por_chofer.items()):
            monto = sum(float(d["total_operacion"] or 0) for d in docs)
            partes.append(f"\n🚚 *{chofer}* — {len(docs)} facturas · USD {monto:,.2f}")
            for d in docs:
                partes.append(
                    f"• {d['nombre_cliente']} · {d['documento']} · "
                    f"USD {float(d['total_operacion'] or 0):,.2f}"
                )

    if recordatorios:
        por_cliente: dict[str, float] = {}
        for d in recordatorios:
            cli = d["nombre_cliente"]
            por_cliente[cli] = por_cliente.get(cli, 0) + float(d["total_operacion"] or 0)
        total_rec = sum(por_cliente.values())
        partes.append(
            f"\n💰 *Pronto pago — vence MAÑANA ({len(por_cliente)} clientes · "
            f"USD {total_rec:,.2f})*"
        )
        for cli, monto in sorted(por_cliente.items(), key=lambda x: -x[1]):
            partes.append(f"• {cli}: USD {monto:,.2f}")

    partes.append("\n— Bot FYS")
    print("\n".join(partes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())