import pdfplumber
import pandas as pd
import re
from pathlib import Path
from datetime import datetime

def extraer_facturas_visual():

    carpeta_entrada = Path("facturacion_pdf")
    archivo_salida = "ventas_productos.xlsx"

    if not carpeta_entrada.exists():
        print(f"Error: La carpeta '{carpeta_entrada}' no existe.")
        return

    archivos_pdf = list(carpeta_entrada.glob("FACT. TABATA MARCOS *.pdf"))

    datos_finales = []

    for pdf_path in archivos_pdf:

        print(f"Procesando: {pdf_path.name}...")

        with pdfplumber.open(pdf_path) as pdf:

            cliente_actual = "Desconocido"
            factura_actual = "Desconocido"
            fecha_actual = None

            for page in pdf.pages:

                texto_visual = page.extract_text(layout=True)
                if not texto_visual: 
                    continue

                lineas = texto_visual.split('\n')

                for linea in lineas:

                    linea_limpia = linea.strip()
                    if not linea_limpia:
                        continue

                    # =========================
                    # CAPTURAR FECHA + FACTURA + CLIENTE
                    # =========================

                    match_cabecera = re.search(
                        r'(\d{1,2}/\d{1,2}/\d{4})\s+(\d{10})\s+FAC\s+[A-Z0-9\-]+\s+(.*)',
                        linea_limpia
                    )

                    if match_cabecera:

                        fecha_str = match_cabecera.group(1)
                        factura_actual = match_cabecera.group(2)
                        resto = match_cabecera.group(3)

                        try:
                            fecha_actual = datetime.strptime(fecha_str, "%d/%m/%Y")
                        except:
                            fecha_actual = None

                        # limpiar cliente
                        resto = re.sub(r'\s+[\d.,]+$', '', resto)
                        resto = re.sub(r'\s+\d{2}-\d{2}-\d{2}$', '', resto)
                        resto = re.sub(r'\s*SALIDA\s+[A-Z]+$', '', resto, flags=re.IGNORECASE)
                        resto = re.sub(r'\s+[\d.,]+$', '', resto)

                        cliente_actual = resto.strip()

                        continue

                    # =========================
                    # CAPTURAR PRODUCTOS
                    # =========================

                    prod_match = re.search(
                        r'^([A-Z0-9\-]{3,15})\s+(.+?)\s+(\d+,\d+)\s+(\d+,\d+)(?:\s+(\d+,\d+))?$',
                        linea_limpia
                    )

                    if prod_match:

                        cod, nom, cant, prec, tot = prod_match.groups()

                        if "CÓDIGO" not in cod.upper() and "TOTAL" not in cod.upper():

                            datos_finales.append({

                                "Fecha": fecha_actual,
                                "Archivo": pdf_path.name,
                                "Cliente": cliente_actual,
                                "Factura": factura_actual,
                                "Código": cod,
                                "Nombre": nom.strip(),
                                "Cant": cant,
                                "Precio": prec,
                                "Total": tot if tot else "0,00"

                            })

    if datos_finales:

        df = pd.DataFrame(datos_finales)
        df["Fecha"] = pd.to_datetime(df["Fecha"])
        df.to_excel(archivo_salida, index=False)

        print("\n--- Extracción Completada ---")
        print(f"Se procesaron {len(df)} registros.")
        print(f"Archivo guardado como: {archivo_salida}")

    else:
        print("No se extrajeron datos. Verifica el formato del PDF.")

if __name__ == "__main__":
    extraer_facturas_visual()