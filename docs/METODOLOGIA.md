# Metodología de extracción y validación

## 1. Facturas (PDF diarios)

### Estructura del documento

Cada PDF diario (`FACT. TABATA MARCOS DD-MM-AA.pdf`) contiene **varias
facturas** de distintos clientes. Cada bloque de factura:

1. **Cabecera** (una línea), en cualquiera de estos dos órdenes:
   ```
   DD/MM/AAAA  NNNNNNNN  FAC  RIF  NOMBRE_CLIENTE  TOTAL_OPERACION
   DD/MM/AAAA  FAC  NNNNNNNN  RIF  NOMBRE_CLIENTE  TOTAL_OPERACION
   ```
2. **Líneas de producto** (ignoradas en este proyecto; no interesan precios
   ni códigos).
3. **Sumatoria de cajas**: la última fila del bloque formada solo por 2
   números; el primero es la cantidad total de cajas de esa factura.

Al final del PDF aparece el **total general en USD** de todas las facturas
del día (a veces solo en la última hoja).

Se excluyen de la extracción los reportes que no son el listado diario de
ventas: archivos `CXC.*` (cuentas por cobrar) y `MASTER*` (catálogo de
clientes), aunque estén dentro de las carpetas mensuales.

### Extracción

Por factura se extrae únicamente:
`fecha_emision`, `documento`, `nombre_cliente`, `total_operacion`, `cajas`.

### Validación (checksum por PDF)

```
suma(total_operacion de todas las facturas del PDF) == total_general_pdf
```

Tolerancia: 0,01 USD (por redondeo). Resultado por PDF:

- `OK`: cuadra.
- `DESVIADO`: no cuadra (bloquea el PDF para revisión).
- `SIN_TOTAL`: no se encontró el total general.
- `ERROR`: falló la lectura del archivo.

### Deduplicación por (fecha, documento) — Fase 9

Un mismo número de documento es **una sola venta**. La oficina a veces imprime
la misma factura en **dos listados del mismo día** (caso real: `0000000128`
INSIEME, S.A., USD 2.009,09 del 07-01-2026, presente en `07-01-26.pdf` y
`07-01-26 2.pdf`). Cada listado incluye la factura en su total general, así
que el checksum por PDF valida OK en ambos, pero el total global la contaría
dos veces.

Solución (autorizada por Marcos, 13-08-2026): en la capa de salida se
conserva la primera aparición de cada `(fecha, documento)` y las eliminadas
quedan registradas en `resumen_global.json` →
`facturas_duplicadas_eliminadas`. El checksum por PDF **no cambia** (refleja
lo impreso); solo el agregado global deja de duplicar.

## 2. Pagos procesados (capturas de pantalla)

### Estructura de cada captura

Tabla con columnas: `Documento | Nombre | Efectivo | Transferencia Bancaria |
Cupón`. Cada captura suele ser un bloque de un día, con una **fila de
totales impresa al pie**.

### Extracción

OCR con Tesseract (idioma `spa+eng`), con preprocesamiento de imagen
(escala 2x, contraste, nitidez) para recuperar comas/puntos perdidos:

1. Pasada `--psm 4`: filas de pago (`PAG-...`), nombres y montos.
2. Pasada `--psm 6`: documentos que el psm 4 omite.
3. Cada token numérico recibe un conjunto de interpretaciones posibles
   (`62547` → 625,47; `1.27951` → 1.279,51) y se resuelve por sección
   buscando la combinación cuyas columnas **sumen exactamente el total
   impreso**.

### Validación por captura

```
sum(filas.efectivo)                 == total_impreso.efectivo
sum(filas.transferencia_bancaria)   == total_impreso.transferencia
sum(filas.cupon)                    == total_impreso.cupon
```

Tolerancia: 0,01 USD. Si cualquiera falla, la captura pasa a `REVISAR`.

### Regla de respaldo (autorizada por el usuario)

- Si no se pueden extraer o validar las filas completas, se usa
  **únicamente la sumatoria impresa** como total del día → estado
  `SOLO_TOTAL` en `pagos_diarios.csv`.
- Si ni la sumatoria se puede leer, la captura queda `SIN_TOTAL` para
  revisión manual (nunca se inventa un monto).

### Recuperación de sumatorias no leídas

Cuando la fila de totales no se detecta (o sale en ceros), se reintenta con
`--psm 6` buscando líneas de 2-3 números después de la última fila `PAG-`.
Esto recuperó la sumatoria de 21 capturas en la corrida de enero–julio.

### Alineación de columnas

Si el total impreso queda en una columna equivocada por ruido del OCR
(p. ej. transferencia leída como cupón) pero las filas coinciden, se permutan
las columnas del total para minimizar la diferencia contra la suma de filas.
El total del día no cambia; solo se corrige el desglose.

## 3. Control de duplicados

