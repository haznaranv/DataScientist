import os
import re
from sqlalchemy import create_engine, text
import urllib.parse

# -------- CONFIGURACIÓN --------
# Configuración de conexión a SQL Server
SERVER = "172.24.254.50"          # Ej: "localhost" o "IP"
DATABASE = "ADX"      # Nombre de la base de datos
USERNAME = "Mercator"         # Usuario de SQL Server
PASSWORD = "Mercator123"      # Contraseña

# Nombre de la tabla
TABLA = "WTX_XML_VIAJES"
CAMPO_FACTURA = "Factura"       # Campo que contiene el número de factura

# Archivo con los números de factura a eliminar (uno por línea)
ARCHIVO_FACTURAS = "Elementos_Eliminar_FACSPACE.txt"


# -------- FUNCIONES AUXILIARES --------
def limpiar_numero_factura(texto):
    """Limpia el número de factura eliminando comas, espacios, etc."""
    texto = texto.strip()
    # Eliminar comas, espacios, y caracteres no deseados
    texto = re.sub(r'[^\d]', '', texto)  # Solo dígitos
    return texto


def leer_facturas_desde_archivo(ruta_archivo):
    """Lee números de factura desde un archivo .txt"""
    if not os.path.exists(ruta_archivo):
        print(f"❌ Error: No se encuentra el archivo '{ruta_archivo}'")
        return None
    
    facturas = []
    with open(ruta_archivo, "r", encoding="utf-8") as f:
        for linea in f:
            if linea.strip():
                factura_limpia = limpiar_numero_factura(linea)
                if factura_limpia:
                    facturas.append(factura_limpia)
    
    print(f"📋 Cargadas {len(facturas)} factura(s) desde '{ruta_archivo}'")
    if facturas:
        print(f"   Ejemplo: {facturas[:5]}")
    return facturas


def conectar_bd():
    """Crea la conexión a SQL Server usando SQLAlchemy"""
    try:
        # Para SQL Server con autenticación SQL
        connection_string = (
            f"mssql+pyodbc://{USERNAME}:{PASSWORD}@{SERVER}/{DATABASE}"
            f"?driver=ODBC+Driver+17+for+SQL+Server"
        )
        
        # Si usas autenticación de Windows, usa esto en su lugar:
        # connection_string = f"mssql+pyodbc://@{SERVER}/{DATABASE}?trusted_connection=yes&driver=ODBC+Driver+17+for+SQL+Server"
        
        engine = create_engine(connection_string, echo=False)
        
        # Probar conexión
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        print(f"✅ Conexión exitosa a SQL Server: {SERVER}/{DATABASE}")
        return engine
    
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return None


def verificar_facturas_existentes(engine, tabla, campo_factura, facturas):
    """Verifica qué facturas existen realmente en la tabla"""
    if not facturas:
        return [], []
    
    # CORREGIDO: Crear placeholders y pasar parámetros correctamente
    placeholders = ','.join(['?' for _ in facturas])
    
    query = text(f"""
        SELECT {campo_factura} 
        FROM {tabla} 
        WHERE {campo_factura} IN ({placeholders})
    """)
    
    with engine.connect() as conn:
        # CORREGIDO: Pasar los parámetros como una tupla
        result = conn.execute(query, tuple(facturas))
        existentes = [row[0] for row in result]
    
    no_existentes = [f for f in facturas if f not in existentes]
    
    return existentes, no_existentes


