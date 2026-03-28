import pandas as pd
import streamlit as st
import re

# -----------------------------
# Función para extraer marca
# -----------------------------
def extraer_marca(nombre):
    """Extrae la marca considerando nombres compuestos con artículos."""
    if not isinstance(nombre, str): return "Sin Marca"
    partes = nombre.split()
    if not partes: return "Sin Marca"
    
    articulos = ["LA", "EL", "LOS", "LAS", "SAN", "SANTA", "DON", "DOÑA", "MI", "DE", "DEL"]
    
    if partes[0].upper() in articulos and len(partes) > 1:
        return f"{partes[0].upper()} {partes[1].upper()}"
    else:
        return partes[0].upper()

# -----------------------------
# Función para calcular unidades
# -----------------------------
def calcular_unidades_por_bulto(nombre):
    """Extrae la cantidad de unidades individuales por bulto según el nombre del producto."""
    if not isinstance(nombre, str): return 1
    name = nombre.upper()
    
    m_hojas = re.search(r'(\d+)\s*(UND|PAQ|ROLLOS)\s*X\s*\d+\s*HOJAS', name)
    if m_hojas:
        return int(m_hojas.group(1))
        
    m_pair = re.search(r'(\d+)\s*(DISP|PAQ|ESTUCHE|CAJA|UND)\w*\s*X\s*(\d+)\s*(UND|ROLLO|TACO|PAQ)\w*', name)
    if m_pair:
        return int(m_pair.group(1)) * int(m_pair.group(3))
        
    m_single = re.findall(r'(\d+)\s*(UND|PAQ|ROLLO|U\b|TACO)', name)
    if m_single:
        m_x = re.search(r'X\s*(\d+)\s*(UND|PAQ|ROLLO|U\b|TACO)', name)
        if m_x:
             return int(m_x.group(1))
        return int(m_single[-1][0])
        
    return 1 

# -----------------------------
# Cargar datos de ventas
# -----------------------------
@st.cache_data
def cargar_ventas(ruta_excel):
    df = pd.read_excel(ruta_excel)
    df.columns = df.columns.str.strip()

    if 'Nombre' in df.columns:
        df = df[~df['Nombre'].astype(str).str.upper().str.contains('TOTAL', na=False)]

    if 'Fecha' in df.columns:
        # Formato aa/mm/dd generado por el extractor
        df['Fecha'] = pd.to_datetime(df['Fecha'], format='%y/%m/%d', errors='coerce')
    elif 'Archivo' in df.columns:
        df['Fecha_Str'] = df['Archivo'].str.extract(r'(\d{2}-\d{2}-\d{2})')[0]
        df['Fecha'] = pd.to_datetime(df['Fecha_Str'], format='%d-%m-%y', errors='coerce')
    else:
        df['Fecha'] = pd.NaT

    if 'Nombre' in df.columns:
        df['Marca'] = df['Nombre'].apply(extraer_marca)
        df['Und_por_bulto'] = df['Nombre'].apply(calcular_unidades_por_bulto)
    else:
        df['Marca'] = "Sin Marca"
        df['Und_por_bulto'] = 1

    for col in ['Cant', 'Precio', 'Total']:
        if col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                df[col] = df[col].str.replace(r'[^\d\.-]', '', regex=True)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0
            
    df['Unidades'] = df['Cant'] * df['Und_por_bulto']

    return df

# -----------------------------
# Cargar master clientes
# -----------------------------
@st.cache_data
def cargar_master_clientes(ruta_excel):
    df_master = pd.read_excel(ruta_excel)
    df_master.columns = df_master.columns.str.strip()
    if 'Nombre' not in df_master.columns:
        st.error("El master de clientes no contiene la columna 'Nombre'")
        return pd.Series([], name='Nombre')
    return df_master['Nombre'].unique()

# -----------------------------
# Configuración de la página
# -----------------------------
st.set_page_config(page_title="Dashboard F&S", layout="wide")

# -----------------------------
# Cargar datos
# -----------------------------
df_ventas = cargar_ventas("ventas_productos.xlsx")
master_clientes = cargar_master_clientes("master_clientes_actualizado.xlsx")

# -----------------------------
# Dashboard
# -----------------------------
st.title("📊 Dashboard F&S Distribución - Marcos Tabata")

# -----------------------------
# Filtros
# -----------------------------
col_filtro1, col_filtro2, col_filtro3 = st.columns(3)

with col_filtro1:
    if df_ventas['Fecha'].notna().any():
        df_ventas['Mes'] = df_ventas['Fecha'].dt.to_period('M')
        mes_actual = pd.Period(pd.Timestamp.now(), freq='M')
        meses_disponibles = df_ventas['Mes'].dropna().sort_values(ascending=False).unique()
        mes_seleccionado = st.selectbox(
            "Selecciona el Mes",
            meses_disponibles,
            index=list(meses_disponibles).index(mes_actual) if mes_actual in meses_disponibles else 0
        )
        df_filtrado_mes = df_ventas[df_ventas['Mes'] == mes_seleccionado]
    else:
        df_filtrado_mes = df_ventas.copy()
        st.warning("⚠️ No se detectaron fechas válidas. Revisa el archivo cargado.")

with col_filtro2:
    if 'Cliente' in df_filtrado_mes.columns:
        clientes_disponibles = df_filtrado_mes['Cliente'].dropna().unique()
        cliente_seleccionado = st.selectbox("Selecciona el Cliente", ["Todos"] + list(clientes_disponibles))
        
        if cliente_seleccionado != "Todos":
            df_filtrado_cli = df_filtrado_mes[df_filtrado_mes['Cliente'] == cliente_seleccionado]
        else:
            df_filtrado_cli = df_filtrado_mes
    else:
        df_filtrado_cli = df_filtrado_mes

