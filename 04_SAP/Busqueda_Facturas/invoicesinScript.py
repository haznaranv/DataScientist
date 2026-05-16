import os
import glob
import re
import pandas as pd
import pyodbc
from itertools import islice
from datetime import datetime

# conexión SQL Server
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=TuDireccionDeServer;"
    "DATABASE=NombredetuBBDD;"
    "UID=TuUsuario;" 
    "PWD=TuPassword"
)

def encontrar_archivo_invoices():
    """Encuentra el archivo que empieza con 'invoicesin_'"""
    archivos = glob.glob("invoicesin_*")
    if archivos:
        return archivos[0]
    else:
        raise FileNotFoundError("No se encontró ningún archivo que empiece con 'invoicesin_'")

def extraer_facturas_ca_regex(archivo):
    """Extrae usando expresiones regulares para mayor precisión"""
    facturas = []
    
    patron = r'^(CA\w+)\s+.*?(\d+\.pdf)'
    
    with open(archivo, 'r', encoding='utf-8') as f:
        lineas = f.readlines()
    
    print(f"📄 Total líneas en archivo: {len(lineas)}")
    
    for i, linea in enumerate(lineas):
        linea = linea.strip()
        if not linea:
        
            continue
            
        match = re.search(patron, linea)
        longitud = len(linea)
        order = ""
        
        if longitud > 80:
            partes = linea.split()
            if len(partes) > 3:
                order = partes[3]
            
        if match:
            numero_factura = match.group(1)
            pdf_archivo = match.group(2)
            facturas.append({
                'factura': numero_factura,
                'pdf': pdf_archivo,
                'orden': order
            })
    
    print(f"✅ Facturas extraídas del fichero: {len(facturas)}")
    return facturas

def transformacion_facturas(facturas):
    """Transforma las facturas a 2 columnas"""
    if not facturas:
        print("⚠️ No hay facturas para transformar")
        return pd.DataFrame()
    
    ordenFacturas = pd.DataFrame(facturas)
    #ordenFacturas['factura'] = ordenFacturas['factura'].str.replace('CA', '', regex=False)
    ordenFacturas['factura'] = ordenFacturas['factura'].apply(lambda x: x[2:] if x.startswith('CA') else x)
    ordenFacturas['orden'] = ordenFacturas['orden'].astype(str)
    
    ordenFacturas = ordenFacturas[["orden", "factura", "pdf"]]
    Salidafactura = pd.DataFrame({
        'Arckey': ordenFacturas['orden'] + '_' + ordenFacturas['factura'], 
        'pdf': ordenFacturas['pdf'],
        'factura_original': 'CA' + ordenFacturas['factura'],  # Guardamos factura original para referencia
        'orden_original': ordenFacturas['orden']
    })
    
    return Salidafactura

def chunked(iterable, size):
    it = iter(iterable)
    while True:
        chunk = list(islice(it, size))
        if not chunk:
            break
        yield chunk

def extracion_sap(Salidafactura, size_query, conn):
    """Consultamos a SAP por Bloques usando OPENQUERY"""
    if Salidafactura.empty:
        print("⚠️ Dataframe vacío, no hay nada que consultar")
        return pd.DataFrame()  # Cambiamos a DataFrame vacío directamente
    
    arckeys = Salidafactura["Arckey"].tolist()
    print(f"\n🔍 Total de Arckeys a consultar: {len(arckeys)}")
    
    resultados_parciales = []
    
    for i, bloque in enumerate(chunked(arckeys, size_query)):
        print(f"\n📋 Bloque {i+1} - Consultando {len(bloque)} arckeys...")
        
        facturas_sql = ",".join([f"''{f}''" for f in bloque])
        
        query = f"""
        SELECT *
        FROM OPENQUERY(GBSAPGRP,'
        SELECT ec.direct, ec.DOCNUM, ec.ARCKEY, ec.STATUS, ec.SNDPOR, ec.SNDPRN, ec.MESTYP, ed.SDATA
        FROM SAPABAP1.EDID4 ed
        INNER JOIN SAPABAP1.edidc ec ON ed.docnum = ec.docnum AND ed.MANDT = ec.MANDT 
        WHERE ed.MANDT = ''300''   
        AND ed.SEGNAM = ''E1EDKT2''
        AND ed.SDATA <> ''''
        AND ec.arckey IN ({facturas_sql})
        ')
        """
        
        try:
            df = pd.read_sql(query, conn)
            print(f"   ✅ Resultados del bloque {i+1}: {len(df)} registros")
            if not df.empty:
                resultados_parciales.append(df)
        except Exception as e:
            print(f"   ❌ Error en consulta del bloque {i+1}: {e}")
    
    # Combinar todos los resultados
    if resultados_parciales:
        resultados_sap = pd.concat(resultados_parciales, ignore_index=True)
        print(f"\n✅ Total registros encontrados en SAP: {len(resultados_sap)}")
        return resultados_sap
    else:
        print("\n⚠️ No se encontraron registros en SAP")
        return pd.DataFrame()