Las capturas se identifican por archivo. En la corrida de enero–julio se
detectó una imagen duplicada (mismo hash SHA-256) en las carpetas `2026-04`
y `2026-05`: `WhatsApp Image 2026-05-01 at 4.26.35 PM.jpeg`. Se eliminó la
copia de `2026-04` (mes incorrecto según el nombre) y se conservó la de
`2026-05`. Si al agregar meses nuevos aparece otra duplicación, eliminar la
copia mal ubicada antes de correr el pipeline.

Desde el 21-08-2026 cada captura lleva su SHA-256 en el resultado y
`pagos.py` avisa en pantalla si dos archivos tienen contenido idéntico
(mismo hash, distinto nombre); `check_corrida.py` marca esa corrida como
con problemas hasta que se elimine la copia manualmente.

## 4. Resultados enero–agosto 2026 (actualizado 21-08-2026)

| Indicador | Valor |
|---|---|
| PDFs de facturas | 136 (136 OK) |
| Facturas | 889 (890 extraídas − 1 duplicada) |
| Monto facturado | USD 348.364,21 |
| Cajas | 11.442,98 |
| Capturas de pagos | 145 (131 VERIFICADO + 14 SOLO_TOTAL, 0 SIN_TOTAL) |
| Filas de pago extraídas | 1.038 |
| Crédito por sumatoria diaria | USD 333.922,40 |

## 5. Catálogo de clientes y activación

`data/master_clientes.csv` contiene el master de clientes actualizado (**142**
clientes), generado con `src/generar_master.py` a partir de:

1. `MASTER TABATA MARCOS 13-05-26.pdf` (131 clientes, el último master
   publicado).
2. Los clientes detectados en las facturas de enero–agosto 2026 que no estaban
   en el master (11 nuevos; se incorporan con su RIF cuando existe).

Los Excel de clientes no se usan como fuente del master (evita duplicados por
caracteres raros en los nombres); solo el PDF + los clientes nuevos.

La unión se hace por RIF (dígitos) y, cuando el RIF no coincide por formato,
por nombre normalizado (se ignoran diferencias de puntuación, acentos y
sufijos tipo "C.A"/"CA"). `data/clientes.csv` es la versión resumida (rif,
nombre) que usa el dashboard para el panel "Clientes activos y sin compra":
**verde** = clientes con factura en el período filtrado, **rojo** = sin
compra, y "(nuevo)" = clientes que facturan pero no están en el catálogo.

## 6. Capa de productos (Fase 1)

Extrae de cada PDF las líneas de producto de cada factura con **solo**:
`codigo_producto`, `nombre_producto` y `cantidad` (sin precio ni total de
línea, que fueron la fuente de los errores históricos).

Validación: la suma de cantidades de las líneas de una factura debe coincidir
con las **cajas** de esa factura en `facturas.csv` (tolerancia 0,10 por el
redondeo a 2 decimales de las cantidades impresas). Resultado por factura:
`VALIDADO` / `PENDIENTE` / `SIN_REFERENCIA`. Las `PENDIENTE` van a
`validacion_productos.csv` para revisión manual y no entran al catálogo de
productos.

### Reglas de parseo de líneas (actualizado 13-08-2026, Fase 9)

- El **código** admite guiones finales (`20007-`, `CV1498-`): regex
  `^[A-Z0-9][A-Z0-9-]{1,13}$`. Antes se rechazaban y la línea entera se
  perdía (facturas PENDIENTE con diff -1/-2/-10 o 0 líneas).
- La **cantidad** es el primer token del **sufijo numérico final** de la
  línea (los últimos 2-3 tokens = cantidad, precio, [total]). El total de
  línea puede ser entero (`423`) o decimal (`21,01`); la cantidad siempre
  lleva decimales. Esto evita confundir tamaños del nombre (`HEINZ VINAGRE
  GALON 3.7 LT`) con la cantidad real (caso LA TURCA, +2,7).
- Tras estos fixes la cobertura pasó de 97,9 % (838/856) a **100 %
  (860/860)**.

### Nota de entorno crítica (Fase 9)

Al ejecutar el pipeline desde una sesión de Hermes, la variable `PYTHONPATH`
apunta al venv de hermes-agent, que contiene un PIL **roto** para el Python
del runtime de Codex (CPython 3.12). El import falla → `_HAVE_PIL=False` →
el OCR de pagos corre **sin preprocesamiento** (escala 2x/contraste) →
capturas SIN_TOTAL y crédito ~USD 50K por debajo. **Siempre** hacer
`unset PYTHONPATH` (o usar `src/run_clean.py`).

La marca se asigna con el catálogo editable `data/marcas.csv` (clave = inicio
del nombre del producto, ej. "LA PASTOREÑA" o "HEINZ KETCHUP"); si la clave no
existe, se usa el primer término del nombre. El usuario puede corregir la
columna `marca` y volver a ejecutar `python src/productos.py`.