with col_filtro3:
    marcas_disponibles = sorted(df_filtrado_cli['Marca'].unique())
    marca_seleccionada = st.selectbox("Selecciona la Marca", ["Todas"] + list(marcas_disponibles))

    if marca_seleccionada != "Todas":
        df_filtrado = df_filtrado_cli[df_filtrado_cli['Marca'] == marca_seleccionada]
    else:
        df_filtrado = df_filtrado_cli

# -----------------------------
# Cálculos previos
# -----------------------------
if 'Cliente' in df_filtrado.columns:
    clientes_activados = [c for c in master_clientes if c in df_filtrado['Cliente'].unique()]
    clientes_faltan = [c for c in master_clientes if c not in df_filtrado['Cliente'].unique()]
    num_activados = len(clientes_activados)
    num_faltan = len(clientes_faltan)
    total_clientes_mes = df_filtrado['Cliente'].nunique()
else:
    clientes_activados = []
    clientes_faltan = []
    num_activados = 0
    num_faltan = 0
    total_clientes_mes = 0

total_facturado = df_filtrado['Total'].sum()
ticket_promedio = total_facturado / num_activados if num_activados > 0 else 0
total_master = len(master_clientes)
cobertura = (num_activados / total_master * 100) if total_master > 0 else 0

# -----------------------------
# Métricas generales
# -----------------------------
st.subheader("📈 Métricas Generales")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Bultos Vendidos", f"{df_filtrado['Cant'].sum():,.0f}")
col2.metric("Unidades Vendidas", f"{df_filtrado['Unidades'].sum():,.0f}")
col3.metric("Monto Facturado", f"${total_facturado:,.2f}")
col4.metric("Total Clientes (Mes)", total_clientes_mes)

col5, col6, col7, col8 = st.columns(4)
col5.metric("Ticket Promedio", f"${ticket_promedio:,.2f}")
col6.metric("Clientes Master Activados", num_activados)
col7.metric("Clientes por Activar", num_faltan)
col8.metric("Cobertura de Ruta", f"{cobertura:.1f}%")

st.divider()

# -----------------------------
# MÉTRICAS POR MARCA
# -----------------------------
st.subheader("🏢 Resumen por Marca")

resumen_marca = df_filtrado.groupby('Marca', as_index=False).agg(
    Bultos=('Cant', 'sum'),
    Unidades=('Unidades', 'sum'),
    Facturación=('Total', 'sum')
).sort_values(by='Facturación', ascending=False)

resumen_marca_mostrar = resumen_marca.copy()
resumen_marca_mostrar['Bultos'] = resumen_marca_mostrar['Bultos'].apply(lambda x: f"{x:,.0f}")
resumen_marca_mostrar['Unidades'] = resumen_marca_mostrar['Unidades'].apply(lambda x: f"{x:,.0f}")
resumen_marca_mostrar['Facturación'] = resumen_marca_mostrar['Facturación'].apply(lambda x: f"${x:,.2f}")

st.dataframe(resumen_marca_mostrar, width='stretch', hide_index=True)

st.divider()

# -----------------------------
# Tendencia Diaria
# -----------------------------
st.subheader("📅 Tendencia de Facturación Diaria")
if not df_filtrado.empty and df_filtrado['Fecha'].notna().any():
    ventas_diarias = df_filtrado.groupby(df_filtrado['Fecha'].dt.date)['Total'].sum()
    st.line_chart(ventas_diarias)
else:
    st.info("No hay datos de fechas para mostrar la tendencia diaria.")

st.divider()

# -----------------------------
# Top Productos
# -----------------------------
st.subheader("🏆 Top Productos por Facturación")
top_productos = (
    df_filtrado.groupby('Nombre', as_index=False)['Total']
    .sum()
    .sort_values(by='Total', ascending=False)
)

col_graf_prod, col_tab_prod = st.columns([1.5, 1])

with col_graf_prod:
    st.markdown("**Top 10 Productos (Gráfico)**")
    if not top_productos.empty:
        st.bar_chart(top_productos.head(10).set_index('Nombre')['Total'])

with col_tab_prod:
    st.markdown("**Top 40 Productos (Tabla)**")
    st.dataframe(top_productos.head(40), width='stretch', hide_index=True)

st.divider()

# -----------------------------
# Top Clientes
# -----------------------------
if 'Cliente' in df_filtrado.columns:
    st.subheader("👥 Top Clientes por Facturación")
    top_clientes = (
        df_filtrado.groupby('Cliente', as_index=False)['Total']
        .sum()
        .sort_values(by='Total', ascending=False)
    )
    
    col_graf_cli, col_tab_cli = st.columns([1.5, 1])
    
    with col_graf_cli:
        st.markdown("**Top 10 Clientes (Gráfico)**")
        if not top_clientes.empty:
            st.bar_chart(top_clientes.head(10).set_index('Cliente')['Total'])
        
    with col_tab_cli:
        st.markdown("**Top 20 Clientes (Tabla)**")
        st.dataframe(top_clientes.head(20), width='stretch', hide_index=True)

st.divider()

# -----------------------------
# Detalle completo de ventas
# -----------------------------
st.subheader("📋 Detalle Completo de Ventas")
df_mostrar = df_filtrado.drop(columns=['Fecha_Str', 'Und_por_bulto', 'Mes'], errors='ignore')

if 'Fecha' in df_mostrar.columns:
    df_mostrar['Fecha'] = df_mostrar['Fecha'].dt.strftime('%Y-%m-%d')

st.dataframe(df_mostrar.sort_values(by='Total', ascending=False), width='stretch', hide_index=True)
