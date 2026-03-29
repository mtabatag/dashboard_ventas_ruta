import pandas as pd
import streamlit as st
import re
import os

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
    try:
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
    except Exception as e:
        st.error(f"Error al cargar ventas: {e}")
        return pd.DataFrame()

# -----------------------------
# Cargar master clientes
# -----------------------------
@st.cache_data
def cargar_master_clientes(ruta_excel):
    try:
        df_master = pd.read_excel(ruta_excel)
        df_master.columns = df_master.columns.str.strip()
        if 'Nombre' not in df_master.columns:
            st.error("El master de clientes no contiene la columna 'Nombre'")
            return pd.Series([], name='Nombre')
        return df_master['Nombre'].unique()
    except Exception:
        return pd.Series([], name='Nombre')

# -----------------------------
# Cargar pagos procesados (Comisiones)
# -----------------------------
@st.cache_data
def cargar_pagos(ruta_txt):
    try:
        df_pagos = pd.read_csv(ruta_txt, sep=None, engine='python')
        df_pagos.columns = df_pagos.columns.str.strip()
        
        col_fecha = next((col for col in df_pagos.columns if 'FECHA' in col.upper()), None)
        if col_fecha:
            df_pagos[col_fecha] = pd.to_datetime(df_pagos[col_fecha], errors='coerce', dayfirst=True)
            
            def clasificar_quincena(fecha):
                if pd.isna(fecha): return "Sin Fecha"
                quincena = "1ra Quincena" if fecha.day <= 15 else "2da Quincena"
                return f"{fecha.strftime('%Y-%m')} - {quincena}"
            
            df_pagos['Quincena'] = df_pagos[col_fecha].apply(clasificar_quincena)
        else:
            df_pagos['Quincena'] = "Sin Fecha"

        total_pago = pd.Series(0.0, index=df_pagos.index)
        
        for col_name in ['TRANSFERENCIA', 'EFECTIVO']:
            col_match = next((c for c in df_pagos.columns if col_name in c.upper()), None)
            if col_match:
                if df_pagos[col_match].dtype == object:
                    df_pagos[col_match] = df_pagos[col_match].astype(str).str.replace(',', '.', regex=False)
                    df_pagos[col_match] = df_pagos[col_match].str.replace(r'[^\d\.-]', '', regex=True)
                df_pagos[f'{col_name}_Num'] = pd.to_numeric(df_pagos[col_match], errors='coerce').fillna(0)
                total_pago += df_pagos[f'{col_name}_Num']
        
        if total_pago.sum() == 0:
            col_monto = next((col for col in df_pagos.columns if any(x in col.upper() for x in ['MONTO', 'TOTAL', 'PAGO', 'VALOR'])), None)
            if col_monto:
                if df_pagos[col_monto].dtype == object:
                    df_pagos[col_monto] = df_pagos[col_monto].astype(str).str.replace(',', '.', regex=False)
                    df_pagos[col_monto] = df_pagos[col_monto].str.replace(r'[^\d\.-]', '', regex=True)
                total_pago = pd.to_numeric(df_pagos[col_monto], errors='coerce').fillna(0)

        df_pagos['Monto_Limpio'] = total_pago

        return df_pagos
    except Exception:
        return pd.DataFrame()

# -----------------------------
# Configuración de la página
# -----------------------------
st.set_page_config(page_title="Dashboard F&S", layout="wide")

# -----------------------------
# Cargar datos
# -----------------------------
df_ventas = cargar_ventas("ventas_productos.xlsx")
master_clientes = cargar_master_clientes("master_clientes_actualizado.xlsx")
df_pagos = cargar_pagos("pagos_procesados.txt")

# -----------------------------
# Dashboard
# -----------------------------
st.title("📊 Dashboard de Ventas F&S Distribución")

# -----------------------------
# Filtros de Ventas
# -----------------------------
col_filtro1, col_filtro2, col_filtro3 = st.columns(3)

with col_filtro1:
    if not df_ventas.empty and df_ventas['Fecha'].notna().any():
        df_ventas['Mes'] = df_ventas['Fecha'].dt.to_period('M')
        mes_actual = pd.Period(pd.Timestamp.now(), freq='M')
        meses_disponibles = df_ventas['Mes'].dropna().sort_values(ascending=False).unique()
        mes_seleccionado = st.selectbox(
            "Selecciona el Mes (Aplica a Ventas)",
            meses_disponibles,
            index=list(meses_disponibles).index(mes_actual) if mes_actual in meses_disponibles else 0
        )
        df_filtrado_mes = df_ventas[df_ventas['Mes'] == mes_seleccionado]
    else:
        df_filtrado_mes = df_ventas.copy()

with col_filtro2:
    if not df_filtrado_mes.empty and 'Cliente' in df_filtrado_mes.columns:
        clientes_disponibles = df_filtrado_mes['Cliente'].dropna().unique()
        cliente_seleccionado = st.selectbox("Selecciona el Cliente", ["Todos"] + list(clientes_disponibles))
        
        if cliente_seleccionado != "Todos":
            df_filtrado_cli = df_filtrado_mes[df_filtrado_mes['Cliente'] == cliente_seleccionado]
        else:
            df_filtrado_cli = df_filtrado_mes
    else:
        df_filtrado_cli = df_filtrado_mes

