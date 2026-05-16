import csv
from collections import defaultdict
import sys
import os

def contar_repeticiones(archivo_entrada, archivo_salida=None, separador=None, columna=0):
    """
    Lee un archivo, cuenta las repeticiones en la primera columna (columna 0)
    y crea un archivo de salida con el número de repeticiones al final de cada línea.
    
    Args:
        archivo_entrada: Ruta del archivo de entrada
        archivo_salida: Ruta del archivo de salida (opcional)
        separador: Separador de campos (opcional, se detecta automáticamente)
        columna: Índice de la columna a verificar (por defecto 0)
    """
    
    # Detectar el separador si no se especifica
    if separador is None:
        with open(archivo_entrada, 'r', encoding='utf-8') as f:
            primera_linea = f.readline()
            # Buscar separadores comunes
            if '\t' in primera_linea:
                separador = '\t'
            elif ';' in primera_linea:
                separador = ';'
            elif ',' in primera_linea:
                separador = ','
            elif '|' in primera_linea:
                separador = '|'
            else:
                # Por defecto usar espacio
                separador = ' '
    
    # Leer el archivo
    datos = []
    valores_columna = []
    
    with open(archivo_entrada, 'r', encoding='utf-8') as f:
        # Leer todas las líneas
        for linea in f:
            # Mantener la línea original para preservar posibles espacios
            linea_limpia = linea.strip()
            if not linea_limpia:
                continue  # Saltar líneas vacías
                
            # Dividir la línea usando el separador
            campos = linea_limpia.split(separador)
            datos.append(campos)
            
            # Obtener el valor de la primera columna (índice 0)
            if len(campos) > columna:
                valores_columna.append(campos[columna])
            else:
                valores_columna.append('')
    
    # Contar repeticiones
    contador = defaultdict(int)
    for valor in valores_columna:
        contador[valor] += 1
    
    # Crear archivo de salida
    if archivo_salida is None:
        nombre_base, extension = os.path.splitext(archivo_entrada)
        archivo_salida = f"{nombre_base}_con_repeticiones{extension}"
    
    with open(archivo_salida, 'w', encoding='utf-8', newline='') as f_out:
        # Escribir cada línea con el conteo al final
        for campos in datos:
            valor_columna = campos[columna] if len(campos) > columna else ''
            repeticiones = contador[valor_columna]
            
            # Crear la línea de salida: campos originales + número de repeticiones
            linea_salida = separador.join(campos) + separador + str(repeticiones)
            f_out.write(linea_salida + '\n')
    
    # Mostrar estadísticas
    print(f"Procesado: {archivo_entrada}")
    print(f"Separador detectado/uso: '{separador}'")
    print(f"Total de registros procesados: {len(datos)}")
    print(f"Valores únicos en la columna {columna}: {len(contador)}")
    
    # Mostrar valores que se repiten
    valores_repetidos = {k: v for k, v in contador.items() if v > 1}
    if valores_repetidos:
        print(f"\nValores que se repiten ({len(valores_repetidos)}):")
        for valor, cuenta in sorted(valores_repetidos.items(), key=lambda x: x[1], reverse=True):
            print(f"  '{valor}': {cuenta} veces")
    else:
        print("\nNo hay valores repetidos en la columna especificada.")
    
    print(f"\nArchivo de salida creado: {archivo_salida}")

def main():
    """Función principal para ejecutar desde línea de comandos"""
    
    # Verificar que se proporcionó un archivo
    if len(sys.argv) < 2:
        print("Uso: python script.py <archivo_entrada> [archivo_salida] [separador]")
        print("\nArgumentos:")
        print("  archivo_entrada: Ruta al archivo a procesar")
        print("  archivo_salida:  Ruta para el archivo de salida (opcional)")
        print("  separador:       Separador de campos (opcional, se detecta automáticamente)")
        print("\nEjemplos:")
        print("  python script.py datos.txt")
        print("  python script.py datos.csv resultados.csv ','")
        print("  python script.py datos.txt resultados.txt ';'")
        return
    
    # Obtener argumentos
    archivo_entrada = sys.argv[1]
    archivo_salida = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Obtener separador si se especifica
    separador = None
    if len(sys.argv) > 3:
        # Manejar caracteres especiales como tabulador
        if sys.argv[3] == '\\t':
            separador = '\t'
        elif sys.argv[3] == '\\n':
            separador = '\n'
        else:
            separador = sys.argv[3]
    
    # Verificar que el archivo existe
    if not os.path.exists(archivo_entrada):
        print(f"Error: El archivo '{archivo_entrada}' no existe.")
        return
    
    try:
        contar_repeticiones(archivo_entrada, archivo_salida, separador)
    except Exception as e:
        print(f"Error al procesar el archivo: {e}")

# Versión para usar directamente con un archivo específico
def procesar_archivo_ejemplo():
    """Ejemplo de uso con parámetros específicos"""
    
    archivo_entrada = "datos.txt"  # Cambia esto por tu archivo
    
    # Opción 1: Usar detección automática del separador
    contar_repeticiones(archivo_entrada)
    
    # Opción 2: Especificar separador manualmente
    # contar_repeticiones(archivo_entrada, "resultados.txt", ",")
    
    # Opción 3: Especificar otra columna (ej: columna 2, índice 1)
    # contar_repeticiones(archivo_entrada, "resultados.txt", ",", columna=1)

if __name__ == "__main__":
    # Usa main() para ejecutar desde línea de comandos
    main()
    
    # O usa procesar_archivo_ejemplo() si quieres modificar el script directamente
    # procesar_archivo_ejemplo()