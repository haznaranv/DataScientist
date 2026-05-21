import json
import os
import sys
import threading
import time
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# ==============================================
# FUNCIONES PARA MANEJAR RUTAS EN EJECUTABLES
# ==============================================

def get_base_path():
    """Obtiene la ruta base para archivos, funcionando tanto en desarrollo como en .exe"""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return base_path

def resource_path(relative_path):
    """Obtiene la ruta absoluta a un recurso, funcionando para desarrollo y para PyInstaller"""
    base_path = get_base_path()
    return os.path.join(base_path, relative_path)

# ==============================================
# LISTA DE PESTAÑAS VERTICAL (LIST WIDGET)
# ==============================================

class ListaPestanasVertical(QListWidget):
    """Widget que muestra las pestañas en vertical como una lista"""
    
    pestana_seleccionada = pyqtSignal(str)  # Señal cuando se selecciona una pestaña
    pestana_eliminar_solicitada = pyqtSignal(str)  # Señal para eliminar pestaña
    pestana_renombrar_solicitada = pyqtSignal(str)  # Señal para renombrar pestaña
    nueva_pestana_solicitada = pyqtSignal()  # Señal para crear nueva pestaña
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(150)  # Ancho mínimo
        self.setMaximumWidth(400)  # Ancho máximo
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.itemClicked.connect(self.on_item_clicked)
        
        # Permitir redimensionamiento
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Conectar menú contextual
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.mostrar_menu_contexto)
        
        # Estilo para la lista de pestañas
        self.setStyleSheet("""
            QListWidget {
                background-color: #2c3e50;
                color: white;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 12px 8px;
                border-bottom: 1px solid #34495e;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QListWidget::item:hover:!selected {
                background-color: #34495e;
            }
        """)
    
    def mostrar_menu_contexto(self, pos):
        """Mostrar menú contextual en la lista de pestañas"""
        # Obtener el item bajo el cursor
        item = self.itemAt(pos)
        
        menu = QMenu()
        
        # Opción para nueva pestaña (siempre disponible)
        accion_nueva = QAction("➕ Nueva Pestaña", self)
        accion_nueva.triggered.connect(self.nueva_pestana_solicitada.emit)
        menu.addAction(accion_nueva)
        
        menu.addSeparator()
        
        if item is not None:
            # Obtener nombre de la pestaña
            nombre_pestana = item.text()
            if " (" in nombre_pestana:
                nombre_pestana = nombre_pestana.split(" (")[0]
            
            # Opciones para la pestaña seleccionada
            accion_renombrar = QAction("📝 Renombrar Pestaña", self)
            accion_renombrar.triggered.connect(lambda: self.pestana_renombrar_solicitada.emit(nombre_pestana))
            menu.addAction(accion_renombrar)
            
            accion_eliminar = QAction("🗑️ Eliminar Pestaña", self)
            accion_eliminar.triggered.connect(lambda: self.pestana_eliminar_solicitada.emit(nombre_pestana))
            menu.addAction(accion_eliminar)
            
            menu.addSeparator()
            
            # Información adicional
            accion_info = QAction(f"ℹ️ {nombre_pestana}", self)
            accion_info.setEnabled(False)
            menu.addAction(accion_info)
        
        # Mostrar el menú
        menu.exec_(self.mapToGlobal(pos))
    
    def on_item_clicked(self, item):
        """Manejar clic en un item de la lista"""
        nombre_pestana = item.text()
        # Extraer solo el nombre (sin el contador)
        if " (" in nombre_pestana:
            nombre_pestana = nombre_pestana.split(" (")[0]
        self.pestana_seleccionada.emit(nombre_pestana)
    
    def actualizar_nombre_pestana(self, nombre_original, nuevo_nombre):
        """Actualizar el nombre de una pestaña en la lista"""
        for i in range(self.count()):
            item = self.item(i)
            texto_actual = item.text()
            if texto_actual.startswith(nombre_original + " (") or texto_actual == nombre_original:
                # Extraer el contador si existe
                if " (" in texto_actual:
                    # Mantener el contador
                    contador_parte = texto_actual.split("(")[-1]
                    nuevo_texto = f"{nuevo_nombre} ({contador_parte}"
                    item.setText(nuevo_texto)
                else:
                    item.setText(nuevo_nombre)
                break
    
    def agregar_pestana(self, nombre_pestana):
        """Agregar una nueva pestaña a la lista (siempre visible)"""
        item = QListWidgetItem(f"{nombre_pestana} (0 rutas, 0 archivos)")
        item.setData(Qt.UserRole, nombre_pestana)
        # Color gris para pestañas sin archivos
        item.setForeground(QColor(150, 150, 150))
        self.addItem(item)
        return item
    
    def eliminar_pestana(self, nombre_pestana):
        """Eliminar una pestaña de la lista completamente"""
        for i in range(self.count()):
            item = self.item(i)
            texto = item.text()
            if texto.startswith(nombre_pestana + " (") or texto == nombre_pestana:
                self.takeItem(i)
                break
    
    def actualizar_estadisticas_pestana(self, nombre_pestana, total_rutas, total_archivos, tiene_archivos):
        """Actualizar las estadísticas mostradas para una pestaña"""
        for i in range(self.count()):
            item = self.item(i)
            texto = item.text()
            if texto.startswith(nombre_pestana + " (") or texto == nombre_pestana:
                # Determinar color según si tiene archivos
                if tiene_archivos:
                    # Rojo brillante si tiene archivos
                    item.setForeground(QColor(255, 100, 100))
                    # Texto en negrita
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                else:
                    # Gris opaco si no tiene archivos
                    item.setForeground(QColor(150, 150, 150))
                    # Texto normal
                    font = item.font()
                    font.setBold(False)
                    item.setFont(font)
                
                nuevo_texto = f"{nombre_pestana} ({total_rutas} rutas, {total_archivos} archivos)"
                item.setText(nuevo_texto)
                break

# ==============================================
# CLASE PARA MANEJAR UNA PESTAÑA (TAB) DE RUTAS
# ==============================================

