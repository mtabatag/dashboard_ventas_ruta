import streamlit as st
import pandas as pd

st.set_page_config(page_title="Dashboard de Ventas - Ruta", layout="wide")

# ===============================
# 1️⃣ CARGA DE DATOS
# ===============================
archivo = "ventas_productos.xlsx"
try:
    df = pd.read_excel(archivo)
except FileNotFoundError:
    st.error(f"No se encontró {archivo}")
    st.stop()

# Limpiar números y convertir fechas
df["Cant_Num"] = df["Cant"].str.replace('.', '').str.replace(',', '.').astype(float)
df["Total_Num"] = df["Total"].str.replace('.', '').str.replace(',', '.').astype(float)
df["Fecha"] = pd.to_datetime(df["Fecha"])
df["Marca"] = df["Nombre"].str.split().str[0].str.upper()

marcas_interes = ["FRITZ","MUNCHY","HEINZ","COLOMBINA","PASTOREÑA"]

# ===============================
# 2️⃣ FILTROS LATERALES
# ===============================
st.sidebar.header("Filtros")
fecha_min = df["Fecha"].min()
fecha_max = df["Fecha"].max()

fecha_seleccion = st.sidebar.date_input("Fecha hasta", value=fecha_max, min_value=fecha_min, max_value=fecha_max)

marcas_seleccion = st.sidebar.multiselect("Seleccionar marcas", options=marcas_interes, default=marcas_interes)

clientes_disponibles = df["Cliente"].unique()
clientes_seleccion = st.sidebar.multiselect("Seleccionar clientes", options=clientes_disponibles, default=list(clientes_disponibles))

df_filtrado = df[
    (df["Fecha"] <= pd.to_datetime(fecha_seleccion)) &
    (df["Marca"].isin(marcas_seleccion)) &
    (df["Cliente"].isin(clientes_seleccion))
]

# ===============================
# 3️⃣ KPIs PRINCIPALES
# ===============================
clientes_activos = df_filtrado["Cliente"].nunique()
total_bultos = df_filtrado["Cant_Num"].sum()
facturacion_total = df_filtrado["Total_Num"].sum()
ticket_promedio = facturacion_total / df_filtrado["Factura"].nunique() if df_filtrado["Factura"].nunique() > 0 else 0

st.title("📊 Dashboard de Ventas - Ruta")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Clientes activos", clientes_activos)
kpi2.metric("Bultos vendidos", f"{total_bultos:,.0f}")
kpi3.metric("Facturación total", f"${facturacion_total:,.2f}")
kpi4.metric("Ticket promedio", f"${ticket_promedio:,.2f}")

# ===============================
# 4️⃣ VENTAS POR MARCA
# ===============================
ventas_marca = df_filtrado[df_filtrado["Marca"].isin(marcas_interes)].groupby("Marca").agg(
    Bultos=("Cant_Num","sum"),
    Facturacion=("Total_Num","sum"),
    Unidades=("Cant_Num","sum")
).sort_values("Facturacion",ascending=False)
ventas_marca["Participacion_%"] = ventas_marca["Facturacion"]/facturacion_total*100

st.subheader("🏷️ Ventas por marca")
st.dataframe(ventas_marca.style.format({"Facturacion":"${:,.2f}","Bultos": "{:,.0f}","Unidades":"{:,.0f}","Participacion_%":"{:.2f}%"}))

st.bar_chart(ventas_marca[["Facturacion","Bultos"]])

# ===============================
# 5️⃣ TOP PRODUCTOS
# ===============================
top_productos = df_filtrado.groupby("Nombre")["Cant_Num"].sum().sort_values(ascending=False).head(20)
st.subheader("🏆 Top 20 Productos por Bultos")
st.bar_chart(top_productos)

# ===============================
# 6️⃣ TOP CLIENTES
# ===============================
top_clientes = df_filtrado.groupby("Cliente")["Total_Num"].sum().sort_values(ascending=False).head(20)
st.subheader("🥇 Top 20 Clientes por Facturación")
st.bar_chart(top_clientes)

# ===============================
# 7️⃣ CLIENTES INACTIVOS
# ===============================
mes_actual = df_filtrado["Fecha"].max().month
clientes_mes = df_filtrado[df_filtrado["Fecha"].dt.month==mes_actual]["Cliente"].unique()
todos_clientes = df_filtrado["Cliente"].unique()
clientes_no_mes = set(todos_clientes)-set(clientes_mes)
st.subheader("📉 Clientes que no compraron este mes")
st.write(list(clientes_no_mes))

# ===============================
# 8️⃣ PRODUCTOS QUE MÁS CRECEN
# ===============================
df_filtrado["Mes"] = df_filtrado["Fecha"].dt.to_period("M")
ventas_mes = df_filtrado.groupby(["Nombre","Mes"])["Cant_Num"].sum().reset_index()
ultimos_meses = ventas_mes["Mes"].sort_values().unique()[-2:]

crecimiento = ventas_mes[ventas_mes["Mes"].isin(ultimos_meses)].pivot(index="Nombre",columns="Mes",values="Cant_Num").fillna(0)
crecimiento["Crecimiento_%"] = ((crecimiento[ultimos_meses[-1]]-crecimiento[ultimos_meses[-2]])/crecimiento[ultimos_meses[-2]].replace(0,1))*100
crecimiento = crecimiento.sort_values("Crecimiento_%",ascending=False).head(20)

st.subheader("📈 Productos que más crecen mes a mes")
st.dataframe(crecimiento.style.format("{:.2f}"))