with col_filtro3:
    if not df_filtrado_cli.empty and 'Marca' in df_filtrado_cli.columns:
        marcas_disponibles = sorted(df_filtrado_cli['Marca'].unique())
        marca_seleccionada = st.selectbox("Selecciona la Marca", ["Todas"] + list(marcas_disponibles))

        if marca_seleccionada != "Todas":
            df_filtrado = df_filtrado_cli[df_filtrado_cli['Marca'] == marca_seleccionada]
        else:
            df_filtrado = df_filtrado_cli
    else:
        df_filtrado = df_filtrado_cli

# -----------------------------
# Cálculos de Ventas y Comisiones
# -----------------------------
if not df_filtrado.empty:
    total_facturado = df_filtrado['Total'].sum()
    
    # Calcular Base Imponible directamente (Total / 1.16)
    base_imponible_total = total_facturado / 1.16
        
    comision_ventas = base_imponible_total * 0.003 # 0.3% sobre la base
    
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
else:
    total_facturado = 0.0
    base_imponible_total = 0.0
    comision_ventas = 0.0
    clientes_activados = []
    clientes_faltan = []
    num_activados = 0
    num_faltan = 0
    total_clientes_mes = 0

ticket_promedio = total_facturado / num_activados if num_activados > 0 else 0
total_master = len(master_clientes)
cobertura = (num_activados / total_master * 100) if total_master > 0 else 0

# -----------------------------
# Módulo de Comisiones Consolidadas
# -----------------------------
st.subheader("💰 Resumen de Comisiones Generadas")

if not df_pagos.empty and 'Quincena' in df_pagos.columns and 'Monto_Limpio' in df_pagos.columns:
    quincenas_disp = sorted(df_pagos['Quincena'].unique(), reverse=True)
    quincena_sel = st.selectbox("Filtrar Quincena de Cobranza", ["Todas"] + list(quincenas_disp))
    
    if quincena_sel != "Todas":
        df_pagos_filtrado = df_pagos[df_pagos['Quincena'] == quincena_sel]
    else:
        df_pagos_filtrado = df_pagos
        
    total_pagos = df_pagos_filtrado['Monto_Limpio'].sum()
    comision_cobranza = total_pagos * 0.012
    
    # Mostrar métricas de cobranza y ventas juntas
    col_c1, col_c2, col_c3, col_c4 = st.columns(4)
    col_c1.metric("Cobranza Procesada", f"${total_pagos:,.2f}")
    col_c2.metric("Comisión Cobranza (1.2%)", f"${comision_cobranza:,.2f}")
    col_c3.metric("Base Imponible (Ventas)", f"${base_imponible_total:,.2f}")
    col_c4.metric("Comisión Ventas (0.3%)", f"${comision_ventas:,.2f}")
    
    with st.expander("Ver detalle de pagos procesados"):
        cols_mostrar = [c for c in df_pagos_filtrado.columns if 'Num' not in c and c != 'Monto_Limpio']
        st.dataframe(df_pagos_filtrado[cols_mostrar], width='stretch', hide_index=True)
else:
    # Si no hay pagos, mostrar solo las comisiones de ventas
    st.info("No hay pagos procesados en esta ruta, mostrando solo proyección de ventas.")
    col_c1, col_c2 = st.columns(2)
    col_c1.metric("Base Imponible (Ventas)", f"${base_imponible_total:,.2f}")
    col_c2.metric("Comisión Ventas (0.3%)", f"${comision_ventas:,.2f}")

st.divider()

# -----------------------------
# Métricas generales de la Ruta
# -----------------------------
st.subheader("📈 Métricas Generales (Ventas)")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Bultos Vendidos", f"{df_filtrado['Cant'].sum():,.0f}" if not df_filtrado.empty else "0")
col2.metric("Unidades Vendidas", f"{df_filtrado['Unidades'].sum():,.0f}" if not df_filtrado.empty else "0")
col3.metric("Monto Facturado", f"${total_facturado:,.2f}")
col4.metric("Ticket Promedio", f"${ticket_promedio:,.2f}")

col5, col6, col7, col8 = st.columns(4)
col5.metric("Total Clientes (Mes)", total_clientes_mes)
col6.metric("Master Activados", num_activados)
col7.metric("Por Activar", num_faltan)
col8.metric("Cobertura de Ruta", f"{cobertura:.1f}%")

st.divider()

# -----------------------------
# MÉTRICAS POR MARCA
# -----------------------------
st.subheader("🏢 Resumen por Marca")

if not df_filtrado.empty:
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
else:
    st.write("No hay datos de marcas para mostrar.")

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
if not df_filtrado.empty:
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
else:
    st.write("No hay datos de productos para mostrar.")

st.divider()

# -----------------------------
# Top Clientes
# -----------------------------
if not df_filtrado.empty and 'Cliente' in df_filtrado.columns:
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
if not df_filtrado.empty:
    df_mostrar = df_filtrado.drop(columns=['Fecha_Str', 'Und_por_bulto', 'Mes'], errors='ignore')

    if 'Fecha' in df_mostrar.columns:
        df_mostrar['Fecha'] = df_mostrar['Fecha'].dt.strftime('%Y-%m-%d')

    st.dataframe(df_mostrar.sort_values(by='Total', ascending=False), width='stretch', hide_index=True)
else:
    st.write("No hay detalle de ventas para mostrar.")