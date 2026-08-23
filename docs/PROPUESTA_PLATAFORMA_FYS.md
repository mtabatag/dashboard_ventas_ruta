# Propuesta inicial — Plataforma FYS multiusuario

> Documento de exploración. No representa todavía una decisión definitiva de
> arquitectura ni autoriza el inicio del desarrollo.

## 1. Visión

Convertir el dashboard actual de FYS en una plataforma web accesible desde
PC, tablet y teléfono, donde cada vendedor pueda cargar sus facturas y pagos
procesados, obtener sus resultados y consultar su información histórica.

La plataforma también tendrá un espacio para supervisores, con información
consolidada por zona, vendedor y período, además de acceso al detalle de cada
vendedor.

## 2. Objetivos

- Simplificar la carga de facturas y pagos.
- Automatizar el procesamiento, validación y actualización del dashboard.
- Evitar que los datos de distintos vendedores se mezclen.
- Permitir supervisión consolidada por zona y vendedor.
- Mantener las reglas actuales de extracción, deduplicación y validación.
- Ofrecer acceso desde cualquier dispositivo con navegador.
- Conservar respaldos, historial y trazabilidad de cada corrida.

## 3. Roles iniciales

### Vendedor

- Ve únicamente sus propios datos.
- Carga facturas y pagos procesados.
- Selecciona o confirma el período de los archivos.
- Consulta su dashboard.
- Revisa errores, duplicados y archivos rechazados.
- Exporta sus reportes.

### Supervisor

- Ve los vendedores y zonas que tiene asignados.
- Consulta información consolidada.
- Compara vendedores y zonas.
- Accede al dashboard individual de cada vendedor.
- Revisa el estado de carga y procesamiento.

### Administrador

- Crea y desactiva usuarios.
- Asigna vendedores a zonas y supervisores.
- Configura catálogos, reglas y parámetros.
- Consulta todos los datos.
- Revisa auditoría, respaldos y ejecuciones.

## 4. Módulos propuestos

### Acceso y usuarios

- Inicio de sesión.
- Recuperación de contraseña.
- Roles y permisos.
- Estado activo/inactivo del usuario.

### Carga de archivos

- Carga desde PC, tablet o teléfono.
- Carga múltiple de PDF e imágenes.
- Identificación de factura o pago.
- Clasificación por vendedor y período.
- Detección de archivos repetidos.
- Historial de cargas.

### Procesamiento

- Cola de procesamiento por vendedor.
- OCR para capturas de pagos.
- Extracción de facturas.
- Procesamiento de productos y despachos.
- Validación de totales y cobertura.
- Resultado: correcto, advertencias o errores.

### Dashboard del vendedor

- Resumen de facturación y cobranza.
- Clientes.
- Productos.
- Reposición.
- Catálogo.
- FRITZ y otras marcas.
- Despachos.
- Filtros por mes, quincena y período.
- Exportación a Excel.

### Dashboard del supervisor

- Resumen global.
- Comparación por zona.
- Comparación por vendedor.
- Facturado, cobrado, crédito y cajas.
- Estado de carga de cada vendedor.
- Vendedores sin novedades o con errores.
- Acceso al detalle individual.

### Administración

- Usuarios, vendedores y zonas.
- Catálogos y marcas.
- Parámetros de comisiones.
- Historial de ejecuciones.
- Auditoría de cambios.
- Respaldos y restauración controlada.

## 5. Modelo conceptual de datos

La base de datos debería separar claramente la organización y la información
comercial:

```text
Empresa
 └── Zona
      └── Vendedor / Usuario
           ├── Facturas
           ├── Pagos
           ├── Clientes
           ├── Productos
           ├── Despachos
           ├── Archivos cargados
           └── Corridas de procesamiento
```

Cada factura, pago, cliente y archivo tendría asociado un vendedor. Esto
permitiría consultar información individual o consolidada sin mezclar datos.

## 6. Flujo principal

```text
Usuario inicia sesión
        ↓
Carga facturas y pagos
        ↓
El sistema identifica y guarda los archivos
        ↓
Se ejecuta el procesamiento del vendedor
        ↓
Se validan duplicados, totales y cobertura
        ↓
Se actualizan los datos
        ↓
El dashboard queda disponible
        ↓
El supervisor puede ver el resumen consolidado
```

## 7. Arquitectura preliminar

- Aplicación web responsive y posteriormente instalable como PWA.
- Backend con API, autenticación y control de permisos.
- Base de datos central como fuente oficial de información.
- Almacenamiento separado para PDFs e imágenes originales.
- Servicios Python para OCR, extracción y validación.
- Dashboard web reutilizando la lógica visual actual.
- Procesamiento en segundo plano para no bloquear la aplicación.
- HTTPS, respaldos automáticos y registro de auditoría.

El proyecto actual seguiría siendo la base del procesamiento de TABATA MARCOS.
La primera implementación debería encapsular el pipeline existente antes de
modificarlo profundamente.

## 8. Alcance sugerido para un MVP

El primer producto funcional debería incluir solamente:

1. Inicio de sesión.
2. Usuarios vendedores y supervisor.
3. Registro de vendedores y zonas.
4. Carga de facturas y pagos.
5. Procesamiento individual por vendedor.
6. Dashboard individual.
7. Resumen consolidado del supervisor.
8. Detección de duplicados y reporte de errores.
9. Historial de corridas.
10. Respaldos automáticos.

Quedarían para una segunda etapa: notificaciones, múltiples empresas,
permisos muy detallados, histórico avanzado de catálogos, aplicación móvil
nativa y automatizaciones externas.

## 9. Decisiones pendientes

- ¿Habrá una sola empresa FYS o varias empresas independientes?
- ¿Un vendedor podrá pertenecer a más de una zona?
- ¿El supervisor verá todos los vendedores o solo los asignados?
- ¿Los catálogos serán globales o específicos por vendedor?
- ¿Los vendedores cargarán archivos manualmente o también habrá carpetas
  sincronizadas?
- ¿Se conservará el esquema de comisiones actual para todos?
- ¿Cuánto tiempo deben conservarse los archivos originales?
- ¿Se necesita aprobación del supervisor antes de publicar los resultados?
- ¿Qué información podrá editar un usuario después del procesamiento?

## 10. Principios del proyecto

- No mezclar información entre vendedores.
- No reemplazar datos validados sin respaldo.
- Mantener los archivos originales.
- Registrar quién cargó, procesó o modificó información.
- Separar datos crudos, datos validados y datos mostrados.
- Permitir corregir errores sin perder el historial.
- Diseñar primero para móvil y tablet, además de PC.
- Construir por etapas y validar cada etapa con datos reales.

## 11. Próximo paso recomendado

Antes de programar, revisar este documento y cerrar estas tres definiciones:

1. Roles y permisos exactos.
2. Flujo de carga y aprobación de archivos.
3. Indicadores que debe ver el supervisor en su primera pantalla.

Una vez aprobadas esas definiciones, se puede preparar el diseño de pantallas
y el esquema inicial de base de datos sin tocar todavía el procesamiento
validado.
