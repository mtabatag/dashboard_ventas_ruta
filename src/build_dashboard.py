"""Genera dashboard/index.html a partir de data/facturas.csv y pagos_diarios.csv.

Uso:
    python src/build_dashboard.py

El HTML resultante es autocontenido (datos embebidos, sin dependencias de red)
y se abre con doble clic en cualquier navegador.
"""
from __future__ import annotations

import base64
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "dashboard" / "index.html"


def cargar_facturas() -> list[dict]:
    rows = []
    with open(DATA / "facturas.csv", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            rows.append(
                {
                    "f": r["fecha_emision"],          # DD/MM/YYYY
                    "d": r["documento"],
                    "c": r["nombre_cliente"],
                    "t": round(float(r["total_operacion"] or 0), 2),
                    "k": round(float(r["cajas"] or 0), 2),
                }
            )
    return rows


def cargar_pagos() -> list[dict]:
    rows = []
    with open(DATA / "pagos_diarios.csv", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            rows.append(
                {
                    "f": r["fecha"],                   # YYYY-MM-DD
                    "e": round(float(r["efectivo"] or 0), 2),
                    "t": round(float(r["transferencia_bancaria"] or 0), 2),
                    "c": round(float(r["cupon"] or 0), 2),
                    "m": round(float(r["total_dia"] or 0), 2),
                    "s": r["estado"],
                }
            )
    return rows


def cargar_clientes() -> list[dict]:
    rows = []
    with open(DATA / "clientes.csv", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            rows.append(
                {
                    "r": r["rif"],
                    "o": r["nombre"],
                    "u": r.get("ultima_venta", "").strip(),
                }
            )
    return rows


def cargar_facturas_rif() -> list[dict]:
    rows = []
    path = DATA / "facturas_rif.csv"
    if not path.is_file():
        return rows
    with open(path, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            rows.append({"r": r["rif"], "o": r["nombre"], "u": r["ultima_fecha"]})
    return rows


def cargar_lineas() -> list[dict]:
    rows = []
    path = DATA / "factura_lineas.csv"
    if not path.is_file():
        return rows
    with open(path, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if r.get("estado_linea") != "VALIDADO":
                continue
            try:
                d, mo, y = r["fecha"].split("/")
            except ValueError:
                continue
            rows.append(
                {
                    "f": f"{y}-{mo}-{d}",
                    "d": r["documento"],
                    "p": r["codigo_producto"],
                    "q": round(float(r["cantidad"] or 0), 2),
                }
            )
    return rows


def cargar_productos() -> list[dict]:
    rows = []
    path = DATA / "productos.csv"
    if not path.is_file():
        return rows
    with open(path, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            rows.append({"c": r["codigo"], "n": r["nombre"], "m": r.get("marca", "")})
    return rows


def cargar_notas() -> dict:
    path = DATA / "notas_clientes.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


HTML = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FYS · Dashboard de Ventas y Cobros</title>
<style>
  :root{
    --bg:#f6f7f9; --fg:#1c2430; --card:#ffffff; --border:#dfe3ea;
    --muted:#64748b; --accent:#1d4ed8; --accent-soft:#e8efff;
    --green:#15803d; --amber:#b45309; --red:#b91c1c;
    --grid:#dfe3ea; --tick:#64748b;
    --chart-1:#1d4ed8; --chart-2:#15803d; --bar:#1d4ed8;
  }
  :root[data-theme="dark"]{
    --bg:#0f1420; --fg:#e6eaf2; --card:#171e2e; --border:#2a3348;
    --muted:#8b96ad; --accent:#6b9aff; --accent-soft:#1c2947;
    --green:#4ade80; --amber:#fbbf24; --red:#f87171;
    --grid:#263048; --tick:#7f8ba3;
    --chart-1:#6b9aff; --chart-2:#4ade80; --bar:#6b9aff;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--fg);
       font:14px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
  .wrap{max-width:1080px;margin:0 auto;padding:20px 16px 40px}
  header{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:18px}
  .logo{height:64px;width:auto;display:block}
  :root[data-theme="dark"] .logo{filter:drop-shadow(0 0 3px rgba(255,255,255,.55))}
  header .titulo{flex:1;min-width:220px}
  header h1{font-size:22px;margin:0 0 2px}
  header .sub{color:var(--muted);margin:0}
  .btn-tema{background:var(--card);color:var(--fg);border:1px solid var(--border);
            border-radius:8px;padding:7px 12px;font-size:13px;cursor:pointer}
  .btn-tema:hover{border-color:var(--accent)}
  .btn-tema.btn-activo{background:var(--red);border-color:var(--red);color:#fff;
                       box-shadow:0 0 0 1px var(--red)}
  .controls{display:flex;flex-wrap:wrap;gap:12px;align-items:end;
            background:var(--card);border:1px solid var(--border);
            border-radius:10px;padding:12px 14px;margin-bottom:16px}
  .controls label{display:flex;flex-direction:column;gap:4px;
                  font-size:12px;color:var(--muted)}
  .controls select{font-size:14px;padding:7px 10px;border:1px solid var(--border);
                   border-radius:8px;background:var(--card);color:var(--fg);min-width:150px}
  .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
        gap:12px;margin-bottom:16px}
  .kpi{background:var(--card);border:1px solid var(--border);border-radius:10px;
       padding:12px 14px}
  .kpi .lab{font-size:12px;color:var(--muted);margin-bottom:4px}
  .kpi .val{font-size:22px;font-weight:600;font-variant-numeric:tabular-nums}
  .kpi .aux{font-size:12px;color:var(--muted);margin-top:2px}
  .kpi .aux.acum{color:var(--accent);font-weight:700;margin-top:6px;font-size:15px;
                 padding-top:5px;border-top:1px dashed var(--border)}
  /* Marcas de clientes */
  tr.marca-baja td{background:rgba(255,80,80,.10)}
  tr.marca-morosidad td{background:rgba(255,170,40,.12)}
  tr.marca-admin td{background:rgba(80,140,255,.10)}
  .nota-badge{display:inline-block;font-size:11px;font-weight:600;border-radius:4px;
              padding:1px 6px;margin-left:6px;vertical-align:middle}
  .nota-badge.baja{background:var(--red);color:#fff}
  .nota-badge.morosidad{background:var(--amber);color:#1a1a1a}
  .nota-badge.admin{background:var(--chart-1);color:#fff}
  .nota-texto{font-size:12px;color:var(--muted);margin-top:3px;max-width:280px;
              white-space:normal;line-height:1.3}
  .marca-select{font-size:12px;padding:3px 6px;border:1px solid var(--border);
                border-radius:6px;background:var(--card);color:var(--fg)}
  .nota-input{font-size:12px;padding:3px 6px;border:1px solid var(--border);
              border-radius:6px;background:var(--card);color:var(--fg);
              width:100%;max-width:240px;box-sizing:border-box}
  .panel{background:var(--card);border:1px solid var(--border);border-radius:10px;
         padding:14px 16px;margin-bottom:16px}
  .panel h2{font-size:15px;margin:0 0 10px}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  @media (max-width:820px){.grid2{grid-template-columns:1fr}}
  table{width:100%;border-collapse:collapse;font-size:13px}
  th,td{padding:7px 8px;border-bottom:1px solid var(--border);text-align:right;
        font-variant-numeric:tabular-nums}
  th:first-child,td:first-child{text-align:left}
  th:nth-child(2),td:nth-child(2){text-align:left}
  th:nth-child(3),td:nth-child(3){text-align:left}
  thead th{color:var(--muted);font-weight:500;font-size:12px}
  tr.total td{font-weight:600;border-top:2px solid var(--border)}
  tr.sub td{color:var(--muted);font-size:12px}
  .fila-ina td{color:var(--muted)}
  .dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;vertical-align:middle}
  .d-ok{background:var(--green)}
  .d-no{background:var(--red)}
  .buscar{width:100%;max-width:340px;padding:7px 10px;border:1px solid var(--border);
          border-radius:8px;background:var(--card);color:var(--fg);font-size:14px;
          margin-bottom:10px}
  .link-cliente{background:none;border:none;color:var(--accent);cursor:pointer;
                font-size:13px;padding:0;text-align:left}
  .link-cliente:hover{text-decoration:underline}
  .detalle-cliente{background:var(--accent-soft);border-radius:8px;
                   padding:10px 12px;margin:2px 0 6px}
  .delta-ok{color:var(--green)}
  .delta-no{color:var(--red)}
  .est-ok{color:var(--green)}
  .est-crit{color:var(--amber)}
  .est-agot{color:var(--red)}
  .meta-row{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
  .meta-progress{flex:1;min-width:180px;height:14px;background:var(--bg);
                 border-radius:8px;overflow:hidden}
  .meta-fill{height:100%;background:var(--green);border-radius:8px;width:0%}
  .app{display:flex;min-height:100vh}
  .sidebar{width:235px;position:sticky;top:0;height:100vh;overflow-y:auto;
           background:var(--card);border-right:1px solid var(--border);
           padding:18px 14px;flex-shrink:0}
  .sidebar .logo{height:52px;margin-bottom:6px}
  .titulo-side{font-size:12px;margin:0 0 14px}
  .nav-secciones{display:flex;flex-direction:column;gap:4px}
  .nav-btn{display:block;width:100%;text-align:left;background:none;border:none;
           color:var(--muted);font-size:14px;padding:10px 12px;border-radius:8px;cursor:pointer}
  .nav-btn:hover{background:var(--accent-soft);color:var(--fg)}
  .nav-btn.is-selected{background:var(--accent);color:#fff;font-weight:500}
  .main{flex:1;min-width:0;padding:16px 20px 40px}
  .topbar{position:sticky;top:0;z-index:5;background:var(--bg);padding:8px 0 12px;
          display:flex;align-items:center;gap:12px;flex-wrap:wrap}
  .topbar .controls{flex:1;margin:0}
  @media (max-width:820px){
    .app{flex-direction:column}
    .sidebar{width:100%;height:auto;position:static;display:flex;align-items:center;
             gap:10px;padding:10px 12px;overflow-x:auto;border-right:none;
             border-bottom:1px solid var(--border)}
    .sidebar .logo{height:36px;margin:0}
    .titulo-side{display:none}
    .nav-secciones{flex-direction:row;flex:1}
    .nav-btn{width:auto;text-align:center;white-space:nowrap;margin:0}
    .main{padding:12px 12px 32px}
    .topbar{position:static}
  }
  .bar-row{display:flex;align-items:center;gap:8px;margin:6px 0}
  .bar-row .name{flex:0 0 34%;font-size:12px;overflow:hidden;
                 text-overflow:ellipsis;white-space:nowrap}
  .bar-track{flex:1;background:var(--bg);border-radius:5px;height:16px;overflow:hidden}
  .bar-fill{height:100%;background:var(--bar);border-radius:5px}
  .bar-fill.monto{background:linear-gradient(90deg, var(--chart-1), var(--bar))}
  .bar-fill.cajas{background:linear-gradient(90deg, var(--chart-2), var(--green))}
  .kpi-donut{display:flex;align-items:center;gap:10px;justify-content:space-between}
  .donut{width:72px;height:72px;flex-shrink:0;display:block;
         filter:drop-shadow(0 2px 3px rgba(0,0,0,.12))}
  .donut-num{font-size:8px;font-weight:600;fill:var(--fg)}
  .bar-val{flex:0 0 88px;text-align:right;font-size:12px;font-variant-numeric:tabular-nums}
  .comi{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}
  .comi-item{border:1px solid var(--border);border-radius:10px;padding:10px 12px}
  .comi-item .lab{font-size:12px;color:var(--muted)}
  .comi-item .val{font-size:18px;font-weight:600;margin-top:2px;
                  font-variant-numeric:tabular-nums}
  .comi-item .val.acum-val{font-size:18px;color:var(--accent);margin-top:6px;
                           padding-top:6px;border-top:1px dashed var(--border)}
  .comi-acum-tag{font-size:11px;font-weight:500;color:var(--muted)}
  .comi-item.est .val{color:var(--amber)}
  .note{font-size:12px;color:var(--muted);margin-top:10px}
  svg{width:100%;height:auto;display:block}
  footer{color:var(--muted);font-size:12px;margin-top:18px}
  .chip{display:inline-block;font-size:11px;padding:1px 8px;border-radius:99px;
        border:1px solid var(--border);color:var(--muted);margin-left:6px}
</style>
</head>
<body>
<div class="app">
  <aside class="sidebar">
    <img class="logo" src="__LOGO__" alt="Logo F&S">
    <p class="sub titulo-side">Ventas y Cobros · TABATA MARCOS</p>
    <nav class="nav-secciones">
      <button type="button" class="nav-btn is-selected" data-seccion="resumen">Resumen</button>
      <button type="button" class="nav-btn" data-seccion="clientes">Clientes</button>
      <button type="button" class="nav-btn" data-seccion="productos">Productos</button>
      <button type="button" class="nav-btn" data-seccion="fritz">FRITZ</button>
      <button type="button" class="nav-btn" data-seccion="despachos">Despachos</button>
    </nav>
  </aside>
  <main class="main">
    <div class="topbar">
      <div class="controls">
        <label>Mes
          <select id="filtro-mes"></select>
        </label>
        <label>Quincena
          <select id="filtro-quincena">
            <option value="0">Todas</option>
            <option value="1">1ª (01–15)</option>
            <option value="2">2ª (16–fin)</option>
          </select>
        </label>
        <button type="button" id="btn-exportar" class="btn-tema">Exportar CSV</button>
      </div>
      <button type="button" id="btn-tema" class="btn-tema" aria-pressed="false">Modo oscuro</button>
    </div>

    <section id="seccion-resumen">
      <div class="kpis" id="kpis"></div>

      <div class="panel" id="panel-comparativa">
        <h2>Comparativa vs período anterior</h2>
        <div class="comi" id="comparativa"></div>
      </div>

      <div class="panel" id="panel-meta">
        <h2>Meta mensual de facturación</h2>
        <div class="meta-row">
          <label>Meta (USD)
            <input type="number" id="meta-input" class="buscar" style="max-width:180px"
                   min="0" step="100" placeholder="0">
          </label>
          <div class="meta-progress"><div class="meta-fill" id="meta-fill"></div></div>
          <div id="meta-texto" class="note"></div>
        </div>
      </div>

      <div class="panel">
        <h2>Comisiones</h2>
        <div class="comi" id="comisiones"></div>
        <p class="note" id="comi-nota"></p>
      </div>

      <div class="panel">
        <h2>Facturado vs cobrado por mes</h2>
        <div id="chart-mensual"></div>
      </div>
      <div class="panel">
        <h2>Cobro diario <span class="chip" id="periodo-diario"></span></h2>
        <div id="chart-diario"></div>
      </div>

      <div class="grid2">
        <div class="panel">
          <h2>Top clientes por monto facturado</h2>
          <div id="top-clientes"></div>
        </div>
        <div class="panel">
          <h2>Top clientes por cajas</h2>
          <div id="top-cajas"></div>
        </div>
      </div>

      <div class="panel">
        <h2>Resumen por mes</h2>
        <div id="tabla-resumen"></div>
      </div>
    </section>

    <section id="seccion-productos" hidden>
      <div class="panel">
        <h2>Productos <span class="chip" id="productos-resumen"></span></h2>
        <div class="meta-row" style="margin-bottom:8px">
          <label>Buscar producto
            <input type="search" id="buscar-producto" class="buscar" style="max-width:300px;margin:0"
                   placeholder="Nombre o código…" autocomplete="off">
          </label>
          <label>Marca
            <select id="filtro-marca" class="buscar" style="max-width:220px;margin:0"></select>
          </label>
        </div>
        <p class="note" id="panel-dejaron" style="margin-bottom:8px"></p>
        <div id="tabla-productos"></div>
      </div>
    </section>

    <section id="seccion-fritz" hidden>
      <div class="panel">
        <h2>Reporte FRITZ <span class="chip" id="fritz-resumen"></span>
          <button type="button" id="btn-exportar-fritz" class="btn-tema" style="float:right;margin-top:-4px">📥 Exportar a Excel</button>
        </h2>
        <p class="note" id="fritz-notas" style="margin-bottom:10px"></p>

        <div id="kpis-fritz" class="kpis" style="margin-bottom:14px"></div>

        <h3 style="margin:14px 0 6px">Ventas FRITZ por mes <span class="chip" id="fritz-chart-resumen"></span></h3>
        <div id="chart-fritz-mensual" style="overflow-x:auto"></div>

        <div class="cols2" style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:18px">
          <div>
            <h3 style="margin:0 0 6px">Top 20 clientes FRITZ</h3>
            <div id="fritz-top-clientes"></div>
          </div>
          <div>
            <h3 style="margin:0 0 6px">Top 20 productos FRITZ</h3>
            <div id="fritz-top-productos"></div>
          </div>
        </div>

        <div class="cols2" style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:18px">
          <div>
            <h3 style="margin:0 0 6px">Clientes que compran FRITZ
              <span class="chip" id="fritz-n-compran"></span></h3>
            <input type="search" id="buscar-fritz-cli" class="buscar" style="max-width:280px"
                   placeholder="Buscar cliente FRITZ…" autocomplete="off">
            <div id="tabla-fritz-clientes" style="margin-top:8px"></div>
          </div>
          <div>
            <h3 style="margin:0 0 6px">Clientes que NO compran FRITZ
              <span class="chip" id="fritz-n-nocompran"></span></h3>
            <input type="search" id="buscar-fritz-nocl" class="buscar" style="max-width:280px"
                   placeholder="Buscar cliente sin FRITZ…" autocomplete="off">
            <div id="tabla-fritz-nocompran" style="margin-top:8px"></div>
          </div>
        </div>

        <h3 style="margin:18px 0 6px">Detalle por producto FRITZ</h3>
        <div id="tabla-fritz-productos"></div>
      </div>
    </section>

    <section id="seccion-despachos" hidden>
      <div class="panel">
        <h2>Despachos <span class="chip" id="despachos-resumen"></span></h2>
        <p class="note" id="despachos-notas" style="margin-bottom:10px"></p>

        <div id="kpis-despachos" class="kpis" style="margin-bottom:14px"></div>

        <h3 style="margin:14px 0 6px">🔍 Consulta por cliente</h3>
        <input type="search" id="buscar-despacho-cliente" class="buscar" style="max-width:340px"
               placeholder="Buscar cliente (ej. MINI SUPER)…" autocomplete="off">
        <div id="despachos-consulta" style="margin-top:10px"></div>

        <div class="cols2" style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:18px">
          <div>
            <h3 style="margin:0 0 6px">📅 Despachos del período</h3>
            <label style="font-weight:400;font-size:.9em">Chofer:
              <select id="filtro-chofer" class="buscar" style="max-width:200px">
                <option value="0">Todos</option>
              </select>
            </label>
            <div id="tabla-despachos" style="margin-top:8px"></div>
          </div>
          <div>
            <h3 style="margin:0 0 6px">⏰ Recordatorios de pago
              <span class="chip" id="despachos-n-recordatorios"></span></h3>
            <p class="note">Próximos a vencer: día 5 (en 2 días) y día 6 (mañana) desde el despacho (plazo 7 días)</p>
            <div id="tabla-recordatorios" style="margin-top:8px"></div>
          </div>
        </div>
      </div>
    </section>

    <section id="seccion-clientes" hidden>
      <div class="panel">
        <h2>Clientes activos y sin compra <span class="chip" id="clientes-resumen"></span></h2>
        <div class="meta-row" style="margin-bottom:8px">
          <input type="search" id="buscar-cliente" class="buscar" style="flex:1;min-width:200px;margin:0"
                 placeholder="Buscar cliente…" autocomplete="off">
          <label>Marcas
            <select id="filtro-marca-cliente" class="buscar" style="max-width:230px;margin:0">
              <option value="0">Todas</option>
              <option value="marcados">Solo marcados</option>
              <option value="baja">⚠ Dar de baja</option>
              <option value="morosidad">💳 No crédito</option>
              <option value="admin">📋 Admin</option>
            </select>
          </label>
          <button type="button" id="btn-filtro-baja" class="btn-tema" title="Mostrar solo clientes marcados para dar de baja">⚠ Dar de baja</button>
          <button type="button" id="btn-exportar-notas" class="btn-tema" title="Descargar marcas y comentarios (JSON)">⬇ Exportar notas</button>
          <button type="button" id="btn-importar-notas" class="btn-tema" title="Cargar marcas y comentarios desde un JSON">⬆ Importar notas</button>
        </div>
        <p class="note" id="notas-leyenda" style="margin-bottom:8px"></p>
        <div id="tabla-clientes"></div>
      </div>
    </section>

    <footer>Fuente: data/facturas.csv y data/pagos_diarios.csv (extracción validada) ·
    Comisiones: 0,3% sobre facturado sin IVA (÷1,16) y 1,2% sobre cobrado.</footer>
  </main>
</div>

<script>
__XLSX_LIB__
</script>
<script>
"use strict";
const DASH_DATA = __DATA__;

const $ = (id) => document.getElementById(id);
const fmtUSD = new Intl.NumberFormat("es", {style:"currency",currency:"USD",minimumFractionDigits:2});
const fmtN = new Intl.NumberFormat("es", {maximumFractionDigits:2});
const MESES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];

function fmtFecha(iso){
  if(!iso) return "–";
  const [y,m,d] = String(iso).split("-");
  return d && m && y ? `${d}/${m}/${y}` : "–";
}

function normCliente(s){
  s = String(s||"").toUpperCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"");
  s = s.replace(/[^A-Z0-9 ]/g," ");
  const toks = s.split(/\s+/).filter(Boolean);
  const out = [];
  let i = 0;
  while(i < toks.length){
    if(toks[i].length===1 && i+1<toks.length && toks[i+1].length===1){
      let j = i;
      while(j < toks.length && toks[j].length===1) j++;
      out.push(toks.slice(i,j).join(""));
      i = j;
    } else { out.push(toks[i]); i++; }
  }
  return out.join(" ");
}
function rifD(s){ return String(s||"").replace(/\D/g,""); }
const CATALOGO = DASH_DATA.clientes.map(c=>({n:normCliente(c.o), o:c.o, u:c.u||"", rif:rifD(c.r), nuevo:false}));
const HIST = new Map();
DASH_DATA.facturas.forEach(f=>{
  const n = normCliente(f.c);
  const [d,mo,y] = String(f.f).split("/");
  const iso = d && mo && y ? `${y}-${mo}-${d}` : "";
  const prev = HIST.get(n) || {o:f.c, u:""};
  if(!HIST.has(n)) HIST.set(n, prev);
  if(iso > prev.u) prev.u = iso;
});
const FACT_RIFS = new Map();
(DASH_DATA.facturas_rif||[]).forEach(x=>{
  const n = normCliente(x.o);
  if(!FACT_RIFS.has(n)) FACT_RIFS.set(n, rifD(x.r));
});
const CAT_SET = new Set(CATALOGO.map(c=>c.n));
const CAT_RIFS = new Set(CATALOGO.map(c=>c.rif).filter(Boolean));
const NUEVOS = [...HIST.entries()].filter(([n])=>{
  if(CAT_SET.has(n)) return false;
  const rif = FACT_RIFS.get(n)||"";
  return !(rif && CAT_RIFS.has(rif));
}).map(([n,v])=>({n, o:v.o, u:v.u, rif:FACT_RIFS.get(n)||"", nuevo:true}));
const UNIVERSO = [...CATALOGO, ...NUEVOS];
const UNIV_BY_RIF = new Map();
const UNIV_BY_NAME = new Map();
UNIVERSO.forEach((u,i)=>{ if(u.rif) UNIV_BY_RIF.set(u.rif,i); UNIV_BY_NAME.set(u.n,i); });
function idxCliente(f){
  const n = normCliente(f.c);
  const rif = FACT_RIFS.get(n)||"";
  if(rif && UNIV_BY_RIF.has(rif)) return UNIV_BY_RIF.get(rif);
  if(UNIV_BY_NAME.has(n)) return UNIV_BY_NAME.get(n);
  const i = UNIVERSO.length;
  UNIVERSO.push({n, o:f.c, u:(HIST.get(n)||{}).u||"", rif, nuevo:true});
  UNIV_BY_NAME.set(n, i);
  if(rif) UNIV_BY_RIF.set(rif, i);
  return i;
}
function mapaActivos(facturas){
  const act = new Map();
  facturas.forEach(f=>{
    const i = idxCliente(f);
    const a = act.get(i) || {fac:0, monto:0, cajas:0};
    a.fac++; a.monto += f.t; a.cajas += f.k;
    act.set(i, a);
  });
  return act;
}
let filtroActual = null;
let estado = {mes:"0", quin:0, facturas:[], pagos:[]};
let seccionActual = "resumen";

// ── Notas y marcas de clientes (incrustadas desde data/notas_clientes.json) ─
const NOTAS_KEY = "fys-notas-clientes";
// NOTAS[idx] = {marca: "baja"|"morosidad"|"admin"|"", comentario: "..."}
let NOTAS = (DASH_DATA.notas && typeof DASH_DATA.notas === "object") ? DASH_DATA.notas : {};
const MARCA_OPCIONES = {
  "": "— Sin marca —",
  "baja": "⚠ Dar de baja",
  "morosidad": "💳 No crédito",
  "admin": "📋 Admin",
};
function guardarNotas(){
  // El archivo compartido se actualiza en la PC al regenerar el dashboard.
  // localStorage sólo conserva cambios temporales mientras se exportan.
  try { localStorage.setItem(NOTAS_KEY, JSON.stringify(NOTAS)); } catch (e) {}
}
function notaDe(i){ return NOTAS[i] || (NOTAS[i] = {marca:"", comentario:""}); }
function notaClase(marca){
  return marca === "baja" ? "marca-baja" : marca === "morosidad" ? "marca-morosidad"
       : marca === "admin" ? "marca-admin" : "";
}
function notaBadge(marca){
  if(marca === "baja") return `<span class="nota-badge baja">⚠ Baja</span>`;
  if(marca === "morosidad") return `<span class="nota-badge morosidad">💳 No crédito</span>`;
  if(marca === "admin") return `<span class="nota-badge admin">📋 Admin</span>`;
  return "";
}
function mostrarSeccion(s){
  seccionActual = s;
  ["resumen","clientes","productos","fritz","despachos"].forEach(k=>{
    const sec = document.getElementById("seccion-" + k);
    if(sec) sec.hidden = (k !== s);
  });
  document.querySelectorAll(".nav-btn").forEach(b=>{
    const sel = b.dataset.seccion === s;
    b.classList.toggle("is-selected", sel);
    b.setAttribute("aria-pressed", String(sel));
  });
  window.scrollTo({top:0});
}

function periodoAnterior(mes, quin){
  if(mes === "0") return null;
  const [y, mm] = mes.split("-").map(Number);
  let py = y, pm = mm - 1;
  if(pm === 0){ pm = 12; py -= 1; }
  return {key:`${py}-${String(pm).padStart(2,"0")}`, quin};
}
function renderComparativa(mes, quin){
  // Compara MESES COMPLETOS (ignora la quincena): mes actual (acumulado si es
  // 2ª quincena) vs el mismo mes del período anterior.
  if(mes === "0"){ $("panel-comparativa").style.display = "none"; return; }
  $("panel-comparativa").style.display = "";
  const prev = periodoAnterior(mes, 0);
  const pf = DASH_DATA.facturas.filter(f=>mesDe(f)===prev.key);
  const pp = DASH_DATA.pagos.filter(p=>mesDePago(p)===prev.key);
  const fMesCur = DASH_DATA.facturas.filter(f=>mesDe(f)===mes);
  const pMesCur = DASH_DATA.pagos.filter(p=>mesDePago(p)===mes);
  const cur = {fac:fMesCur.reduce((s,f)=>s+f.t,0), caj:fMesCur.reduce((s,f)=>s+f.k,0), cob:pMesCur.reduce((s,p)=>s+p.m,0)};
  const ant = {fac:pf.reduce((s,f)=>s+f.t,0), caj:pf.reduce((s,f)=>s+f.k,0), cob:pp.reduce((s,p)=>s+p.m,0)};
  const etiqueta = `${prev.key.slice(5,7)}/${prev.key.slice(0,4)}`;
  const etiquetaCur = mes.slice(5,7) + "/" + mes.slice(0,4);
  if(!ant.fac && !ant.caj && !ant.cob){
    $("comparativa").innerHTML = `<p class="note">Sin datos del mes anterior (${etiqueta}).</p>`;
    return;
  }
  const items = [
    ["Facturado", cur.fac, ant.fac, fmtUSD],
    ["Cajas", cur.caj, ant.caj, fmtN],
    ["Cobrado", cur.cob, ant.cob, fmtUSD],
  ];
  $("comparativa").innerHTML = items.map(([lab, cv, av, fm])=>{
    const d = av > 0 ? ((cv - av) / av) * 100 : (cv > 0 ? 100 : 0);
    const cls = d >= 0 ? "delta-ok" : "delta-no";
    const sign = d >= 0 ? "▲ +" : "▼ ";
    return `<div class="comi-item"><div class="lab">${lab} · ${etiquetaCur} vs ${etiqueta}</div>
      <div class="val">${fm.format(cv)} <span class="${cls}">${sign}${d.toFixed(1)}%</span></div></div>`;
  }).join("");
}

function periodBounds(mes, quin){
  const [y, mm] = mes.split("-").map(Number);
  const last = new Date(y, mm, 0).getDate();
  const d1 = quin === 2 ? 16 : 1;
  const d2 = quin === 1 ? 15 : last;
  return [
    `${y}-${String(mm).padStart(2,"0")}-${String(d1).padStart(2,"0")}`,
    `${y}-${String(mm).padStart(2,"0")}-${String(d2).padStart(2,"0")}`,
  ];
}
const PRIMERA = new Map();
DASH_DATA.facturas.forEach(f=>{
  const i = idxCliente(f);
  const [d,mo,y] = String(f.f).split("/");
  const iso = d && mo && y ? `${y}-${mo}-${d}` : "";
  if(!iso) return;
  const p = PRIMERA.get(i);
  if(!p || iso < p.iso){ PRIMERA.set(i, {iso, monto:f.t}); }
  else if(iso === p.iso){ p.monto += f.t; }
});
function activacionesDelPeriodo(mes, quin){
  let a, b;
  if(mes === "0"){
    let min = "", max = "";
    DASH_DATA.facturas.forEach(f=>{
      const [d,mo,y] = String(f.f).split("/");
      const iso = `${y}-${mo}-${d}`;
      if(!min || iso < min) min = iso;
      if(!max || iso > max) max = iso;
    });
    a = min; b = max;
  } else {
    [a, b] = periodBounds(mes, quin);
  }
  let n = 0, monto = 0;
  PRIMERA.forEach(v=>{ if(v.iso >= a && v.iso <= b){ n++; monto += v.monto; } });
  return {n, monto};
}
function contarNuevos(mesKey, quin){
  const [a, b] = periodBounds(mesKey, quin);
  let n = 0;
  PRIMERA.forEach(v=>{ if(v.iso >= a && v.iso <= b) n++; });
  return n;
}

const PRODUCTO_MAP = new Map((DASH_DATA.productos||[]).map(p=>[p.c, p]));
const LINEAS = DASH_DATA.lineas || [];
const DOC_CLIENTE = new Map();
DASH_DATA.facturas.forEach(f=>{ if(!DOC_CLIENTE.has(f.d)) DOC_CLIENTE.set(f.d, f.c); });
function quinDeISO(f){ return Number(f.slice(8,10)) <= 15 ? 1 : 2; }
function lineasDelPeriodo(mes, quin){
  return LINEAS.filter(l=> (mes === "0" || l.f.startsWith(mes)) && (quin === 0 || quinDeISO(l.f) === quin));
}
function agregarProductos(lineas){
  const agg = new Map();
  lineas.forEach(l=>{
    const a = agg.get(l.p) || {q:0, n:0, cli:new Set()};
    a.q += l.q; a.n++; a.cli.add(DOC_CLIENTE.get(l.d) || "");
    agg.set(l.p, a);
  });
  return agg;
}
let productoAbierto = "";
function htmlDetalleProducto(codigo){
  const porMes = new Map();
  let total = {q:0, n:0};
  LINEAS.forEach(l=>{
    if(l.p !== codigo) return;
    const m = porMes.get(l.f.slice(0,7)) || {q:0, n:0};
    m.q += l.q; m.n++;
    porMes.set(l.f.slice(0,7), m);
    total.q += l.q; total.n++;
  });
  let filas = "";
  [...porMes.keys()].sort().forEach(k=>{
    const m = porMes.get(k);
    filas += `<tr><td>${MESES[Number(k.slice(5))-1]} ${k.slice(0,4)}</td>
      <td>${fmtN.format(m.q)}</td><td>${m.n}</td></tr>`;
  });
  const p = PRODUCTO_MAP.get(codigo) || {n:codigo, m:""};
  return `<div class="detalle-cliente">
    <p><strong>${p.n}</strong> <span class="chip">${p.m || "sin marca"}</span> · ${codigo}</p>
    <p class="note">Total: ${fmtN.format(total.q)} unidades · ${total.n} líneas</p>
    <div class="table-responsive"><table>
      <thead><tr><th>Mes</th><th>Unidades</th><th>Líneas</th></tr></thead>
      <tbody>${filas}</tbody></table></div></div>`;
}
function renderProductos(mes, quin){
  const agg = agregarProductos(lineasDelPeriodo(mes, quin));
  const q = normCliente($("buscar-producto").value);
  const marcaSel = $("filtro-marca").value;
  let lista = [...agg.entries()];
  if(q || marcaSel !== "0"){
    lista = lista.filter(([cod])=>{
      const p = PRODUCTO_MAP.get(cod) || {};
      const txt = normCliente((p.n||"") + " " + cod + " " + (p.m||""));
      return (!q || txt.includes(q)) && (marcaSel === "0" || (p.m||"") === marcaSel);
    });
  }
  lista.sort((a,b)=>b[1].q-a[1].q);
  const top = (q || marcaSel !== "0") ? lista : lista.slice(0,30);
  const unidades = lista.reduce((s,[,a])=>s+a.q,0);
  $("productos-resumen").textContent =
    `${fmtN.format(lista.length)} productos · ${fmtN.format(unidades)} unidades`;
  if(!top.length){
    $("tabla-productos").innerHTML = `<p class="note">Sin productos en el período.</p>`;
  } else {
    const fila = ([cod, a]) => `
      <tr>
        <td><button type="button" class="link-cliente" data-p="${cod}">${(PRODUCTO_MAP.get(cod)||{}).n || cod}</button></td>
        <td>${(PRODUCTO_MAP.get(cod)||{}).m || "—"}</td>
        <td>${fmtN.format(a.q)}</td><td>${a.n}</td><td>${a.cli.size}</td></tr>
      ${cod === productoAbierto ? `<tr class="detalle-row"><td colspan="5">${htmlDetalleProducto(cod)}</td></tr>` : ""}`;
    $("tabla-productos").innerHTML = `<div class="table-responsive"><table>
      <thead><tr><th>Producto</th><th>Marca</th><th>Unidades</th><th>Líneas</th><th>Clientes</th></tr></thead>
      <tbody>${top.map(fila).join("")}</tbody></table></div>`;
    $("tabla-productos").querySelectorAll(".link-cliente").forEach(b=>{
      b.addEventListener("click", ()=>{
        const p = b.dataset.p;
        productoAbierto = productoAbierto === p ? "" : p;
        renderProductos(estado.mes, estado.quin);
        if(productoAbierto){
          const detalle = document.querySelector(".detalle-row");
          if(detalle) detalle.scrollIntoView({block:"nearest"});
        }
      });
    });
  }
  const div = $("panel-dejaron");
  if(mes === "0"){ div.innerHTML = ""; return; }
  const prev = periodoAnterior(mes, quin);
  const aggPrev = agregarProductos(lineasDelPeriodo(prev.key, quin));
  const dejaron = [...aggPrev.entries()].filter(([cod])=>!agg.has(cod) || agg.get(cod).q === 0)
    .sort((a,b)=>b[1].q-a[1].q).slice(0,15);
  div.innerHTML = dejaron.length
    ? `Dejaron de venderse vs ${prev.key.slice(5,7)}: ` +
      dejaron.map(([cod,a])=>`${(PRODUCTO_MAP.get(cod)||{}).n || cod} (${fmtN.format(a.q)})`).join(", ")
    : "Ninguno de los productos del período anterior dejó de venderse.";
}

// ── Reporte FRITZ ──────────────────────────────────────────────────────
function esFritz(l){
  const cod = String(l.p || "").toUpperCase();
  const prod = PRODUCTO_MAP.get(l.p) || {};
  const nom = String(prod.n || "").toUpperCase();
  return cod.startsWith("FRITZ") || nom.startsWith("FRITZ") || (prod.m || "").toUpperCase() === "FRITZ";
}
function lineasFritz(mes, quin){
  return lineasDelPeriodo(mes, quin).filter(esFritz);
}
function agregarFritzClientes(lineas){
  // por cliente (nombre normalizado): unidades, facturas, último mes
  const agg = new Map();
  lineas.forEach(l=>{
    const nom = DOC_CLIENTE.get(l.d) || "¿?";   // nombre como viene en factura
    const n = normCliente(nom);
    const a = agg.get(n) || {o:nom, u:0, fac:0, ult:""};
    a.u += l.q; a.fac++;
    if(l.f.slice(0,7) > a.ult) a.ult = l.f.slice(0,7);
    agg.set(n, a);
  });
  return agg;
}
function agregarFritzProductos(lineas){
  const agg = new Map();
  lineas.forEach(l=>{
    const a = agg.get(l.p) || {q:0, n:0, cli:new Set()};
    a.q += l.q; a.n++; a.cli.add(DOC_CLIENTE.get(l.d) || "");
    agg.set(l.p, a);
  });
  return agg;
}
function renderFritz(mes, quin){
  const lineas = lineasFritz(mes, quin);
  const porCli = agregarFritzClientes(lineas);
  const porProd = agregarFritzProductos(lineas);
  const unidades = lineas.reduce((s,l)=>s+l.q, 0);
  const nFact = new Set(lineas.map(l=>l.d)).size;
  const nClientes = porCli.size;
  const nProd = porProd.size;

  const periodo = mes === "0" ? "todo el período" : `${MESES[Number(mes.slice(5))-1]} ${mes.slice(0,4)}` + (quin ? ` · ${quin}ª quincena` : "");
  $("fritz-resumen").textContent = `${fmtN.format(nProd)} productos · ${fmtN.format(nClientes)} clientes`;
  $("fritz-notas").textContent = `Período: ${periodo} · FRITZ = marca de salsas, vinagres, mayonesas y papas (códigos FRITZ*).`;

  // KPIs
  $("kpis-fritz").innerHTML = `
    <div class="kpi"><div class="kpi-v">${fmtN.format(unidades)}</div><div class="kpi-l">Unidades vendidas</div></div>
    <div class="kpi"><div class="kpi-v">${fmtN.format(nFact)}</div><div class="kpi-l">Facturas con FRITZ</div></div>
    <div class="kpi"><div class="kpi-v">${fmtN.format(nClientes)}</div><div class="kpi-l">Clientes que compran</div></div>
    <div class="kpi"><div class="kpi-v">${fmtN.format(nProd)}</div><div class="kpi-l">Productos FRITZ</div></div>`;

  // Gráfico mensual (unidades FRITZ por mes)
  const meses = [...new Set(LINEAS.filter(esFritz).map(l=>l.f.slice(0,7)))].sort();
  const series = meses.map(m=>{
    const ls = LINEAS.filter(l=>esFritz(l) && l.f.startsWith(m));
    return {m, u: ls.reduce((s,l)=>s+l.q, 0), n: new Set(ls.map(l=>l.d)).size};
  });
  const W=940,H=300,PL=64,PB=40,PT=30;
  const max = Math.max(1, ...series.map(s=>s.u));
  const bw = (W-PL)/Math.max(1,series.length), bwBar = Math.min(46, bw*0.55);
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Unidades FRITZ por mes">
    <title>Unidades FRITZ por mes</title>
    <defs><linearGradient id="gF" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" style="stop-color:var(--chart-1);stop-opacity:1"></stop>
      <stop offset="1" style="stop-color:var(--chart-1);stop-opacity:.4"></stop>
    </linearGradient></defs>`;
  const yN=5;
  for(let i=0;i<=yN;i++){
    const v = max*i/yN, y = H-PB-(H-PB-PT)*i/yN;
    svg += `<line x1="${PL}" y1="${y}" x2="${W}" y2="${y}" stroke="var(--grid)"></line>`;
    svg += `<text x="${PL-8}" y="${y+4}" text-anchor="end" font-size="11" style="fill:var(--tick)">${fmtCompact(v)}</text>`;
  }
  series.forEach((s,i)=>{
    const x = PL + i*bw;
    const h = (s.u/max)*(H-PB-PT);
    const sel = mes === s.m;
    svg += `<rect x="${x+(bw-bwBar)/2}" y="${H-PB-h}" width="${bwBar}" height="${Math.max(0,h)}" fill="url(#gF)" rx="5"${sel?"":" opacity=\".72\""}>
      <title>${s.m}: ${fmtN.format(s.u)} u · ${s.n} facturas</title></rect>`;
    if(h>22) svg += `<text x="${x+bw/2}" y="${H-PB-h-6}" text-anchor="middle" font-size="11" font-weight="500" style="fill:var(--fg)">${fmtCompact(s.u)}</text>`;
    svg += `<text x="${x+bw/2}" y="${H-PB+18}" text-anchor="middle" font-size="12" style="fill:${sel?"var(--fg)":"var(--tick)"}" font-weight="${sel?600:400}">${MESES[Number(s.m.slice(5))-1].slice(0,3)}</text>`;
  });
  svg += "</svg>";
  $("chart-fritz-mensual").innerHTML = svg;
  $("fritz-chart-resumen").textContent = `${fmtN.format(series.reduce((s,x)=>s+x.u,0))} u`;

  // Top 20 clientes
  const topCli = [...porCli.values()].sort((a,b)=>b.u-a.u).slice(0,20);
  const maxCli = Math.max(1, ...topCli.map(c=>c.u));
  $("fritz-top-clientes").innerHTML = topCli.length ? topCli.map(c=>`
    <div class="bar-row">
      <div class="name" title="${c.o}">${c.o}</div>
      <div class="bar-track"><div class="bar-fill monto" style="width:${(c.u/maxCli*100).toFixed(1)}%"></div></div>
      <div class="bar-val">${fmtN.format(c.u)} u</div>
    </div>`).join("") : `<p class="note">Sin clientes FRITZ en el período.</p>`;

  // Top 20 productos
  const topProd = [...porProd.entries()].sort((a,b)=>b[1].q-a[1].q).slice(0,20);
  $("fritz-top-productos").innerHTML = topProd.length ? `<div class="table-responsive"><table>
    <thead><tr><th>Producto</th><th>Unid.</th><th>Fact.</th><th>Clientes</th></tr></thead>
    <tbody>${topProd.map(([cod,a])=>`
      <tr><td>${(PRODUCTO_MAP.get(cod)||{}).n || cod}</td>
      <td>${fmtN.format(a.q)}</td><td>${a.n}</td><td>${a.cli.size}</td></tr>`).join("")}
    </tbody></table></div>` : `<p class="note">Sin productos FRITZ en el período.</p>`;

  // Clientes que compran FRITZ (tabla con buscador)
  const qC = normCliente($("buscar-fritz-cli").value);
  const listaCompran = [...porCli.entries()].filter(([n])=>!qC || n.includes(qC))
    .sort((a,b)=>b[1].u-a[1].u);
  $("fritz-n-compran").textContent = `${fmtN.format(porCli.size)} clientes`;
  $("tabla-fritz-clientes").innerHTML = listaCompran.length ? `<div class="table-responsive"><table>
    <thead><tr><th>Cliente</th><th>Unidades</th><th>Facturas</th><th>Último mes</th></tr></thead>
    <tbody>${listaCompran.slice(0,200).map(([n,a])=>`
      <tr><td>${a.o}</td><td>${fmtN.format(a.u)}</td><td>${a.fac}</td><td>${a.ult || "—"}</td></tr>`).join("")}
    </tbody></table></div>${listaCompran.length>200?`<p class="note">Mostrando 200 de ${fmtN.format(listaCompran.length)}.</p>`:""}`
    : `<p class="note">Sin resultados.</p>`;

  // Clientes que NO compran FRITZ (universo sin compra FRITZ en el período)
  const compranSet = new Set(porCli.keys());
  const qNC = normCliente($("buscar-fritz-nocl").value);
  const noCompran = UNIVERSO.filter(u=>!compranSet.has(u.n) && (!qNC || u.n.includes(qNC)))
    .sort((a,b)=>b.u.localeCompare(a.u));
  $("fritz-n-nocompran").textContent = `${fmtN.format(noCompran.length)} clientes`;
  $("tabla-fritz-nocompran").innerHTML = noCompran.length ? `<div class="table-responsive"><table>
    <thead><tr><th>Cliente</th><th>Última venta</th><th>¿Nuevo?</th></tr></thead>
    <tbody>${noCompran.slice(0,200).map(u=>`
      <tr><td>${u.o}</td><td>${fmtFecha(u.u)}</td><td>${u.nuevo?"(nuevo)":"—"}</td></tr>`).join("")}
    </tbody></table></div>${noCompran.length>200?`<p class="note">Mostrando 200 de ${fmtN.format(noCompran.length)}.</p>`:""}`
    : `<p class="note">Sin resultados.</p>`;

  // Detalle por producto (todos los FRITZ vendidos en el período)
  const detalle = [...porProd.entries()].sort((a,b)=>b[1].q-a[1].q);
  $("tabla-fritz-productos").innerHTML = detalle.length ? `<div class="table-responsive"><table>
    <thead><tr><th>Código</th><th>Producto</th><th>Unidades</th><th>Facturas</th><th>Clientes</th></tr></thead>
    <tbody>${detalle.slice(0,200).map(([cod,a])=>`
      <tr><td>${cod}</td><td>${(PRODUCTO_MAP.get(cod)||{}).n || cod}</td>
      <td>${fmtN.format(a.q)}</td><td>${a.n}</td><td>${a.cli.size}</td></tr>`).join("")}
    </tbody></table></div>` : `<p class="note">Sin productos FRITZ en el período.</p>`;
}

function exportarFritzExcel(){
  const {mes, quin} = estado;
  const lineas = lineasFritz(mes, quin);
  const porCli = agregarFritzClientes(lineas);
  const porProd = agregarFritzProductos(lineas);
  const unidades = lineas.reduce((s,l)=>s+l.q, 0);
  const nFact = new Set(lineas.map(l=>l.d)).size;

  const periodo = mes === "0" ? "Todo el período" :
    `${MESES[Number(mes.slice(5))-1]} ${mes.slice(0,4)}` + (quin ? ` · ${quin}ª quincena` : "");

  if (typeof XLSX === "undefined") {
    alert("La librería de Excel no está disponible en este dashboard.");
    return;
  }
  const wb = XLSX.utils.book_new();
  const num = v => (v == null ? 0 : Number(v));

  // Hoja 1: Resumen
  XLSX.utils.book_append_sheet(wb,
    XLSX.utils.aoa_to_sheet([
      ["Reporte FRITZ"],
      ["Período", periodo],
      ["Unidades vendidas", num(unidades)],
      ["Facturas con FRITZ", num(nFact)],
      ["Clientes que compran", num(porCli.size)],
      ["Productos FRITZ vendidos", num(porProd.size)],
    ]), "Resumen");

  // Hoja 2: Top 20 clientes
  const topCli = [...porCli.values()].sort((a,b)=>b.u-a.u).slice(0,20);
  XLSX.utils.book_append_sheet(wb,
    XLSX.utils.aoa_to_sheet([
      ["Cliente", "Unidades", "Facturas", "Último mes"],
      ...topCli.map(c=>[c.o, num(c.u), num(c.fac), c.ult]),
    ]), "Top 20 Clientes");

  // Hoja 3: Top 20 productos
  const topProd = [...porProd.entries()].sort((a,b)=>b[1].q-a[1].q).slice(0,20);
  XLSX.utils.book_append_sheet(wb,
    XLSX.utils.aoa_to_sheet([
      ["Código", "Producto", "Unidades", "Facturas", "Clientes"],
      ...topProd.map(([cod,a])=>[cod, (PRODUCTO_MAP.get(cod)||{}).n || cod, num(a.q), num(a.n), num(a.cli.size)]),
    ]), "Top 20 Productos");

  // Hoja 4: Clientes que compran FRITZ (todos)
  const compranFilas = [...porCli.values()].sort((a,b)=>b.u-a.u)
    .map(c=>[c.o, num(c.u), num(c.fac), c.ult]);
  XLSX.utils.book_append_sheet(wb,
    XLSX.utils.aoa_to_sheet([
      ["Cliente", "Unidades", "Facturas", "Último mes"],
      ...compranFilas,
    ]), "Clientes FRITZ");

  // Hoja 5: Clientes que NO compran FRITZ
  const compranSet = new Set(porCli.keys());
  const noCompranFilas = UNIVERSO.filter(u=>!compranSet.has(u.n))
    .sort((a,b)=>b.u.localeCompare(a.u))
    .map(u=>[u.o, fmtFecha(u.u), u.nuevo?"(nuevo)":""]);
  XLSX.utils.book_append_sheet(wb,
    XLSX.utils.aoa_to_sheet([
      ["Cliente", "Última venta", "Nuevo"],
      ...noCompranFilas,
    ]), "No compran FRITZ");

  // Hoja 6: Detalle por producto
  const detalleFilas = [...porProd.entries()].sort((a,b)=>b[1].q-a[1].q)
    .map(([cod,a])=>[cod, (PRODUCTO_MAP.get(cod)||{}).n || cod, num(a.q), num(a.n), num(a.cli.size)]);
  XLSX.utils.book_append_sheet(wb,
    XLSX.utils.aoa_to_sheet([
      ["Código", "Producto", "Unidades", "Facturas", "Clientes"],
      ...detalleFilas,
    ]), "Detalle Productos");

  XLSX.writeFile(wb, `fritz_${mes === "0" ? "todo" : mes}${quin ? "_q"+quin : ""}.xlsx`);
}

// ── Despachos (chofer + fecha de salida) ───────────────────────────────
function despachosDelPeriodo(mes, quin){
  return (DASH_DATA.despachos || []).filter(d=>{
    if (mes !== "0") {
      // d.f es dd/mm/yyyy → comparar "yyyy-mm"
      const fMes = d.f.slice(6) + "-" + d.f.slice(3,5);
      if (fMes !== mes) return false;
    }
    if (quin !== 0) {
      const dia = Number(d.f.slice(0,2));
      if (quin === 1 && dia > 15) return false;
      if (quin === 2 && dia <= 15) return false;
    }
    return true;
  });
}

function fechaISO(f){ // dd/mm/yyyy -> Date
  if (!f) return null;
  const [dd,mm,yy] = f.split("/").map(Number);
  return new Date(yy, mm-1, dd);
}

function fmtDespacho(f){ // dd/mm/yyyy -> "vie 21-08-2026"
  const d = fechaISO(f);
  if (!d) return "—";
  const dias = ["dom","lun","mar","mié","jue","vie","sáb"];
  return `${dias[d.getDay()]} ${d.getDate().toString().padStart(2,"0")}-${String(d.getMonth()+1).padStart(2,"0")}-${d.getFullYear()}`;
}

function renderDespachos(mes, quin){
  const hoy = new Date(); hoy.setHours(0,0,0,0);
  const lista = despachosDelPeriodo(mes, quin);
  const nSinChofer = lista.filter(d=>!d.ch || d.ch==="SIN DATO").length;
  const nSinSalida = lista.filter(d=>!d.s).length;

  // KPIs
  const kpi = (v,lab,sub="") => `<div class="kpi"><div class="kpi-v">${v}</div><div class="kpi-l">${lab}</div>${sub?`<div class="kpi-sub">${sub}</div>`:""}</div>`;
  const choferes = [...new Set(lista.map(d=>d.ch).filter(c=>c&&c!=="SIN DATO"))].sort();
  const salidasHoy = lista.filter(d=>d.s && fechaISO(d.s)?.getTime() === hoy.getTime());
  const montosHoy = salidasHoy.reduce((s,d)=>s+d.t,0);
  $("kpis-despachos").innerHTML =
    kpi(lista.length, "Facturas del período") +
    kpi(lista.reduce((s,d)=>s+d.t,0).toLocaleString("es-VE",{minimumFractionDigits:2}), "Monto despachado", "USD") +
    kpi(choferes.length, "Choferes activos", choferes.join(" · ")) +
    kpi(fmtDespacho(lista.filter(d=>d.s).map(d=>d.s).sort().pop()), "Última salida");
  $("despachos-notas").innerHTML =
    (nSinChofer ? `⚠ ${nSinChofer} facturas sin chofer detectado · ` : "") +
    (nSinSalida ? `⚠ ${nSinSalida} sin fecha de salida · ` : "") +
    `Hoy salen: ${salidasHoy.length} facturas (USD ${montosHoy.toLocaleString("es-VE",{minimumFractionDigits:2})})`;

  // Filtro de choferes (conservar selección actual si sigue existiendo)
  const choferSelAnt = $("filtro-chofer").value;
  $("filtro-chofer").innerHTML = `<option value="0">Todos</option>` +
    choferes.map(c=>`<option>${c}</option>`).join("");
  if (choferSelAnt && choferes.includes(choferSelAnt)) {
    $("filtro-chofer").value = choferSelAnt;
  }

  // Consulta por cliente
  const q = ($("buscar-despacho-cliente").value || "").trim().toLowerCase();
  let divConsulta = $("despachos-consulta");
  if (q.length < 3) {
    divConsulta.innerHTML = `<p class="note">Escribe al menos 3 letras para buscar un cliente.</p>`;
  } else {
    // Agrupar por cliente
    const porCli = new Map();
    lista.forEach(d=>{
      if (!d.c.toLowerCase().includes(q)) return;
      if (!porCli.has(d.c)) porCli.set(d.c, []);
      porCli.get(d.c).push(d);
    });
    if (porCli.size === 0) {
      divConsulta.innerHTML = `<p class="note">Sin resultados para "${q}".</p>`;
    } else {
      divConsulta.innerHTML = [...porCli.entries()].slice(0,8).map(([cli, docs])=>{
        const ord = docs.sort((a,b)=>fechaISO(b.f)-fechaISO(a.f));
        const filas = ord.map(d=>{
          const vence = d.s ? new Date(fechaISO(d.s).getTime() + 7*86400000) : null;
          const venceTxt = vence ? fmtDespacho(`${vence.getDate()}/${vence.getMonth()+1}/${vence.getFullYear()}`) : "—";
          return `<tr>
            <td>${d.f}</td><td>${d.d}</td>
            <td><strong>${d.ch||"SIN DATO"}</strong></td>
            <td>${fmtDespacho(d.s)}</td>
            <td style="text-align:right">USD ${d.t.toLocaleString("es-VE",{minimumFractionDigits:2})}</td>
            <td style="text-align:right">${d.k.toFixed(2)}</td>
            <td>${venceTxt}</td>
          </tr>`;
        }).join("");
        const total = docs.reduce((s,d)=>s+d.t,0);
        return `<div class="panel" style="margin-bottom:10px;padding:10px 14px">
          <h4 style="margin:0 0 4px">${cli} <span class="chip">${docs.length} facturas · USD ${total.toLocaleString("es-VE",{minimumFractionDigits:2})}</span></h4>
          <div class="table-responsive"><table><thead><tr>
            <th>Facturación</th><th>Documento</th><th>Chofer</th><th>Salida</th>
            <th>Monto</th><th>Cajas</th><th>Vence pago</th>
          </tr></thead><tbody>${filas}</tbody></table></div></div>`;
      }).join("");
    }
  }

  // Tabla de despachos del período (agrupada por fecha de salida)
  const choferSel = $("filtro-chofer").value;
  let vis = lista.filter(d=>choferSel==="0" || d.ch===choferSel);
  const grupos = new Map();
  vis.forEach(d=>{
    const k = d.s || "sin-fecha";
    if (!grupos.has(k)) grupos.set(k, []);
    grupos.get(k).push(d);
  });
  const filasTabla = [...grupos.entries()].sort((a,b)=> (a[0]==="sin-fecha"?99999999:(fechaISO(a[0])?.getTime()||0)) - (b[0]==="sin-fecha"?99999999:(fechaISO(b[0])?.getTime()||0)))
    .map(([sal, docs])=>{
      const porChofer = new Map();
      docs.forEach(d=>{
        const c = d.ch||"SIN DATO";
        porChofer.set(c, (porChofer.get(c)||0) + d.t);
      });
      const chTxt = [...porChofer.entries()].map(([c,m])=>`${c} (USD ${m.toLocaleString("es-VE",{minimumFractionDigits:0})})`).join("<br>");
      return `<tr>
        <td>${sal==="sin-fecha" ? "—" : fmtDespacho(sal)}</td>
        <td>${docs.length}</td>
        <td>${docs.reduce((s,d)=>s+d.t,0).toLocaleString("es-VE",{minimumFractionDigits:2})}</td>
        <td>${chTxt}</td>
        <td>${docs.map(d=>`${d.c} · ${d.d}`).join("<br>")}</td>
      </tr>`;
    }).join("");
  $("tabla-despachos").innerHTML = vis.length === 0
    ? `<p class="note">Sin despachos en el período.</p>`
    : `<div class="table-responsive"><table><thead><tr>
        <th>Salida</th><th>Facturas</th><th>Monto</th><th>Choferes</th><th>Clientes</th>
      </tr></thead><tbody>${filasTabla}</tbody></table></div>`;

  // Recordatorios de pago: próximos a vencer (plazo 7 días desde despacho).
  // Solo se muestran los que están en Día 6 (vence mañana) y Día 5 (vence en 2 días).
  const recordatorios = [];
  // Los recordatorios son globales: no dependen del mes/quincena elegido.
  (DASH_DATA.despachos || []).forEach(d=>{
    if (!d.s) return;
    const sal = fechaISO(d.s);
    if (!sal) return;
    const vence = new Date(sal.getTime() + 7*86400000);
    const difDias = Math.round((vence.getTime() - hoy.getTime())/86400000);
    if (difDias === 1) recordatorios.push({d, estado:"Día 6 · Vence mañana", orden: 1});
    else if (difDias === 2) recordatorios.push({d, estado:"Día 5 · Vence en 2 días", orden: 2});
  });
  recordatorios.sort((a,b) => a.orden - b.orden || b.d.t - a.d.t);
  $("despachos-n-recordatorios").textContent = recordatorios.length ? `${recordatorios.length} avisos` : "sin avisos";
  $("tabla-recordatorios").innerHTML = recordatorios.length === 0
    ? `<p class="note">Sin vencimientos próximos.</p>`
    : `<div class="table-responsive"><table><thead><tr>
        <th>Cliente</th><th>Despacho</th><th>Vence</th><th>Monto</th><th>Estado</th>
      </tr></thead><tbody>` +
      recordatorios.map(r=>{
        const vence = new Date(fechaISO(r.d.s).getTime() + 7*86400000);
        return `<tr>
          <td>${r.d.c}</td>
          <td>${fmtDespacho(r.d.s)} (${r.d.ch||"—"})</td>
          <td>${fmtDespacho(`${vence.getDate()}/${vence.getMonth()+1}/${vence.getFullYear()}`)}</td>
          <td style="text-align:right">USD ${r.d.t.toLocaleString("es-VE",{minimumFractionDigits:2})}</td>
          <td><strong>${r.estado}</strong></td>
        </tr>`;
      }).join("") + `</tbody></table></div>`;
}

function renderReposicion(mes, quin){
  // Cruzar ventas del período (productos) con existencia del catálogo:
  // productos que se venden bien y tienen stock bajo/crítico (reponer ya),
  // y productos agotados que vendían (reposición prioritaria).
  const ventas = agregarProductos(lineasDelPeriodo(mes, quin));
  const catalogo = DASH_DATA.catalogo || [];
  const exMap = new Map(catalogo.map(x => [x.c, x]));
  const filas = [];
  ventas.forEach((v, cod) => {
    const cat = exMap.get(cod);
    if (!cat || cat.ex === null || cat.ex === undefined) return; // sin dato de existencia
    const ex = cat.ex;
    const rotacion = v.q; // unidades vendidas en el período
    if (ex <= 5 && rotacion > 0) { // stock bajo o crítico + tiene ventas
      filas.push({cod, n: cat.n, cat: cat.cat, m: cat.m || "—", ex, vendido: v.q, facturas: v.n,
                  estado: ex <= 0.05 ? "Agotado" : ex <= 2 ? "Crítico" : "Bajo"});
    }
  });
  filas.sort((a,b) => b.vendido - a.vendido);
  const nAgot = filas.filter(f => f.estado === "Agotado").length;
  const nCrit = filas.filter(f => f.estado === "Crítico").length;
  $("reposicion-resumen").textContent =
    `${fmtN.format(filas.length)} a reponer · ${nAgot} agotados · ${nCrit} críticos`;
  if (!filas.length) {
    $("tabla-reposicion").innerHTML =
      `<p class="note">Sin productos con stock bajo en el período (o sin catálogo cargado).</p>`;
    return;
  }
  const visible = filas.slice(0, 200);
  const fila = f => `<tr>
    <td>${f.cod}</td><td>${f.n}</td><td>${f.cat}</td><td>${f.m}</td>
    <td class="${f.estado === "Agotado" ? "est-agot" : f.estado === "Crítico" ? "est-crit" : "est-ok"}">${f.estado}</td>
    <td>${fmtN.format(f.ex)}</td><td>${fmtN.format(f.vendido)}</td><td>${f.facturas}</td>
  </tr>`;
  $("tabla-reposicion").innerHTML = `<div class="table-responsive"><table>
    <thead><tr><th>Código</th><th>Producto</th><th>Categoría</th><th>Marca</th>
    <th>Estado</th><th>EXIST</th><th>Vendido (período)</th><th>Facturas</th></tr></thead>
    <tbody>${visible.map(fila).join("")}</tbody></table></div>
    <p class="note">Ordenado por unidades vendidas. Reponer primero lo que más rota con stock crítico.</p>`;
}

function renderCatalogo(mes, quin){
  const ventas = agregarProductos(lineasDelPeriodo(mes, quin));
  const q = normCliente($("buscar-catalogo").value);
  const catSel = $("filtro-categoria").value;
  const marcaSel = $("filtro-marca-cat").value;
  let lista = (DASH_DATA.catalogo||[]).filter(x=>{
    if(catSel !== "0" && x.cat !== catSel) return false;
    if(marcaSel !== "0" && (x.m||"") !== marcaSel) return false;
    if(q){
      const txt = normCliente((x.n||"") + " " + x.c + " " + (x.m||""));
      if(!txt.includes(q)) return false;
    }
    return true;
  });
  lista.sort((a,b)=>{
    const va = ventas.get(a.c), vb = ventas.get(b.c);
    const qa = va ? va.q : 0, qb = vb ? vb.q : 0;
    if((qa > 0) !== (qb > 0)) return qa > 0 ? -1 : 1;
    if(qa !== qb) return qb - qa;
    return (a.n||"").localeCompare(b.n||"");
  });
  const nAgot = lista.filter(x=>x.ex !== null && x.ex !== undefined && x.ex <= 0.05).length;
  const nCrit = lista.filter(x=>x.ex !== null && x.ex !== undefined && x.ex > 0.05 && x.ex <= 5).length;
  $("catalogo-resumen").textContent =
    `${fmtN.format(lista.length)} productos · ${nAgot} agotados · ${nCrit} críticos`;
  const vendidosSinCat = [...ventas.keys()].filter(c=>!CATALOGO_CODS.has(c));
  const catSinVenta = lista.filter(x=>!ventas.has(x.c)).length;
  $("catalogo-notas").innerHTML =
    `Se vendió en el período y NO está en el catálogo: <strong>${fmtN.format(vendidosSinCat.length)}</strong> · ` +
    `En catálogo sin ventas en el período: <strong>${fmtN.format(catSinVenta)}</strong>`;
  if(!lista.length){
    $("tabla-catalogo").innerHTML = `<p class="note">Sin resultados.</p>`;
    return;
  }
  const visible = lista.slice(0,400);
  const fila = x => {
    const v = ventas.get(x.c);
    const estado = x.ex === null || x.ex === undefined ? "—" : x.ex <= 0.05 ? "Agotado" : x.ex <= 5 ? "Crítico" : "OK";
    const cls = x.ex === null || x.ex === undefined ? "" : x.ex <= 0.05 ? "est-agot" : x.ex <= 5 ? "est-crit" : "est-ok";
    return `<tr>
      <td>${x.c}</td><td>${x.n}</td><td>${x.cat}</td><td>${x.m || "—"}</td>
      <td>${x.pb !== null && x.pb !== undefined ? fmtUSD.format(x.pb) : "—"}</td>
      <td>${x.pu !== null && x.pu !== undefined ? fmtUSD.format(x.pu) : "—"}</td>
      <td>${x.ex !== null && x.ex !== undefined ? fmtN.format(x.ex) : "—"}</td>
      <td class="${cls}">${estado}</td>
      <td>${v ? fmtN.format(v.q) : "—"}</td><td>${v ? v.n : "—"}</td>
    </tr>`;
  };
  $("tabla-catalogo").innerHTML = `<div class="table-responsive"><table>
    <thead><tr><th>Código</th><th>Producto</th><th>Categoría</th><th>Marca</th>
    <th>Bulto</th><th>Unidad</th><th>EXIST</th><th>Estado</th><th>Vendido</th><th>Facturas</th></tr></thead>
    <tbody>${visible.map(fila).join("")}</tbody></table></div>
    ${lista.length > 400 ? `<p class="note">Mostrando 400 de ${fmtN.format(lista.length)} resultados — usa el buscador o los filtros.</p>` : ""}`;
}

function renderTop(facturas, campo, el){
  const agg = new Map();
  facturas.forEach(f=>{
    const i = idxCliente(f);
    const a = agg.get(i) || {o:UNIVERSO[i].o, monto:0, cajas:0, n:0};
    a.monto += f.t; a.cajas += f.k; a.n += 1;
    agg.set(i, a);
  });
  const top = [...agg.values()].sort((a,b)=>b[campo]-a[campo]).slice(0,20);
  if(!top.length){ el.innerHTML = `<p class="note">Sin facturas en el período.</p>`; return; }
  const max = Math.max(1, ...top.map(a=>a[campo]));
  const fm = campo === "cajas" ? fmtN : fmtUSD;
  el.innerHTML = top.map(a=>`
    <div class="bar-row">
      <div class="name" title="${a.o}">${a.o}</div>
      <div class="bar-track"><div class="bar-fill ${campo === "cajas" ? "cajas" : "monto"}" style="width:${(a[campo]/max*100).toFixed(1)}%"></div></div>
      <div class="bar-val">${fm.format(a[campo])}</div>
    </div>`).join("") +
    `<p class="note">Top 20 por ${campo === "cajas" ? "cajas" : "monto"} · ${fmtN.format(top.length)} de ${agg.size} clientes.</p>`;
}

function renderMeta(mes, facturado){
  const meta = Number($("meta-input").value) || 0;
  if(mes === "0"){
    $("meta-fill").style.width = "0%";
    $("meta-texto").textContent = "Selecciona un mes para ver el avance de la meta.";
    return;
  }
  if(!meta){
    $("meta-fill").style.width = "0%";
    $("meta-texto").textContent = "Define tu meta mensual (USD) para ver el avance.";
    return;
  }
  const pct = Math.min(100, facturado / meta * 100);
  $("meta-fill").style.width = pct.toFixed(1) + "%";
  $("meta-texto").textContent = `Facturado ${fmtUSD.format(facturado)} de ${fmtUSD.format(meta)} (${pct.toFixed(1)}%)`;
}

function exportarCSV(){
  const {mes, quin, facturas, pagos} = estado;
  const facturado = facturas.reduce((s,f)=>s+f.t,0);
  const cajas = facturas.reduce((s,f)=>s+f.k,0);
  const cobrado = pagos.reduce((s,p)=>s+p.m,0);
  const activos = mapaActivos(facturas).size;
  const nuevos = activacionesDelPeriodo(mes, quin).n;
  const lineas = [];
  lineas.push("Resumen FYS - " + (mes === "0" ? "Todos" : mes) + (quin ? " Q" + (quin === 1 ? "1" : "2") : ""));
  lineas.push(["Mes/Quincena", mes === "0" ? "Todos" : mes, "Quincena", quin === 0 ? "Todas" : quin === 1 ? "1ª" : "2ª"].join(";"));
  lineas.push(["Monto facturado", facturado.toFixed(2), "Cajas", cajas.toFixed(2), "Monto cobrado", cobrado.toFixed(2), "Com. 0,3% sin IVA", ((facturado/1.16)*0.003).toFixed(2), "Com. 1,2%", (cobrado*0.012).toFixed(2), "Clientes activos", activos, "Clientes nuevos", nuevos].join(";"));
  lineas.push("");
  lineas.push("TOP CLIENTES POR MONTO");
  lineas.push("Cliente;Monto;Cajas;Facturas");
  const agg = new Map();
  facturas.forEach(f=>{
    const i = idxCliente(f);
    const a = agg.get(i) || {o:UNIVERSO[i].o, monto:0, cajas:0, n:0};
    a.monto += f.t; a.cajas += f.k; a.n += 1;
    agg.set(i, a);
  });
  [...agg.values()].sort((a,b)=>b.monto-a.monto).slice(0,20).forEach(a=>
    lineas.push([`"${a.o}"`, a.monto.toFixed(2), a.cajas.toFixed(2), a.n].join(";")));
  lineas.push("");
  lineas.push("CLIENTES (ACTIVOS / SIN COMPRA)");
  lineas.push("Estado;Cliente;Ultima compra;Facturas;Monto;Cajas");
  const act = mapaActivos(facturas);
  UNIVERSO.forEach((u,i)=>{
    const a = act.get(i);
    lineas.push([a ? "Activo" : "Sin compra", `"${u.o}"`, u.u || "", a ? a.fac : 0, a ? a.monto.toFixed(2) : "", a ? a.cajas.toFixed(2) : ""].join(";"));
  });
  const csv = "\ufeff" + lineas.join("\r\n");
  const blob = new Blob([csv], {type:"text/csv;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = "fys_resumen.csv";
  document.body.appendChild(a); a.click();
  setTimeout(()=>{ URL.revokeObjectURL(url); a.remove(); }, 100);
}

let clienteAbierto = null;
function htmlDetalle(i){
  const u = UNIVERSO[i];
  const porMes = new Map();
  let total = {n:0, monto:0, cajas:0};
  let ult = "";
  DASH_DATA.facturas.forEach(f=>{
    if(idxCliente(f) !== i) return;
    const [d,mo,y] = String(f.f).split("/");
    const iso = `${y}-${mo}-${d}`;
    if(iso > ult) ult = iso;
    const key = `${y}-${mo}`;
    const m = porMes.get(key) || {n:0, monto:0, cajas:0};
    m.n++; m.monto += f.t; m.cajas += f.k;
    porMes.set(key, m);
    total.n++; total.monto += f.t; total.cajas += f.k;
  });
  const prim = PRIMERA.get(i);
  let filas = "";
  [...porMes.keys()].sort().forEach(key=>{
    const m = porMes.get(key);
    filas += `<tr><td>${MESES[Number(key.slice(5))-1]} ${key.slice(0,4)}</td>
      <td>${m.n}</td><td>${fmtUSD.format(m.monto)}</td><td>${fmtN.format(m.cajas)}</td></tr>`;
  });
  const docs = new Set();
  DASH_DATA.facturas.forEach(f=>{ if(idxCliente(f) === i) docs.add(f.d); });
  const prodCli = new Map();
  LINEAS.forEach(l=>{
    if(!docs.has(l.d)) return;
    const a = prodCli.get(l.p) || {q:0, n:0};
    a.q += l.q; a.n++;
    prodCli.set(l.p, a);
  });
  const topP = [...prodCli.entries()].sort((a,b)=>b[1].q-a[1].q).slice(0,15);
  const filasP = topP.map(([cod,a])=>`<tr><td>${(PRODUCTO_MAP.get(cod)||{}).n || cod}</td>
    <td>${(PRODUCTO_MAP.get(cod)||{}).m || "—"}</td>
    <td>${fmtN.format(a.q)}</td><td>${a.n}</td></tr>`).join("");
  return `<div class="detalle-cliente">
    <p><strong>${u.o}</strong>${u.rif ? ` · RIF ${u.rif}` : ""}</p>
    <p class="note">Primera compra: ${fmtFecha(prim ? prim.iso : "")} · Última: ${fmtFecha(ult)} ·
    Total: ${total.n} facturas · ${fmtUSD.format(total.monto)} · ${fmtN.format(total.cajas)} cajas</p>
    <div class="table-responsive"><table>
      <thead><tr><th>Mes</th><th>Facturas</th><th>Monto</th><th>Cajas</th></tr></thead>
      <tbody>${filas}</tbody></table></div>
    ${topP.length ? `<p style="margin-top:8px"><strong>Productos que compró</strong></p>
    <div class="table-responsive"><table>
      <thead><tr><th>Producto</th><th>Marca</th><th>Unidades</th><th>Líneas</th></tr></thead>
      <tbody>${filasP}</tbody></table></div>` : ""}
  </div>`;
}

function aplicarTema(t){
  document.documentElement.dataset.theme = t;
  const btn = $("btn-tema");
  btn.textContent = t === "dark" ? "Modo claro" : "Modo oscuro";
  btn.setAttribute("aria-pressed", String(t === "dark"));
}
function temaInicial(){
  try { return localStorage.getItem("fys-tema") || "light"; } catch(e){ return "light"; }
}
function alternarTema(){
  const t = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  aplicarTema(t);
  try { localStorage.setItem("fys-tema", t); } catch(e){}
}

function parseFactura(f){ // DD/MM/YYYY -> {y,m,d,iso}
  const [d,m,y] = f.f.split("/").map(Number);
  return {y,m,d,iso:`${y}-${String(m).padStart(2,"0")}-${String(d).padStart(2,"0")}`};
}
function mesDe(f){ const p = parseFactura(f); return `${p.y}-${String(p.m).padStart(2,"0")}`; }
function quinDe(f){ return parseFactura(f).d <= 15 ? 1 : 2; }
function mesDePago(p){ return p.f.slice(0,7); }
function quinDePago(p){ return Number(p.f.slice(8,10)) <= 15 ? 1 : 2; }

function filtrar(){
  const mes = $("filtro-mes").value;
  const quin = Number($("filtro-quincena").value);
  const facturas = DASH_DATA.facturas.filter(f =>
    (mes === "0" || mesDe(f) === mes) && (quin === 0 || quinDe(f) === quin));
  const pagos = DASH_DATA.pagos.filter(p =>
    (mes === "0" || mesDePago(p) === mes) && (quin === 0 || quinDePago(p) === quin));
  return {mes, quin, facturas, pagos};
}

function render(){
  const {mes, quin, facturas, pagos} = filtrar();
  // Para 2ª quincena se calcula también el acumulado del mes completo (1ª+2ª)
  const fMes = mes !== "0" ? DASH_DATA.facturas.filter(f => mesDe(f) === mes) : [];
  const pMes = mes !== "0" ? DASH_DATA.pagos.filter(p => mesDePago(p) === mes) : [];
  const usarMes = quin === 2 && mes !== "0";  // ¿mostrar acumulado del mes?
  filtroActual = usarMes ? fMes : facturas;
  estado = {mes, quin, facturas, pagos};
  const facturado = facturas.reduce((s,f)=>s+f.t,0);
  const cajas = facturas.reduce((s,f)=>s+f.k,0);
  const cobrado = pagos.reduce((s,p)=>s+p.m,0);
  const clientes = mapaActivos(facturas).size;
  const totalCli = UNIVERSO.length;
  const inacCli = totalCli - clientes;
  const pctA = totalCli ? Math.round(clientes / totalCli * 100) : 0;
  const pctI = 100 - pctA;
  const activ = activacionesDelPeriodo(mes, quin);

  // Acumulado del mes (para 2ª quincena)
  const facturadoMes = fMes.reduce((s,f)=>s+f.t,0);
  const cajasMes = fMes.reduce((s,f)=>s+f.k,0);
  const cobradoMes = pMes.reduce((s,p)=>s+p.m,0);
  const clientesMes = mapaActivos(fMes).size;
  const activMes = mes !== "0" ? activacionesDelPeriodo(mes, 0) : activ;
  const pctMes = totalCli ? Math.round(clientesMes / totalCli * 100) : 0;
  const acum = usarMes ? {facturadoMes, cajasMes, cobradoMes, clientesMes, activMes,
            pctMes, nFactMes: fMes.length, nPagosMes: pMes.length} : null;
  const acumTxt = (fn) => acum ? `<div class="aux acum">Acum. mes: ${fn()}</div>` : "";
  const acumTxt2 = (fn1, fn2) => acum ? `<div class="aux acum">Acum. mes: ${fn1()} · ${fn2()}</div>` : "";

  // Clientes activos: en 2ª quincena NO se reinician — muestran el acumulado
  // del mes (valor + gráfico).
  const cliAct = usarMes ? clientesMes : clientes;
  const pctAct = usarMes ? pctMes : pctA;
  const inacAct = totalCli - cliAct;
  const pctInact = 100 - pctAct;

  const donut = `<svg class="donut" viewBox="0 0 42 42" role="img" aria-label="Clientes activos ${pctAct}%, sin compra ${pctInact}%">
    <defs>
      <linearGradient id="dg1" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" style="stop-color:var(--green);stop-opacity:1"></stop>
        <stop offset="1" style="stop-color:var(--chart-2);stop-opacity:.45"></stop>
      </linearGradient>
      <linearGradient id="dg2" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" style="stop-color:var(--red);stop-opacity:1"></stop>
        <stop offset="1" style="stop-color:var(--red);stop-opacity:.4"></stop>
      </linearGradient>
    </defs>
    <circle cx="21" cy="21" r="15.915" fill="none" stroke="var(--bg)" stroke-width="6"></circle>
    <circle cx="21" cy="21" r="15.915" fill="none" stroke="url(#dg1)" stroke-width="6"
      stroke-dasharray="${pctAct} ${100 - pctAct}" stroke-linecap="round" transform="rotate(-90 21 21)"></circle>
    <circle cx="21" cy="21" r="15.915" fill="none" stroke="url(#dg2)" stroke-width="6"
      stroke-dasharray="${pctInact} ${100 - pctInact}" stroke-dashoffset="${-pctAct}" stroke-linecap="round" transform="rotate(-90 21 21)"></circle>
    <text x="21" y="22.5" text-anchor="middle" class="donut-num">${pctAct}%</text>
  </svg>`;
  const kpis = [
    {lab:"Monto facturado", val:fmtUSD.format(facturado), aux:`${fmtN.format(facturas.length)} facturas`,
     acum: acumTxt(() => `${fmtUSD.format(acum.facturadoMes)} · ${fmtN.format(acum.nFactMes)} facturas`)},
    {lab:"Número de cajas", val:fmtN.format(cajas), aux:"",
     acum: acumTxt(() => fmtN.format(acum.cajasMes))},
    {lab:"Monto cobrado", val:fmtUSD.format(cobrado), aux:`${fmtN.format(pagos.length)} días de cobro`,
     acum: acumTxt(() => `${fmtUSD.format(acum.cobradoMes)} · ${fmtN.format(acum.nPagosMes)} días`)},
    {lab:"Índice de cobranza", val:facturado > 0 ? `${fmtN.format(cobrado / facturado * 100)}%` : "–", aux:"cobrado / facturado",
     acum: acum && acum.facturadoMes > 0 ? acumTxt(() => `${fmtN.format(acum.cobradoMes / acum.facturadoMes * 100)}% del mes`) : ""},
    {lab:"Clientes activos", val:`${fmtN.format(cliAct)} (${pctAct}%)`,
     aux:`${fmtN.format(inacAct)} sin compra (${pctInact}%)`, donut:true,
     acum: usarMes ? `<div class="aux acum">Acumulado del mes</div>` : ""},
    {lab:"Clientes nuevos", val:fmtN.format(activ.n), aux:`${fmtUSD.format(activ.monto)} en primeras compras`,
     acum: acumTxt2(() => fmtN.format(acum.activMes.n), () => `${fmtUSD.format(acum.activMes.monto)} en primeras compras`)},
  ];
  $("kpis").innerHTML = kpis.map(k=>`<div class="kpi${k.donut ? " kpi-donut" : ""}">
    <div>
      <div class="lab">${k.lab}</div>
      <div class="val">${k.val}</div>
      ${k.aux ? `<div class="aux">${k.aux}</div>` : ""}
      ${k.acum || ""}
    </div>
    ${k.donut ? donut : ""}
  </div>`).join("");

  const c0_3 = (facturado / 1.16) * 0.003;
  const c1_2 = cobrado * 0.012;
  // En 2ª quincena, las comisiones muestran también el acumulado del mes en
  // números grandes (mismo tamaño que el principal).
  const c0_3M = usarMes ? (facturadoMes / 1.16) * 0.003 : null;
  const c1_2M = usarMes ? cobradoMes * 0.012 : null;
  const comiItem = (lab, val, valMes) => `<div class="comi-item"><div class="lab">${lab}</div>
    <div class="val">${val}</div>
    ${valMes !== null ? `<div class="val acum-val">${fmtUSD.format(valMes)} <span class="comi-acum-tag">acumulado del mes</span></div>` : ""}
  </div>`;
  $("comisiones").innerHTML =
    comiItem("0,30% sobre facturado sin IVA (÷1,16)", fmtUSD.format(c0_3), c0_3M) +
    comiItem("1,20% sobre cobrado", fmtUSD.format(c1_2), c1_2M);
  $("comi-nota").textContent =
    "La base imponible no se extrae de los PDFs; la comisión 0,30% se calcula sobre el facturado sin IVA 16% (facturado ÷ 1,16)." +
    (usarMes ? " En 2ª quincena se muestra también la comisión sobre el acumulado del mes." : "");

  renderComparativa(mes, quin);
  renderMeta(mes, usarMes ? facturadoMes : facturado);
  chartMensual(mes);
  chartDiario(mes, quin, pagos);
  renderTop(facturas, "monto", $("top-clientes"));
  renderTop(facturas, "cajas", $("top-cajas"));
  tablaResumen(mes, quin);
  renderProductos(mes, quin);
  renderDespachos(mes, quin);
  renderFritz(mes, quin);
  tablaClientes(usarMes ? fMes : facturas);
}

function buscarClientes(){
  if(filtroActual) tablaClientes(filtroActual);
}

function fmtCompact(n){
  return n >= 1000 ? (n/1000).toFixed(1).replace(".",",") + "k" : fmtN.format(n);
}
function chartMensual(mesSel){
  const meses = [...new Set(DASH_DATA.facturas.map(mesDe))].sort();
  const series = meses.map(m => {
    const fs = DASH_DATA.facturas.filter(f=>mesDe(f)===m);
    const ps = DASH_DATA.pagos.filter(p=>mesDePago(p)===m);
    return {m, fac: fs.reduce((s,f)=>s+f.t,0), cob: ps.reduce((s,p)=>s+p.m,0)};
  });
  const W=940,H=320,PL=68,PB=44,PT=34;
  const max = Math.max(1, ...series.flatMap(s=>[s.fac,s.cob]));
  const bw = (W-PL) / series.length;
  const bwBar = Math.min(34, bw*0.32);
  const g = (bw - bwBar*2) / 2;
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Facturado y cobrado por mes">
    <title>Facturado y cobrado por mes</title>
    <defs>
      <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" style="stop-color:var(--chart-1);stop-opacity:1"></stop>
        <stop offset="1" style="stop-color:var(--chart-1);stop-opacity:.45"></stop>
      </linearGradient>
      <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" style="stop-color:var(--chart-2);stop-opacity:1"></stop>
        <stop offset="1" style="stop-color:var(--chart-2);stop-opacity:.4"></stop>
      </linearGradient>
    </defs>`;
  const yN = 5;
  for(let i=0;i<=yN;i++){
    const v = max*i/yN, y = H-PB-(H-PB-PT)*i/yN;
    svg += `<line x1="${PL}" y1="${y}" x2="${W}" y2="${y}" stroke="var(--grid)" stroke-width="1"></line>`;
    svg += `<text x="${PL-8}" y="${y+4}" text-anchor="end" font-size="11" style="fill:var(--tick)">${fmtCompact(v)}</text>`;
  }
  series.forEach((s,i)=>{
    const x = PL + i*bw;
    const hf = (s.fac/max)*(H-PB-PT), hc = (s.cob/max)*(H-PB-PT);
    const sel = mesSel===s.m;
    const op = sel ? "" : ' opacity=".72"';
    svg += `<rect x="${x+g}" y="${H-PB-hf}" width="${bwBar}" height="${Math.max(0,hf)}" fill="url(#g1)" rx="5"${op}>
      <title>${s.m} facturado ${fmtUSD.format(s.fac)}</title></rect>`;
    svg += `<rect x="${x+g+bwBar+2}" y="${H-PB-hc}" width="${bwBar}" height="${Math.max(0,hc)}" fill="url(#g2)" rx="5"${op}>
      <title>${s.m} cobrado ${fmtUSD.format(s.cob)}</title></rect>`;
    if(hf > 24) svg += `<text x="${x+g+bwBar/2}" y="${H-PB-hf-6}" text-anchor="middle" font-size="11" font-weight="500" style="fill:var(--fg)">${fmtCompact(s.fac)}</text>`;
    if(hc > 24) svg += `<text x="${x+g+bwBar+2+bwBar/2}" y="${H-PB-hc-6}" text-anchor="middle" font-size="11" font-weight="500" style="fill:var(--fg)">${fmtCompact(s.cob)}</text>`;
    svg += `<text x="${x+bw/2}" y="${H-PB+18}" text-anchor="middle" font-size="12"
      style="fill:${sel?"var(--fg)":"var(--tick)"}" font-weight="${sel?600:400}">${MESES[Number(s.m.slice(5))-1].slice(0,3)}</text>`;
  });
  svg += `<rect x="${PL}" y="${PT-16}" width="16" height="9" fill="url(#g1)" rx="2"></rect>
    <text x="${PL+22}" y="${PT-9}" font-size="12" style="fill:var(--tick)">Facturado</text>
    <rect x="${PL+100}" y="${PT-16}" width="16" height="9" fill="url(#g2)" rx="2"></rect>
    <text x="${PL+122}" y="${PT-9}" font-size="12" style="fill:var(--tick)">Cobrado</text>
    <text x="${W}" y="${H-6}" text-anchor="end" font-size="12" style="fill:var(--tick)">USD</text>`;
  svg += "</svg>";
  $("chart-mensual").innerHTML = svg;
}

function chartDiario(mes, quin, pagos){
  $("periodo-diario").textContent = mes==="0" ? "todas las semanas" :
    `${MESES[Number(mes.slice(5))-1]} · ${quin===1?"1ª quincena":quin===2?"2ª quincena":"mes completo"}`;
  if(mes==="0"){
    const porSem = {};
    pagos.forEach(p=>{
      const d = new Date(p.f+"T12:00:00");
      const monday = new Date(d); monday.setDate(d.getDate()-((d.getDay()+6)%7));
      const key = `${monday.getFullYear()}-${String(monday.getMonth()+1).padStart(2,"0")}-${String(monday.getDate()).padStart(2,"0")}`;
      porSem[key] = (porSem[key]||0) + p.m;
    });
    const items = Object.entries(porSem).sort((a,b)=>a[0].localeCompare(b[0]))
      .map(([k,v])=>({lab:`${k.slice(8,10)}/${k.slice(5,7)}`, v}));
    barras(items, $("chart-diario"));
  } else {
    const items = pagos.slice().sort((a,b)=>a.f.localeCompare(b.f))
      .map(p=>({lab:`${p.f.slice(8,10)}/${p.f.slice(5,7)}`, v:p.m}));
    barras(items, $("chart-diario"));
  }
}

function barras(items, el){
  if(!items.length){ el.innerHTML = `<p class="note">Sin cobros en el período.</p>`; return; }
  const max = Math.max(1, ...items.map(i=>i.v));
  const W=940,H=300,PL=68,PB=42,PT=16;
  const n = items.length;
  const bw = (W-PL)/n;
  const bwBar = Math.max(3, Math.min(26, bw*0.62));
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Cobro diario">
    <title>Cobro diario</title>
    <defs>
      <linearGradient id="g3" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" style="stop-color:var(--chart-1);stop-opacity:1"></stop>
        <stop offset="1" style="stop-color:var(--chart-1);stop-opacity:.35"></stop>
      </linearGradient>
    </defs>`;
  for(let i=0;i<=4;i++){
    const v = max*i/4, y = H-PB-(H-PB-PT)*i/4;
    svg += `<line x1="${PL}" y1="${y}" x2="${W}" y2="${y}" stroke="var(--grid)" stroke-width="1"></line>`;
    svg += `<text x="${PL-8}" y="${y+4}" text-anchor="end" font-size="11" style="fill:var(--tick)">${fmtCompact(v)}</text>`;
  }
  const paso = Math.max(1, Math.ceil(n/14));
  items.forEach((it,i)=>{
    const h = (it.v/max)*(H-PB-PT);
    const x = PL + i*bw;
    svg += `<rect x="${x+(bw-bwBar)/2}" y="${H-PB-h}" width="${bwBar}" height="${Math.max(0,h)}" fill="url(#g3)" rx="3">
      <title>${it.lab}: ${fmtUSD.format(it.v)}</title></rect>`;
    if(i%paso===0) svg += `<text x="${x+bw/2}" y="${H-12}" text-anchor="middle" font-size="10" style="fill:var(--tick)">${it.lab}</text>`;
  });
  svg += `<text x="${W}" y="${H-4}" text-anchor="end" font-size="12" style="fill:var(--tick)">USD</text></svg>`;
  el.innerHTML = svg;
}

function tablaResumen(mesSel, quinSel){
  const meses = [...new Set(DASH_DATA.facturas.map(mesDe))].sort();
  let filas = "";
  let tF=0,tK=0,tC=0,tD=0;
  meses.forEach(m=>{
    const fs = DASH_DATA.facturas.filter(f=>mesDe(f)===m);
    const ps = DASH_DATA.pagos.filter(p=>mesDePago(p)===m);
    const q1 = {f:fs.filter(f=>quinDe(f)===1), p:ps.filter(p=>quinDePago(p)===1)};
    const q2 = {f:fs.filter(f=>quinDe(f)===2), p:ps.filter(p=>quinDePago(p)===2)};
    const fila = (label, q) => {
      const fac = q.f.reduce((s,f)=>s+f.t,0), k = q.f.reduce((s,f)=>s+f.k,0);
      const cob = q.p.reduce((s,p)=>s+p.m,0), dias = q.p.length;
      const nuevos = contarNuevos(m, label === "1ª" ? 1 : label === "2ª" ? 2 : 0);
      if(quinSel!==0 && !((label==="1ª"&&quinSel===1)||(label==="2ª"&&quinSel===2))) return;
      filas += `<tr${label==="Total"?" class=\"total\"":label==="Mes"?" class=\"sub\"":""}>
        <td>${m.slice(5)} ${label}</td>
        <td>${fmtUSD.format(fac)}</td><td>${fmtN.format(k)}</td><td>${nuevos}</td>
        <td>${fmtUSD.format(cob)}</td><td>${fac > 0 ? fmtN.format(cob / fac * 100) + "%" : "–"}</td>
        <td>${fmtUSD.format(fac/1.16*0.003)}</td>
        <td>${fmtUSD.format(cob*0.012)}</td><td>${dias}</td></tr>`;
    };
    fila("1ª", q1); fila("2ª", q2); fila("Total", {f:fs,p:ps});
    if(mesSel==="0" || mesSel===m){
      const fac = fs.reduce((s,f)=>s+f.t,0), cob = ps.reduce((s,p)=>s+p.m,0);
      tF+=fac; tK+=fs.reduce((s,f)=>s+f.k,0); tC+=cob; tD+=ps.length;
    }
  });
  if(mesSel!=="0"){
    filas += `<tr class="total"><td>Acumulado filtro</td><td>${fmtUSD.format(tF)}</td>
      <td>${fmtN.format(tK)}</td><td>${contarNuevos(mesSel, quinSel === 0 ? 0 : quinSel)}</td><td>${fmtUSD.format(tC)}</td>
      <td>${tF > 0 ? fmtN.format(tC / tF * 100) + "%" : "–"}</td>
      <td>${fmtUSD.format(tF/1.16*0.003)}</td><td>${fmtUSD.format(tC*0.012)}</td><td>${tD}</td></tr>`;
  }
  $("tabla-resumen").innerHTML = `<div class="table-responsive">
    <table>
      <thead><tr><th>Mes</th><th>Facturado</th><th>Cajas</th><th>Nuevos</th><th>Cobrado</th><th>Cobranza</th>
      <th>Com. 0,3%</th><th>Com. 1,2%</th><th>Días con cobro</th></tr></thead>
      <tbody>${filas}</tbody></table></div>`;
}

function tablaClientes(facturas){
  const q = normCliente($("buscar-cliente").value);
  const fMarca = $("filtro-marca-cliente").value;
  const activos = mapaActivos(facturas);
  const lista = UNIVERSO.map((u,i)=>{
    const a = activos.get(i);
    return {
      idx: i,
      o: u.o,
      u: u.u,
      nuevo: u.nuevo,
      activo: !!a,
      fac: a ? a.fac : 0,
      monto: a ? a.monto : 0,
      cajas: a ? a.cajas : 0,
    };
  }).filter(x=>!q || normCliente(x.o).includes(q));
  // Filtro por marca/notas
  const listaF = lista.filter(x=>{
    const n = notaDe(x.idx);
    if(fMarca === "0") return true;
    if(fMarca === "marcados") return n.marca !== "" || (n.comentario || "").trim() !== "";
    return n.marca === fMarca;
  });
  const activosL = listaF.filter(x=>x.activo).sort((a,b)=>b.monto-a.monto);
  const inactivosL = listaF.filter(x=>!x.activo).sort((a,b)=>a.o.localeCompare(b.o));
  const nMarca = (m)=>NOTAS && Object.values(NOTAS).filter(n=>n && n.marca===m).length;
  $("clientes-resumen").textContent =
    `${fmtN.format(activosL.length)} activos · ${fmtN.format(inactivosL.length)} sin compra`;
  // Botón "⚠ Dar de baja" resaltado cuando el filtro está activo + conteo
  const nBaja = nMarca("baja");
  const btnBaja = $("btn-filtro-baja");
  btnBaja.textContent = nBaja > 0 ? `⚠ Dar de baja (${nBaja})` : "⚠ Dar de baja";
  btnBaja.classList.toggle("btn-activo", fMarca === "baja");
  $("notas-leyenda").innerHTML =
    `Marcas guardadas: ⚠ <b>${nMarca("baja")}</b> dar de baja · 💳 <b>${nMarca("morosidad")}</b> no crédito · 📋 <b>${nMarca("admin")}</b> admin — se incrustan al regenerar el dashboard en la PC.`;
  const fila = x => {
    const n = notaDe(x.idx);
    const cls = notaClase(n.marca);
    const marcaSel = Object.entries(MARCA_OPCIONES).map(([v,lab])=>
      `<option value="${v}" ${n.marca===v?"selected":""}>${lab}</option>`).join("");
    const comentario = (n.comentario || "").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    return `<tr class="${x.activo?"":"fila-ina"} ${cls}">
    <td><span class="dot ${x.activo?"d-ok":"d-no"}"></span>${x.activo?"Activo":"Sin compra"}${x.activo&&x.nuevo?' <span style="color:var(--muted)">(nuevo)</span>':""}${notaBadge(n.marca)}</td>
    <td><button type="button" class="link-cliente" data-i="${x.idx}">${x.o}</button>
        ${n.comentario ? `<div class="nota-texto">${comentario}</div>` : ""}</td>
    <td>${fmtFecha(x.u)}</td>
    <td>${x.activo?x.fac:"–"}</td>
    <td>${x.activo?fmtUSD.format(x.monto):"–"}</td>
    <td>${x.activo?fmtN.format(x.cajas):"–"}</td>
    <td><select class="marca-select" data-marca="${x.idx}">${marcaSel}</select></td>
    <td><input class="nota-input" data-nota="${x.idx}" value="${comentario}" placeholder="Comentario…" autocomplete="off"></td></tr>
    ${x.idx === clienteAbierto ? `<tr class="detalle-row"><td colspan="8">${htmlDetalle(x.idx)}</td></tr>` : ""}`;
  };
  $("tabla-clientes").innerHTML = `<div class="table-responsive">
    <table>
      <thead><tr><th>Estado</th><th>Cliente</th><th>Última compra</th><th>Facturas</th><th>Monto</th><th>Cajas</th><th>Marca</th><th>Comentario</th></tr></thead>
      <tbody>${activosL.map(fila).join("")}${inactivosL.map(fila).join("")}</tbody>
    </table></div>`;
  $("tabla-clientes").querySelectorAll(".marca-select").forEach(sel=>{
    sel.addEventListener("change", ()=>{
      notaDe(Number(sel.dataset.marca)).marca = sel.value;
      guardarNotas();
      tablaClientes(filtroActual);
    });
  });
  $("tabla-clientes").querySelectorAll(".nota-input").forEach(inp=>{
    inp.addEventListener("change", ()=>{
      notaDe(Number(inp.dataset.nota)).comentario = inp.value.trim();
      guardarNotas();
      tablaClientes(filtroActual);
    });
  });
  $("tabla-clientes").querySelectorAll(".link-cliente").forEach(b=>{
    b.addEventListener("click", ()=>{
      const i = Number(b.dataset.i);
      clienteAbierto = clienteAbierto === i ? null : i;
      tablaClientes(filtroActual);
      if(clienteAbierto !== null){
        const detalle = document.querySelector(".detalle-row");
        if(detalle) detalle.scrollIntoView({block:"nearest"});
      }
    });
  });
}

function exportarNotas(){
  // Exporta marcas + comentarios con el nombre del cliente (legible y portable)
  const datos = {};
  Object.entries(NOTAS).forEach(([idx, n])=>{
    if(!n || (!n.marca && !(n.comentario||"").trim())) return;
    const i = Number(idx);
    datos[idx] = {cliente: UNIVERSO[i] ? UNIVERSO[i].o : "", marca: n.marca || "", comentario: n.comentario || ""};
  });
  const blob = new Blob([JSON.stringify(datos, null, 2)], {type:"application/json"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `fys_notas_clientes_${new Date().toISOString().slice(0,10)}.json`;
  a.click();
  URL.revokeObjectURL(a.href);
}

function importarNotas(){
  const inp = document.createElement("input");
  inp.type = "file";
  inp.accept = ".json,application/json";
  inp.addEventListener("change", ()=>{
    const f = inp.files && inp.files[0];
    if(!f) return;
    const lector = new FileReader();
    lector.onload = ()=>{
      try {
        const datos = JSON.parse(lector.result);
        let n = 0;
        Object.entries(datos).forEach(([idx, d])=>{
          const i = Number(idx);
          if(!Number.isFinite(i) || i < 0 || i >= UNIVERSO.length || !d) return;
          const marca = ["", "baja", "morosidad", "admin"].includes(d.marca) ? d.marca : "";
          NOTAS[i] = {marca, comentario: String(d.comentario || "").trim()};
          n++;
        });
        guardarNotas();
        alert(`Importadas ${n} notas de clientes.`);
        tablaClientes(filtroActual || estado.facturas);
      } catch (e) {
        alert("No se pudo leer el archivo: no es un JSON válido de notas.");
      }
    };
    lector.readAsText(f);
  });
  inp.click();
}

function init(){
  aplicarTema(temaInicial());
  const meses = [...new Set(DASH_DATA.facturas.map(mesDe))].sort();
  $("filtro-mes").innerHTML = `<option value="0">Todos</option>` +
    meses.map(m=>`<option value="${m}">${MESES[Number(m.slice(5))-1]} ${m.slice(0,4)}</option>`).join("");
  $("filtro-mes").addEventListener("change", render);
  $("filtro-quincena").addEventListener("change", render);
  $("buscar-cliente").addEventListener("input", buscarClientes);
  $("filtro-marca-cliente").addEventListener("change", buscarClientes);
  $("btn-filtro-baja").addEventListener("click", ()=>{
    const sel = $("filtro-marca-cliente");
    sel.value = sel.value === "baja" ? "0" : "baja";
    buscarClientes();
  });
  $("btn-exportar-notas").addEventListener("click", exportarNotas);
  $("btn-importar-notas").addEventListener("click", importarNotas);
  $("btn-tema").addEventListener("click", alternarTema);
  const metaGuardada = Number(localStorage.getItem("fys-meta")) || 0;
  if(metaGuardada) $("meta-input").value = metaGuardada;
  $("meta-input").addEventListener("input", ()=>{
    localStorage.setItem("fys-meta", $("meta-input").value);
    render();
  });
  $("btn-exportar").addEventListener("click", exportarCSV);
  const marcas = [...new Set((DASH_DATA.productos||[]).map(p=>p.m).filter(Boolean))].sort();
  $("filtro-marca").innerHTML = `<option value="0">Todas</option>` +
    marcas.map(m=>`<option>${m}</option>`).join("");
  $("buscar-producto").addEventListener("input", ()=>renderProductos(estado.mes, estado.quin));
  $("filtro-marca").addEventListener("change", ()=>renderProductos(estado.mes, estado.quin));
  $("buscar-fritz-cli").addEventListener("input", ()=>renderFritz(estado.mes, estado.quin));
  $("buscar-fritz-nocl").addEventListener("input", ()=>renderFritz(estado.mes, estado.quin));
  $("btn-exportar-fritz").addEventListener("click", exportarFritzExcel);
  $("buscar-despacho-cliente").addEventListener("input", ()=>renderDespachos(estado.mes, estado.quin));
  $("filtro-chofer").addEventListener("change", ()=>renderDespachos(estado.mes, estado.quin));
  document.querySelectorAll(".nav-btn").forEach(b=>{
    b.addEventListener("click", ()=>mostrarSeccion(b.dataset.seccion));
  });
  mostrarSeccion("resumen");
  render();
}
init();
</script>
</body>
</html>
"""


def _xlsx_lib() -> str:
    """Devuelve la librería SheetJS incrustada (dashboard autocontenido)."""
    lib = ROOT / "dashboard" / "assets" / "xlsx.full.min.js"
    if not lib.is_file():
        return "/* xlsx lib no disponible */"
    src = lib.read_text(encoding="utf-8")
    # Evitar que "</script>" dentro de la librería rompa el HTML
    return src.replace("</script>", "<\\/script>")


def cargar_despachos() -> list[dict]:
    """Carga data/despachos.csv (chofer + fecha de salida por factura)."""
    p = DATA / "despachos.csv"
    if not p.is_file():
        return []
    with open(p, encoding="utf-8-sig") as f:
        return [
            {
                "f": r["fecha_facturacion"],       # fecha facturación dd/mm/yyyy
                "d": r["documento"],
                "c": r["nombre_cliente"],
                "r": r["rif"],
                "t": float(r["total_operacion"] or 0),
                "k": float(r["cajas"] or 0),
                "ch": r["chofer"],
                "s": r["fecha_salida"],            # dd/mm/yyyy o ""
                "di": int(r["dias_espera"]) if r["dias_espera"] not in ("", None) else None,
            }
            for r in csv.DictReader(f)
        ]


def main():
    facturas = cargar_facturas()
    pagos = cargar_pagos()
    clientes = cargar_clientes()
    payload = {
        "facturas": facturas,
        "pagos": pagos,
        "clientes": clientes,
        "facturas_rif": cargar_facturas_rif(),
        "lineas": cargar_lineas(),
        "productos": cargar_productos(),
        "notas": cargar_notas(),
        "despachos": cargar_despachos(),
    }
    logo_path = ROOT / "dashboard" / "assets" / "logo-fs.png"
    if logo_path.is_file():
        logo_b64 = base64.b64encode(logo_path.read_bytes()).decode("ascii")
        logo_src = f"data:image/png;base64,{logo_b64}"
    else:
        logo_src = ""
    html = (
        HTML.replace("__DATA__", json.dumps(payload, ensure_ascii=False))
        .replace("__LOGO__", logo_src)
        .replace("__XLSX_LIB__", _xlsx_lib())
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    total_f = round(sum(f["t"] for f in facturas), 2)
    total_k = round(sum(f["k"] for f in facturas), 2)
    total_c = round(sum(p["m"] for p in pagos), 2)
    print(f"Dashboard generado: {OUT}")
    print(f"Facturas: {len(facturas)} | Facturado: {total_f} | Cajas: {total_k}")
    print(f"Días de cobro: {len(pagos)} | Cobrado: {total_c}")


if __name__ == "__main__":
    main()
