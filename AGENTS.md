# AGENTS — Briefing del proyecto FYS

Este archivo es la puerta de entrada para cualquier agente que continúe el
proyecto. Es el proyecto **canónico y limpio** de FYS (vendedor TABATA
MARCOS). Todo lo demás en la raíz de FYS son proyectos viejos o descartables.

## Qué es

- Datos comerciales **validados** de enero a agosto 2026: facturas (fecha,
  documento, cliente, RIF, total operación, cajas), pagos procesados por día,
  clientes (master), productos por factura y catálogos de venta.
- Dashboard interactivo autocontenido (`dashboard/index.html`), que funciona
  en PC, tablet y desde Google Drive (logo y catálogo embebidos). No requiere
  Chrome: abre con Edge o cualquier navegador.

## Estado actual (21-08-2026)

| Dato | Valor |
|---|---|
| Facturas | 889 en 136/136 PDFs validados (1 duplicado eliminado) |
| Monto facturado | USD 348.364,21 |
| Cajas | 11.442,98 |
| Pagos | 145 capturas (131 VERIFICADO + 14 SOLO_TOTAL, 0 sin total) |
| Crédito | USD 333.922,40 |
| Clientes | 142 (131 del master PDF + 11 nuevos de facturas) |
| Detalle de productos | 890/890 (100 %) · 9.567 líneas · 1.218 productos |
| Catálogos | 1.447 productos (alimentos 593, limpieza 597, confitería 257) |
| Secciones dashboard | Resumen, Clientes, Productos, FRITZ, Despachos |
| Repositorio git | Rama master; cada corrida registra un commit automático |

## Dónde está cada cosa

- `data/*.csv` — datos finales (facturas, pagos_diarios, clientes,
  master_clientes, factura_lineas, productos, marcas, validaciones,
  corridas_log).
- `dashboard/index.html` — dashboard (se regenera, no se edita a mano); las
  notas de clientes se incrustan desde `data/notas_clientes.json`.
- `src/run_pipeline.py` — **orquestador completo** (run_all + productos +
  master + dashboard) con log en `data/corridas_log.csv`. USAR ESTE.
- `Actualizar_Dashboard.bat` — **launcher de doble clic para el uso diario**
  (respaldo + pipeline + chequeo + commit git). Hay un lanzador igual en la
  raíz de FYS que delega a este.
- `src/backup_data.py` — respaldo previo de `data/*.csv|json` a
  `data/backup/<fecha>/` (conserva los últimos 15); si falla, aborta.
- `src/git_commit_corrida.py` — commit automático con resumen de la corrida
  (facturas, monto, capturas, crédito, resultado del chequeo).
- `src/run_all.py` — extrae facturas y pagos desde las carpetas fuente y
  regenera `data/`.
