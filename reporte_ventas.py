import pandas as pd
import re
from datetime import datetime

def generar_reporte_completo():

    archivo = "ventas_productos.xlsx"

    try:
        df = pd.read_excel(archivo)
    except FileNotFoundError:
        print(f"No se encontró {archivo}")
        return

    # ----------------------
    # LIMPIEZA NUMÉRICA
    # ----------------------

    def limpiar_numero(x):
        if pd.isna(x):
            return 0.0
        x = str(x).replace('.', '').replace(',', '.')
        try:
            return float(x)
        except:
            return 0.0

    df["Cant_Num"] = df["Cant"].apply(limpiar_numero)
    df["Total_Num"] = df["Total"].apply(limpiar_numero)

    # ----------------------
    # DETECTAR MARCA
    # ----------------------

    df["Marca"] = df["Nombre"].str.split().str[0].str.upper()
    marcas_interes = ["FRITZ","MUNCHY","HEINZ","COLOMBINA","PASTOREÑA"]
    df_marcas = df[df["Marca"].isin(marcas_interes)]

    # ----------------------
    # UNIDADES INDIVIDUALES
    # ----------------------

    def calcular_unidades(nombre, cant_bultos):
        nombre = str(nombre).upper()
        disp_match = re.search(r'X\s*(\d+)\s*DISP', nombre)
        disp = int(disp_match.group(1)) if disp_match else 1
        und_match = re.search(r'(?:X\s*)?(\d+)\s*UND', nombre)
        und = int(und_match.group(1)) if und_match else 1
        return cant_bultos * (disp * und)

    df["Unidades_Individuales"] = df.apply(
        lambda row: calcular_unidades(row["Nombre"], row["Cant_Num"]),
        axis=1
    )

    # ----------------------
    # KPI GENERALES
    # ----------------------

    clientes_activos = df["Cliente"].nunique()
    total_bultos = df["Cant_Num"].sum()
    facturacion_total = df["Total_Num"].sum()
    ticket_promedio = facturacion_total / df["Factura"].nunique() if df["Factura"].nunique()>0 else 0

    # ----------------------
    # VENTAS POR MARCA
    # ----------------------

    ventas_marca = df_marcas.groupby("Marca").agg(
        Bultos=("Cant_Num","sum"),
        Facturacion=("Total_Num","sum"),
        Unidades=("Unidades_Individuales","sum")
    ).sort_values("Facturacion",ascending=False)

    ventas_marca["Participacion_%"] = ventas_marca["Facturacion"] / facturacion_total * 100

    # ----------------------
    # TOP PRODUCTOS
    # ----------------------

    top_productos = df.groupby("Nombre")["Cant_Num"].sum().sort_values(ascending=False).head(20)

    # ----------------------
    # TOP CLIENTES POR FACTURACION
    # ----------------------

    facturacion_cliente = df.groupby("Cliente")["Total_Num"].sum().sort_values(ascending=False)
    top_clientes = facturacion_cliente.head(20)

    # ----------------------
    # RANKING CLIENTES POR MARCA
    # ----------------------

    ranking_marca = df_marcas.groupby(["Marca","Cliente"])["Total_Num"].sum().reset_index()
    ranking_marca = ranking_marca.sort_values(["Marca","Total_Num"],ascending=False)

    # ----------------------
    # PRODUCTOS QUE MÁS CRECEN (si hay Fecha)
    # ----------------------

    crecimiento_productos = None
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"])
        df["Mes"] = df["Fecha"].dt.to_period("M")
        ventas_mes = df.groupby(["Nombre","Mes"])["Cant_Num"].sum().reset_index()
        crecimiento_productos = ventas_mes.sort_values("Mes").groupby("Nombre").tail(2)

    # ----------------------
    # CLIENTES QUE NO COMPRARON ESTE MES
    # ----------------------

    clientes_no_mes = None
    if "Fecha" in df.columns:
        mes_actual = df["Fecha"].max().month
        clientes_mes = df[df["Fecha"].dt.month==mes_actual]["Cliente"].unique()
        todos_clientes = df["Cliente"].unique()
        clientes_no_mes = set(todos_clientes) - set(clientes_mes)

    # ----------------------
    # REPORTE
    # ----------------------

    print("\n" + "="*90)
    print("REPORTE COMERCIAL AVANZADO".center(90))
    print("="*90)

    print(f"Clientes activos: {clientes_activos}")
    print(f"Bultos vendidos: {total_bultos:,.2f}")
    print(f"Facturación total: ${facturacion_total:,.2f}")
    print(f"Ticket promedio: ${ticket_promedio:,.2f}")

    print("\n" + "-"*90)
    print("VENTAS POR MARCA")
    print("-"*90)
    for marca,row in ventas_marca.iterrows():
        print(f"{marca:<12} Bultos:{row['Bultos']:>10,.2f} | Facturación:${row['Facturacion']:>12,.2f} | Unidades:{row['Unidades']:>10,.0f} | Participación:{row['Participacion_%']:>6.2f}%")

    print("\n" + "-"*90)
    print("TOP 20 PRODUCTOS")
    print("-"*90)
    for i,(prod,cant) in enumerate(top_productos.items(),1):
        print(f"{i:2d}. {prod[:60]:60} {cant:>10,.2f} bultos")

    print("\n" + "-"*90)
    print("TOP 20 CLIENTES POR FACTURACIÓN")
    print("-"*90)
    for i,(cli,val) in enumerate(top_clientes.items(),1):
        print(f"{i:2d}. {cli[:40]:40} ${val:>12,.2f}")

    print("\n" + "-"*90)
    print("RANKING CLIENTES POR MARCA")
    print("-"*90)
    for marca in marcas_interes:
        print(f"\n{marca}")
        top = ranking_marca[ranking_marca["Marca"]==marca].head(10)
        for _,row in top.iterrows():
            print(f"   {row['Cliente'][:40]:40} ${row['Total_Num']:>10,.2f}")

    if clientes_no_mes:
        print("\n" + "-"*90)
        print("CLIENTES QUE NO HAN COMPRADO ESTE MES")
        print("-"*90)
        for c in list(clientes_no_mes)[:20]:
            print(c)

    print("\n" + "="*90 + "\n")

if __name__ == "__main__":
    generar_reporte_completo()