from extraer_facturas import extraer_facturas_visual
from reporte_ventas import generar_reporte_completo

print("\n==============================")
print("ACTUALIZANDO BASE DE VENTAS")
print("==============================")

extraer_facturas_visual()

print("\n==============================")
print("GENERANDO ANALISIS")
print("==============================")

generar_reporte_completo()

print("\nSistema actualizado correctamente")