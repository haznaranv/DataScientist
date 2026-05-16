# Nombre del archivo de entrada y salida
archivo_entrada = "SOLO_PO_ARCKEY_25032026 - Copy.txt"
archivo_salida = "resultado_SOLO_PO_ARCKEY_25032026 - Copy.txt"

with open(archivo_entrada, "r", encoding="utf-8") as entrada, \
     open(archivo_salida, "w", encoding="utf-8") as salida:
    
    for linea in entrada:
        codigo = linea.strip()  # quitar espacios y saltos de línea
        
        if codigo:  # evitar líneas vacías
            nuevo_formato = f"''{codigo}_{codigo}'',\n"
            salida.write(nuevo_formato)

print("Proceso terminado.")