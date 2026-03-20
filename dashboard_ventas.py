import pandas as pd
import re
import os
import streamlit as st
from datetime import datetime

# ---------------------------
# Función para cargar datos
# ---------------------------
@st.cache_data
def cargar_datos():
    archivo = os.path.join(os.path.dirname(__file__), "ventas_productos.xlsx")
    try:
        df = pd.read_excel(archivo)
    except FileNotFoundError:
        st.error(f"No se encontró el archivo '{archivo}'")
        return pd.DataFrame()
    
    # Limpiar números
    def limpiar_numero(x):
        if pd.isna(x): return 0.0
        x_str = str(x).replace('.', '').replace(',', '.')
        try:
            return float(x_str)
        except:
            return 0.0

    df['Cant_Num'] = df['Cant'].apply(limpiar_numero)
    df['Total_Num'] = df['Total'].apply(limpiar_numero)

    # Unidades individuales
    def calcular_unidades(nombre, cant_bultos):
        nombre = str(nombre).upper()
        disp_match = re.search(r'X\s*(\d+)\s*DISP', nombre)
        disp = int(disp_match.group(1)) if disp_match else 1
        und_match = re.search(r'(?:X\s*)?(\d+)\s*UND', nombre)
        und = int(und_match.group(1)) if und_match else 1
        return cant_bultos * (disp * und)

    df['Unidades_Individuales'] = df.apply(lambda row: calcular_unidades(row['Nombre'], row['Cant_Num']), axis=1)

    if 'Fecha' in df.columns:
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')

    return df

# ---------------------------
# Dashboard principal
# ---------------------------
def generar_dashboard():
    st.set_page_config(page_title="Dashboard Ventas", layout="wide")
    st.title("📊 Dashboard de Ventas de Ruta - Streamlit Ligero")

    # Botón para recargar datos
    if st.button("🔄 Recargar datos"):
        st.cache_data.clear()
        df = cargar_datos()
        st.success("Datos actualizados!")
    else:
        df = cargar_datos()

    if df.empty:
        st.warning("No hay datos para mostrar")
        return

    # ---------------------------
    # KPIs generales
    # ---------------------------
    facturacion_total = df['Total_Num'].sum()
    total_bultos = df['Cant_Num'].sum()
    clientes_activos = df['Cliente'].nunique()
    ticket_promedio = facturacion_total / clientes_activos if clientes_activos > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💰 Facturación Total", f"${facturacion_total:,.2f}")
    col2.metric("📦 Total de Bultos", f"{total_bultos:,.2f}")
    col3.metric("👥 Clientes Activos", clientes_activos)
    col4.metric("🧾 Ticket Promedio", f"${ticket_promedio:,.2f}")

    # ---------------------------
    # Filtrar por marcas
    # ---------------------------
    marcas = ["FRITZ","MUNCHY","HEINZ","COLOMBINA","PASTOREÑA"]
    st.subheader("🏷️ Filtrar por marcas")
    marcas_seleccionadas = st.multiselect("Selecciona marcas", marcas, default=marcas)

    if marcas_seleccionadas:
        df_marcas = df[df['Nombre'].str.upper().str.contains('|'.join(marcas_seleccionadas))]
    else:
        df_marcas = df.copy()

    # Métricas por marca
    st.subheader("📊 Métricas por Marca")
    resumen_marcas = []
    for marca in marcas_seleccionadas:
        df_m = df[df['Nombre'].str.upper().str.contains(marca)]
        bultos = df_m['Cant_Num'].sum()
        facturacion = df_m['Total_Num'].sum()
        unidades = df_m['Unidades_Individuales'].sum()
        resumen_marcas.append([marca, bultos, unidades, facturacion])

    if resumen_marcas:
        df_marcas_display = pd.DataFrame(resumen_marcas, columns=["Marca","Bultos","Unidades","Facturación"])
        df_marcas_display["Bultos"] = df_marcas_display["Bultos"].apply(lambda x: f"{x:,.2f}")
        df_marcas_display["Unidades"] = df_marcas_display["Unidades"].apply(lambda x: f"{x:,.2f}")
        df_marcas_display["Facturación"] = df_marcas_display["Facturación"].apply(lambda x: f"${x:,.2f}")
        st.table(df_marcas_display)

    # ---------------------------
    # Top 20 Productos
    # ---------------------------
    st.subheader("🏆 Top 20 Productos")
    top_productos = df.groupby("Nombre")["Cant_Num"].sum().sort_values(ascending=False).head(20)
    df_top_prod = top_productos.reset_index().rename(columns={"Nombre":"Producto","Cant_Num":"Bultos"})
    df_top_prod["Bultos"] = df_top_prod["Bultos"].apply(lambda x: f"{x:,.2f}")
    st.table(df_top_prod)

    # ---------------------------
    # Top 20 Clientes
    # ---------------------------
    st.subheader("🥇 Top 20 Clientes")
    facturas = df.groupby(["Cliente","Factura"])["Total_Num"].sum().reset_index(name="Monto_Factura")
    top_clientes = facturas.groupby("Cliente").agg(
        Volumen_Total=("Monto_Factura","sum"),
        Factura_Mas_Alta=("Monto_Factura","max")
    ).reset_index().sort_values(by="Volumen_Total", ascending=False).head(20)

    df_top_cli = top_clientes.rename(columns={
        "Cliente":"Cliente",
        "Volumen_Total":"Volumen Total",
        "Factura_Mas_Alta":"Factura Más Alta"
    })
    df_top_cli["Volumen Total"] = df_top_cli["Volumen Total"].apply(lambda x: f"${x:,.2f}")
    df_top_cli["Factura Más Alta"] = df_top_cli["Factura Más Alta"].apply(lambda x: f"${x:,.2f}")
    st.table(df_top_cli)

    # ---------------------------
    # Alertas importantes
    # ---------------------------
    st.subheader("⚠️ Alertas")
    hoy = datetime.now()
    if 'Fecha' in df.columns:
        mes_actual = hoy.month
        clientes_mes = df[df['Fecha'].dt.month==mes_actual]['Cliente'].unique()
        clientes_todos = df['Cliente'].unique()
        clientes_inactivos = set(clientes_todos) - set(clientes_mes)
        st.write(f"Clientes que no compraron este mes: {len(clientes_inactivos)}")
        st.write(list(clientes_inactivos)[:20])

        ultimos_meses = df['Fecha'].max() - pd.DateOffset(months=2)
        df_reciente = df[df['Fecha'] > ultimos_meses]
        top_crecimiento = df_reciente.groupby("Nombre")["Cant_Num"].sum().sort_values(ascending=False).head(10)
        df_top_crec = top_crecimiento.reset_index().rename(columns={"Nombre":"Producto","Cant_Num":"Bultos"})
        df_top_crec["Bultos"] = df_top_crec["Bultos"].apply(lambda x: f"{x:,.2f}")
        st.write("Productos que están creciendo en los últimos 2 meses:")
        st.table(df_top_crec)
    else:
        st.write("No hay columna Fecha para alertas y productos en crecimiento.")

# ---------------------------
# Ejecutar dashboard
# ---------------------------
if __name__ == "__main__":
    generar_dashboard()