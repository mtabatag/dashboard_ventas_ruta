# FYS DATOS VALIDADOS

Proyecto autocontenido con los extractores mínimos y los datos finales
**validados** de facturación y pagos de FYS (vendedor TABATA MARCOS) para
enero–agosto 2026. Es la base limpia para el dashboard.

## Qué contiene

| Carpeta / archivo | Descripción |
|---|---|
| `src/facturas.py` | Extractor de facturas (PDF) → fecha, documento, cliente, total operación y cajas (deduplica por fecha+documento). |
| `src/pagos.py` | Extractor de pagos procesados (capturas) → filas y total del día por captura. |
| `src/run_all.py` | Orquesta facturas + pagos y regenera `data/`. |
| `src/run_pipeline.py` | **Orquestador completo** (run_all + productos + despachos + master + dashboard) con log en `data/corridas_log.csv`. |
| `Actualizar_Dashboard.bat` | **Uso diario**: respaldo de `data/` + pipeline + chequeo de calidad + commit automático en git. |
| `src/backup_data.py` | Respaldo previo de `data/*.csv|json` a `data/backup/<fecha>/` (conserva los últimos 15). |
| `src/git_commit_corrida.py` | Commit automático con el resumen de la corrida (conteos + resultado del chequeo). |
| `src/build_dashboard.py` | Genera `dashboard/index.html` con los datos embebidos. |
| `src/ingesta.py` | Fase A (opcional): mueve archivos nuevos de `FYS\Entrada\` a sus carpetas mensuales y corre el pipeline. |
| `src/despachos.py` | **Fase 10**: extrae chofer + fecha de salida del encabezado de cada PDF → `data/despachos.csv`. |
| `src/despacho_diario.py` | Mensaje diario por WhatsApp: despachos de hoy + recordatorios de pago (vence a 7 días del despacho). |
| `src/check_corrida.py` | Chequeo de calidad post-corrida (SIN_TOTAL, cobertura, duplicados). |
| `src/fys_consulta.py` | CLI de consultas para el bot de WhatsApp. |
| `src/run_clean.py` | Wrapper que limpia `PYTHONPATH` y corre cualquier script. |
| `dashboard/index.html` | Dashboard interactivo (facturado, cajas, cobrado, top clientes, comisiones, productos, FRITZ, despachos). |
| `data/facturas.csv` | **889 facturas** con fecha, documento, cliente, RIF, total y cajas. |
| `data/pagos_diarios.csv` | **Total de cada día** de cobranza (145 capturas). |
| `data/pagos_detalle.csv` | Filas de pago extraídas (1.038). |
| `data/clientes.csv` | Catálogo de clientes (142) para el listado de activos/sin compra. |
| `data/master_clientes.csv` | Master actualizado (142): origen, primera/última venta y nº de facturas. |
| `data/Master de Clientes FYS 2026-08.xlsx` | Copia del master para Excel. |
| `data/factura_lineas.csv` | **Capa de productos:** líneas por factura (código, nombre, cantidad). |
| `data/validacion_productos.csv` | Validación del detalle por factura (cobertura). |
| `data/productos.csv` | Catálogo único de productos con su marca. |
| `data/marcas.csv` | Catálogo de marcas **editable** (clave → marca). |
| `data/validacion_facturas_por_pdf.csv` | Checksum de cada PDF (136/136 OK). |
| `data/corridas_log.csv` | Registro histórico de cada corrida del pipeline. |
| `data/resumen_global.json` | Totales globales y desglose mensual. |
| `docs/METODOLOGIA.md` | Reglas de extracción y validación en detalle. |

## Resultados validados (enero–agosto 2026, actualizado 21-08-2026)

- **Facturas:** 889 facturas en 136/136 PDFs validados (la suma de los totales
  de operación de cada PDF coincide con el total general impreso). Se eliminó
  una factura duplicada (0000000128 INSIEME, impresa en 2 listados del
  07-01-2026).
- **Monto facturado:** USD 348.364,21 · **Cajas:** 11.442,98.
- **Pagos:** 145 capturas, 131 verificadas fila a fila y 14 con solo la
  sumatoria impresa (respaldo autorizado). Ninguna quedó sin total.
- **Crédito por sumatoria diaria:** USD 333.922,40.

> Nota: se eliminó una captura duplicada (la imagen del 01-05-2026 estaba
> copiada idéntica en las carpetas abril y mayo; se conservó solo la de mayo).

## Consultas por WhatsApp (bot)

El bot de Hermes conectado a WhatsApp responde consultas sobre los datos con
`src/fys_consulta.py` (skill `fys-consultas`):

```
¿Cuánto facturé en julio?     → facturado --mes 2026-07
¿Cuánto cobré este mes?       → cobrado --mes 2026-07
Top clientes / productos      → top-clientes / top-productos
¿Cuánto me compra X?          → cliente "NOMBRE"
¿Comisiones?                  → comisiones
¿Hay algo pendiente?          → pendientes
```

Números autorizados: 584129769561, 584148237433, 584148616638. Las
notificaciones de Hermes (ingesta automática, cron) llegan al 584148237433.

## Uso diario (sin agente ni API)

1. Mueve a mano los archivos nuevos de `FYS\Entrada\` a su carpeta mensual
   (`Facturas\2026-MM` / `Pagos_procesados\2026-MM`).
2. Doble clic en `Actualizar_Dashboard.bat` (en la raíz de FYS o del
   proyecto). Hace, en orden:
   1. **Respaldo** de `data/` a `data/backup/<fecha>/` (`src/backup_data.py`;
      si falla, aborta).
   2. **Pipeline completo** con log de corrida (`src/run_pipeline.py`) — solo
      procesa los archivos nuevos (caché por SHA-256); sin novedades tarda
      segundos.
   3. **Chequeo de calidad** (`src/check_corrida.py`).
   4. **Commit automático en git** (`src/git_commit_corrida.py`) con el
      resumen de la corrida y el resultado del chequeo.
3. Abre `dashboard/index.html`.

Si el pipeline falla no hay commit: el estado anterior queda intacto en git
y en `data/backup/`. Si el chequeo detecta problemas, el commit se registra
igualmente pero marcado `check=PROBLEMAS`.

### Regeneración manual (desarrollo)

```powershell
# IMPORTANTE: limpiar PYTHONPATH (PIL roto del venv Hermes degrada el OCR)
unset PYTHONPATH
python src/run_pipeline.py
```

O sin acordarse del PYTHONPATH:

```powershell
python src/run_clean.py src/run_pipeline.py
```

## Requisitos

- Python 3.11 o superior.
- Tesseract OCR instalado (por defecto
  `C:\Program Files\Tesseract-OCR\tesseract.exe`; se puede cambiar con la
  variable de entorno `TESSERACT_PATH`).

```powershell
python -m pip install -r requirements.txt
```

Las carpetas fuente por defecto son `..\Facturas` y `..\Pagos_procesados`
respecto a este proyecto (dentro de `Mi unidad\FYS`). Se pueden indicar otras:

```powershell
python src/run_all.py --facturas "D:\ruta\Facturas" --pagos "D:\ruta\Pagos_procesados"
```

Para procesar un mes nuevo (ej. septiembre 2026):
1. Guarda los PDFs en `Facturas\2026-09\` y las capturas en
   `Pagos_procesados\2026-09\` (o déjalos en `FYS\Entrada\` y corre
   `src/ingesta.py`).
2. Ejecuta `Actualizar_Dashboard.bat` (o, a mano,
   `python src/run_clean.py src/run_pipeline.py`).
3. Revisa el chequeo de calidad que corre al final; también puedes correr
   `python src/check_corrida.py`.
4. El dashboard queda regenerado en `dashboard/index.html`.

Ingesta automática opcional desde la carpeta de entrada:

```powershell
python src/ingesta.py            # mueve archivos de FYS\Entrada\ y corre todo
python src/ingesta.py --check    # solo lista qué hay en Entrada\
```

## Dashboard

Abre `dashboard/index.html` en cualquier navegador (doble clic; es
autocontenido, sin conexión a internet). Funciona con Edge, Chrome, Firefox,
tablet y desde Google Drive. Las notas se leen desde
`data/notas_clientes.json` al regenerar el dashboard; desde la tablet se pueden
exportar como JSON y copiar luego ese archivo a la PC antes de regenerar.

Incluye filtros por **mes** y **quincena** (1ª: días 01–15, 2ª: 16–fin) y
muestra:

- KPIs: monto facturado, número de cajas, monto cobrado y clientes activos.
- Comisiones: **0,3% sobre facturado sin IVA** (base = facturado ÷ 1,16, ya
  que la base imponible no se extrae de los PDFs) y **1,2% sobre cobrado**.
- Gráficos: facturado vs cobrado por mes, cobro diario/semanal y top clientes.
- Tabla resumen por mes y quincena (la columna "Días con cobro" indica
  cuántos días con capturas de pagos tiene el período).
- Listado de clientes **activos (verde)** y **sin compra (rojo)** en el período,
  con los mismos filtros; los clientes que no están en el catálogo se marcan
  como "(nuevo)".
- Panel lateral con secciones **Resumen / Clientes / Productos / FRITZ /
  Despachos** (en pantallas pequeñas se convierte en barra
  superior); los filtros quedan siempre visibles.
- Sección **FRITZ**: reporte completo de la marca FRITZ — KPIs (unidades,
  facturas, clientes, productos), gráfico mensual de unidades, top 20
  clientes, top 20 productos, listado de clientes que compran FRITZ y de los
  que NO compran (con buscadores) y detalle por producto. Botón
  **"Exportar a Excel"** descarga un `.xlsx` real (SheetJS incrustado, sin
  conexión) con 6 hojas (Resumen, Top 20 Clientes, Top 20 Productos,
  Clientes FRITZ, No compran FRITZ, Detalle Productos) del período filtrado.
- Sección **Despachos**: chofer y fecha de salida por factura — KPIs,
  buscador por cliente (chofer, salida, facturación, documentos, montos,
  vencimiento), despachos del período agrupados por fecha de salida con
  filtro de chofer, y recordatorios de pronto pago (vence a los 7 días del
  despacho · aviso al día 6).

## Mensaje diario por WhatsApp (despachos)

Cron de Hermes a las 7:00 AM (`fys_despacho_diario.py`): envía los despachos
del día agrupados por chofer (cliente, documento, monto) y los recordatorios
de pronto pago de los clientes cuyo despacho cumple 6 días (vence mañana).
Si no hay nada que reportar, no envía nada.

## Capa de productos (Fase 1)

Capa adicional, sin tocar lo ya validado. Extrae de los mismos PDFs solo
**código, nombre y cantidad** por línea (sin precios ni totales de línea) y
valida cada factura comparando la suma de cantidades contra las **cajas** ya
validadas de `facturas.csv`.

- Cobertura actual: 890/890 facturas validan su detalle (100 %); si alguna
  quedara `PENDIENTE` en `validacion_productos.csv` (revisión), nunca se
  carga a ciegas.
- `data/marcas.csv` es editable: cambia la columna `marca` (ej. clave `HEINZ
  KETCHUP` → marca `HEINZ`) y regenera con `python src/productos.py`.
- El dashboard con buscador de productos/marcas, top productos y tendencias
  se agrega en la Fase 2, usando estos archivos.

## Cómo se valida

- **Facturas:** cada PDF se lee completo; la suma de los totales de operación
  de sus facturas debe ser igual al total general del documento (a veces solo
  aparece en la última hoja). Tolerancia 0,01 USD.
- **Pagos:** por cada captura, la suma de filas (efectivo, transferencia,
  cupón) debe coincidir con la sumatoria impresa al pie. Si no se logra, se
  usa solo la sumatoria impresa (estado `SOLO_TOTAL`); si ni esa se lee, la
  captura queda `SIN_TOTAL` para revisión manual.

Ver `docs/METODOLOGIA.md` para el detalle completo.