def comparar_resultados(facturas_originales, df_sap, limpieza_df):
    """
    Compara las facturas del fichero con los resultados de SAP
    y genera informes detallados
    """
    print("\n" + "=" * 80)
    print("📊 ANÁLISIS DE COMPARACIÓN")
    print("=" * 80)
    
    # Estadísticas básicas
    total_fichero = len(facturas_originales)
    total_sap = len(df_sap) if not df_sap.empty else 0
    
    print(f"\n📁 Facturas en fichero: {total_fichero}")
    print(f"🗄️  Facturas encontradas en SAP: {total_sap}")
    
    # Crear timestamp para nombres de archivos
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. Si no hay resultados en SAP
    if df_sap.empty:
        print("\n❌ NO SE ENCONTRARON RESULTADOS EN SAP")
        
        # Guardar todas las facturas como no encontradas
        no_encontradas = limpieza_df.copy()
        no_encontradas.to_csv(f'no_encontradas_sap_{timestamp}.csv', index=False)
        
        # Crear informe TXT
        with open(f'informe_no_encontradas_{timestamp}.txt', 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("INFORME DE FACTURAS NO ENCONTRADAS EN SAP\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Total facturas en fichero: {total_fichero}\n")
            f.write(f"Total facturas encontradas en SAP: 0\n\n")
            f.write("📋 LISTADO DE FACTURAS NO ENCONTRADAS:\n")
            f.write("-" * 60 + "\n")
            for idx, row in limpieza_df.iterrows():
                f.write(f"{idx+1:3d}. Arckey: {row['Arckey']} | PDF: {row['pdf']} | Factura: {row['factura_original']}\n")
        
        print(f"\n📝 Informe guardado: 'informe_no_encontradas_{timestamp}.txt'")
        return
    
    # 2. Si hay resultados, comparar
    arckeys_fichero = set(limpieza_df['Arckey'].tolist())
    arckeys_sap = set(df_sap['ARCKEY'].tolist())
    
    # Encontrados y no encontrados
    arckeys_encontrados = arckeys_fichero.intersection(arckeys_sap)
    arckeys_no_encontrados = arckeys_fichero - arckeys_sap
    
    print(f"\n✅ Arckeys encontrados: {len(arckeys_encontrados)}")
    print(f"❌ Arckeys NO encontrados: {len(arckeys_no_encontrados)}")
    
    # Crear DataFrames para análisis detallado
    df_encontrados = limpieza_df[limpieza_df['Arckey'].isin(arckeys_encontrados)].copy()
    df_no_encontrados = limpieza_df[limpieza_df['Arckey'].isin(arckeys_no_encontrados)].copy()
    
    # 3. Guardar resultados según el caso
    if len(arckeys_no_encontrados) == 0:
        # CASO 1: TODOS ENCONTRADOS
        print("\n" + "=" * 80)
        print("✅ PROCESO COMPLETADO CORRECTAMENTE")
        print("=" * 80)
        print(f"\n📁 En el fichero invoicesin había {total_fichero} registros")
        print(f"🗄️  En SAP se encontraron {total_sap} registros")
        print("\n✨ TODAS LAS FACTURAS SE PROCESARON CORRECTAMENTE EN SAP")
        
        with open(f'informe_completo_{timestamp}.txt', 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("INFORME DE PROCESAMIENTO EXITOSO\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"📁 Facturas en fichero invoicesin: {total_fichero}\n")
            f.write(f"🗄️  Facturas encontradas en SAP: {total_sap}\n\n")
            f.write("✨ RESULTADO: Se procesaron correctamente en SAP\n")
            f.write("\n📋 LISTADO DE FACTURAS PROCESADAS:\n")
            f.write("-" * 60 + "\n")
            for idx, row in df_encontrados.iterrows():
                f.write(f"{idx+1:3d}. Arckey: {row['Arckey']} | PDF: {row['pdf']}\n")
        
        print(f"\n📝 Informe guardado: 'informe_completo_{timestamp}.txt'")
        
    else:
        # CASO 2: HAY FACTURAS NO ENCONTRADAS
        print("\n" + "=" * 80)
        print("⚠️  PROCESO COMPLETADO CON ADVERTENCIAS")
        print("=" * 80)
        print(f"\n📁 Facturas en fichero: {total_fichero}")
        print(f"🗄️  Facturas encontradas en SAP: {len(arckeys_encontrados)}")
        print(f"❌ Facturas NO encontradas en SAP: {len(arckeys_no_encontrados)}")
        
        # Guardar facturas no encontradas
        df_no_encontrados.to_csv(f'facturas_no_encontradas_{timestamp}.csv', index=False)
        
        # Crear informe detallado TXT
        with open(f'informe_incompleto_{timestamp}.txt', 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("INFORME DE FACTURAS NO ENCONTRADAS EN SAP\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"📁 Total facturas en fichero: {total_fichero}\n")
            f.write(f"✅ Encontradas en SAP: {len(arckeys_encontrados)}\n")
            f.write(f"❌ No encontradas en SAP: {len(arckeys_no_encontrados)}\n\n")
            
            if len(arckeys_encontrados) > 0:
                f.write("✅ FACTURAS ENCONTRADAS EN SAP:\n")
                f.write("-" * 60 + "\n")
                for idx, row in df_encontrados.iterrows():
                    f.write(f"{idx+1:3d}. Arckey: {row['Arckey']} | PDF: {row['pdf']}\n")
                f.write("\n")
            
            f.write("❌ FACTURAS NO ENCONTRADAS EN SAP:\n")
            f.write("-" * 60 + "\n")
            for idx, row in df_no_encontrados.iterrows():
                f.write(f"{idx+1:3d}. Arckey: {row['Arckey']} | PDF: {row['pdf']} | Factura: {row['factura_original']}\n")
        
        print(f"\n📝 Informe guardado: 'informe_incompleto_{timestamp}.txt'")
        print(f"📊 CSV con no encontradas: 'facturas_no_encontradas_{timestamp}.csv'")
    
    # Guardar también los resultados completos de SAP
    df_sap.to_csv(f'resultados_sap_{timestamp}.csv', index=False)
    print(f"📊 Resultados SAP guardados: 'resultados_sap_{timestamp}.csv'")
    
    return {
        'total_fichero': total_fichero,
        'total_sap': total_sap,
        'encontrados': len(arckeys_encontrados),
        'no_encontrados': len(arckeys_no_encontrados),
        'df_encontrados': df_encontrados,
        'df_no_encontrados': df_no_encontrados
    }

def main():
    conn = None
    try:
        print("🔄 Iniciando conexión a BD...")
        conn = pyodbc.connect(conn_str)
        print("✅ Conexión establecida correctamente")

        archivo = encontrar_archivo_invoices()
        print(f"📁 Archivo encontrado: {archivo}\n")
        
        print("📄 Extrayendo facturas del archivo...")
        facturas = extraer_facturas_ca_regex(archivo)
        
        if not facturas:
            print("❌ No se encontraron facturas en el archivo")
            return

        print(f"\n📊 Transformando {len(facturas)} facturas...")
        limpieza = transformacion_facturas(facturas)
        
        if limpieza.empty:
            print("❌ El DataFrame transformado está vacío")
            return
        
        # Filtrar arckeys vacíos
        limpieza = limpieza[limpieza['Arckey'] != '_']
        if limpieza.empty:
            print("❌ Todos los arckeys están vacíos")
            return
        
        size_query = 20

        print("\n" + "=" * 80)
        print("🔍 CONSULTANDO EN SAP...")
        print("=" * 80)
        
        resultados_sap = extracion_sap(limpieza, size_query, conn)

        print("\n" + "=" * 80)
        print("📋 RESUMEN DE FACTURAS CA")
        print("=" * 80)
        
        if facturas:
            for i, fac in enumerate(facturas, 1):
                print(f"✓ {i:3d}. Factura: {fac['factura']:20} | PDF: {fac['pdf']:15} | Orden: {fac['orden']}")
        
        print("=" * 80)
        print(f"💰 TOTAL FACTURAS PROCESADAS: {len(facturas)}")
        print("=" * 80)
        
        # COMPARAR RESULTADOS Y GENERAR INFORMES
        comparar_resultados(facturas, resultados_sap, limpieza)
        
        # Guardar resumen básico de facturas (siempre)
        with open('resumen_facturas_ca.txt', 'w', encoding='utf-8') as f:
            f.write(f"Total facturas CA: {len(facturas)}\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            for fac in facturas:
                f.write(f"{fac['factura']};{fac['pdf']};{fac['orden']}\n")
        print("\n✅ Resumen básico guardado en 'resumen_facturas_ca.txt'")
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()
            print("🔌 Conexión cerrada")

if __name__ == "__main__":
    main()