class TabRutasWidget(QWidget):
    """Widget que representa una pestaña con sus rutas"""
    
    seleccion_changed = pyqtSignal()
    doble_clic_ruta = pyqtSignal(str)
    solicitar_renombrar = pyqtSignal(str)
    estadisticas_actualizadas = pyqtSignal(str, int, int, bool)  # nombre, total_rutas, total_archivos, tiene_archivos
    
    def __init__(self, parent, nombre_tab, archivo_json=None):
        super().__init__(parent)
        self.parent_app = parent
        self.nombre = nombre_tab
        self.archivo_json = archivo_json
        
        # Variables para guardar configuración
        self.column_widths = [400, 80, 80, 100, 150]  # Anchos por defecto
        
        # Variables
        self.rutas = []
        self.conteos = {}
        self.current_selection = None
        
        # Inicializar interfaz
        self.inicializar_interfaz()
        
        # Cargar rutas si se proporciona un archivo JSON
        if archivo_json and os.path.exists(archivo_json):
            self.cargar_json_desde_ruta(archivo_json)
    
    def inicializar_interfaz(self):
        """Inicializar la interfaz de la pestaña"""
        layout = QVBoxLayout(self)
        
        # Panel de información
        panel_info = QFrame()
        panel_info.setFrameStyle(QFrame.Panel | QFrame.Raised)
        layout_info = QHBoxLayout(panel_info)
        
        # Nombre de la pestaña
        self.lbl_nombre_tab = QLabel(f"Pestaña: {self.nombre}")
        self.lbl_nombre_tab.setFont(QFont("Arial", 10, QFont.Bold))
        layout_info.addWidget(self.lbl_nombre_tab)
        
        # Información del archivo JSON
        nombre_json = os.path.basename(self.archivo_json) if self.archivo_json else "Sin archivo"
        self.lbl_json_tab = QLabel(f"JSON: {nombre_json}")
        self.lbl_json_tab.setStyleSheet("color: #666666;")
        layout_info.addWidget(self.lbl_json_tab)
        
        # Contador de rutas
        self.lbl_contador_tab = QLabel("Rutas: 0")
        layout_info.addWidget(self.lbl_contador_tab)
        
        layout_info.addStretch()
        layout.addWidget(panel_info)
        
        # Tabla para mostrar rutas
        self.crear_tabla()
        layout.addWidget(self.tabla)
    
    def crear_tabla(self):
        """Crear la tabla para mostrar rutas"""
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(5)
        self.tabla.setHorizontalHeaderLabels(['Ruta', 'Archivos', 'Cambio', 'Estado', 'Última Verificación'])
        
        # Configurar cabecera para permitir redimensionamiento manual
        header = self.tabla.horizontalHeader()
        header.setSectionsMovable(True)
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.mostrar_menu_contexto_header)
        
        # Configurar tabla para menú contextual
        self.tabla.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabla.customContextMenuRequested.connect(self.mostrar_menu_contexto_tabla)
        
        # Aplicar anchos guardados si existen
        for i, width in enumerate(self.column_widths):
            if i < self.tabla.columnCount():
                self.tabla.setColumnWidth(i, width)
        
        # Configurar selección
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setSelectionMode(QTableWidget.SingleSelection)
        
        # Conectar señales
        self.tabla.itemSelectionChanged.connect(self.on_seleccion_changed)
        self.tabla.cellDoubleClicked.connect(self.on_cell_double_clicked)
        
        # Guardar anchos cuando cambien
        header.sectionResized.connect(self.guardar_anchos_columnas)
    
    def mostrar_menu_contexto_header(self, pos):
        """Mostrar menú contextual para el header de la tabla"""
        menu = QMenu()
        
        action_ajustar_auto = menu.addAction("Ajustar automáticamente")
        action_restaurar_anchos = menu.addAction("Restaurar anchos por defecto")
        menu.addSeparator()
        action_guardar_config = menu.addAction("💾 Guardar configuración de columnas")
        
        action = menu.exec_(self.tabla.horizontalHeader().mapToGlobal(pos))
        
        if action == action_ajustar_auto:
            self.tabla.horizontalHeader().resizeSections(QHeaderView.ResizeToContents)
        elif action == action_restaurar_anchos:
            anchos_por_defecto = [400, 80, 80, 100, 150]
            for i, width in enumerate(anchos_por_defecto):
                if i < self.tabla.columnCount():
                    self.tabla.setColumnWidth(i, width)
            self.column_widths = anchos_por_defecto.copy()
        elif action == action_guardar_config:
            self.parent_app.guardar_configuracion()
            self.parent_app.agregar_log("✓ Configuración de columnas guardada")
    
    def mostrar_menu_contexto_tabla(self, pos):
        """Mostrar menú contextual para la tabla"""
        menu = QMenu()
        
        # Obtener el item bajo el cursor
        item = self.tabla.itemAt(pos)
        if item is not None:
            row = item.row()
            if row < len(self.rutas):
                ruta = self.rutas[row]
                
                action_abrir = menu.addAction("📂 Abrir directorio")
                menu.addSeparator()
                action_eliminar = menu.addAction("🗑️ Eliminar ruta")
                menu.addSeparator()
                action_actualizar = menu.addAction("🔄 Actualizar esta ruta")
                
                action = menu.exec_(self.tabla.mapToGlobal(pos))
                
                if action == action_abrir:
                    self.parent_app.abrir_directorio_con_ruta(ruta)
                elif action == action_eliminar:
                    self.eliminar_ruta(ruta)
                elif action == action_actualizar:
                    self.actualizar_fila_especifica(row)
    
    def actualizar_fila_especifica(self, fila):
        """Actualizar una fila específica de la tabla"""
        if fila < len(self.rutas):
            ruta = self.rutas[fila]
            conteo, estado, detalles = self.contar_archivos_ruta(ruta)
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            if conteo is not None:
                anterior = self.conteos[ruta]['actual']
                cambio = conteo - anterior
                
                self.conteos[ruta].update({
                    'anterior': anterior,
                    'actual': conteo,
                    'cambio': cambio,
                    'estado': estado,
                    'ultima_verificacion': timestamp,
                    'detalles': detalles
                })
                
                # Actualizar tabla
                if fila < self.tabla.rowCount():
                    # Archivos
                    item_archivos = self.tabla.item(fila, 1)
                    if item_archivos:
                        item_archivos.setText(str(conteo))
                        if conteo > 0:
                            item_archivos.setForeground(QColor(255, 50, 50))
                            item_archivos.setFont(QFont("Arial", 9, QFont.Bold))
                        else:
                            item_archivos.setForeground(QColor(0, 0, 0))
                            item_archivos.setFont(QFont("Arial", 9, QFont.Normal))
                    
                    # Cambio
                    item_cambio = self.tabla.item(fila, 2)
                    if item_cambio:
                        cambio_str = f"+{cambio}" if cambio > 0 else str(cambio)
                        item_cambio.setText(cambio_str)
                        if cambio > 0:
                            item_cambio.setForeground(QColor(0, 150, 0))
                            item_cambio.setFont(QFont("Arial", 9, QFont.Bold))
                        elif cambio < 0:
                            item_cambio.setForeground(QColor(200, 0, 0))
                        else:
                            item_cambio.setForeground(QColor(100, 100, 100))
                    
                    # Estado
                    item_estado = self.tabla.item(fila, 3)
                    if item_estado:
                        item_estado.setText(estado)
                    
                    # Última verificación
                    item_verificacion = self.tabla.item(fila, 4)
                    if item_verificacion:
                        item_verificacion.setText(timestamp)
                    
                    # Resaltar la fila completa si tiene archivos
                    self.resaltar_fila_si_tiene_archivos(fila, conteo)
            else:
                self.conteos[ruta].update({
                    'estado': estado,
                    'ultima_verificacion': timestamp,
                    'detalles': []
                })
                
                # Actualizar tabla
                if fila < self.tabla.rowCount():
                    item_estado = self.tabla.item(fila, 3)
                    if item_estado:
                        item_estado.setText(estado)
                    
                    item_verificacion = self.tabla.item(fila, 4)
                    if item_verificacion:
                        item_verificacion.setText(timestamp)
            
            self.parent_app.agregar_log(f"✓ Ruta actualizada: {ruta}")


    def resaltar_fila_si_tiene_archivos(self, fila, conteo):
        """Resaltar una fila completa si tiene archivos"""
        if conteo > 0:
            # Cambiar color de fondo de toda la fila a rojo claro
            for col in range(self.tabla.columnCount()):
                item = self.tabla.item(fila, col)
                if item:
                    item.setBackground(QColor(255, 220, 220))
        else:
            # Restaurar color de fondo
            for col in range(self.tabla.columnCount()):
                item = self.tabla.item(fila, col)
                if item:
                    item.setBackground(QColor(255, 255, 255))
    
    def guardar_anchos_columnas(self, logicalIndex, oldSize, newSize):
        """Guardar los anchos de las columnas cuando se redimensionen"""
        if logicalIndex < len(self.column_widths):
            self.column_widths[logicalIndex] = newSize
    
    def cargar_json_desde_ruta(self, ruta_json):
        """Cargar JSON desde una ruta específica"""
        try:
            with open(ruta_json, 'r', encoding='utf-8') as f:
                self.rutas = json.load(f)
            
            if not isinstance(self.rutas, list):
                QMessageBox.critical(self, "Error", "El JSON debe contener una lista de rutas")
                return False
            
            # Actualizar archivo JSON
            self.archivo_json = ruta_json
            nombre_json = os.path.basename(ruta_json)
            self.lbl_json_tab.setText(f"JSON: {nombre_json}")
            
            # Limpiar tabla
            self.tabla.setRowCount(0)
            
            # Inicializar conteos
            self.conteos = {}
            for ruta in self.rutas:
                self.conteos[ruta] = {
                    'actual': 0,
                    'anterior': 0,
                    'cambio': 0,
                    'estado': 'Pendiente',
                    'ultima_verificacion': '--',
                    'detalles': []
                }
                # Insertar en tabla
                self.insertar_fila_ruta(ruta)
            
            # Actualizar contador
            self.lbl_contador_tab.setText(f"Rutas: {len(self.rutas)}")
            self.parent_app.agregar_log(f"✓ Pestaña '{self.nombre}': Cargadas {len(self.rutas)} rutas desde {nombre_json}")
            
            return True
            
        except Exception as e:
            self.parent_app.agregar_log(f"✗ Error cargando JSON en pestaña '{self.nombre}': {str(e)}")
            QMessageBox.critical(self, "Error", f"No se pudo cargar el JSON en la pestaña '{self.nombre}':\n{str(e)}")
            return False
    
    def insertar_fila_ruta(self, ruta):
        """Insertar una nueva fila en la tabla para una ruta"""
        row = self.tabla.rowCount()
        self.tabla.insertRow(row)
        
        # Columna 0: Ruta
        item_ruta = QTableWidgetItem(ruta)
        self.tabla.setItem(row, 0, item_ruta)
        
        # Columna 1: Archivos
        item_archivos = QTableWidgetItem("--")
        item_archivos.setTextAlignment(Qt.AlignCenter)
        self.tabla.setItem(row, 1, item_archivos)
        
        # Columna 2: Cambio
        item_cambio = QTableWidgetItem("--")
        item_cambio.setTextAlignment(Qt.AlignCenter)
        self.tabla.setItem(row, 2, item_cambio)
        
        # Columna 3: Estado
        item_estado = QTableWidgetItem("Pendiente")
        item_estado.setTextAlignment(Qt.AlignCenter)
        self.tabla.setItem(row, 3, item_estado)
        
        # Columna 4: Última verificación
        item_verificacion = QTableWidgetItem("--")
        item_verificacion.setTextAlignment(Qt.AlignCenter)
        self.tabla.setItem(row, 4, item_verificacion)
    
    def actualizar_conteos(self):
        """Actualizar todos los conteos de esta pestaña"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        total_archivos_pestana = 0
        tiene_archivos = False
        
        for row in range(len(self.rutas)):
            if row < len(self.rutas):
                ruta = self.rutas[row]
                conteo, estado, detalles = self.contar_archivos_ruta(ruta)
                
                if conteo is not None:
                    total_archivos_pestana += conteo
                    if conteo > 0:
                        tiene_archivos = True
                    
                    anterior = self.conteos[ruta]['actual']
                    cambio = conteo - anterior
                    
                    self.conteos[ruta].update({
                        'anterior': anterior,
                        'actual': conteo,
                        'cambio': cambio,
                        'estado': estado,
                        'ultima_verificacion': timestamp,
                        'detalles': detalles
                    })
                    
                    # Actualizar tabla
                    if row < self.tabla.rowCount():
                        # Archivos
                        item_archivos = self.tabla.item(row, 1)
                        if item_archivos:
                            item_archivos.setText(str(conteo))
                            # Resaltar en rojo si tiene archivos
                            if conteo > 0:
                                item_archivos.setForeground(QColor(255, 50, 50))
                                item_archivos.setFont(QFont("Arial", 9, QFont.Bold))
                            else:
                                item_archivos.setForeground(QColor(0, 0, 0))
                                item_archivos.setFont(QFont("Arial", 9, QFont.Normal))
                        
                        # Cambio
                        item_cambio = self.tabla.item(row, 2)
                        if item_cambio:
                            cambio_str = f"+{cambio}" if cambio > 0 else str(cambio)
                            item_cambio.setText(cambio_str)
                            if cambio > 0:
                                item_cambio.setForeground(QColor(0, 150, 0))
                                item_cambio.setFont(QFont("Arial", 9, QFont.Bold))
                            elif cambio < 0:
                                item_cambio.setForeground(QColor(200, 0, 0))
                            else:
                                item_cambio.setForeground(QColor(100, 100, 100))
                        
                        # Estado
                        item_estado = self.tabla.item(row, 3)
                        if item_estado:
                            item_estado.setText(estado)
                        
                        # Última verificación
                        item_verificacion = self.tabla.item(row, 4)
                        if item_verificacion:
                            item_verificacion.setText(timestamp)
                        
                        # Resaltar la fila completa si tiene archivos
                        self.resaltar_fila_si_tiene_archivos(row, conteo)
                else:
                    self.conteos[ruta].update({
                        'estado': estado,
                        'ultima_verificacion': timestamp,
                        'detalles': []
                    })
                    
                    # Actualizar tabla
                    if row < self.tabla.rowCount():
                        item_estado = self.tabla.item(row, 3)
                        if item_estado:
                            item_estado.setText(estado)
                        
                        item_verificacion = self.tabla.item(row, 4)
                        if item_verificacion:
                            item_verificacion.setText(timestamp)
        
        # Emitir señal con estadísticas de la pestaña
        self.estadisticas_actualizadas.emit(self.nombre, len(self.rutas), total_archivos_pestana, tiene_archivos)
        self.parent_app.actualizar_estadisticas_globales()
    
    def contar_archivos_ruta(self, ruta):
        """Contar archivos en una ruta específica y obtener detalles"""
        try:
            ruta_path = Path(ruta)
            
            if not ruta_path.exists():
                return None, "Ruta no existe", []
            
            if not ruta_path.is_dir():
                return None, "No es directorio", []
            
            # Contar archivos y obtener detalles
            archivos_info = []
            try:
                for item in ruta_path.iterdir():
                    if item.is_file():
                        # Obtener fecha de modificación
                        mod_time = datetime.fromtimestamp(item.stat().st_mtime)
                        archivos_info.append({
                            'nombre': item.name,
                            'modificacion': mod_time,
                            'tamaño': item.stat().st_size
                        })
            except PermissionError:
                return None, "Permiso denegado", []
            
            # Ordenar por fecha de modificación (más recientes primero)
            archivos_info.sort(key=lambda x: x['modificacion'], reverse=True)
            
            return len(archivos_info), "Activo", archivos_info[:20]  # Limitamos a 20 archivos para no saturar
            
        except Exception as e:
            return None, f"Error: {str(e)}", []   
         
    def contar_archivos_recursivo(self, ruta):
        """Contar archivos recursivamente"""
        try:
            ruta_path = Path(ruta)
            
            if not ruta_path.exists() or not ruta_path.is_dir():
                return 0
            
            contador = 0
            for root, dirs, files in os.walk(ruta_path):
                contador += len(files)
            
            return contador
            
        except:
            return 0
    
    def obtener_datos_seleccionados(self):
        """Obtener datos de la ruta seleccionada en esta pestaña"""
        selected_rows = self.tabla.selectedItems()
        if not selected_rows:
            return None
        
        row = self.tabla.currentRow()
        if row < 0 or row >= len(self.rutas):
            return None
        
        ruta = self.rutas[row]
        
        if ruta in self.conteos:
            datos = self.conteos[ruta].copy()
            datos['ruta'] = ruta
            datos['nombre_tab'] = self.nombre
            return datos
        
        return None
    
    def anadir_ruta(self, ruta):
        """Añadir una nueva ruta a esta pestaña"""
        # Normalizar la ruta
        ruta = os.path.normpath(ruta)
        
        # Verificar si la ruta ya existe
        if ruta in self.rutas:
            QMessageBox.information(self, "Información", "Esta ruta ya está en la lista")
            return False
        
        # Añadir a la lista
        self.rutas.append(ruta)
        
        # Inicializar conteo para la nueva ruta
        self.conteos[ruta] = {
            'actual': 0,
            'anterior': 0,
            'cambio': 0,
            'estado': 'Pendiente',
            'ultima_verificacion': '--',
            'detalles': []
        }
        
        # Añadir a la tabla
        self.insertar_fila_ruta(ruta)
        
        # Actualizar contador
        self.lbl_contador_tab.setText(f"Rutas: {len(self.rutas)}")
        
        return True
    
    def eliminar_ruta(self, ruta=None):
        """Eliminar una ruta de esta pestaña"""
        if ruta is None:
            # Obtener ruta seleccionada
            row = self.tabla.currentRow()
            if row < 0:
                QMessageBox.warning(self, "Advertencia", "Seleccione una ruta para eliminar")
                return False
            
            ruta = self.rutas[row]
        
        # Eliminar de la lista
        if ruta in self.rutas:
            self.rutas.remove(ruta)
        
        # Eliminar de los conteos
        if ruta in self.conteos:
            del self.conteos[ruta]
        
        # Reconstruir tabla
        self.recargar_tabla_completa()
        
        # Actualizar contador
        self.lbl_contador_tab.setText(f"Rutas: {len(self.rutas)}")
        
        return True
    
    def recargar_tabla_completa(self):
        """Recargar completamente la tabla"""
        self.tabla.setRowCount(0)
        for ruta in self.rutas:
            self.insertar_fila_ruta(ruta)
    
    def on_seleccion_changed(self):
        """Manejar cambio de selección en la tabla"""
        self.seleccion_changed.emit()
    
    def on_cell_double_clicked(self, row, column):
        """Manejar doble clic en una celda"""
        if row < len(self.rutas):
            ruta = self.rutas[row]
            self.doble_clic_ruta.emit(ruta)
    
    def obtener_configuracion(self):
        """Obtener configuración de esta pestaña para guardar"""
        # Obtener anchos actuales de las columnas
        self.column_widths = []
        for i in range(self.tabla.columnCount()):
            self.column_widths.append(self.tabla.columnWidth(i))
        
        return {
            'nombre': self.nombre,
            'archivo_json': self.archivo_json if self.archivo_json else "",
            'rutas': self.rutas,
            'column_widths': self.column_widths
        }
    
    def aplicar_configuracion(self, config):
        """Aplicar configuración guardada a esta pestaña"""
        if 'column_widths' in config and isinstance(config['column_widths'], list):
            self.column_widths = config['column_widths']
            for i, width in enumerate(self.column_widths):
                if i < self.tabla.columnCount():
                    self.tabla.setColumnWidth(i, width)
    
    def renombrar(self, nuevo_nombre):
        """Renombrar esta pestaña"""
        if nuevo_nombre and nuevo_nombre != self.nombre:
            antiguo_nombre = self.nombre
            self.nombre = nuevo_nombre
            self.lbl_nombre_tab.setText(f"Pestaña: {self.nombre}")
            self.parent_app.agregar_log(f"📝 Pestaña renombrada: '{antiguo_nombre}' → '{nuevo_nombre}'")
            return True
        return False
    
    def limpiar_y_eliminar(self):
        """Limpiar todos los datos de la pestaña antes de eliminar"""
        self.rutas = []
        self.conteos = {}
        self.tabla.setRowCount(0)
        self.archivo_json = None

# ==============================================
# CLASE PRINCIPAL DE LA APLICACIÓN
# ==============================================

class ContadorArchivosApp(QMainWindow):
    """Aplicación principal con sistema de pestañas verticales"""
    
    def __init__(self):
        super().__init__()
        
        # Obtener ruta base
        self.BASE_PATH = get_base_path()
        
        # Variables
        self.tabs = {}  # Diccionario de pestañas: {nombre: widget_tab}
        self.tab_actual = None
        self.hilo_activo = False
        self.intervalo_actualizacion = 2  # segundos (valor por defecto)
        
        # Variables para guardar configuración de interfaz
        self.window_geometry = None
        self.splitter_sizes = None
        self.panel_derecho_visible = True
        self.ancho_panel_derecho = 400
        
        # Inicializar timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.actualizar_todo)
        
        # Inicializar interfaz
        self.inicializar_interfaz()
        
        # Cargar configuración
        self.cargar_configuracion()
    
    def inicializar_interfaz(self):
        """Inicializar la interfaz gráfica"""
        self.setWindowTitle("Monitor de Archivos - Sistema Multi-Pestañas Vertical")
        self.setGeometry(100, 100, 1400, 800)
        
        # Crear menú principal
        self.crear_menu_principal()
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout_principal = QVBoxLayout(central_widget)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        
        # Panel de estadísticas
        self.crear_panel_estadisticas(layout_principal)
        
        # Panel principal con splitter horizontal (lista de pestañas | contenido | panel derecho)
        self.crear_panel_principal(layout_principal)
        
        # Barra de estado
        self.statusBar().showMessage("Aplicación lista | Click derecho en pestañas para opciones")
    
    def crear_menu_principal(self):
        """Crear menú principal de la aplicación"""
        menubar = self.menuBar()
        
        # Menú: Archivo
        menu_archivo = menubar.addMenu("📁 Archivo")
        
        accion_nueva_tab = QAction("➕ Nueva Pestaña", self)
        accion_nueva_tab.triggered.connect(self.crear_nueva_tab_dialogo)
        accion_nueva_tab.setShortcut("Ctrl+N")
        menu_archivo.addAction(accion_nueva_tab)
        
        accion_eliminar_tab = QAction("🗑️ Eliminar Pestaña", self)
        accion_eliminar_tab.triggered.connect(self.eliminar_tab_actual)
        accion_eliminar_tab.setShortcut("Ctrl+Delete")
        menu_archivo.addAction(accion_eliminar_tab)
        
        menu_archivo.addSeparator()
        
        accion_cargar_json = QAction("📂 Cargar JSON en Pestaña", self)
        accion_cargar_json.triggered.connect(self.cargar_json_en_tab)
        menu_archivo.addAction(accion_cargar_json)
        
        accion_guardar_tab = QAction("💾 Guardar Pestaña", self)
        accion_guardar_tab.triggered.connect(self.guardar_tab_actual)
        menu_archivo.addAction(accion_guardar_tab)
        
        menu_archivo.addSeparator()
        
        accion_guardar_todo = QAction("💾 Guardar Todo", self)
        accion_guardar_todo.triggered.connect(self.guardar_todo)
        accion_guardar_todo.setShortcut("Ctrl+S")
        menu_archivo.addAction(accion_guardar_todo)
        
        accion_exportar = QAction("📊 Exportar Todo (TXT)", self)
        accion_exportar.triggered.connect(self.exportar_todo_txt)
        menu_archivo.addAction(accion_exportar)
        
        menu_archivo.addSeparator()
        
        accion_salir = QAction("🚪 Salir", self)
        accion_salir.triggered.connect(self.close)
        accion_salir.setShortcut("Ctrl+Q")
        menu_archivo.addAction(accion_salir)
        
        # Menú: Rutas
        menu_rutas = menubar.addMenu("📂 Rutas")
        
        accion_anadir_ruta = QAction("➕ Añadir Ruta", self)
        accion_anadir_ruta.triggered.connect(self.anadir_ruta_tab_actual)
        menu_rutas.addAction(accion_anadir_ruta)
        
        accion_eliminar_ruta = QAction("🗑️ Eliminar Ruta", self)
        accion_eliminar_ruta.triggered.connect(self.eliminar_ruta_tab_actual)
        menu_rutas.addAction(accion_eliminar_ruta)
        
        accion_recargar_tab = QAction("🔄 Recargar Pestaña", self)
        accion_recargar_tab.triggered.connect(self.recargar_tab_actual)
        menu_rutas.addAction(accion_recargar_tab)
        
        # Menú: Monitoreo
        menu_monitoreo = menubar.addMenu("🔄 Monitoreo")
        
        accion_iniciar = QAction("▶ Iniciar Monitoreo", self)
        accion_iniciar.triggered.connect(self.iniciar_monitoreo)
        menu_monitoreo.addAction(accion_iniciar)
        
        accion_pausar = QAction("⏸ Pausar Monitoreo", self)
        accion_pausar.triggered.connect(self.pausar_monitoreo)
        menu_monitoreo.addAction(accion_pausar)
        
        accion_reanudar = QAction("▶ Reanudar Monitoreo", self)
        accion_reanudar.triggered.connect(self.reanudar_monitoreo)
        menu_monitoreo.addAction(accion_reanudar)
        
        accion_actualizar = QAction("🔄 Actualizar Ahora", self)
        accion_actualizar.triggered.connect(self.actualizar_todo)
        accion_actualizar.setShortcut("F5")
        menu_monitoreo.addAction(accion_actualizar)
        
        menu_monitoreo.addSeparator()
        
        submenu_intervalo = menu_monitoreo.addMenu("⏱ Intervalo")
        
        for intervalo in [1, 2, 5, 10, 30, 60]:
            accion_intervalo = QAction(f"{intervalo} segundos", self)
            accion_intervalo.triggered.connect(lambda checked, i=intervalo: self.establecer_intervalo(i))
            submenu_intervalo.addAction(accion_intervalo)
        
        # Menú: Vista
        menu_vista = menubar.addMenu("👁️ Vista")
        
        accion_toggle_panel = QAction("👁️ Mostrar/Ocultar Panel Derecho", self)
        accion_toggle_panel.triggered.connect(self.toggle_panel_derecho)
        accion_toggle_panel.setShortcut("Ctrl+D")
        menu_vista.addAction(accion_toggle_panel)
        
        # Menú: Herramientas
        menu_herramientas = menubar.addMenu("⚙️ Herramientas")
        
        accion_renombrar_tab = QAction("📝 Renombrar Pestaña", self)
        accion_renombrar_tab.triggered.connect(self.renombrar_tab_actual)
        menu_herramientas.addAction(accion_renombrar_tab)
        
        # Menú: Ayuda
        menu_ayuda = menubar.addMenu("❓ Ayuda")
        
        accion_acerca = QAction("ℹ️ Acerca de", self)
        accion_acerca.triggered.connect(self.mostrar_acerca_de)
        menu_ayuda.addAction(accion_acerca)
        
        accion_manual = QAction("📖 Manual de Usuario", self)
        accion_manual.triggered.connect(self.mostrar_manual)
        menu_ayuda.addAction(accion_manual)
    
    def crear_panel_principal(self, layout_principal):
        """Crear panel principal con splitter horizontal"""
        # Crear splitter horizontal principal
        self.splitter_principal = QSplitter(Qt.Horizontal)
        
        # Panel izquierdo: Lista de pestañas vertical (redimensionable)
        self.lista_pestanas = ListaPestanasVertical()
        self.lista_pestanas.pestana_seleccionada.connect(self.cambiar_pestana_desde_lista)
        self.lista_pestanas.pestana_eliminar_solicitada.connect(self.eliminar_pestana_por_nombre)
        self.lista_pestanas.pestana_renombrar_solicitada.connect(self.renombrar_tab_dialogo)
        self.lista_pestanas.nueva_pestana_solicitada.connect(self.crear_nueva_tab_dialogo)
        
        # Panel central: Stack de widgets (contenido de pestañas)
        self.stack_contenido = QStackedWidget()
        
        # Panel derecho: Detalles y logs (redimensionable)
        self.panel_derecho = QWidget()
        self.panel_derecho.setMinimumWidth(200)
        self.panel_derecho.setMaximumWidth(800)
        layout_derecho = QVBoxLayout(self.panel_derecho)
        layout_derecho.setContentsMargins(0, 0, 0, 0)
        
        # Widget con pestañas para detalles y logs
        self.tab_detalles_logs = QTabWidget()
        
        # Pestaña de detalles
        tab_detalles = QWidget()
        layout_detalles = QVBoxLayout(tab_detalles)
        
        # Ruta clicable y botón
        frame_ruta = QFrame()
        layout_ruta = QHBoxLayout(frame_ruta)
        
        layout_ruta.addWidget(QLabel("Ruta:"))
        
        self.lbl_ruta_clicable = QLabel("Seleccione una ruta")
        self.lbl_ruta_clicable.setStyleSheet("color: gray;")
        self.lbl_ruta_clicable.setCursor(Qt.PointingHandCursor)
        self.lbl_ruta_clicable.mousePressEvent = self.abrir_directorio_desde_label
        layout_ruta.addWidget(self.lbl_ruta_clicable, 1)
        
        self.btn_abrir_directorio = QPushButton("📂 Abrir")
        self.btn_abrir_directorio.clicked.connect(self.abrir_directorio_desde_boton)
        self.btn_abrir_directorio.setEnabled(False)
        layout_ruta.addWidget(self.btn_abrir_directorio)
        
        layout_detalles.addWidget(frame_ruta)
        
        # Área de texto para detalles
        self.txt_detalles = QTextEdit()
        self.txt_detalles.setReadOnly(True)
        layout_detalles.addWidget(self.txt_detalles)
        
        # Pestaña de logs
        tab_logs = QWidget()
        layout_logs = QVBoxLayout(tab_logs)
        
        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        layout_logs.addWidget(self.txt_logs)
        
        # Añadir pestañas
        self.tab_detalles_logs.addTab(tab_detalles, "Detalles")
        self.tab_detalles_logs.addTab(tab_logs, "Registro")
        
        layout_derecho.addWidget(self.tab_detalles_logs)
        
        # Añadir widgets al splitter
        self.splitter_principal.addWidget(self.lista_pestanas)
        self.splitter_principal.addWidget(self.stack_contenido)
        self.splitter_principal.addWidget(self.panel_derecho)
        
        # Configurar el splitter para permitir redimensionamiento
        self.splitter_principal.setStretchFactor(0, 0)  # Panel izquierdo - tamaño fijo pero redimensionable
        self.splitter_principal.setStretchFactor(1, 1)  # Panel central - se expande
        self.splitter_principal.setStretchFactor(2, 0)  # Panel derecho - tamaño fijo pero redimensionable
        
        # Establecer tamaños iniciales
        self.splitter_principal.setSizes([200, 800, 400])
        
        layout_principal.addWidget(self.splitter_principal, 1)
    
    def crear_panel_estadisticas(self, layout_principal):
        """Crear panel de estadísticas"""
        panel_estadisticas = QFrame()
        panel_estadisticas.setFrameStyle(QFrame.Panel | QFrame.Raised)
        layout_estadisticas = QHBoxLayout(panel_estadisticas)
        
        # Etiquetas de estadísticas
        self.lbl_total_tabs = QLabel("Pestañas: 0")
        self.lbl_total_tabs.setFont(QFont("Arial", 10, QFont.Bold))
        layout_estadisticas.addWidget(self.lbl_total_tabs)
        
        self.lbl_total_rutas = QLabel("Total rutas: 0")
        self.lbl_total_rutas.setFont(QFont("Arial", 10, QFont.Bold))
        layout_estadisticas.addWidget(self.lbl_total_rutas)
        
        self.lbl_total_archivos = QLabel("Total archivos: 0")
        self.lbl_total_archivos.setFont(QFont("Arial", 10, QFont.Bold))
        layout_estadisticas.addWidget(self.lbl_total_archivos)
        
        self.lbl_ultima_actualizacion = QLabel("Última actualización: --")
        layout_estadisticas.addWidget(self.lbl_ultima_actualizacion)
        
        layout_estadisticas.addStretch()
        
        # Configuración de intervalo
        frame_intervalo = QFrame()
        layout_intervalo = QHBoxLayout(frame_intervalo)
        layout_intervalo.setContentsMargins(5, 0, 5, 0)
        
        layout_intervalo.addWidget(QLabel("Intervalo:"))
        
        self.spin_intervalo = QSpinBox()
        self.spin_intervalo.setRange(1, 60)
        self.spin_intervalo.setValue(self.intervalo_actualizacion)
        self.spin_intervalo.setFixedWidth(60)
        self.spin_intervalo.valueChanged.connect(self.cambiar_intervalo)
        layout_intervalo.addWidget(self.spin_intervalo)
        
        layout_intervalo.addWidget(QLabel("s"))
        
        layout_estadisticas.addWidget(frame_intervalo)
        
        # Botones de control rápido
        frame_controles = QFrame()
        layout_controles = QHBoxLayout(frame_controles)
        layout_controles.setContentsMargins(5, 0, 5, 0)
        
        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedWidth(30)
        self.btn_play.setToolTip("Iniciar monitoreo")
        self.btn_play.clicked.connect(self.iniciar_monitoreo)
        layout_controles.addWidget(self.btn_play)
        
        self.btn_pause = QPushButton("⏸")
        self.btn_pause.setFixedWidth(30)
        self.btn_pause.setToolTip("Pausar monitoreo")
        self.btn_pause.clicked.connect(self.pausar_monitoreo)
        layout_controles.addWidget(self.btn_pause)
        
        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setFixedWidth(30)
        self.btn_refresh.setToolTip("Actualizar ahora")
        self.btn_refresh.clicked.connect(self.actualizar_todo)
        layout_controles.addWidget(self.btn_refresh)
        
        layout_estadisticas.addWidget(frame_controles)
        
        # Información de estado
        self.lbl_estado = QLabel("Estado: Iniciando...")
        self.lbl_estado.setFont(QFont("Arial", 9, QFont.Bold))
        layout_estadisticas.addWidget(self.lbl_estado)
        
        layout_principal.addWidget(panel_estadisticas)
    
    def cambiar_pestana_desde_lista(self, nombre_pestana):
        """Cambiar a la pestaña seleccionada desde la lista"""
        if nombre_pestana in self.tabs:
            self.tab_actual = nombre_pestana
            widget = self.tabs[nombre_pestana]
            self.stack_contenido.setCurrentWidget(widget)
            self.mostrar_detalles_actuales()
            self.agregar_log(f"🔄 Cambiado a pestaña: '{nombre_pestana}'")
    
    def eliminar_pestana_por_nombre(self, nombre_pestana):
        """Eliminar una pestaña por su nombre (desde menú contextual)"""
        if nombre_pestana in self.tabs:
            respuesta = QMessageBox.question(
                self, 
                "Confirmar eliminación", 
                f"¿Está seguro de que desea eliminar la pestaña '{nombre_pestana}'?\n\n"
                f"Todas las rutas y configuraciones se perderán.",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if respuesta == QMessageBox.Yes:
                # Limpiar y eliminar la pestaña
                widget = self.tabs[nombre_pestana]
                widget.limpiar_y_eliminar()
                
                # Eliminar del stack
                index = self.stack_contenido.indexOf(widget)
                self.stack_contenido.removeWidget(widget)
                widget.deleteLater()
                
                # Eliminar de la lista vertical
                self.lista_pestanas.eliminar_pestana(nombre_pestana)
                
                # Eliminar del diccionario
                del self.tabs[nombre_pestana]
                
                # Actualizar pestaña actual
                if self.tab_actual == nombre_pestana:
                    if self.tabs:
                        # Seleccionar la primera pestaña disponible
                        primer_nombre = list(self.tabs.keys())[0]
                        self.tab_actual = primer_nombre
                        self.stack_contenido.setCurrentWidget(self.tabs[primer_nombre])
                        # Seleccionar en la lista
                        for i in range(self.lista_pestanas.count()):
                            item = self.lista_pestanas.item(i)
                            texto = item.text()
                            if texto.startswith(primer_nombre + " (") or texto == primer_nombre:
                                self.lista_pestanas.setCurrentItem(item)
                                break
                    else:
                        self.tab_actual = None
                
                # Limpiar detalles
                self.limpiar_detalles()
                
                # Detener monitoreo si no hay pestañas
                if len(self.tabs) == 0:
                    self.pausar_monitoreo()
                
                self.actualizar_info_tabs()
                self.agregar_log(f"🗑️ Pestaña '{nombre_pestana}' eliminada completamente")
    
    def toggle_panel_derecho(self):
        """Mostrar/ocultar panel derecho"""
        self.panel_derecho_visible = not self.panel_derecho_visible
        
        if self.panel_derecho_visible:
            self.panel_derecho.show()
        else:
            self.panel_derecho.hide()
        
        self.agregar_log(f"👁️ Panel derecho {'mostrado' if self.panel_derecho_visible else 'ocultado'}")
    
    # ==============================================
    # MÉTODOS PARA GESTIÓN DE PESTAÑAS
    # ==============================================
    
    def crear_nueva_tab_dialogo(self):
        """Crear una nueva pestaña mediante diálogo"""
        nombre, ok = QInputDialog.getText(
            self, 
            "Nueva Pestaña", 
            "Ingrese nombre para la pestaña:",
            text=f"Pestaña {len(self.tabs) + 1}"
        )
        
        if ok and nombre:
            self.crear_nueva_tab(nombre)
    
    def crear_nueva_tab(self, nombre, archivo_json=None):
        """Crear una nueva pestaña"""
        # Verificar que el nombre no exista
        if nombre in self.tabs:
            QMessageBox.warning(self, "Advertencia", "Ya existe una pestaña con ese nombre")
            return
        
        # Crear widget de pestaña
        tab = TabRutasWidget(self, nombre, archivo_json)
        
        # Conectar señales
        tab.seleccion_changed.connect(self.mostrar_detalles_actuales)
        tab.doble_clic_ruta.connect(self.abrir_directorio_con_ruta)
        tab.solicitar_renombrar.connect(self.renombrar_tab_dialogo)
        tab.estadisticas_actualizadas.connect(self.actualizar_lista_pestana)
        
        # Añadir al diccionario
        self.tabs[nombre] = tab
        
        # Añadir al stack de contenido
        self.stack_contenido.addWidget(tab)
        
        # Añadir a la lista vertical (SIEMPRE visible)
        self.lista_pestanas.agregar_pestana(nombre)
        
        # Seleccionar la nueva pestaña automáticamente para poder añadir rutas
        self.tab_actual = nombre
        self.stack_contenido.setCurrentWidget(tab)
        # Seleccionar el item en la lista
        for i in range(self.lista_pestanas.count()):
            item = self.lista_pestanas.item(i)
            if item.text().startswith(nombre + " (") or item.text() == nombre:
                self.lista_pestanas.setCurrentItem(item)
                break
        
        self.actualizar_info_tabs()
        self.agregar_log(f"➕ Nueva pestaña creada: '{nombre}'")
        
        # Iniciar monitoreo automáticamente si hay rutas
        if len(tab.rutas) > 0 and not self.hilo_activo:
            self.iniciar_monitoreo()
    
    def actualizar_lista_pestana(self, nombre, total_rutas, total_archivos, tiene_archivos):
        """Actualizar la información mostrada en la lista de pestañas"""
        self.lista_pestanas.actualizar_estadisticas_pestana(nombre, total_rutas, total_archivos, tiene_archivos)
        self.actualizar_info_tabs()
    
    def eliminar_tab_actual(self):
        """Eliminar la pestaña actual"""
        if not self.tab_actual:
            QMessageBox.warning(self, "Advertencia", "No hay pestaña seleccionada")
            return
        
        self.eliminar_pestana_por_nombre(self.tab_actual)
    
    def cargar_json_en_tab(self):
        """Cargar un archivo JSON en la pestaña actual"""
        if not self.tab_actual:
            QMessageBox.warning(self, "Advertencia", "Seleccione una pestaña primero")
            return
        
        archivo_json, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo JSON",
            self.BASE_PATH,
            "Archivos JSON (*.json);;Todos los archivos (*.*)"
        )
        
        if archivo_json:
            tab = self.tabs[self.tab_actual]
            if tab.cargar_json_desde_ruta(archivo_json):
                # Iniciar monitoreo automáticamente si hay rutas
                if len(tab.rutas) > 0 and not self.hilo_activo:
                    self.iniciar_monitoreo()
    
    def guardar_tab_actual(self):
        """Guardar las rutas de la pestaña actual en un archivo JSON"""
        if not self.tab_actual:
            QMessageBox.warning(self, "Advertencia", "Seleccione una pestaña primero")
            return
        
        tab = self.tabs[self.tab_actual]
        
        # Si ya tiene un archivo JSON, usar ese
        if tab.archivo_json:
            archivo = tab.archivo_json
        else:
            # Solicitar nuevo archivo
            archivo, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar pestaña como JSON",
                os.path.join(self.BASE_PATH, f"{self.tab_actual}.json"),
                "Archivos JSON (*.json);;Todos los archivos (*.*)"
            )
        
        if archivo:
            try:
                # Guardar rutas
                with open(archivo, 'w', encoding='utf-8') as f:
                    json.dump(tab.rutas, f, indent=2, ensure_ascii=False)
                
                # Actualizar referencia
                tab.archivo_json = archivo
                nombre_json = os.path.basename(archivo)
                tab.lbl_json_tab.setText(f"JSON: {nombre_json}")
                
                self.agregar_log(f"💾 Pestaña '{self.tab_actual}' guardada en: {nombre_json}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{str(e)}")
                self.agregar_log(f"✗ Error guardando pestaña '{self.tab_actual}': {str(e)}")
    
    def anadir_ruta_tab_actual(self):
        """Añadir una nueva ruta a la pestaña actual"""
        if not self.tab_actual:
            QMessageBox.warning(self, "Advertencia", "Seleccione una pestaña primero")
            return
        
        tab = self.tabs[self.tab_actual]
        
        # Opción 1: Seleccionar directorio
        ruta = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar directorio para añadir",
            tab.rutas[0] if tab.rutas else "."
        )
        
        # Opción 2: Ingresar manualmente
        if not ruta:
            ruta, ok = QInputDialog.getText(
                self,
                "Añadir Ruta",
                f"Ingrese la ruta del directorio para '{self.tab_actual}':",
                text="C:\\" if os.name == 'nt' else "/"
            )
            if not ok or not ruta:
                return
        
        if ruta:
            if tab.anadir_ruta(ruta):
                self.agregar_log(f"➕ Ruta añadida a '{self.tab_actual}': {ruta}")
                # Actualizar inmediatamente
                self.actualizar_manual_tab(tab)
                # Iniciar monitoreo si no está activo
                if not self.hilo_activo:
                    self.iniciar_monitoreo()
    
    def eliminar_ruta_tab_actual(self):
        """Eliminar ruta seleccionada de la pestaña actual"""
        if not self.tab_actual:
            QMessageBox.warning(self, "Advertencia", "Seleccione una pestaña primero")
            return
        
        tab = self.tabs[self.tab_actual]
        
        if tab.eliminar_ruta():
            self.agregar_log(f"🗑️ Ruta eliminada de '{self.tab_actual}'")
            self.limpiar_detalles()
    
    def recargar_tab_actual(self):
        """Recargar la pestaña actual"""
        if not self.tab_actual:
            QMessageBox.warning(self, "Advertencia", "Seleccione una pestaña primero")
            return
        
        tab = self.tabs[self.tab_actual]
        
        if tab.archivo_json and os.path.exists(tab.archivo_json):
            tab.cargar_json_desde_ruta(tab.archivo_json)
            self.agregar_log(f"🔄 Pestaña '{self.tab_actual}' recargada")
            # Iniciar monitoreo si no está activo
            if len(tab.rutas) > 0 and not self.hilo_activo:
                self.iniciar_monitoreo()
        else:
            QMessageBox.information(self, "Información", "La pestaña no tiene un archivo JSON asociado")
    
    def renombrar_tab_actual(self):
        """Renombrar la pestaña actual"""
        if not self.tab_actual:
            QMessageBox.warning(self, "Advertencia", "Seleccione una pestaña primero")
            return
        
        self.renombrar_tab_dialogo(self.tab_actual)
    
    def renombrar_tab_dialogo(self, nombre_actual):
        """Renombrar una pestaña mediante diálogo"""
        nuevo_nombre, ok = QInputDialog.getText(
            self, 
            "Renombrar Pestaña", 
            "Ingrese nuevo nombre para la pestaña:",
            text=nombre_actual
        )
        
        if ok and nuevo_nombre and nuevo_nombre != nombre_actual:
            # Verificar que el nuevo nombre no exista
            if nuevo_nombre in self.tabs:
                QMessageBox.warning(self, "Advertencia", "Ya existe una pestaña con ese nombre")
                return
            
            # Renombrar en el diccionario
            if nombre_actual in self.tabs:
                tab = self.tabs.pop(nombre_actual)
                self.tabs[nuevo_nombre] = tab
                
                # Renombrar en la lista vertical
                self.lista_pestanas.actualizar_nombre_pestana(nombre_actual, nuevo_nombre)
                
                # Renombrar el widget
                tab.renombrar(nuevo_nombre)
                
                # Actualizar pestaña actual si es necesario
                if self.tab_actual == nombre_actual:
                    self.tab_actual = nuevo_nombre
    
    def actualizar_info_tabs(self):
        """Actualizar información de pestañas"""
        total_rutas = sum(len(tab.rutas) for tab in self.tabs.values())
        total_archivos = 0
        pestanas_con_archivos = 0
        
        for tab in self.tabs.values():
            archivos_tab = 0
            for datos in tab.conteos.values():
                if isinstance(datos['actual'], (int, float)):
                    archivos_tab += datos['actual']
            if archivos_tab > 0:
                pestanas_con_archivos += 1
            total_archivos += archivos_tab
        
        self.lbl_total_tabs.setText(f"Pestañas: {len(self.tabs)} | Con archivos: {pestanas_con_archivos}")
        self.lbl_total_rutas.setText(f"Total rutas: {total_rutas}")
        self.lbl_total_archivos.setText(f"Total archivos: {total_archivos}")
    
    # ==============================================
    # MÉTODOS PARA MONITOREO
    # ==============================================
    
    def iniciar_monitoreo(self):
        """Iniciar monitoreo de todas las pestañas"""
        if not self.tabs:
            self.agregar_log("⚠ No hay pestañas para monitorear")
            return
        
        # Verificar si hay rutas para monitorear
        total_rutas = sum(len(tab.rutas) for tab in self.tabs.values())
        if total_rutas == 0:
            self.agregar_log("⚠ No hay rutas para monitorear")
            return
        
        if not self.hilo_activo:
            self.hilo_activo = True
            self.timer.start(self.intervalo_actualizacion * 1000)
            self.agregar_log("▶ Monitoreo iniciado para todas las pestañas")
            self.lbl_estado.setText(f"Estado: Monitoreando ({len(self.tabs)} pestañas totales)")
            self.btn_play.setEnabled(False)
            self.btn_pause.setEnabled(True)
            
            # Realizar primera actualización inmediatamente
            self.actualizar_todo()
    
    def reanudar_monitoreo(self):
        """Reanudar monitoreo después de pausar"""
        if not self.hilo_activo:
            self.hilo_activo = True
            self.timer.start(self.intervalo_actualizacion * 1000)
            self.agregar_log("▶ Monitoreo reanudado")
            self.lbl_estado.setText("Estado: Monitoreando...")
            self.btn_play.setEnabled(False)
            self.btn_pause.setEnabled(True)
            
            # Realizar actualización inmediatamente
            self.actualizar_todo()
    
    def pausar_monitoreo(self):
        """Pausar monitoreo de todas las pestañas"""
        self.hilo_activo = False
        self.timer.stop()
        self.agregar_log("⏸ Monitoreo pausado")
        self.lbl_estado.setText("Estado: Pausado")
        self.btn_play.setEnabled(True)
        self.btn_pause.setEnabled(False)
    
    def establecer_intervalo(self, intervalo):
        """Establecer intervalo desde el menú"""
        self.spin_intervalo.setValue(intervalo)
        self.cambiar_intervalo()
    
    def cambiar_intervalo(self):
        """Cambiar intervalo de actualización"""
        try:
            nuevo_intervalo = self.spin_intervalo.value()
            if 1 <= nuevo_intervalo <= 60:
                self.intervalo_actualizacion = nuevo_intervalo
                self.agregar_log(f"⏱ Intervalo cambiado a {nuevo_intervalo} segundos")
                
                # Actualizar timer si está activo
                if self.hilo_activo:
                    self.timer.setInterval(nuevo_intervalo * 1000)
                    
            else:
                QMessageBox.warning(self, "Advertencia", "El intervalo debe estar entre 1 y 60 segundos")
        except ValueError:
            QMessageBox.warning(self, "Advertencia", "Ingrese un número válido")
    
    def actualizar_todo(self):
        """Actualizar todas las pestañas"""
        for nombre_tab, tab in self.tabs.items():
            tab.actualizar_conteos()
        
        # Actualizar última actualización
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.lbl_ultima_actualizacion.setText(f"Última actualización: {timestamp}")
    
    def actualizar_manual_tab(self, tab):
        """Actualizar una pestaña específica manualmente"""
        threading.Thread(target=tab.actualizar_conteos, daemon=True).start()
    
    def actualizar_estadisticas_globales(self):
        """Actualizar estadísticas globales de todas las pestañas"""
        total_rutas = 0
        total_archivos = 0
        
        for tab in self.tabs.values():
            total_rutas += len(tab.rutas)
            
            # Sumar archivos de todas las rutas en esta pestaña
            for datos in tab.conteos.values():
                if isinstance(datos['actual'], (int, float)):
                    total_archivos += datos['actual']
        
        # Actualizar labels
        self.lbl_total_rutas.setText(f"Total rutas: {total_rutas}")
        self.lbl_total_archivos.setText(f"Total archivos: {total_archivos}")
    
    # ==============================================
    # MÉTODOS PARA DETALLES
    # ==============================================
    
    def mostrar_detalles_actuales(self):
        """Mostrar detalles de la ruta seleccionada en la pestaña actual"""
        if not self.tab_actual:
            self.limpiar_detalles()
            return
        
        tab = self.tabs[self.tab_actual]
        datos = tab.obtener_datos_seleccionados()
        
        if datos is None:
            self.limpiar_detalles()
            return
        
        # Actualizar label de ruta
        ruta = datos['ruta']
        ruta_corta = ruta
        if len(ruta) > 60:
            ruta_corta = "..." + ruta[-57:]
        
        self.lbl_ruta_clicable.setText(ruta_corta)
        self.lbl_ruta_clicable.setStyleSheet("color: #0645AD; text-decoration: underline;")
        self.btn_abrir_directorio.setEnabled(True)
        
        # Actualizar detalles con formato mejorado
        info = f"<b>📊 INFORMACIÓN DE LA RUTA</b><br><br>"
        info += f"<b>📁 Pestaña:</b> {datos['nombre_tab']}<br>"
        info += f"<b>📍 Ruta:</b> <i>{ruta}</i><br><br>"
        info += f"<b>📈 ESTADÍSTICAS:</b><br>"
        info += f"  • <b>Archivos actuales:</b> {datos['actual']}<br>"
        info += f"  • <b>Archivos anteriores:</b> {datos['anterior']}<br>"
        info += f"  • <b>Cambio:</b> {datos['cambio']:+d}<br>"
        info += f"  • <b>Estado:</b> {datos['estado']}<br>"
        info += f"  • <b>Última verificación:</b> {datos['ultima_verificacion']}<br>"
        info += f"  • <b>Archivos totales (recursivo):</b> {tab.contar_archivos_recursivo(ruta)}<br>"
        info += "<br>"
        
        # Mostrar archivos con sus fechas de modificación
        if datos['detalles'] and isinstance(datos['detalles'], list) and len(datos['detalles']) > 0:
            info += f"<b>📄 ARCHIVOS ENCONTRADOS ({len(datos['detalles'])} mostrados de {datos['actual']}):</b><br><br>"
            info += "<table border='0' cellpadding='5' cellspacing='0' style='width:100%'>"
            info += "<tr style='background-color: #4CAF50; color: white;'>"
            info += "<th style='text-align:left; padding:5px'>#</th>"
            info += "<th style='text-align:left; padding:5px'>Nombre del archivo</th>"
            info += "<th style='text-align:left; padding:5px'>Fecha modificación</th>"
            info += "<th style='text-align:right; padding:5px'>Tamaño</th>"
            info += "</tr>"
            
            for idx, archivo in enumerate(datos['detalles'][:20], 1):
                # Acortar nombre si es muy largo
                nombre = archivo['nombre'] if isinstance(archivo, dict) else str(archivo)
                if len(nombre) > 40:
                    nombre = nombre[:37] + "..."
                
                # Formatear fecha
                if isinstance(archivo, dict) and 'modificacion' in archivo:
                    fecha = archivo['modificacion'].strftime("%d/%m/%Y %H:%M:%S")
                    tamaño = archivo.get('tamaño', 0)
                    # Formatear tamaño
                    if tamaño < 1024:
                        tamaño_str = f"{tamaño} B"
                    elif tamaño < 1024 * 1024:
                        tamaño_str = f"{tamaño/1024:.1f} KB"
                    else:
                        tamaño_str = f"{tamaño/(1024*1024):.1f} MB"
                else:
                    fecha = "Fecha no disponible"
                    tamaño_str = "N/A"
                
                # Alternar colores de fila
                bg_color = "#f9f9f9" if idx % 2 == 0 else "#ffffff"
                info += f"<tr style='background-color:{bg_color}'>"
                info += f"<td style='padding:5px'>{idx}</td>"
                info += f"<td style='padding:5px'>📄 {nombre}</td>"
                info += f"<td style='padding:5px'>🕒 {fecha}</td>"
                info += f"<td style='padding:5px; text-align:right'>💾 {tamaño_str}</td>"
                info += "</tr>"
            
            info += "</table>"
            
            if datos['actual'] > 20:
                info += f"<br><i>... y {datos['actual'] - 20} archivos más no mostrados</i>"
        else:
            info += f"<b>📄 ARCHIVOS ENCONTRADOS:</b><br>"
            info += f"<i>No se encontraron archivos en esta ruta</i>"
        
        # Mostrar mensaje de recuento recursivo
        if tab.contar_archivos_recursivo(ruta) > datos['actual']:
            info += f"<br><br><b>ℹ️ NOTA:</b> Se encontraron {tab.contar_archivos_recursivo(ruta) - datos['actual']} archivos en subdirectorios."
        
        self.txt_detalles.setHtml(info)
    
    def limpiar_detalles(self):
        """Limpiar panel de detalles"""
        self.lbl_ruta_clicable.setText("Seleccione una ruta")
        self.lbl_ruta_clicable.setStyleSheet("color: gray;")
        self.btn_abrir_directorio.setEnabled(False)
        self.txt_detalles.clear()
    
    # ==============================================
    # MÉTODOS PARA ABRIR DIRECTORIOS
    # ==============================================
    
    def abrir_directorio_desde_label(self, event):
        """Abrir directorio desde el label clicable"""
        if self.tab_actual:
            tab = self.tabs[self.tab_actual]
            datos = tab.obtener_datos_seleccionados()
            if datos:
                self.abrir_directorio_con_ruta(datos['ruta'])
    
    def abrir_directorio_desde_boton(self):
        """Abrir directorio desde el botón"""
        if self.tab_actual:
            tab = self.tabs[self.tab_actual]
            datos = tab.obtener_datos_seleccionados()
            if datos:
                self.abrir_directorio_con_ruta(datos['ruta'])
    
    def abrir_directorio_con_ruta(self, ruta):
        """Abrir un directorio dado en el explorador de archivos"""
        try:
            if not os.path.exists(ruta):
                QMessageBox.critical(self, "Error", f"La ruta no existe:\n{ruta}")
                return
            
            sistema = os.name
            if sistema == 'nt':  # Windows
                os.startfile(ruta)
            elif sistema == 'posix':  # Linux/Mac
                subprocess.Popen(['xdg-open', ruta])
            else:
                subprocess.Popen(['open' if os.name == 'mac' else 'xdg-open', ruta])
            
            self.agregar_log(f"📁 Directorio abierto: {ruta}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el directorio:\n{str(e)}")
            self.agregar_log(f"✗ Error abriendo directorio: {str(e)}")
    
    # ==============================================
    # MÉTODOS DE CONFIGURACIÓN
    # ==============================================
    
    def cargar_configuracion(self):
        """Cargar configuración guardada"""
        config_file = os.path.join(self.BASE_PATH, "monitor_config_multi.json")
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Cargar intervalo
                if "intervalo" in config:
                    self.intervalo_actualizacion = config["intervalo"]
                    self.spin_intervalo.setValue(self.intervalo_actualizacion)
                    self.agregar_log(f"✓ Intervalo cargado: {self.intervalo_actualizacion} segundos")
                
                # Cargar geometría de ventana
                if "window_geometry" in config:
                    self.window_geometry = config["window_geometry"]
                    if self.window_geometry:
                        self.restoreGeometry(QByteArray.fromHex(self.window_geometry.encode()))
                
                # Cargar tamaños del splitter
                if "splitter_sizes" in config:
                    self.splitter_sizes = config["splitter_sizes"]
                    if hasattr(self, 'splitter_principal') and self.splitter_sizes:
                        self.splitter_principal.setSizes(self.splitter_sizes)
                
                # Cargar visibilidad del panel derecho
                if "panel_derecho_visible" in config:
                    self.panel_derecho_visible = config["panel_derecho_visible"]
                
                # Cargar ancho del panel derecho
                if "ancho_panel_derecho" in config:
                    self.ancho_panel_derecho = config["ancho_panel_derecho"]
                
                # Cargar pestañas
                if "tabs" in config and isinstance(config["tabs"], list):
                    for tab_config in config["tabs"]:
                        nombre = tab_config.get("nombre", f"Pestaña {len(self.tabs) + 1}")
                        archivo_json = tab_config.get("archivo_json")
                        
                        # Crear pestaña
                        if archivo_json and os.path.exists(archivo_json):
                            self.crear_nueva_tab(nombre, archivo_json)
                        else:
                            self.crear_nueva_tab(nombre)
                        
                        # Aplicar configuración de columnas si existe
                        if nombre in self.tabs and "column_widths" in tab_config:
                            self.tabs[nombre].aplicar_configuracion(tab_config)
                    
                    self.agregar_log(f"✓ Cargadas {len(config['tabs'])} pestañas desde configuración")
                
                # Si no hay pestañas en la configuración, crear una por defecto
                if len(self.tabs) == 0:
                    self.crear_tab_inicial()
                
                # Aplicar visibilidad del panel derecho
                if hasattr(self, 'panel_derecho'):
                    if not self.panel_derecho_visible:
                        self.panel_derecho.hide()
                
                # Iniciar monitoreo automáticamente si hay rutas
                total_rutas = sum(len(tab.rutas) for tab in self.tabs.values())
                if total_rutas > 0:
                    self.iniciar_monitoreo()
                
            except Exception as e:
                self.agregar_log(f"⚠ Error cargando configuración: {str(e)}")
                self.crear_tab_inicial()
        else:
            self.crear_tab_inicial()
    
    def crear_tab_inicial(self):
        """Crear pestaña inicial"""
        self.crear_nueva_tab("Principal")
        self.agregar_log("✓ Pestaña inicial 'Principal' creada")
    
    def guardar_todo(self):
        """Guardar toda la configuración"""
        self.guardar_configuracion()
    
    def guardar_configuracion(self):
        """Guardar configuración actual"""
        config_file = os.path.join(self.BASE_PATH, "monitor_config_multi.json")
        
        # Preparar configuración de pestañas
        tabs_config = []
        for nombre, tab in self.tabs.items():
            tabs_config.append(tab.obtener_configuracion())
        
        # Guardar geometría de ventana
        window_geometry = self.saveGeometry().toHex().data().decode()
        
        # Guardar tamaños del splitter
        splitter_sizes = []
        if hasattr(self, 'splitter_principal'):
            splitter_sizes = self.splitter_principal.sizes()
        
        config = {
            "tabs": tabs_config,
            "intervalo": self.intervalo_actualizacion,
            "window_geometry": window_geometry,
            "splitter_sizes": splitter_sizes,
            "panel_derecho_visible": self.panel_derecho_visible,
            "ancho_panel_derecho": self.ancho_panel_derecho,
            "guardado_el": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "3.0-vertical-contextual"
        }
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            self.agregar_log("✓ Configuración completa guardada")
            self.statusBar().showMessage("Configuración guardada correctamente", 3000)
            
        except Exception as e:
            self.agregar_log(f"✗ Error guardando configuración: {str(e)}")
            QMessageBox.critical(self, "Error", f"No se pudo guardar la configuración:\n{str(e)}")
    
    # ==============================================
    # MÉTODOS DE AYUDA
    # ==============================================
    
    def mostrar_acerca_de(self):
        """Mostrar diálogo Acerca de"""
        QMessageBox.about(self, "Acerca de",
            f"""<b>Monitor de Archivos - Sistema Multi-Pestañas Vertical</b><br><br>
            Versión: 3.0<br>
            Desarrollado con PyQt5<br><br>
            Características:<br>
            • Pestañas verticales redimensionables<br>
            • Menú contextual en pestañas (click derecho)<br>
            • Resaltado en rojo de rutas con archivos<br>
            • Paneles ajustables manualmente<br>
            • Monitoreo multi-pestañas<br>
            • Configuración persistente<br>
            • Columnas redimensionables<br>
            • Exportación de resultados<br><br>
            © 2024 - Todos los derechos reservados""")
    
    def mostrar_manual(self):
        """Mostrar manual de usuario"""
        manual_text = """
        <h2>Manual de Usuario - Monitor de Archivos (Versión Vertical)</h2>
        
        <h3>📋 Novedades de esta versión:</h3>
        <ul>
        <li><b>Menú contextual:</b> Click derecho en las pestañas para opciones rápidas</li>
        <li><b>Eliminación completa:</b> Las pestañas se eliminan completamente al guardar</li>
        <li><b>Pestañas siempre visibles:</b> Todas las pestañas son visibles para gestionar rutas</li>
        <li><b>Indicador visual:</b> Rojo = tiene archivos, Gris = sin archivos</li>
        </ul>
        
        <h3>🎯 Uso Básico:</h3>
        <ol>
        <li><b>Crear pestaña:</b> Menú Archivo → Nueva Pestaña (o click derecho → Nueva Pestaña)</li>
        <li><b>Añadir rutas:</b> Menú Rutas → Añadir Ruta</li>
        <li><b>Iniciar monitoreo:</b> Menú Monitoreo → Iniciar Monitoreo</li>
        <li><b>Exportar resultados:</b> Menú Archivo → Exportar Todo (TXT)</li>
        </ol>
        
        <h3>🖱️ Menú Contextual (Click Derecho):</h3>
        <ul>
        <li><b>En pestañas:</b> Nueva Pestaña, Renombrar, Eliminar</li>
        <li><b>En tabla de rutas:</b> Abrir directorio, Eliminar ruta, Actualizar</li>
        <li><b>En encabezados:</b> Ajustar columnas, Guardar configuración</li>
        </ul>
        
        <h3>🛠️ Atajos de Teclado:</h3>
        <ul>
        <li><b>Ctrl+N:</b> Nueva pestaña</li>
        <li><b>Ctrl+S:</b> Guardar todo</li>
        <li><b>Ctrl+Q:</b> Salir</li>
        <li><b>Ctrl+Delete:</b> Eliminar pestaña actual</li>
        <li><b>F5:</b> Actualizar ahora</li>
        <li><b>Ctrl+D:</b> Mostrar/ocultar panel derecho</li>
        </ul>
        
        <h3>📝 Indicadores visuales:</h3>
        <ul>
        <li><b>🔴 Texto rojo en pestaña:</b> La pestaña contiene archivos</li>
        <li><b>⚪ Texto gris en pestaña:</b> La pestaña no contiene archivos</li>
        <li><b>🎨 Fondo rojo en tabla:</b> La ruta contiene archivos</li>
        <li><b>🟢 Cambio positivo en verde:</b> Aumentó el número de archivos</li>
        <li><b>🔴 Cambio negativo en rojo:</b> Disminuyó el número de archivos</li>
        </ul>
        
        <h3>🖱️ Ajuste de paneles:</h3>
        <ul>
        <li><b>Panel izquierdo:</b> Arrastra el borde derecho para ajustar el ancho de la lista de pestañas</li>
        <li><b>Panel derecho:</b> Arrastra el borde izquierdo para ajustar el ancho del panel de detalles</li>
        <li><b>Ocultar panel derecho:</b> Ctrl+D o menú Vista</li>
        </ul>
        """
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Manual de Usuario")
        dialog.setGeometry(200, 200, 600, 500)
        
        layout = QVBoxLayout()
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml(manual_text)
        layout.addWidget(text_edit)
        
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(dialog.close)
        layout.addWidget(btn_cerrar)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    # ==============================================
    # MÉTODOS DE EXPORTACIÓN
    # ==============================================
    
    def exportar_todo_txt(self):
        """Exportar resultados de todas las pestañas a TXT"""
        if not self.tabs:
            QMessageBox.warning(self, "Advertencia", "No hay pestañas para exportar")
            return
        
        archivo, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar resultados completos en TXT",
            os.path.join(self.BASE_PATH, f"monitor_completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"),
            "Archivos de texto (*.txt);;Todos los archivos (*.*)"
        )
        
        if archivo:
            try:
                self.exportar_todo_estructurado(archivo)
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo exportar:\n{str(e)}")
    
    def exportar_todo_estructurado(self, archivo):
        """Exportar todas las pestañas a TXT con formato estructurado"""
        fecha_actual = datetime.now()
        
        with open(archivo, 'w', encoding='utf-8') as f:
            # Cabecera del informe
            f.write("=" * 80 + "\n")
            f.write("INFORME COMPLETO DE MONITOREO MULTI-PESTAÑAS (VERSIÓN VERTICAL)\n")
            f.write("=" * 80 + "\n\n")
            
            # Información general
            f.write("INFORMACIÓN GENERAL\n")
            f.write("-" * 40 + "\n")
            f.write(f"Fecha de generación: {fecha_actual.strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Total de pestañas: {len(self.tabs)}\n")
            f.write(f"Pestañas con archivos: {sum(1 for tab in self.tabs.values() if any(datos['actual'] > 0 for datos in tab.conteos.values()))}\n")
            f.write(f"Intervalo de monitoreo: {self.intervalo_actualizacion} segundos\n")
            f.write(f"Configuración guardada en: {os.path.join(self.BASE_PATH, 'monitor_config_multi.json')}\n")
            f.write("\n")
            
            # Resumen por pestaña
            total_rutas = 0
            total_archivos = 0
            
            for nombre_tab, tab in self.tabs.items():
                f.write(f"PESTAÑA: {nombre_tab}\n")
                f.write("-" * 40 + "\n")
                f.write(f"Archivo JSON: {tab.archivo_json if tab.archivo_json else 'No guardado'}\n")
                f.write(f"Total rutas en pestaña: {len(tab.rutas)}\n")
                
                # Calcular archivos en esta pestaña
                archivos_pestaña = 0
                for datos in tab.conteos.values():
                    if isinstance(datos['actual'], (int, float)):
                        archivos_pestaña += datos['actual']
                
                f.write(f"Total archivos en pestaña: {archivos_pestaña}\n")
                f.write(f"Tiene archivos: {'Sí' if archivos_pestaña > 0 else 'No'}\n\n")
                
                total_rutas += len(tab.rutas)
                total_archivos += archivos_pestaña
            
            f.write(f"\nRESUMEN GLOBAL\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total rutas monitoreadas: {total_rutas}\n")
            f.write(f"Total archivos contados: {total_archivos}\n\n")
            
            # Detalle por pestaña (solo las que tienen archivos para no saturar)
            f.write("DETALLE DE PESTAÑAS CON ARCHIVOS\n")
            f.write("=" * 80 + "\n\n")
            
            for nombre_tab, tab in self.tabs.items():
                archivos_pestaña = sum(datos['actual'] for datos in tab.conteos.values() if isinstance(datos['actual'], (int, float)))
                if archivos_pestaña == 0:
                    continue
                    
                f.write(f"\n{'=' * 80}\n")
                f.write(f"DETALLE COMPLETO - PESTAÑA: {nombre_tab}\n")
                f.write("=" * 80 + "\n\n")
                
                for i, ruta in enumerate(tab.rutas, 1):
                    datos = tab.conteos[ruta]
                    
                    f.write(f"RUTA {i}: {ruta}\n")
                    f.write("-" * 60 + "\n")
                    f.write(f"  Estado: {datos['estado']}\n")
                    f.write(f"  Archivos actuales: {datos['actual'] if datos['actual'] != 0 else '0'}\n")
                    f.write(f"  Archivos anteriores: {datos['anterior']}\n")
                    f.write(f"  Cambio: {datos['cambio']:+.0f}\n")
                    f.write(f"  Última verificación: {datos['ultima_verificacion']}\n")
                    
                    # Archivos recursivos
                    recursivo = tab.contar_archivos_recursivo(ruta)
                    f.write(f"  Archivos totales (recursivo): {recursivo}\n\n")
            
            # Pie de página
            f.write("\n" + "=" * 80 + "\n")
            f.write("FIN DEL INFORME\n")
            f.write(f"Generado por Monitor de Archivos Multi-Pestañas v3.0\n")
            f.write("=" * 80 + "\n")
        
        self.agregar_log(f"✓ Resultados completos exportados a TXT: {archivo}")
        
        respuesta = QMessageBox.question(
            self,
            "Éxito",
            f"Informe completo exportado correctamente a:\n{archivo}\n\n¿Desea abrir el archivo generado?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if respuesta == QMessageBox.Yes:
            try:
                if os.name == 'nt':
                    os.startfile(archivo)
                else:
                    subprocess.Popen(['xdg-open', archivo])
            except:
                pass
    
    # ==============================================
    # MÉTODOS AUXILIARES
    # ==============================================
    
    def agregar_log(self, mensaje):
        """Agregar mensaje al registro"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.txt_logs.append(f"[{timestamp}] {mensaje}")
    
    def closeEvent(self, event):
        """Manejar cierre de la aplicación"""
        respuesta = QMessageBox.question(
            self, 
            "Confirmar salida", 
            "¿Está seguro de que desea terminar el monitoreo y salir?\n\n"
            "Se guardará la configuración actual automáticamente.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if respuesta == QMessageBox.Yes:
            self.pausar_monitoreo()
            self.guardar_configuracion()
            self.agregar_log("🚪 Aplicación terminada por el usuario")
            time.sleep(0.5)
            event.accept()
        else:
            event.ignore()

# ==============================================
# FUNCIÓN PRINCIPAL
# ==============================================

def main():
    # Crear aplicación
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Establecer estilo
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f0f0f0;
        }
        QStackedWidget {
            background-color: white;
        }
        QPushButton {
            padding: 5px 10px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:pressed {
            background-color: #3d8b40;
        }
        QPushButton:disabled {
            background-color: #cccccc;
        }
        QLabel[style*="color: #0645AD"] {
            text-decoration: none;
        }
        QLabel[style*="color: #0645AD"]:hover {
            text-decoration: underline;
        }
        QSplitter::handle {
            background-color: #c4c4c4;
        }
        QSplitter::handle:hover {
            background-color: #a0a0a0;
        }
        QTableWidget {
            gridline-color: #e0e0e0;
        }
        QHeaderView::section {
            background-color: #f0f0f0;
            padding: 5px;
            border: 1px solid #d0d0d0;
            font-weight: bold;
        }
        QMenuBar {
            background-color: #f0f0f0;
        }
        QMenuBar::item:selected {
            background-color: #e0e0e0;
        }
        QMenu {
            background-color: white;
            border: 1px solid #c4c4c4;
        }
        QMenu::item:selected {
            background-color: #4CAF50;
            color: white;
        }
        QSplitter {
            handle-size: 4px;
        }
    """)
    
    # Crear ventana principal
    ventana = ContadorArchivosApp()
    ventana.show()
    
    # Ejecutar aplicación
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()