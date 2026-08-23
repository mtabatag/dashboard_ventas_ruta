# FYS — Historial completo del proyecto (respaldo de la conversación)

> Documento de respaldo creado el **12-08-2026** para conservar todo el
> recorrido del proyecto (dashboard + datos validados) aunque se cambie de
> herramienta o configuración. Este archivo es la memoria oficial del
> proyecto junto con `README.md` y `docs/METODOLOGIA.md`.

---

## 1. Objetivo del proyecto

Centralizar en una sola carpeta limpia y validada los datos comerciales de FYS
(vendedor: TABATA MARCOS):

- **Facturas** (PDF): fecha de emisión, número de documento, nombre del
  cliente, total operación y cantidad total de cajas por factura.
- **Pagos procesados** (capturas de imagen): total cobrado por día
  (efectivo + transferencia bancaria + cupón), validando contra la sumatoria
  impresa al pie de cada captura.
- **Clientes**: master actualizado con clientes activos e inactivos.
- **Productos** (capa adicional, sin precios): qué compró cada cliente y en
  qué cantidades, para análisis por producto/marca.
- **Catálogos de venta** (3 PDFs diarios): productos con precios y existencia.
- **Dashboard interactivo** con filtros de mes y quincena, comisiones,
  clientes top, activos/inactivos y análisis de productos.

La regla general que se mantuvo siempre: **no romper lo ya validado** y dejar
cada fase nueva como capa adicional.

---

## 2. Cronología de la conversación (lo que se pidió y lo que se hizo)

### Fase 0 — Origen y creación de la carpeta limpia

- Proyectos anteriores tenían extractores con demasiados campos (precios,
  códigos de producto por línea) que complicaban y rompían la extracción.
- Se decidió extraer **solo**: `FECHA DE EMISION`, `DOCUMENTO`,
  `NOMBRE DE CLIENTE`, `TOTAL OPERACION` y la **sumatoria de cantidades en
  cajas** que aparece bajo la columna "cantidad" de cada factura.
- Para pagos procesados: extraer las columnas efectivo / transferencia /
  cupón de cada captura y validar contra la **sumatoria total impresa abajo**.
  Si no se podía extraer todo, se aceptaba usar únicamente esa sumatoria
  (capturas "solo total").
- Se eliminó una captura duplicada (`WhatsApp Image 2026-05-01...jpeg`
  aparecía idéntica en abril y mayo; se conservó la de mayo).
- Los PDFs `CXC.*` y `MASTER*` **no** son listados de ventas y se excluyen
  del proyecto (el CXC — cuentas por cobrar — quedó fuera por decisión).
- Se creó `FYS_DATOS_VALIDADOS` con los extractores mínimos, guía,
  documentación y resultados validados, lista para eliminar los demás
  proyectos inconclusos o con basura.

### Fase 1 — Primer dashboard

- Dashboard con: monto facturado, número de cajas, monto cobrado, clientes
  top y filtros quincenales (1ª quincena = 01–15, 2ª = 16–fin).
- Comisiones: **0,3% del monto facturado** y **1,2% del monto cobrado**.
  Se aclaró que una de ellas se calcula sobre la base imponible (sin IVA);
  finalmente se aplica **÷ 1,16 (IVA)** a la comisión del **0,3% facturado**.
- Actualización de datos: se agregaron PDFs de julio (del 18 en adelante),
  la carpeta de agosto con PDFs hasta la fecha y los pagos de `2026-08`.

### Fase 2 — Logo, modo oscuro y presentación

- Modo oscuro (con preferencia guardada) y logo de F&S arriba a la izquierda.
- Varias iteraciones del logo: demasiado pequeño → más grande → versión
  transparente → "ahora sí se ve perfecto".
- El logo no se veía desde la tablet porque la ruta local no era accesible;
  se resolvió **embebiendo el logo en base64 dentro del HTML** (funciona en
  PC, tablet y desde Drive).
- Se quitó el texto "FYS" del encabezado; quedó solo el logo.

### Fase 3 — Clientes: activos e inactivos

- Listado de clientes activos (verde) y sin compra (rojo) con el mismo filtro
  de mes/quincena del resto del dashboard.