- `src/build_dashboard.py` — regenera `dashboard/index.html`.
- `src/productos.py`, `src/generar_master.py` — capa de productos y master.
- `src/ingesta.py` — Fase A: mueve archivos nuevos de `FYS\Entrada\` a las
  carpetas mensuales y corre el pipeline.
- `src/ingesta_cron.py` — envoltorio para el cron de Hermes (notifica por
  WhatsApp solo cuando hay novedades).
- `src/check_corrida.py` — chequeo de calidad post-corrida.
- `src/fys_consulta.py` — CLI de consultas para el bot de WhatsApp.
- `src/run_clean.py` — wrapper que limpia `PYTHONPATH` y corre cualquier
  script del proyecto.
- `CATALOGOS_VENTAS/` — parser de catálogos, `catalogo_productos.csv` y
  `ANALISIS_CATALOGOS.md`.
- Carpetas fuente en la raíz de FYS: `Facturas\2026-MM\` y
  `Pagos_procesados\2026-MM\`.

## Cómo actualizar (uso diario, sin agente)

```bash
# Doble clic en Actualizar_Dashboard.bat (raíz de FYS o del proyecto).
# Equivale a, en orden:
#   1. src/backup_data.py        respaldo de data/ (aborta si falla)
#   2. src/run_pipeline.py       pipeline completo con log de corrida
#   3. src/check_corrida.py      puerta de calidad
#   4. src/git_commit_corrida.py commit automático ("Corrida ... check=OK")
```

ANTES de ejecutarlo hay que mover a mano los archivos nuevos de
`Entrada\` a su carpeta mensual (`Facturas\2026-MM` /
`Pagos_procesados\2026-MM`): la ingesta automática quedó como capa
opcional. El pipeline solo procesa archivos nuevos (caché por SHA-256 en
`data/*_cache.json`); una corrida sin novedades tarda segundos.

Si el chequeo detecta problemas el commit se registra igual pero marcado
`check=PROBLEMAS`; si el pipeline falla NO se hace commit y el estado
anterior sigue intacto en git + `data/backup/`.

### Regeneración manual (desarrollo)

```bash
# SIEMPRE limpiar PYTHONPATH (PIL roto del venv Hermes degrada el OCR):
unset PYTHONPATH
python src/run_pipeline.py        # todo, con log de corrida

# o equivalente sin acordarse:
python src/run_clean.py src/run_pipeline.py
```

Usar el Python del runtime empaquetado de Codex:
`C:\Users\Marcos\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`
Tesseract: `C:\Program Files\Tesseract-OCR\tesseract.exe`.

⚠️ **Sin `unset PYTHONPATH`** el OCR de pagos corre sin preprocesamiento y
produce SIN_TOTAL (regresión grave: el crédito cae ~USD 50K). Ver
HISTORIA_PROYECTO.md Fase 9.

## Ingesta automática (Fase A) — OPCIONAL

- Carpeta de entrada: `FYS\Entrada\` (PDFs de facturas y capturas de pago).
- El flujo diario es **manual**: mover archivos a las carpetas mensuales y
  ejecutar `Actualizar_Dashboard.bat`.
- `src/ingesta.py` sigue disponible (mueve + corre pipeline) y
  `src/ingesta_cron.py` para el cron de Hermes (notifica por WhatsApp al
  584148237433 solo si hay novedades o errores).
- Como la deduplicación de la ingesta ya no corre siempre, `pagos.py`
  avisa en cada corrida si dos capturas tienen el mismo SHA-256 (mismo
  contenido con distinto nombre) y `check_corrida.py` lo marca como error.

## Bot de WhatsApp (consultas FYS)

- El bot responde consultas con `src/fys_consulta.py` (skill `fys-consultas`):
  facturado, cobrado, top clientes/productos, comisiones, pendientes.
- Comandos: `facturado --mes 2026-07`, `cobrado`, `top-clientes --n 5`,
  `cliente "MINI SUPER"`, `comisiones`, `pendientes`, `resumen`.
- Números autorizados: 584129769561, 584148237433, 584148616638.
- Notificaciones de Hermes van al 584148237433 (WHATSAPP_HOME_CHANNEL).

## Reglas no negociables

- Los Excel **nunca** alimentan el master; solo el PDF del master + clientes
  nuevos detectados en facturas.
- `CXC.*` (cuentas por cobrar) y `MASTER*` no son listados de ventas: se
  excluyen.
- Si una captura de pago está duplicada (mismo archivo/SHA), eliminar la
  copia y conservar una sola.
- No cambiar dependencias ni romper lo validado; cada fase nueva es una capa
  adicional.
- Comisiones finales: **0,3 % del facturado ÷ 1,16 (IVA)** y **1,2 % del
  cobrado**.
- Un mismo número de documento es **una sola venta**: deduplicar por
  (fecha, documento); el duplicado queda en `resumen_global.json`.
- **Siempre limpiar `PYTHONPATH`** al ejecutar el pipeline desde Hermes.
- Trabajar solo dentro de `FYS_DATOS_VALIDADOS` salvo que el usuario indique
  otra cosa; la raíz de FYS contiene proyectos viejos/descartables (ARES,
  ARES_v2, extractor-facturas-criticas, extraccion-validada-fys, etc.) que no
  se tocan sin pedido explícito.
- **Documentar siempre**: cualquier cambio va al historial
  (`docs/HISTORIA_PROYECTO.md`), metodología y este briefing.

## Próximos pasos (pendientes)

1. ~~Ingesta automática (Fase A)~~ ✅ Implementada; desde el 21-08-2026 el
   flujo diario es **manual** (mover archivos + `Actualizar_Dashboard.bat`)
   y la ingesta/cron queda como capa opcional.
2. **Histórico de catálogos**: snapshots diarios con alertas de agotados,
   nuevos y cambios de precio (pospuesto por decisión de Marcos).
3. **Afinar marcas**: revisar claves mal mapeadas (p. ej. "EVERY NIGHT").
4. Panel de reposición y catálogo de inventario: archivados por ahora; el
   flujo actual conserva el análisis de Productos sin depender de existencias.
5. **Nube/VPS**: Contabo + carpeta Drive (rclone) + bot de WhatsApp.
6. Confirmar con Marcos la semántica de `EXIST` y los precios del catálogo.
7. Bot de WhatsApp con consultas FYS — ✅ CLI listo + skill `fys-consultas`;
   falta probar en vivo.

## Documentación de referencia

- `docs/HISTORIA_PROYECTO.md` (y `docs/historia_proyecto.html`) — recorrido
  completo de la conversación: qué se pidió, qué se hizo y por qué.
- `docs/METODOLOGIA.md` — reglas de extracción y validación en detalle.
- `README.md` — descripción general y estructura.
