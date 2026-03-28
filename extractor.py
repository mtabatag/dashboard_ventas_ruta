import pdfplumber
import pandas as pd
import re
from pathlib import Path

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
        
        # EXTRAER Y FORMATEAR LA FECHA DEL ARCHIVO
        # Buscamos el patrón DD-MM-AA (ej: 20-02-26)
        match_fecha = re.search(r'(\d{2})-(\d{2})-(\d{2})', pdf_path.name)
        if match_fecha:
            dia, mes, anio = match_fecha.groups()
            # Invertimos al formato aa/mm/dd para que se ordene perfectamente
            fecha_formateada = f"{anio}/{mes}/{dia}"
        else:
            fecha_formateada = "Sin fecha"
            
        with pdfplumber.open(pdf_path) as pdf:
            cliente_actual = "Desconocido"
            factura_actual = "Desconocido"
            
            for page in pdf.pages:
                # Extraemos el texto respetando los espacios físicos exactos
                texto_visual = page.extract_text(layout=True)
                if not texto_visual: continue
                
                lineas = texto_visual.split('\n')
                
                for linea in lineas:
                    linea_limpia = linea.strip()
                    if not linea_limpia: continue

                    # 1. CAPTURAR FACTURA Y CLIENTE
                    # Buscamos la línea horizontal exacta. 
                    match_cabecera = re.search(r'\d{1,2}/\d{1,2}/\d{4}\s+(\d{10})\s+FAC\s+[A-Z0-9\-]+\s+(.*)', linea_limpia)
                    
                    if match_cabecera:
                        factura_actual = match_cabecera.group(1)
                        resto = match_cabecera.group(2)
                        
                        # Limpiamos información extra a la derecha del cliente
                        resto = re.sub(r'\s+[\d.,]+$', '', resto)
                        resto = re.sub(r'\s+\d{2}-\d{2}-\d{2}$', '', resto)
                        resto = re.sub(r'\s*SALIDA\s+[A-Z]+$', '', resto, flags=re.IGNORECASE)
                        resto = re.sub(r'\s+[\d.,]+$', '', resto)
                        
                        cliente_actual = resto.strip()
                        continue

                    # 2. CAPTURAR PRODUCTOS
                    prod_match = re.search(r'^([A-Z0-9\-]{3,15})\s+(.+?)\s+(\d+,\d+)\s+(\d+,\d+)(?:\s+(\d+,\d+))?$', linea_limpia)
                    
                    if prod_match:
                        cod, nom, cant, prec, tot = prod_match.groups()
                        
                        # Bloqueo total para evitar meter títulos de columnas
                        if "CÓDIGO" not in cod.upper() and "TOTAL" not in cod.upper():
                            datos_finales.append({
                                "Archivo": pdf_path.name,
                                "Fecha": fecha_formateada,  # <-- Columna Fecha agregada aquí
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
        df.to_excel(archivo_salida, index=False)
        print(f"\n--- Extracción Completada ---")
        print(f"Se procesaron {len(df)} registros.")
        print(f"Archivo guardado como: {archivo_salida}")
    else:
        print("No se extrajeron datos. Verifica el formato del PDF.")

if __name__ == "__main__":
    extraer_facturas_visual()