- Buscador dentro del cuadro de clientes.
- **Última fecha de compra**: se toma de la última factura donde aparece el
  cliente; si no tiene facturas, se usa la fecha del master.
- Se corrigieron fechas que venían del master cuando el cliente sí aparecía
  en facturas recientes (ALVAREZ PLAZA MARKET, WU SUPERTODO, SUPERMERCADO
  VIÑEDO, NG DARLY MUNDO, etc.).
- Se revisaron duplicados (Panadería La Naranja, Gran Oriente, City Mansion):
  decisión firme de usar **solo el PDF del master + los clientes nuevos
  detectados en facturas**; los Excel se descartan (traían basura y
  caracteres extraños).

### Fase 4 — Master de clientes actualizado

- Base: `MASTER TABATA MARCOS 13-05-26.pdf` con 131 clientes.
- Se agregaron **11 clientes nuevos** detectados en facturas.
- Master final: **142 clientes** (se esperaban más de 145; el número exacto
  real es 142).
- Generador: `src/generar_master.py` + `data/master_clientes.csv`.

### Fase 5 — Ajustes finales del dashboard (versión "buenísima")

- Comisiones corregidas: solo **0,3% de lo facturado − IVA** y
  **1,2% de lo cobrado**.
- "Resumen por periodo" renombrado a **Mes o meses**.
- Se explicó la columna **"Días"**: son los días con al menos un cobro
  registrado dentro del período consultado.
- Top clientes por monto facturado: **20 mejores**.
- KPI de clientes activos: ahora muestra también el número y porcentaje de
  **activos e inactivos** (con gráfico de dona).
- Filtros de mes y quincena corregidos para verse oscuros en modo oscuro.
- Panel lateral de secciones: **Resumen / Clientes / Productos / Catálogo**.
- Historial del cliente: al hacer clic en el nombre se despliega **debajo de
  la misma fila** (acordeón) con los productos que compró.
- Estilos unificados (top clientes con el mismo diseño de tarjeta).
- Exportar a CSV desde el resumen.
- Meta mensual editable y comparativa vs período anterior.

### Fase 6 — Productos por factura (capa adicional)

- Análisis previo: se evaluó agregar productos vendidos por cliente sin
  romper lo validado. Se eligió la **Opción A**: extraer solo **código y
  nombre del producto + cantidad** (sin precios ni totales por línea, que era
  lo que complicaba todo).
- Resultados: **838 de 856 facturas** con detalle validado (97,9 %),
  **9.009 líneas** validadas, **1.174 productos** únicos.
- Sección Productos del dashboard: buscador, filtro por marca, top 30 por
  unidades, historial mensual de cada producto y listado de productos que
  **dejaron de venderse** vs el período anterior.
- Catálogo de marcas editable (`data/marcas.csv`), con correcciones como
  CONVE02 → **LA PASTOREÑA**.

### Fase 7 — Catálogos de venta (proyecto complementario)

- Los 3 catálogos diarios (alimentos, limpieza, confitería) se analizaron
  completos: código, descripción, precio bulto, precio unidad/display o
  paquete, y existencia.
- Parser Fase 1 completado: **1.447 productos** (593 alimentos, 597
  limpieza, 257 confitería), todos con precio; solo `INA03` sin existencia.
- Integración al dashboard: estado del producto (OK / crítico / agotado),
  vendido en el período, y notas: "se vendió y no está en catálogo" /
  "en catálogo sin ventas".
- Pendientes: mejorar captura de marcas, historial diario de catálogos con
  alertas (agotados, nuevos, cambios de precio) y panel de reposición
  ("se vende mucho y se está agotando").

### Fase 8 — Infraestructura (conversación, pendiente)

- Se consultó sobre trabajar desde la nube (VPS tipo Contabo) con Hermes
  desktop, carpeta compartida en Drive y envío de PDFs por WhatsApp.
- Recomendación dada: primero hacer la **ingesta automática local** (vigilar
  una carpeta de entrada, mover PDFs/capturas a `Facturas\2026-MM` y
  `Pagos_procesados\2026-MM`, y correr extracción + dashboard), y más
  adelante el VPS con rclone/Drive y bot de WhatsApp.

