import pyodbc
import pandas as pd
from itertools import islice
from src.classXML import xml_xml

# -----------------------------
# CONFIGURACION
# -----------------------------

# conexión SQL Server
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=nicedb.domgb.net;"
    "DATABASE=Integration;"
    "UID=Mercator;" 
    "PWD=Mercator123"
)

# fichero con facturas (1 por línea)
input_file = "registros_diferentes que no hay en sap.txt"

# fichero resultado
output_file = "Resultado_facturas_con_PO.txt"

# tamaño de bloque
chunk_size = 20

# -----------------------------
# CONEXION
# -----------------------------

conn = pyodbc.connect(conn_str)

resultados = []

class ConsultaSAP():
    def __init__(self, factura, size, conn):
        self.factura=factura
        self.size=size
        self.conn=conn
        self.resultados=[]

# -----------------------------
# FUNCION PARA DIVIDIR EN BLOQUES
# -----------------------------
    def bloques_segmentos(self):
        it = iter(self.factura)
        while True:
            chunk = list(islice(it, self.size))
            if not chunk:
                break
            yield chunk
    
    def obtener_bloques(self):
        """Método auxiliar para obtener todos los bloques como lista"""
        return list(self.bloques_segmentos())
    
    
    def mostrar_bloques(self):
        """Método para imprimir todos los bloques"""
        for i, bloque in enumerate(self.bloques_segmentos(), 1):
            print(f"Bloque {i}: {bloque}")

    def consultar_todos_los_bloques(self):
        """Meotod que consulta en sap todos los bloqeus"""
        for bloque in self.bloques_segmentos():
            resultado_bloque=self._consultar_bloque(bloque)
            if resultado_bloque is not None:
                self.resultados.append(resultado_bloque)
        return pd.concat(self.resultados, ignore_index=True) if self.resultados else pd.DataFrame()
    
    
    def _consultar_bloque(self, bloque):
        """Método privado para consultar un bloque específico"""
        facturas_sql = ",".join([f"''{f}''" for f in bloque])
        
        query = f"""
        SELECT numfra, PO
        FROM OPENQUERY(GBSAPGRP,
        'SELECT 
        EKKO.VERKF as numfra, 
        EKPO.EBELN as PO, 
        EKPO.EBELP as POSICION, 
        EKKO.AEDAT AS FECHA 
        FROM SAPABAP1.EKKO EKKO
        INNER JOIN SAPABAP1.EKPO EKPO 
            ON EKPO.MANDT = EKKO.MANDT 
            AND EKPO.EBELN = EKKO.EBELN
        WHERE EKKO.MANDT = ''300''
          AND EKKO.BSART = ''ZSTR''
          AND EKKO.EKORG = ''ES01''
          AND SUBSTRING(EKKO.IHREZ, 1, 2) = ''IB''
          AND EKKO.VERKF IN ({facturas_sql})
        ')
        """
        print(f"Consultando bloque de {len(bloque)} facturas...")
        
        try:
            return pd.read_sql(query, self.conn)
        except Exception as e:
            print(f"Error en bloque: {e}")
            print(f"Facturas del bloque que falló: {bloque}")
            return None
        
    def _consultar_bloque_status(self, fecha):
         """Método privado para consultar un bloque específico"""
         fecha_sap=fecha
         query = f"""
         SELECT
         *
         FROM OPENQUERY(GBSAPGRP,'
         SELECT  
         distinct ec.DOCNUM, 
         ec.ARCKEY as arckey, 
         ec.STATUS,
         es.stapa1 as STAPA1,
         ec.credat
         FROM SAPABAP1.EDID4 ed
         INNER JOIN SAPABAP1.edidc ec ON ed.docnum = ec.docnum AND ed.MANDT = ec.MANDT 
         INNER JOIN SAPABAP1.edidS es ON ed.docnum = es.docnum AND ed.MANDT = es.MANDT
         WHERE ed.MANDT = ''300'' 
         and EC.RCVPRN like ''%125608''
         AND ED.SEGNAM LIKE ''E1BPEKPOC%''
         AND EC.credat = (''{fecha_sap}'')			   -- FECHA CON LA QUE INGRESO A SAP
         --AND ES.STAPA1 like ''Web services''
         ')
        """
         try:
            return pd.read_sql(query, self.conn)

         except Exception as e:
            print(f"Error en bloque: {e}")
            print(f"Facturas del bloque que falló: {fecha}")
            return None

    def separador_de_arckey(self, fecha, column1=None, nombre=None, column2=None, directorio=None):
        """
        FECHA, Con ella busca en la BBDD y extrae todo "_" \n
        COLUMN1, Campos con nulos o con NA \n
        NOMBRE, EL nombre nuevo a la columna nueva del DATAFRAME \n
        COLUMN2, campos que estan unidos por un caracter \n
        directorio: Subcarpeta dentro de output (opcional)
        """
        try:
            # Consultar datos
            df1 = self._consultar_bloque_status(fecha)
            
            if df1.empty:
                print(" No hay datos que mostrar")
                return None

            # Filtrar datos no nulos y no vacíos
            if column1 is not None:
                df_sin_duplicados = df1[(df1[column1].notna()) & (df1[column1] != '')].drop_duplicates()
            else:
                df_sin_duplicados = df1   
            
            if df_sin_duplicados.empty:
                print("No hay datos después del filtrado")
                return None
            
            # Separar la columna
            if column2 is not None and nombre is not None:
                if column2 in df_sin_duplicados.columns:  
                    df_sin_duplicados[nombre] = df_sin_duplicados[column2].str.split('_').str[0]
                    print(f"Columna '{nombre}' creada desde '{column2}'")
                else:
                    print(f"La columna '{column2}' no existe")
                    print(f"Columnas disponibles: {df_sin_duplicados.columns.tolist()}")
                    return df_sin_duplicados
            
            # Filtrar por STATUS
            Status_53 = df_sin_duplicados[df_sin_duplicados['STATUS'] == '53']
            Status_51 = df_sin_duplicados[df_sin_duplicados['STATUS'] == '51']
            
            # Guardar usando la clase CSV (necesitamos pasar el directorio)
            # Aquí usamos el directorio que se pasa como parámetro
            guardar_csv = xml_xml(None, directorio)
            
            if not Status_53.empty:
                Status_53=Status_53.drop(columns=[column2, column1, 'CREDAT'])
                guardar_csv.guardar_datos_a_csv(Status_53, "Facturas_Status_53.csv",'status_53')
                
                # Solo quedandome con la lista de facturas
                Status_53=Status_53.drop(columns=['DOCNUM','STATUS']).drop_duplicates()
                
                guardar_csv.guardar_datos_a_csv(Status_53, "Facturas_53.csv",'status_53')
                print(f"Status 53 guardado: {len(Status_53)} registros")
            else:
                print("No hay registros para el status 53")

            if not Status_51.empty:
                #Status_51=Status_51.drop(columns=[column2, column1, 'CREDAT'])
                guardar_csv.guardar_datos_a_csv(Status_51, "Facturas_Status_51.csv",'status_51')
                print(f"Status 51 guardado: {len(Status_51)} registros")
            else:
                print("No hay registros para el status 51")
            
            # Mostrar resumen
            print("\n Resumen:")
            print(f"   - Status 53: {len(Status_53)} registros")
            print(f"   - Status 51: {len(Status_51)} registros")
            print(f"   - Total: {len(df_sin_duplicados)} registros sin duplicados")
            
            return Status_51, Status_53

        except Exception as e:
            print(f"Error en separador_de_arckey: {e}")
            import traceback
            traceback.print_exc()
            return None