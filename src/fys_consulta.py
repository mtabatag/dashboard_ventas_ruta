"""Consultas rápidas FYS para el bot de WhatsApp.

CLI que responde preguntas frecuentes sobre los datos validados:

    python src/fys_consulta.py resumen [--mes 2026-07]
    python src/fys_consulta.py facturado [--mes 2026-07] [--quincena 1|2]
    python src/fys_consulta.py cobrado [--mes 2026-07]
    python src/fys_consulta.py top-clientes [--n 5] [--mes 2026-07]
    python src/fys_consulta.py cliente "NOMBRE" [--detalle]
    python src/fys_consulta.py top-productos [--n 5] [--mes 2026-07]
    python src/fys_consulta.py comisiones [--mes 2026-07]
    python src/fys_consulta.py pendientes

Salida en texto plano (apta para WhatsApp: sin tablas anchas, montos en USD).
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def _load(name: str) -> list[dict]:
    with open(DATA / name, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def _fmt_usd(v: float) -> str:
    return f"USD {v:,.2f}"


def _mes_de_fecha_ddmm(fecha: str) -> str | None:
    try:
        d, m, y = fecha.split("/")
        return f"{y}-{int(m):02d}"
    except (ValueError, AttributeError):
        return None


def cmd_resumen(args) -> None:
    facturas = _load("facturas.csv")
    pagos = _load("pagos_diarios.csv")
    clientes = _load("clientes.csv")
    facturado = sum(float(f["total_operacion"] or 0) for f in facturas)
    cajas = sum(float(f["cajas"] or 0) for f in facturas)
    cobrado = sum(float(p["total_dia"] or 0) for p in pagos)
    print(f"📊 *Resumen FYS* (ene–ago 2026)")
    print(f"• Facturado: {_fmt_usd(facturado)}")
    print(f"• Cajas: {cajas:,.2f}")
    print(f"• Cobrado: {_fmt_usd(cobrado)}")
    print(f"• Facturas: {len(facturas)} · Clientes: {len(clientes)}")


def cmd_facturado(args) -> None:
    facturas = _load("facturas.csv")
    if args.mes:
        facturas = [f for f in facturas if _mes_de_fecha_ddmm(f["fecha_emision"]) == args.mes]
    if args.quincena:
        q = int(args.quincena)
        facturas = [
            f for f in facturas
            if (int(f["fecha_emision"].split("/")[0]) <= 15) == (q == 1)
        ]
    if not facturas:
        print("Sin facturas para ese período.")
        return
    total = sum(float(f["total_operacion"] or 0) for f in facturas)
    cajas = sum(float(f["cajas"] or 0) for f in facturas)
    n = len(facturas)
    label = args.mes or "todo el período"
    q_label = f" · {args.quincena}ª quincena" if args.quincena else ""
    print(f"🧾 *Facturado {label}{q_label}*")
    print(f"• Monto: {_fmt_usd(total)}")
    print(f"• Cajas: {cajas:,.2f} · Facturas: {n}")
    if args.mes and not args.quincena:
        por_q = {"1ª": 0.0, "2ª": 0.0}
        for f in facturas:
            por_q["1ª" if int(f["fecha_emision"].split("/")[0]) <= 15 else "2ª"] += float(f["total_operacion"] or 0)
        print(f"• 1ª quincena: {_fmt_usd(por_q['1ª'])} · 2ª: {_fmt_usd(por_q['2ª'])}")


def cmd_cobrado(args) -> None:
    pagos = _load("pagos_diarios.csv")
    if args.mes:
        pagos = [p for p in pagos if p["mes"] == args.mes]
    if not pagos:
        print("Sin pagos para ese período.")
        return
    total = sum(float(p["total_dia"] or 0) for p in pagos)
    ef = sum(float(p["efectivo"] or 0) for p in pagos)
    tf = sum(float(p["transferencia_bancaria"] or 0) for p in pagos)
    cp = sum(float(p["cupon"] or 0) for p in pagos)
    dias = len({p["fecha"] for p in pagos})
    label = args.mes or "todo el período"
    print(f"💰 *Cobrado {label}*")
    print(f"• Total: {_fmt_usd(total)}")
    print(f"• Efectivo: {_fmt_usd(ef)} · Transferencia: {_fmt_usd(tf)} · Cupón: {_fmt_usd(cp)}")
    print(f"• Días con cobro: {dias}")


def cmd_top_clientes(args) -> None:
    facturas = _load("facturas.csv")
    if args.mes:
        facturas = [f for f in facturas if _mes_de_fecha_ddmm(f["fecha_emision"]) == args.mes]
    agg: dict[str, dict] = {}
    for f in facturas:
        c = agg.setdefault(f["nombre_cliente"], {"monto": 0.0, "cajas": 0.0, "n": 0})
        c["monto"] += float(f["total_operacion"] or 0)
        c["cajas"] += float(f["cajas"] or 0)
        c["n"] += 1
    top = sorted(agg.items(), key=lambda x: -x[1]["monto"])[: args.n]
    label = args.mes or "todo el período"
    print(f"🏆 *Top {len(top)} clientes ({label})*")
    for i, (nombre, c) in enumerate(top, 1):
        print(f"{i}. {nombre[:42]}")
        print(f"   {_fmt_usd(c['monto'])} · {c['cajas']:,.1f} cajas · {c['n']} facturas")


def cmd_cliente(args) -> None:
    facturas = _load("facturas.csv")
    q = args.cliente.upper()
    match = [f for f in facturas if q in f["nombre_cliente"].upper()]
    if not match:
        print(f"Cliente no encontrado: {args.cliente}")
        return
    nombre = match[0]["nombre_cliente"]
    monto = sum(float(f["total_operacion"] or 0) for f in match)
    cajas = sum(float(f["cajas"] or 0) for f in match)
    n = len(match)
    fechas = sorted({f["fecha_emision"] for f in match})
    print(f"👤 *{nombre}*")
    print(f"• Facturado: {_fmt_usd(monto)} · Cajas: {cajas:,.1f}")
    print(f"• Facturas: {n} · Primera: {fechas[0]} · Última: {fechas[-1]}")
    if args.detalle:
        print("• Últimas facturas:")
        for f in sorted(match, key=lambda x: x["fecha_emision"])[-5:]:
            print(f"   {f['fecha_emision']} doc={f['documento']} {_fmt_usd(float(f['total_operacion']))}")


def cmd_top_productos(args) -> None:
    lineas = _load("factura_lineas.csv")
    if args.mes:
        def _mes_linea(fecha: str) -> str | None:
            try:
                d, m, y = fecha.split("/")
                return f"{y}-{int(m):02d}"
            except (ValueError, AttributeError):
                return None
        lineas = [l for l in lineas if _mes_linea(l["fecha"]) == args.mes]
    agg: dict[str, float] = defaultdict(float)
    for l in lineas:
        agg[l["nombre_producto"]] += float(l["cantidad"] or 0)
    top = sorted(agg.items(), key=lambda x: -x[1])[: args.n]
    label = args.mes or "todo el período"
    print(f"📦 *Top {len(top)} productos ({label})*")
    for i, (nombre, cant) in enumerate(top, 1):
        print(f"{i}. {nombre[:45]}")
        print(f"   {cant:,.2f} unidades")


def cmd_comisiones(args) -> None:
    facturas = _load("facturas.csv")
    pagos = _load("pagos_diarios.csv")
    if args.mes:
        facturas = [f for f in facturas if _mes_de_fecha_ddmm(f["fecha_emision"]) == args.mes]
        pagos = [p for p in pagos if p["mes"] == args.mes]
    facturado = sum(float(f["total_operacion"] or 0) for f in facturas)
    cobrado = sum(float(p["total_dia"] or 0) for p in pagos)
    com_fact = facturado / 1.16 * 0.003   # 0,3% sobre base sin IVA
    com_cobro = cobrado * 0.012           # 1,2% sobre cobrado
    label = args.mes or "todo el período"
    print(f"💵 *Comisiones ({label})*")
    print(f"• 0,3% facturado sin IVA: {_fmt_usd(com_fact)}  (base {_fmt_usd(facturado / 1.16)})")
    print(f"• 1,2% cobrado: {_fmt_usd(com_cobro)}")
    print(f"• Total: {_fmt_usd(com_fact + com_cobro)}")


def cmd_pendientes(args) -> None:
    print("🔎 *Pendientes de revisión*")
    val_fact = _load("validacion_facturas_por_pdf.csv")
    malos = [v for v in val_fact if v["validacion"] not in ("OK",)]
    if malos:
        print(f"• PDFs de facturas no OK: {len(malos)}")
        for m in malos:
            print(f"   {m['archivo']} → {m['validacion']}")
    else:
        print("• Facturas: 0 PDFs con problemas")
    val_prod = _load("validacion_productos.csv")
    pend = [v for v in val_prod if v["estado"] == "PENDIENTE"]
    if pend:
        print(f"• Detalle de productos PENDIENTE: {len(pend)} facturas")
    else:
        print("• Detalle de productos: 0 pendientes")
    pagos = _load("pagos_diarios.csv")
    st = [p for p in pagos if p["estado"] == "SOLO_TOTAL"]
    if st:
        print(f"• Capturas SOLO_TOTAL (sin desglose): {len(st)}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Consultas FYS para bot")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("resumen"); p.set_defaults(fn=cmd_resumen)
    for name, fn, extra in [
        ("facturado", cmd_facturado, ["mes", "quincena"]),
        ("cobrado", cmd_cobrado, ["mes"]),
        ("top-clientes", cmd_top_clientes, ["mes"]),
        ("top-productos", cmd_top_productos, ["mes"]),
        ("comisiones", cmd_comisiones, ["mes"]),
    ]:
        p = sub.add_parser(name); p.set_defaults(fn=fn)
        p.add_argument("--mes", help="YYYY-MM")
        if "quincena" in extra:
            p.add_argument("--quincena", choices=["1", "2"])
        if name == "top-clientes":
            p.add_argument("--n", type=int, default=5)
        if name == "top-productos":
            p.add_argument("--n", type=int, default=5)

    p = sub.add_parser("cliente"); p.set_defaults(fn=cmd_cliente)
    p.add_argument("cliente"); p.add_argument("--detalle", action="store_true")

    p = sub.add_parser("pendientes"); p.set_defaults(fn=cmd_pendientes)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