def eliminar_por_facturas(engine, tabla, campo_factura, facturas, usar_batch=True, batch_size=500):
    """
    Elimina registros por número de factura
    
    Args:
        engine: Conexión de SQLAlchemy
        tabla: Nombre de la tabla
        campo_factura: Nombre del campo de factura
        facturas: Lista de números de factura a eliminar
        usar_batch: Si True, elimina en lotes (más eficiente)
        batch_size: Tamaño del lote
    """
    if not facturas:
        print("⚠️ No hay facturas para eliminar")
        return 0
    
    total_eliminadas = 0
    
    if usar_batch:
        # Eliminar en lotes para mejor rendimiento
        for i in range(0, len(facturas), batch_size):
            batch = facturas[i:i+batch_size]
            placeholders = ','.join(['?' for _ in batch])
            
            delete_stmt = text(f"""
                DELETE FROM {tabla} 
                WHERE {campo_factura} IN ({placeholders})
            """)
            
            with engine.connect() as conn:
                # CORREGIDO: Pasar los parámetros como una tupla
                result = conn.execute(delete_stmt, tuple(batch))
                conn.commit()
                batch_eliminadas = result.rowcount
                total_eliminadas += batch_eliminadas
                print(f"   Lote {i//batch_size + 1}: {batch_eliminadas} registro(s) eliminado(s)")
    else:
        # Eliminar una por una (más lento pero útil para depuración)
        for factura in facturas:
            delete_stmt = text(f"""
                DELETE FROM {tabla} 
                WHERE {campo_factura} = :factura
            """)
            
            with engine.connect() as conn:
                result = conn.execute(delete_stmt, {"factura": factura})
                conn.commit()
                if result.rowcount > 0:
                    total_eliminadas += result.rowcount
                    print(f"   ✅ Eliminada factura: {factura}")
                else:
                    print(f"   ⚠️ No encontrada: {factura}")
    
    return total_eliminadas


def main():
    """Función principal"""
    print("="*60)
    print("      ELIMINADOR DE REGISTROS POR FACTURA")
    print("="*60)
    print(f"📋 Tabla: {TABLA}")
    print(f"🔑 Campo: {CAMPO_FACTURA}")
    print(f"📁 Archivo: {ARCHIVO_FACTURAS}")
    print("="*60)
    
    # 1. Leer facturas del archivo
    facturas = leer_facturas_desde_archivo(ARCHIVO_FACTURAS)
    if not facturas:
        print("❌ No se cargaron facturas. Verifica el archivo.")
        return
    
    # 2. Conectar a la base de datos
    engine = conectar_bd()
    if engine is None:
        return
    
    # 3. Verificar qué facturas existen
    print("\n🔍 Verificando facturas existentes...")
    existentes, no_existentes = verificar_facturas_existentes(engine, TABLA, CAMPO_FACTURA, facturas)
    
    if no_existentes:
        print(f"⚠️ Facturas no encontradas en la tabla ({len(no_existentes)}):")
        for f in no_existentes[:10]:
            print(f"   - {f}")
        if len(no_existentes) > 10:
            print(f"   ... y {len(no_existentes) - 10} más")
    
    if not existentes:
        print("❌ Ninguna de las facturas existe en la tabla.")
        return
    
    print(f"\n✅ Facturas existentes a eliminar: {len(existentes)}")
    
    # 4. Confirmar eliminación
    print("\n⚠️  ¡ADVERTENCIA! Esta acción eliminará registros de forma permanente.")
    confirmacion = input(f"¿Eliminar {len(existentes)} registro(s)? (escribe 'SI' para confirmar): ")
    
    if confirmacion.upper() != "SI":
        print("❌ Operación cancelada.")
        return
    
    # 5. Ejecutar eliminación
    print("\n🗑️ Eliminando registros...")
    total = eliminar_por_facturas(engine, TABLA, CAMPO_FACTURA, existentes)
    
    # 6. Resumen final
    print("\n" + "="*60)
    print("                 RESUMEN FINAL")
    print("="*60)
    print(f"📊 Facturas procesadas: {len(facturas)}")
    print(f"   - Existentes en BD: {len(existentes)}")
    print(f"   - No encontradas: {len(no_existentes)}")
    print(f"   - Eliminadas: {total}")
    print("="*60)
    
    if total == len(existentes):
        print("✅ ¡Eliminación completada con éxito!")
    else:
        print("⚠️ Algunos registros no se eliminaron correctamente.")


# -------- EJECUCIÓN --------
if __name__ == "__main__":
    main()