import xml.etree.ElementTree as ET
from pathlib import Path


class xml_xml():
    def __init__(self, input:None, output:None):
        self.input=input
        self.output=Path(output)
        #self.directorio=Path(self.directorio)
        self.output_file = "Resultado_facturas_con_PO.txt"
        #self.campo1=campo1
    
    def obtener_xml(self):
        filenames=[]
        for xmls in Path(f"{self.input}").glob("*.xml"):
            pathfilename=str(xmls.absolute())
            filenames.append(pathfilename)
        return filenames[0]

#--------------------------------------------------------------------------------------------
# Transformacion con  XML
#--------------------------------------------------------------------------------------------
    
    def extraccion_valor_unico(self,campos):
        """
        Elige un campo del XML de preferencia hijo si \n
        necesitas obneter los valores y epxortarlo a un \n
        fichero
        """
        ruta_xml=self.obtener_xml()
        tree=ET.parse(ruta_xml)
        root=tree.getroot()

        camposxml=[]

        elementos=root.findall(f".//{campos}")  #buscamos los elementos de la etiqueta del xml
        for elemento in elementos:
            if elemento.text:
                    camposxml.append(elemento.text)
        return camposxml
    
    def obtener_arbol_xml(self):
        #if self.tree is None:
        ruta_xml=self.obtener_xml(False)
        if ruta_xml:
             return ET.parse(ruta_xml)
        return None
    
    def obtener_raiz_xml(self):
         """Retorna el elemento raíz del XML"""
         arbol = self.obtener_arbol_xml()
         if arbol:
                return arbol.getroot()
         return None
        
    def muestra_estructura_xml(self, elemento=None, nivel=0, prefijo='', es_ultimo=True):
        """Muestra la estructura jerárquica del XML"""
        # Si no se pasa elemento, carga el XML
        if elemento is None:
            ruta_xml = self.obtener_xml()
            tree = ET.parse(ruta_xml)
            elemento = tree.getroot()
            print(" ESTRUCTURA DEL XML:")
            print("-" * 50)
        
        # Construye el prefijo para mejor visualización
        if nivel == 0:
            prefijo_actual = ""
        else:
            prefijo_actual = prefijo + "  "
        
        print(f"{prefijo_actual}├─ {elemento.tag}")
        
        etiquetas_vistas=set()
        for hijo in elemento:
             if hijo.tag not in etiquetas_vistas:
                  etiquetas_vistas.add(hijo.tag)
                  self.muestra_estructura_xml(hijo, nivel +1 , prefijo_actual)
        """
        # Si tiene hijos, los muestra recursivamente
        for i, hijo in enumerate(elemento):
            es_ultimo = (i == len(elemento) - 1)
            nuevo_prefijo = prefijo_actual + ("  " if es_ultimo else "│ ")
            self.muestra_estructura_xml(hijo, nivel + 1, nuevo_prefijo)
        """

    def _recoger_estructura(self, elemento, lineas, nivel=0, prefijo=""):
        """Función recursiva para recoger la estructura en una lista"""
        
        if nivel == 0:
            prefijo_actual = ""
        else:
            prefijo_actual = prefijo + "  "
        
        lineas.append(f"{prefijo_actual}├─ {elemento.tag}")
        
        etiquetas_vistas = set()
        for hijo in elemento:
            if hijo.tag not in etiquetas_vistas:
                etiquetas_vistas.add(hijo.tag)
                self._recoger_estructura(hijo, lineas, nivel + 1, prefijo_actual) 
                
#--------------------------------------------------------------------------------------------
# Constructores de Guardados
#--------------------------------------------------------------------------------------------
    
    def guardar_datos_a_ficheros(self, regtotal, regunicos:None):
        with open(f"{self.output}resultado_total.txt",'w', encoding='utf-8') as total,\
        open(f"{self.output}resultado_total_unicos.txt",'w', encoding='utf-8') as unicos:
            """
            for i in range (len(registros)):
                total.write(f"{registros[0][i]}\n") 
            """
            for registro in regtotal:
                total.write(f"{registro}\n") 
            
            for registro in regunicos:
                unicos.write(f"{registro}\n") 

    def guardar_estructura(self, nombre_archivo="estructura_xml.txt"):
        """Guarda la estructura usando el método guardar_datos_a_ficheros"""
        
        # Obtener estructura como lista
        ruta_xml = self.obtener_xml()
        tree = ET.parse(ruta_xml)
        elemento = tree.getroot()
        
        lineas = ["ESTRUCTURA DEL XML (ETIQUETAS ÚNICAS):"]
        lineas.append("-" * 60)
        self._recoger_estructura(elemento, lineas)
        
        # Usar tu método existente
        with open(f"{self.output}{nombre_archivo}", 'w', encoding='utf-8') as f:
            for linea in lineas:
                f.write(linea + "\n")
        
        print(f"Estructura guardada en: {self.output}{nombre_archivo}")
    
    def guardar_datos_a_csv(self, datosSAP,nombre_archivo=None, directorio=None):
        """Despues de extraer y encontrar registros en SAP"""
        
        if nombre_archivo is None:
            nombre_archivo=self.output_file
        #self.output.mkdir(parents=True, exist_ok=True)
        if directorio is not None:
               directorio_path=self.output /Path(directorio)
               directorio_path.mkdir(parents=True, exist_ok=True)
               file_path=directorio_path/nombre_archivo
        else :
                self.output.mkdir(parents=True, exist_ok=True)
                file_path=self.output/nombre_archivo

        if not datosSAP.empty:
            datosSAP.to_csv(file_path, index=False, sep=';', encoding='utf-8')
            print(f"Resultados guardados en {file_path}")
        else:
            print("No se encontraron resultados")

#--------------------------------------------------------------------------------------------
# Extraccion de elementos por numeros de facturas  y montado de nuevo XML
#--------------------------------------------------------------------------------------------
    def nueva_formacion_xml_por_facturas(self,fichero_xml, Facturas_a_extraer, campo_padre, campo_hijo):
         tree=ET.parse(fichero_xml)
         root=tree.getroot()

         # -- Servicios Filtradis ---
         """
         Escogemos solo lo que hay en el fichero que le pasamos, los codigos en el \n
         fichero XML principal.
         """
         servicios_filtrados=[]

         for servicio in root.findall(f".//{campo_padre}"):
              nodo_factura=servicio.find(campo_hijo)
              
              if nodo_factura is not None:
                   numero=nodo_factura.text.strip()

                   if numero in  Facturas_a_extraer:
                        servicios_filtrados.append(servicio)
         

         # Crecion de nuevo XML
         nuevo_root=ET.Element("facturacion")

         fecha=root.find("fecha_ejecucion")

         if fecha is not None:
              nuevo_root.append(fecha)
        
         expedientes=ET.SubElement(nuevo_root, "expedientes")

         for servicio in servicios_filtrados:
              expedientes.append(servicio)

         tree_Salida=ET.ElementTree(nuevo_root)
         
         tree_Salida.write("GBFoodsXML.xml", encoding='utf-8', xml_declaration=True, method='xml')
         
         with open("GBFoodsXML.xml", 'r', encoding='utf-8') as f:
              contenido = f.read()
         contenido_una_linea = ''.join(contenido.split())
         
         with open("GBFoodsXML.xml", 'w', encoding='utf-8') as f:
              f.write(contenido_una_linea)
            
        






        

    