### Fase 9 — Blindaje, correcciones y automatización (13-08-2026)

En esta fase se auditó el proyecto completo, se corrigieron hallazgos y se
automatizó la ingesta. Cambios:

**Corrección de duplicado (factura 0000000128)**
- Se detectó que la factura `0000000128` (INSIEME, S.A., USD 2.009,09 del
  07-01-2026) aparecía **en los dos listados del día** (`07-01-26.pdf` y
  `07-01-26 2.pdf`), y cada listado la incluye en su total general impreso.
  Por eso el checksum por PDF validaba OK en ambos, pero el total global la
  contaba dos veces.
- Decisión de Marcos: **error de impresión — contar la factura UNA sola vez**.
- Solución en `src/facturas.py`: deduplicación por `(fecha, documento)` en la
  capa de salida; se conserva la primera aparición y la eliminada queda
  registrada en `resumen_global.json` (`facturas_duplicadas_eliminadas`).
- Resultado: 859 facturas (860 extraídas − 1 duplicada), USD 336.311,62.

**Corrección del detalle de productos (18 facturas PENDIENTE)**
- Causa 1: códigos de producto con **guion final** (`20007-`, `CV1498-`) que
  el regex `RE_CODIGO = ^[A-Z0-9]{2,14}$` rechazaba → la línea se perdía y la
  factura quedaba PENDIENTE (0 líneas o -1/-2/-10).
  Fix: `^[A-Z0-9][A-Z0-9-]{1,13}$`.
- Causa 2: la **cantidad** se tomaba como el primer token numérico, pero el
  nombre del producto contiene tamaños numéricos (`HEINZ VINAGRE GALON 3.7
  LT`) → se tomaba `3.7` como cantidad (caso LA TURCA, +2,7).
  Fix: la cantidad es el **primer token del sufijo numérico final** de la
  línea (los últimos 2-3 tokens = cantidad, precio, [total]).

**Hallazgo crítico: PYTHONPATH contaminado**
- Al ejecutar el pipeline desde una sesión de Hermes, la variable
  `PYTHONPATH` apunta a `hermes-agent\venv\Lib\site-packages`, que contiene
  un PIL **roto** para el Python del runtime de Codex (CPython 3.12). El
  import fallaba → `_HAVE_PIL=False` → el OCR de pagos corría **sin
  preprocesamiento** (escala 2x/contraste) → 10 capturas caían a
  SIN_TOTAL/REVISAR y el crédito bajaba USD ~50K.
- Solución: `unset PYTHONPATH` antes de correr (o `src/run_clean.py`, que lo
  hace automáticamente). Verificado: con entorno limpio los pagos vuelven a
  120 VERIFICADO + 14 SOLO_TOTAL + 0 SIN_TOTAL, crédito USD 306.924,54
  (idéntico al validado del 12-08).
- ⚠️ **Regla nueva**: todo script que invoque el pipeline debe limpiar
  `PYTHONPATH` (ya aplicado en `ingesta.py`, `run_pipeline.py` y
  `run_clean.py`).

**Nuevos scripts**
- `src/run_pipeline.py` — orquestador: corre run_all + productos +
  generar_master + build_dashboard y registra cada corrida en
  `data/corridas_log.csv` (fecha, duración, conteos, estado) para detectar
  regresiones.
