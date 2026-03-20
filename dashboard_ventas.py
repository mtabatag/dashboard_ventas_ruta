import pandas as pd
import re
import os

def generar_reporte_completo():
    # Ruta absoluta del archivo Excel, relativa al script
    archivo = os.path.join(os.path.dirname(__file__), "ventas_productos.xlsx")
    
    try:
        df = pd.read_excel(archivo)
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{archivo}'.")
        return

    # Limpieza de valores numéricos
    def limpiar_numero(x):
        if pd.isna(x):
            return 0.0
        x_str = str(x).replace('.', '').replace(',', '.')
        try:
            return float(x_str)
        except ValueError:
            return 0.0

    df['Cant_Num'] = df['Cant'].apply(limpiar_numero)
    df['Total_Num'] = df['Total'].apply(limpiar_numero)

    # Función para calcular unidades individuales dentro del bulto
    def calcular_unidades(nombre, cant_bultos):
        nombre = str(nombre).upper()
        
        # Buscar displays (ej. "X 4 DISP" o "X 12DISP")
        disp_match = re.search(r'X\s*(\d+)\s*DISP', nombre)
        disp = int(disp_match.group(1)) if disp_match else 1
        
        # Buscar unidades (ej. "X 5 UND", "X 24UND", "12 UND")
        und_match = re.search(r'(?:X\s*)?(\d+)\s*UND', nombre)
        und = int(und_match.group(1)) if und_match else 1
        
        return cant_bultos * (disp * und)

    # Aplicamos el cálculo a toda la base de datos
    df['Unidades_Individuales'] = df.apply(lambda row: calcular_unidades(row['Nombre'], row['Cant_Num']), axis=1)

    # 1. Clientes y Bultos generales
    clientes_activos = df['Cliente'].nunique()
    total_bultos = df['Cant_Num'].sum()

    # 2. Análisis por Marcas Específicas
    df_fritz = df[df['Nombre'].str.contains('FRITZ', case=False, na=False)]
    bultos_fritz = df_fritz['Cant_Num'].sum()
    unidades_fritz = df_fritz['Unidades_Individuales'].sum()

    df_munchy = df[df['Nombre'].str.contains('MUNCHY', case=False, na=False)]
    bultos_munchy = df_munchy['Cant_Num'].sum()
    unidades_munchy = df_munchy['Unidades_Individuales'].sum()

    # 3. TOP 20 PRODUCTOS (Agrupados por bultos vendidos)
    top_productos = df.groupby('Nombre')['Cant_Num'].sum().sort_values(ascending=False).head(20)

    # 4. TOP 20 CLIENTES (suma total y factura mayor)
    facturas = df.groupby(['Cliente', 'Factura'])['Total_Num'].sum().reset_index(name='Monto_Factura')
    top_clientes = facturas.groupby('Cliente').agg(
        Volumen_Total=('Monto_Factura', 'sum'),
        Factura_Mas_Alta=('Monto_Factura', 'max')
    ).reset_index().sort_values(by='Volumen_Total', ascending=False).head(20)

    # REPORTE EN PANTALLA
    print("\n" + "="*80)
    print("📊 REPORTE DETALLADO DE VENTAS (TOP 20 Y MARCAS)".center(80))
    print("="*80)
    
    print(f"👥 Clientes activos este mes: {clientes_activos}")
    print(f"📦 Total de bultos/cajas vendidas: {total_bultos:,.2f}\n")
    
    print("-" * 80)
    print("🏷️  VENTAS POR MARCA ESPECÍFICA:")
    print(f"  • FRITZ:  {bultos_fritz:>8,.2f} bultos  --->  (Equivale a {unidades_fritz:,.2f} unidades individuales)")
    print(f"  • MUNCHY: {bultos_munchy:>8,.2f} bultos  --->  (Equivale a {unidades_munchy:,.2f} unidades individuales)")
    print("-" * 80 + "\n")
    
    print("🏆 TOP 20 PRODUCTOS MÁS VENDIDOS (Por bulto):")
    for i, (prod, cant) in enumerate(top_productos.items(), 1):
        print(f"  {i:2d}. {prod[:55]:<55} | {cant:,.2f} bultos")

    print("\n🥇 TOP 20 CLIENTES CON MÁS VOLUMEN:")
    print(f"      {'CLIENTE':<35} | {'VOLUMEN TOTAL':<13} | {'FACTURA MÁS ALTA'}")
    print("-" * 80)
    for i, (_, row) in enumerate(top_clientes.iterrows(), 1):
        print(f"  {i:2d}. {row['Cliente'][:35]:<35} | $ {row['Volumen_Total']:>11,.2f} | $ {row['Factura_Mas_Alta']:>11,.2f}")
        
    print("="*80 + "\n")

if __name__ == "__main__":
    generar_reporte_completo()