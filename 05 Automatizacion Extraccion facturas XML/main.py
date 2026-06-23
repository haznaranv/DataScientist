import src.classXML as xml
import src.classReadBBDD as sap
import pandas as pd


path_input="data/input/"
path_output="data/output"

# ------------------------------------
# 01 Busqueda y extraccion de facturas
# ------------------------------------
ficheroXML=xml.xml_xml(path_input,path_output )

# Obtenemos el nombre del fichero con la ruta completa
rutaxml = ficheroXML.obtener_xml()
print (f"archivo encontrado {rutaxml}")

# ------------------------------------

estructura=ficheroXML.muestra_estructura_xml()
estructura=ficheroXML.guardar_estructura("estructura_xml.txt")

# ------------------------------------
#Obtenemos los valores unicos de un campo del XML
registrosTotales=ficheroXML.extraccion_valor_unico("numero_de_factura")
registrosUnicos=set(registrosTotales)

# Guarda los valores totales unicos en cada ficheros en la carpeta de salida que se ha definido inicialmente
ficheroXML.guardar_datos_a_ficheros(registrosTotales, registrosUnicos)

# ------------------------------------------------------------------------
# 02 Comprobaciones de las facturas en SAP por fecha de creacion
# ------------------------------------------------------------------------

#Conexion a la BBDD
conn=sap.conn

# Numero de tamaño por bloques para no saturar SAP
chunk_size=20
# creams el objeto para realizar busquedas
consultasap=sap.ConsultaSAP(registrosUnicos,chunk_size, conn)

#Consultamos las facturas unicas en SAP si tienen PO 
# Consultar todos los bloques y obtener un DataFrame unificado

df_resultado = consultasap.separador_de_arckey(
    fecha='20260611',
    column1='STAPA1',
    nombre='ARCKEY_0',  # Nombre de la nueva columna
    column2='ARCKEY',   # Columna a separar
    directorio=path_output  # Directorio donde guardar
    )

#print(df_resultado[1])
# ------------------------------------------------------------------------
# 03 Hallamos las POs del STATUS 53 y 51
# ------------------------------------------------------------------------
if isinstance(df_resultado, tuple):
    print(f" el DF_RESULTADO es una tupla con {len(df_resultado)} de elementos")

    if len(df_resultado)==2:
        df_status_51=df_resultado[0]
        df_status_53=df_resultado[1]
    else:
        df_status_51=df_resultado[0]
        df_status_53=None
elif isinstance(df_resultado, pd.DataFrame):
    print(f" el DF_RESULTADO es una DataFrame con {len(df_resultado)} de elementos")
    df_status_51=df_resultado[0]
    df_status_53=df_resultado[1]

if 'ARCKEY_0' in df_status_53.columns:
    facturas_53=df_status_53['ARCKEY_0'].astype(str).tolist()
    #print(facturas_53)

# Consultar PO de Status 53
if facturas_53:
    status_53_sap = sap.ConsultaSAP(facturas_53, chunk_size, conn)
    resultado_po_53 = status_53_sap.consultar_todos_los_bloques()
    resultado_po_53=resultado_po_53.drop_duplicates()
    ficheroXML.guardar_datos_a_csv(resultado_po_53, "Facturas_53_PO.csv", 'status_53')
    #print(resultado_po_53)


#-----------------------------------
# 03.1 STATUS 51
# Consultamos y separamos facturas con sus respectivos errores de Status 51
if not df_status_51.empty:
    df_status_51=pd.DataFrame(df_status_51)
    df_status_51=df_status_51.drop(columns=['ARCKEY', 'STATUS', 'CREDAT'])
    elementos_unicos=df_status_51['STAPA1'].unique()
    for i in range(len(elementos_unicos)):
        nombre_Err=elementos_unicos[i]
        
        #creamos el filtro para cada error
        df_filtrado = df_status_51[df_status_51['STAPA1'] == nombre_Err]
        

        #Guardamos el error en su respectivo fichero con su nombre
        ficheroXML.guardar_datos_a_csv(df_filtrado, f"df_status_51_{nombre_Err}.csv", 'status_51')
        
        if nombre_Err.startswith("XXXXX"):
            df_filtrado_x=df_filtrado
            #print (df_filtrado_x)

        # Crear la variable dinámica con globals()
        globals()[f"df_status_51_{nombre_Err}"] = df_filtrado
        print(f"Creado: df_status_51_{nombre_Err} con {len(df_filtrado)} registros")
            
# ------------------------------------------------------------------------
# 04 Comparaciones de resultados status 53 y 51 con las facturas del fichero
#   que se ha enviado por proceso
# ------------------------------------------------------------------------

# registrosUnicos
# df_status_51
#df_status_53
df_status_51=df_status_51['ARCKEY_0'].drop_duplicates()
df_status_53=df_status_53['ARCKEY_0'].drop_duplicates()

conjunto_Total=set(registrosUnicos)
print("Total de registros: ",len(conjunto_Total))

conjunto_51=set(df_status_51)
print("Numero de registros status 51: ",len(conjunto_51))


conjunto_53=set (df_status_53)
print("Numero de registros status 53: ",len(conjunto_53))

# Elementos del conjunto_total que no esten en Conjunto_53
Registros_diferentes=conjunto_Total - conjunto_53

# Elementos del registros_diferentes que no esten en Conjunto_51
Registros_diferentes=Registros_diferentes - conjunto_51

print("registros diferentes: ", len(Registros_diferentes))
#print("registros diferentes: ", Registros_diferentes)
Registros_diferentes=pd.DataFrame(Registros_diferentes, )
ficheroXML.guardar_datos_a_csv(Registros_diferentes, f"df_status_51_99999.csv", 'status_51')

# ------------------------------------------------------------------------
# 05 Extracciones cuando el error es "9999999" del XML inicial 
#   
# ------------------------------------------------------------------------
df_filtrado_x=df_filtrado_x.drop(columns=['DOCNUM', 'STAPA1']).drop_duplicates()
df_filtrado_x['ARCKEY_0']=df_filtrado_x['ARCKEY_0'].str.strip()

conjunto_Facturas_XXX=set(df_filtrado_x['ARCKEY_0'])

for i, factura in enumerate(list(conjunto_Facturas_XXX)[:5]):
    print(f"  {i+1}. {factura}")

#df_filtrado_x=df_filtrado_x['ARCKEY_0'].to_list()


espejo= ficheroXML.nueva_formacion_xml_por_facturas(rutaxml,conjunto_Facturas_XXX, "servicio","numero_de_factura"  )