- `src/ingesta.py` — **Fase A**: mueve PDFs/capturas nuevos de
  `FYS\Entrada\` a sus carpetas mensuales (evitando duplicados por hash) y
  corre el pipeline. Se programa con el cron de Hermes.
- `src/check_corrida.py` — chequeo de calidad post-corrida (0 SIN_TOTAL,
  cobertura de productos ≥ 95 %, duplicados registrados).
- `src/fys_consulta.py` — CLI de consultas para el bot de WhatsApp
  (facturado, cobrado, top clientes, top productos, comisiones, pendientes).
- `src/run_clean.py` — wrapper que fuerza `unset PYTHONPATH`.

**Dashboard**
- Nueva sección **Reposición**: productos con ventas en el período y
  existencia baja/crítica del catálogo (cruce ventas × EXIST), ordenados por
  rotación.
- Nueva sección **FRITZ**: reporte completo de la marca (49 productos, 1.146
  líneas, 77 clientes que compran, 65 que no): KPIs, gráfico mensual de
  unidades, top 20 clientes, top 20 productos, lista de clientes que compran
  y que NO compran FRITZ (con buscador), y detalle por producto.
- Botón **"Exportar a Excel"** en la sección FRITZ: descarga un `.xlsx`
  **real** (librería SheetJS incrustada en el HTML, sin dependencias de red)
  con 6 hojas — Resumen, Top 20 Clientes, Top 20 Productos, Clientes FRITZ,
  No compran FRITZ y Detalle Productos — del período filtrado en el
  dashboard. (Primera versión usaba XML Spreadsheet 2003 con extensión
  `.xls`, que Excel abría como texto plano; se reemplazó por `.xlsx` real.)

### Fase 10 — Módulo de Despachos (chofer y fecha de salida) — 20-08-2026

Solicitud de Marcos: las facturas traen en el encabezado el **chofer** y la
**fecha de salida** del despacho; necesita consultar por cliente (chofer,
fecha de salida, fecha de facturación, documentos, montos), ver despachos
por semana/mes/quincena, y tener recordatorios de pronto pago (vence a los
7 días del despacho; aviso al día 6), en el dashboard y por WhatsApp diario.

**Extracción (`src/despachos.py`)**
- El encabezado de cada PDF (líneas 1-4 de página 1) trae chofer + salida en
  3 formatos:
  A) `CHOFER HEINNER G. SALIDA JUEVES 20-08-26` (fecha explícita),
  B) `CHOFER WILLIANS T.` + línea de impresión `17/8/2026 01:56 p.m. 18-08-26`
  (fecha al final), C) `CHOFER CARLOS M. FACTURACION VIERNES SALIDA LUNES`
  + `1 de 2 15/5/2026 4:47 p.m. 18-05-26`.
- Asociación factura→chofer por (fecha, documento) re-extraído de cada PDF
  (dos PDFs del mismo día pueden tener choferes distintos, caso 07-01-26).
- Cobertura: 116/135 PDFs con chofer; 19 sin CHOFER quedan "SIN DATO" y el
  cron lo alerta. 0 PDFs multi-chofer (un chofer por PDF).
- Normalización de nombres en `data/choferes.csv` (editable):
  WUILLIANS/WILLIANS T. → WUILLIANS T., HEINNER/HEINER G. → HEINNER G.
  Choferes: WUILLIANS T., CARLOS M., HEINNER G., JHONNY R.
- Salida: `data/despachos.csv` (factura, cliente, monto, cajas, chofer,
  fecha salida, días de espera). Se integra a `run_pipeline.py`.

**Dashboard — sección "Despachos"**
- KPIs: facturas del período, monto despachado, choferes activos, última
  salida; nota con alertas (sin chofer/sin salida) y salidas de hoy.
- Buscador por cliente: chofer, salida, facturación, documentos, montos,
  cajas y fecha de vencimiento de pago por factura.
- Tabla de despachos del período agrupada por fecha de salida (montos por
  chofer), con filtro de chofer.
- Recordatorios de pago: vence en 7 días desde la salida; avisos "vence
  mañana / hoy / vencido".

**WhatsApp diario (`src/despacho_diario.py` + cron 7:00)**
- Despachos de hoy agrupados por chofer (cliente, documento, monto).
- Recordatorios de pronto pago del día 6 (vence mañana) por cliente.
- Silencioso si no hay nada que reportar.

**Propuestas aceptadas/incorporadas**
- Totales por chofer en la vista de despachos.
- Alertas de calidad (facturas sin chofer o sin fecha de salida).
- El recordatorio incluye monto exacto por cliente.

**Otros**
- `data/facturas.csv` ahora incluye la columna `rif`.
- `requirements.txt` completo: pdfplumber, Pillow, openpyxl.
- `.gitignore` + repositorio git inicializado en `FYS_DATOS_VALIDADOS`.
- `data/corridas_log.csv` — registro histórico de corridas.

---

## 3. Estado validado (13-08-2026, tras la Fase 9)

| Dato | Valor |
|---|---|
| Facturas | **859** en 132/132 PDFs validados (1 duplicado eliminado) |
| Monto facturado | **USD 336.311,62** |
| Cajas totales | **11.007,27** |
| Pagos (capturas) | **134** (120 verificadas + 14 solo total, 0 sin total) |
| Crédito por sumatoria diaria | **USD 306.924,54** |
| Clientes master | **142** (131 del PDF + 11 nuevos) |
| Facturas con detalle de productos | pendiente de confirmar tras re-corrida |
| Líneas de producto validadas | pendiente de confirmar tras re-corrida |
| Productos únicos | pendiente de confirmar tras re-corrida |
| Catálogos (3) | 1.447 productos |
| Secciones dashboard | Resumen, Clientes, Productos, Reposición, **FRITZ**, Catálogo |

---

## 4. Archivos clave y cómo se regenera todo

| Archivo | Función |
|---|---|
| `data/facturas.csv` | Facturas: fecha, documento, cliente, total, cajas |
| `data/pagos_diarios.csv` | Total de cada día (134 capturas) |
| `data/clientes.csv` | Catálogo de clientes para activos/inactivos |
| `data/master_clientes.csv` | Master actualizado (142) |
| `data/factura_lineas.csv` | Productos por factura (9.009 líneas) |
| `data/productos.csv` · `data/marcas.csv` | Catálogo de productos y marcas editable |
| `data/validacion_*.csv` · `resumen_global.json` | Validaciones y totales |
| `src/run_all.py` | Extrae facturas y pagos y regenera `data/` |
| `src/build_dashboard.py` | Regenera `dashboard/index.html` |
| `src/productos.py` | Capa de productos por factura |
| `src/generar_master.py` | Genera el master desde PDF + facturas |
| `dashboard/index.html` | Dashboard autocontenido (logo embebido + catálogo) |
| `CATALOGOS_VENTAS/parse_catalogo.py` | Parser de catálogos |
| `CATALOGOS_VENTAS/catalogo_productos.csv` | Productos de catálogo (1.447) |
| `CATALOGOS_VENTAS/ANALISIS_CATALOGOS.md` | Análisis e ideas de uso |
| `src/run_pipeline.py` | Orquestador completo con log en `data/corridas_log.csv` |
| `src/ingesta.py` | Ingesta automática desde `FYS\Entrada\` (Fase A) |
| `src/check_corrida.py` | Chequeo de calidad post-corrida |
| `src/fys_consulta.py` | CLI de consultas para el bot de WhatsApp |
| `src/run_clean.py` | Wrapper que limpia `PYTHONPATH` antes de correr |

Para regenerar **todo** (recomendado):

```
python src\run_pipeline.py
```

O paso a paso:

```
python src\run_all.py            (reextraer facturas + pagos)
python src\productos.py          (capa de productos)
python src\generar_master.py     (master de clientes)
python src\build_dashboard.py    (regenerar dashboard)
```

> ⚠️ **Nota técnica CRÍTICA**: usar el Python del runtime empaquetado de Codex
> (`C:\Users\Marcos\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`).
> Tesseract está en `C:\Program Files\Tesseract-OCR\tesseract.exe`.
> **Siempre limpiar `PYTHONPATH`** antes de correr (`unset PYTHONPATH` en
> bash, o usar `src/run_clean.py`): el PYTHONPATH de una sesión Hermes
> apunta a un PIL roto del venv que degrada el OCR de pagos.

---

## 5. Reglas y restricciones aprendidas

- Los Excel **nunca** alimentan el master; solo el PDF del master + clientes
  nuevos de facturas.
- `CXC.*` y `MASTER*` no son listados de ventas y se excluyen.
- Si una captura de pago está duplicada (mismo archivo), se elimina la copia.
- No cambiar dependencias ni romper lo validado; cada fase es capa adicional.
- Comisiones finales: **0,3 % del facturado ÷ 1,16 (IVA)** y
  **1,2 % del cobrado**.
- Un mismo número de documento es **una sola venta**: si aparece en dos
  listados del mismo día, se deduplica por `(fecha, documento)` y queda
  registrado en `resumen_global.json`.
- **Siempre limpiar `PYTHONPATH`** al ejecutar el pipeline desde Hermes.

---

## 6. Pendientes / próximos pasos

1. ~~Ingesta automática (Fase A)~~ ✅ **Implementada** (`src/ingesta.py`) —
   falta programar el cron de Hermes (cada N horas) + notificación por
   WhatsApp.
2. **Histórico de catálogos**: snapshots diarios con alertas de agotados,
   nuevos y cambios de precio (pospuesto por decisión de Marcos).
3. **Afinar marcas**: revisar claves mal mapeadas (p. ej. "EVERY NIGHT").
4. ~~Panel de reposición~~ ✅ **Implementado** en el dashboard (sección
   Reposición).
5. **Nube/VPS**: Contabo + carpeta Drive (rclone) + bot de WhatsApp.
6. Confirmar con Marcos la semántica de `EXIST` y los precios del catálogo.
7. Bot de WhatsApp con consultas FYS — ✅ CLI listo (`src/fys_consulta.py`),
   integrado como skill `fys-consultas`; probar en vivo.

---

## 7. Cómo continuar si se pierde esta conversación

- Leer este documento + `README.md` + `docs/METODOLOGIA.md`.
- La data validada vive en `data/*.csv` y el dashboard en
  `dashboard/index.html` (autocontenido).
- Cualquier dato nuevo se procesa con `run_all.py` y se regenera el dashboard
  con `build_dashboard.py`.
- En la app de Codex, la conversación se conserva mientras el hilo no se
  elimina; se puede **fijar (pin)** o **archivar** el hilo para que no se
  pierda de vista.

---

## 8. Actualización 21-08-2026: `Actualizar_Dashboard.bat` (uso diario sin agente)

Marcos pidió un script para operar el dashboard sin agentes ni API: soltar
archivos y ejecutar. Decisiones:

- **La ingesta automática queda como capa opcional**: Marcos mueve a mano
  los archivos de `Entrada\` a las carpetas mensuales y luego ejecuta
  `Actualizar_Dashboard.bat` (lanzador en la raíz de FYS que delega al del
  proyecto). El flujo: respaldo → pipeline → chequeo → commit git.
- **Respaldo previo obligatorio** (`src/backup_data.py`): copia
  `data/*.csv|json` a `data/backup/<fecha>/` (conserva 15); si falla,
  aborta antes de tocar nada.
- **Commit automático** (`src/git_commit_corrida.py`): mensaje con conteos
  de la corrida + resultado del chequeo (`check=OK` / `check=PROBLEMAS`).
  Si el pipeline falla no hay commit; git + respaldo permiten rollback.
- **Guardia anti-duplicados en pagos** (`pagos.py`): al no correr la
  ingesta siempre, una captura copiada dos veces con distinto nombre se
  detectaría tarde. Ahora cada captura lleva su SHA-256 y se avisa si hay
  duplicados; `check_corrida.py` lo marca como error.
- **Limpieza**: eliminadas las copias de conflicto de Drive en `data/`
  (`* (1).*`, 11 archivos) y `src/despacho_diario.py.bak`.
- Prueba end-to-end OK: corrida completa con caché caliente en ~14 s,
  chequeo saludable (889 facturas · USD 348.364,21 · crédito
  USD 333.922,40) y commit registrado.

## 9. Recordatorios globales y notas incrustadas — 22-08-2026

- Los recordatorios de pago próximos a vencer se calculan sobre todos los
  despachos, sin quedar limitados por el mes o la quincena seleccionados.
- Las marcas y comentarios de clientes se leen desde
  `data/notas_clientes.json` y se incrustan al regenerar `dashboard/index.html`.
  La tablet puede exportar el JSON para copiarlo posteriormente a la PC.
- Se retiraron las pestañas Reposición y Catálogo: dependían de mantener un
  inventario diario y no forman parte del flujo actual. FRITZ queda basado en
  las líneas de productos vendidos.
