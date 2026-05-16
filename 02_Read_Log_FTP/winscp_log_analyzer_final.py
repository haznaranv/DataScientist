import json
import os
import re
import glob
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime, timedelta
import threading
from pathlib import Path
import subprocess
import csv

class WinSCPLogAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Analizador de Logs WinSCP")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')
        
        # Cargar configuraciones
        self.config_file = 'config.json'
        self.errores_file = 'errores_personalizados.json'
        self.ultima_fecha_file = 'ultima_fecha_analisis.json'
        
        # Variables
        self.rutas = []
        self.errores_conocidos = []
        self.ultima_fecha_analisis = {}
        self.analisis_en_progreso = False
        self.datos_archivos = []
        self.visores_abiertos = {}
        
        # Cargar datos
        self.cargar_configuracion()
        self.cargar_errores()
        self.cargar_ultima_fecha()
        
        # Configurar estilo
        self.setup_styles()
        
        # Crear interfaz
        self.crear_interfaz()
        
        # Actualizar lista de rutas
        self.actualizar_lista_rutas()
    
    def setup_styles(self):
        """Configurar estilos para la interfaz"""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Colores
        self.color_principal = '#2c3e50'
        self.color_secundario = '#3498db'
        self.color_exito = '#27ae60'
        self.color_error = '#e74c3c'
        self.color_advertencia = '#f39c12'
        
        # Configurar estilos personalizados
        self.style.configure('Exito.TLabel', foreground=self.color_exito)
        self.style.configure('Error.TLabel', foreground=self.color_error)
        self.style.configure('Advertencia.TLabel', foreground=self.color_advertencia)
        self.style.configure('Accent.TButton', background=self.color_secundario, foreground='white')
    
    def crear_interfaz(self):
        """Crear todos los widgets de la interfaz"""
        
        # Frame principal con paned window para dividir la pantalla
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Panel izquierdo (configuración)
        left_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(left_frame, weight=1)
        
        # Panel derecho (resultados)
        right_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(right_frame, weight=2)
        
        # ========== PANEL IZQUIERDO: CONFIGURACIÓN ==========
        ttk.Label(left_frame, text="⚙️ CONFIGURACIÓN", font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
        # Sección: Gestión de rutas
        rutas_frame = ttk.LabelFrame(left_frame, text="📁 Rutas de logs", padding="10")
        rutas_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Lista de rutas
        self.rutas_listbox = tk.Listbox(rutas_frame, height=8, selectmode=tk.SINGLE)
        self.rutas_listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Scrollbar para lista
        scrollbar = ttk.Scrollbar(rutas_frame, orient="vertical", command=self.rutas_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.rutas_listbox.configure(yscrollcommand=scrollbar.set)
        
        # Botones para rutas
        btn_frame = ttk.Frame(rutas_frame)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="➕ Añadir ruta", 
                  command=self.agregar_ruta).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="➖ Eliminar", 
                  command=self.eliminar_ruta).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📂 Abrir", 
                  command=self.explorar_ruta).pack(side=tk.LEFT, padx=5)
        
        # Sección: Configuración de análisis
        config_frame = ttk.LabelFrame(left_frame, text="🔍 Opciones de análisis", padding="10")
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Opciones de fecha
        self.fecha_var = tk.StringVar(value="ultima")
        ttk.Radiobutton(config_frame, text="Buscar desde última fecha", 
                       variable=self.fecha_var, value="ultima").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(config_frame, text="Analizar todo el archivo", 
                       variable=self.fecha_var, value="completo").pack(anchor=tk.W, pady=2)
        
        # Botón de análisis
        self.analizar_btn = ttk.Button(left_frame, text="🚀 INICIAR ANÁLISIS", 
                                      command=self.iniciar_analisis, 
                                      style='Accent.TButton')
        self.analizar_btn.pack(fill=tk.X, pady=(10, 5))
        
        # Barra de progreso
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(left_frame, variable=self.progress_var, 
                                           maximum=100, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))
        
        # Sección: Estadísticas rápidas
        stats_frame = ttk.LabelFrame(left_frame, text="📊 Estadísticas", padding="10")
        stats_frame.pack(fill=tk.X)
        
        self.stats_label = ttk.Label(stats_frame, text="Esperando análisis...")
        self.stats_label.pack()
        
        # Botón de salir
        ttk.Button(left_frame, text="🚪 Salir", 
                  command=self.salir).pack(fill=tk.X, pady=(20, 0))
        
        # ========== PANEL DERECHO: RESULTADOS ==========
        ttk.Label(right_frame, text="📋 RESULTADOS - Doble clic para ver log", 
                 font=('Arial', 11, 'bold')).pack(pady=(0, 10))
        
        # Frame para controles de resultados
        resultados_ctrl_frame = ttk.Frame(right_frame)
        resultados_ctrl_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Botones de acción
        ttk.Button(resultados_ctrl_frame, text="📤 Exportar CSV", 
                  command=self.exportar_csv).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(resultados_ctrl_frame, text="📄 Generar Reporte", 
                  command=self.generar_reporte_personalizado).pack(side=tk.LEFT, padx=5)
        ttk.Button(resultados_ctrl_frame, text="🔄 Limpiar", 
                  command=self.limpiar_resultados).pack(side=tk.LEFT, padx=5)
        ttk.Button(resultados_ctrl_frame, text="🔍 Buscar texto", 
                  command=self.busqueda_global).pack(side=tk.LEFT, padx=5)
        
        # Filtros
        filtro_frame = ttk.Frame(resultados_ctrl_frame)
        filtro_frame.pack(side=tk.RIGHT)
        
        ttk.Label(filtro_frame, text="Filtrar:").pack(side=tk.LEFT)
        self.filtro_var = tk.StringVar()
        self.filtro_var.trace('w', self.aplicar_filtro)
        filtro_combo = ttk.Combobox(filtro_frame, textvariable=self.filtro_var, 
                                   values=["Todos", "Correcto", "Error", "Hoy", "Ayer", "Antiguos"],
                                   width=15, state='readonly')
        filtro_combo.pack(side=tk.LEFT, padx=(5, 0))
        self.filtro_var.set("Todos")
        
        # Treeview para resultados
        tree_frame = ttk.Frame(right_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configurar Treeview
        columns = ('Archivo', 'Estado', 'Modificación', 'Última Fecha', 'Errores', 'Acción')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
        # Configurar columnas
        column_widths = {
            'Archivo': 250,
            'Estado': 100,
            'Modificación': 150,
            'Última Fecha': 150,
            'Errores': 80,
            'Acción': 150
        }
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=column_widths.get(col, 100))
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Bind eventos
        self.tree.bind('<Double-Button-1>', self.abrir_log_doble_click)
        self.tree.bind('<Button-3>', self.mostrar_menu_contextual)
        self.tree.bind('<ButtonRelease-1>', self.seleccionar_archivo)
        
        # Detalles del archivo seleccionado
        detalle_frame = ttk.LabelFrame(right_frame, text="📄 Detalles del archivo", padding="10")
        detalle_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Frame para información del archivo
        info_frame = ttk.Frame(detalle_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Botones de acción en detalles
        btn_frame_detalle = ttk.Frame(detalle_frame)
        btn_frame_detalle.pack(fill=tk.X, pady=(0, 10))
        
        self.btn_ver_log = ttk.Button(btn_frame_detalle, text="📖 Ver log completo", 
                                     command=self.ver_log_desde_detalle, state='disabled')
        self.btn_ver_log.pack(side=tk.LEFT, padx=(0, 10))
        
        self.btn_abrir_carpeta = ttk.Button(btn_frame_detalle, text="📂 Abrir carpeta", 
                                           command=self.abrir_carpeta_desde_detalle, state='disabled')
        self.btn_abrir_carpeta.pack(side=tk.LEFT)
        
        # Área de texto para detalles
        self.detalle_text = scrolledtext.ScrolledText(detalle_frame, height=6, wrap=tk.WORD)
        self.detalle_text.pack(fill=tk.BOTH, expand=True)
        
        # Menú contextual para el Treeview
        self.menu_contextual = tk.Menu(self.root, tearoff=0)
        self.menu_contextual.add_command(label="📖 Ver log completo", command=self.ver_log_completo)
        self.menu_contextual.add_command(label="📂 Abrir carpeta", command=self.abrir_carpeta)
        self.menu_contextual.add_command(label="📋 Copiar información", command=self.copiar_informacion)
        self.menu_contextual.add_separator()
        self.menu_contextual.add_command(label="🗑️ Eliminar de resultados", command=self.eliminar_resultado)
    
    def seleccionar_archivo(self, event):
        """Mostrar detalles del archivo seleccionado"""
        seleccion = self.tree.selection()
        if seleccion:
            item = seleccion[0]
            indice = self.tree.index(item)
            
            if indice < len(self.datos_archivos):
                resultado = self.datos_archivos[indice]
                self.mostrar_detalles_archivo(resultado)
                
                # Habilitar botones de acción
                self.btn_ver_log.config(state='normal')
                self.btn_abrir_carpeta.config(state='normal')
    
    def mostrar_detalles_archivo(self, resultado):
        """Mostrar detalles del archivo seleccionado"""
        self.detalle_text.delete(1.0, tk.END)
        
        texto = f"📄 ARCHIVO: {resultado['nombre']}\n"
        texto += f"📁 RUTA: {resultado['archivo']}\n"
        texto += f"📅 MODIFICACIÓN: {resultado['modificacion']}\n"
        texto += f"⏰ ÚLTIMA FECHA EN LOG: {resultado['ultima_fecha_log'] or 'No encontrada'}\n"
        texto += f"📊 ESTADO: {resultado['estado']}\n"
        texto += f"📏 TAMAÑO: {resultado['tamano']}\n"
        texto += f"🔢 LÍNEAS ANALIZADAS: {resultado.get('lineas_analizadas', 0)}\n"
        texto += f"❌ ERRORES ENCONTRADOS: {len(resultado['errores'])}\n"
        
        if resultado['errores']:
            texto += "\n📋 DETALLES DE ERRORES:\n"
            texto += "-" * 50 + "\n"
            for i, error in enumerate(resultado['errores'], 1):
                texto += f"\n{i}. Línea {error['linea']}:\n"
                texto += f"   Hora: {error['timestamp'] or 'Sin timestamp'}\n"
                texto += f"   Error: {error['error']}\n"
                texto += f"   Mensaje: {error['mensaje'][:100]}...\n"
        
        self.detalle_text.insert(1.0, texto)
    
    def abrir_log_doble_click(self, event):
        """Abrir log completo con doble clic"""
        seleccion = self.tree.selection()
        if seleccion:
            self.ver_log_completo_item(seleccion[0])
    
    def ver_log_completo_item(self, item):
        """Ver log completo desde un item del Treeview"""
        indice = self.tree.index(item)
        
        if indice < len(self.datos_archivos):
            resultado = self.datos_archivos[indice]
            archivo = resultado['archivo']
            
            if os.path.exists(archivo):
                self.abrir_visor_log(archivo, resultado['nombre'])
            else:
                messagebox.showerror("Error", f"El archivo no existe:\n{archivo}")
    
    def ver_log_desde_detalle(self):
        """Ver log desde el botón de detalles"""
        seleccion = self.tree.selection()
        if seleccion:
            self.ver_log_completo_item(seleccion[0])
    
    def abrir_carpeta_desde_detalle(self):
        """Abrir carpeta desde el botón de detalles"""
        seleccion = self.tree.selection()
        if seleccion:
            self.abrir_carpeta_seleccionada()
    
    def abrir_carpeta(self):
        """Abrir carpeta desde menú contextual"""
        seleccion = self.tree.selection()
        if seleccion:
            self.abrir_carpeta_seleccionada()
    
    def abrir_carpeta_seleccionada(self):
        """Abrir la carpeta del archivo seleccionado"""
        seleccion = self.tree.selection()
        if seleccion:
            item = seleccion[0]
            indice = self.tree.index(item)
            
            if indice < len(self.datos_archivos):
                resultado = self.datos_archivos[indice]
                archivo = resultado['archivo']
                directorio = os.path.dirname(archivo)
                
                if os.path.exists(directorio):
                    try:
                        # Abrir carpeta en explorador
                        if os.name == 'nt':  # Windows
                            os.startfile(directorio)
                        elif os.name == 'posix':  # Linux/Mac
                            subprocess.run(['xdg-open', directorio])
                    except Exception as e:
                        messagebox.showerror("Error", f"No se pudo abrir la carpeta:\n{str(e)}")
                else:
                    messagebox.showerror("Error", f"La carpeta no existe:\n{directorio}")
    
    def cargar_configuracion(self):
        """Cargar configuración desde archivo JSON"""
        config_default = {
            "log_paths": [],
            "file_patterns": ["*.log"],
            "error_patterns": [
                "Error", "Failure", "Failed", "Rejected", 
                "Timeout", "Disconnected", "Access denied",
                "Permission denied", "Authentication failed"
            ],
            "output_file": "errores_encontrados.json",
            "encoding": "utf-8"
        }
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.rutas = config.get('log_paths', [])
                config_default.update(config)
                return config_default
        except FileNotFoundError:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_default, f, indent=2, ensure_ascii=False)
            self.rutas = []
            return config_default
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar configuración: {e}")
            self.rutas = []
            return config_default
    
    def cargar_errores(self):
        """Cargar errores personalizados"""
        try:
            with open(self.errores_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.errores_conocidos = data.get('errores_conocidos', [])
        except FileNotFoundError:
            self.errores_conocidos = []
    
    def cargar_ultima_fecha(self):
        """Cargar última fecha de análisis por archivo"""
        try:
            with open(self.ultima_fecha_file, 'r', encoding='utf-8') as f:
                self.ultima_fecha_analisis = json.load(f)
        except FileNotFoundError:
            self.ultima_fecha_analisis = {}
    
    def guardar_configuracion(self):
        """Guardar configuración actual"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except:
            config = {}
        
        config['log_paths'] = self.rutas
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def agregar_ruta(self):
        """Agregar una nueva ruta a la lista"""
        ruta = filedialog.askdirectory(title="Seleccionar carpeta con logs")
        if ruta:
            ruta_normalizada = os.path.normpath(ruta)
            if ruta_normalizada not in self.rutas:
                self.rutas.append(ruta_normalizada)
                self.actualizar_lista_rutas()
                self.guardar_configuracion()
    
    def eliminar_ruta(self):
        """Eliminar la ruta seleccionada"""
        seleccion = self.rutas_listbox.curselection()
        if seleccion:
            indice = seleccion[0]
            self.rutas.pop(indice)
            self.actualizar_lista_rutas()
            self.guardar_configuracion()
    
    def explorar_ruta(self):
        """Abrir explorador en la ruta seleccionada"""
        seleccion = self.rutas_listbox.curselection()
        if seleccion:
            indice = seleccion[0]
            ruta = self.rutas[indice]
            if os.path.exists(ruta):
                try:
                    if os.name == 'nt':  # Windows
                        os.startfile(ruta)
                    elif os.name == 'posix':  # Linux/Mac
                        subprocess.run(['xdg-open', ruta])
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo abrir la carpeta:\n{str(e)}")
    
    def actualizar_lista_rutas(self):
        """Actualizar el ListBox con las rutas actuales"""
        self.rutas_listbox.delete(0, tk.END)
        for ruta in self.rutas:
            nombre_corto = os.path.basename(ruta) if os.path.basename(ruta) else ruta
            self.rutas_listbox.insert(tk.END, f"{nombre_corto} → {ruta}")
    
    def iniciar_analisis(self):
        """Iniciar análisis en un hilo separado"""
        if not self.rutas:
            messagebox.showwarning("Advertencia", "Agrega al menos una ruta para analizar")
            return
        
        if self.analisis_en_progreso:
            return
        
        self.analisis_en_progreso = True
        self.analizar_btn.config(state='disabled')
        self.limpiar_resultados()
        self.progress_var.set(0)
        
        thread = threading.Thread(target=self.ejecutar_analisis_thread)
        thread.daemon = True
        thread.start()
    
    def ejecutar_analisis_thread(self):
        """Ejecutar análisis en segundo plano"""
        try:
            resultados = self.realizar_analisis()
            self.mostrar_resultados(resultados)
        except Exception as e:
            self.mostrar_error(f"Error durante el análisis: {str(e)}")
        finally:
            self.analisis_en_progreso = False
            self.root.after(0, lambda: self.analizar_btn.config(state='normal'))
    
    def realizar_analisis(self):
        """Realizar el análisis de logs"""
        archivos_log = []
        
        # Buscar archivos en todas las rutas
        for ruta in self.rutas:
            if os.path.exists(ruta):
                for patron in ["*.log", "*.txt"]:
                    archivos = glob.glob(os.path.join(ruta, patron), recursive=True)
                    archivos_log.extend(archivos)
        
        if not archivos_log:
            self.root.after(0, lambda: self.mostrar_error("No se encontraron archivos .log"))
            return []
        
        self.root.after(0, lambda: self.actualizar_progreso(10, f"Encontrados {len(archivos_log)} archivos"))
        
        resultados = []
        archivos_procesados = 0
        
        for archivo in archivos_log:
            archivos_procesados += 1
            progreso = 10 + (archivos_procesados / len(archivos_log)) * 80
            
            self.root.after(0, lambda p=progreso, a=archivo: 
                          self.actualizar_progreso(p, f"Analizando: {os.path.basename(a)}"))
            
            resultado = self.analizar_archivo(archivo)
            resultados.append(resultado)
        
        return resultados
    
    def analizar_archivo(self, archivo_path):
        """Analizar un archivo de log específico"""
        resultado = {
            'archivo': archivo_path,
            'nombre': os.path.basename(archivo_path),
            'estado': 'Correcto',
            'modificacion': '',
            'ultima_fecha_log': None,
            'tamano': '',
            'errores': [],
            'detalles_errores': [],
            'lineas_analizadas': 0
        }
        
        try:
            # Obtener información del archivo
            mod_time = os.path.getmtime(archivo_path)
            resultado['modificacion'] = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
            
            # Obtener tamaño del archivo
            tamano_bytes = os.path.getsize(archivo_path)
            if tamano_bytes < 1024:
                resultado['tamano'] = f"{tamano_bytes} B"
            elif tamano_bytes < 1024 * 1024:
                resultado['tamano'] = f"{tamano_bytes/1024:.1f} KB"
            else:
                resultado['tamano'] = f"{tamano_bytes/(1024*1024):.1f} MB"
            
            with open(archivo_path, 'r', encoding='utf-8', errors='ignore') as f:
                lineas = f.readlines()
            
            if not lineas:
                return resultado
            
            # Determinar línea de inicio basado en configuración
            if self.fecha_var.get() == "ultima":
                linea_inicio = self.determinar_linea_inicio(archivo_path, lineas)
            else:
                linea_inicio = 0
            
            resultado['lineas_analizadas'] = len(lineas) - linea_inicio
            
            # Patrones de error combinados
            patrones_error = [
                "error", "failure", "failed", "rejected", "timeout",
                "disconnected", "access denied", "permission denied",
                "authentication failed", "connection failed"
            ] + [e.lower() for e in self.errores_conocidos]
            
            # Analizar líneas
            errores_encontrados = []
            for i in range(linea_inicio, len(lineas)):
                linea = lineas[i].strip()
                
                # Extraer timestamp si existe
                timestamp = self.extraer_timestamp(linea)
                if timestamp and not resultado['ultima_fecha_log']:
                    resultado['ultima_fecha_log'] = timestamp
                
                # Buscar errores
                for patron in patrones_error:
                    if patron in linea.lower():
                        error_info = {
                            'linea': i + 1,
                            'timestamp': timestamp,
                            'error': patron,
                            'mensaje': linea[:200],
                            'fecha_deteccion': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        errores_encontrados.append(error_info)
                        break
            
            resultado['errores'] = errores_encontrados
            resultado['detalles_errores'] = [f"Línea {e['linea']}: {e['mensaje']}" for e in errores_encontrados]
            
            if errores_encontrados:
                resultado['estado'] = 'Error'
                resultado['conteo_errores'] = len(errores_encontrados)
            else:
                resultado['estado'] = 'Correcto'
                resultado['conteo_errores'] = 0
            
            # Actualizar última fecha de análisis
            self.actualizar_ultima_fecha_archivo(archivo_path, lineas)
            
        except Exception as e:
            resultado['estado'] = 'Error de análisis'
            resultado['detalles_errores'] = [f"Error al analizar: {str(e)}"]
        
        return resultado
    
    def determinar_linea_inicio(self, archivo_path, lineas):
        """Determinar desde qué línea comenzar el análisis"""
        # Buscar la última fecha en el archivo (últimas 100 líneas para eficiencia)
        ultima_fecha = None
        ultima_linea_con_fecha = 0
        
        for i in range(max(0, len(lineas) - 100), len(lineas)):
            fecha = self.extraer_timestamp(lineas[i])
            if fecha:
                ultima_fecha = fecha
                ultima_linea_con_fecha = i
        
        if not ultima_fecha:
            return 0
        
        # Buscar todas las líneas con la última fecha
        linea_inicio = ultima_linea_con_fecha
        for i in range(ultima_linea_con_fecha, 0, -1):
            fecha_linea = self.extraer_timestamp(lineas[i])
            if fecha_linea and fecha_linea == ultima_fecha:
                linea_inicio = i
            else:
                break
        
        return linea_inicio
    
    def extraer_timestamp(self, linea):
        """Extraer timestamp de una línea de log"""
        patrones = [
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})',
            r'(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})',
            r'(\d{2}:\d{2}:\d{2}\.\d{3})',
            r'(\d{2}:\d{2}:\d{2})',
            r'(\[.*?\d{2}:\d{2}:\d{2}.*?\])',
        ]
        
        for patron in patrones:
            match = re.search(patron, linea)
            if match:
                return match.group(1)
        
        return None
    
    def actualizar_ultima_fecha_archivo(self, archivo_path, lineas):
        """Actualizar la última fecha conocida para un archivo"""
        # Buscar la última fecha en las últimas líneas
        for linea in reversed(lineas[-50:]):
            fecha_str = self.extraer_timestamp(linea)
            if fecha_str:
                fecha_key = os.path.basename(archivo_path)
                self.ultima_fecha_analisis[fecha_key] = fecha_str
                # Guardar en archivo
                with open(self.ultima_fecha_file, 'w', encoding='utf-8') as f:
                    json.dump(self.ultima_fecha_analisis, f, indent=2, ensure_ascii=False)
                break
    
    def actualizar_progreso(self, valor, mensaje):
        """Actualizar barra de progreso y mensaje"""
        self.progress_var.set(valor)
        self.stats_label.config(text=mensaje)
    
    def mostrar_resultados(self, resultados):
        """Mostrar resultados en el Treeview"""
        self.root.after(0, lambda: self.actualizar_progreso(100, "Análisis completado"))
        
        self.datos_archivos = resultados
        
        if not resultados:
            self.root.after(0, lambda: messagebox.showinfo("Información", "No se encontraron archivos para analizar"))
            return
        
        # Limpiar treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Clasificar por fecha de modificación
        hoy = datetime.now().date()
        ayer = hoy - timedelta(days=1)
        
        for resultado in resultados:
            try:
                fecha_mod = datetime.strptime(resultado['modificacion'].split()[0], "%Y-%m-%d").date()
                if fecha_mod == hoy:
                    grupo = "Hoy"
                elif fecha_mod == ayer:
                    grupo = "Ayer"
                else:
                    grupo = "Antiguos"
            except:
                grupo = "Desconocido"
            
            # Determinar color según estado
            estado = resultado['estado']
            if estado == 'Correcto':
                estado_text = "✅ Correcto"
                color = 'green'
            elif estado == 'Error':
                estado_text = "❌ Error"
                color = 'red'
            else:
                estado_text = "⚠️ Error análisis"
                color = 'orange'
            
            # Insertar en treeview
            valores = (
                resultado['nombre'],
                estado_text,
                resultado['modificacion'],
                resultado['ultima_fecha_log'] or 'No encontrada',
                len(resultado['errores']),
                "Doble clic para abrir"
            )
            
            item_id = self.tree.insert('', tk.END, values=valores, tags=(estado, grupo))
        
        # Configurar tags para colores
        self.tree.tag_configure('Correcto', foreground='green')
        self.tree.tag_configure('Error', foreground='red')
        self.tree.tag_configure('Error de análisis', foreground='orange')
        
        # Actualizar estadísticas
        total_archivos = len(resultados)
        archivos_con_error = sum(1 for r in resultados if r['estado'] == 'Error')
        total_errores = sum(len(r['errores']) for r in resultados)
        
        self.stats_label.config(
            text=f"📊 Archivos: {total_archivos} | Con errores: {archivos_con_error} | Total errores: {total_errores}"
        )
        
        # Guardar resultados en JSON
        self.guardar_resultados_json(resultados)
    
    def mostrar_error(self, mensaje):
        """Mostrar mensaje de error"""
        messagebox.showerror("Error", mensaje)
    
    def guardar_resultados_json(self, resultados):
        """Guardar resultados en archivo JSON"""
        try:
            datos_guardar = []
            for resultado in resultados:
                datos_guardar.append({
                    'archivo': resultado['archivo'],
                    'nombre': resultado['nombre'],
                    'estado': resultado['estado'],
                    'modificacion': resultado['modificacion'],
                    'ultima_fecha_log': resultado['ultima_fecha_log'],
                    'tamano': resultado['tamano'],
                    'conteo_errores': len(resultado['errores']),
                    'errores': resultado['errores']
                })
            
            with open('resultados_analisis.json', 'w', encoding='utf-8') as f:
                json.dump(datos_guardar, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error al guardar JSON: {e}")
    
    def mostrar_menu_contextual(self, event):
        """Mostrar menú contextual en el Treeview"""
        seleccion = self.tree.identify_row(event.y)
        if seleccion:
            self.tree.selection_set(seleccion)
            self.menu_contextual.post(event.x_root, event.y_root)
    
    def ver_log_completo(self):
        """Abrir el archivo de log completo desde menú contextual"""
        seleccion = self.tree.selection()
        if seleccion:
            self.ver_log_completo_item(seleccion[0])
    
    def abrir_visor_log(self, archivo_path, nombre_archivo):
        """Abrir visor interno de logs"""
        # Verificar si ya hay un visor abierto para este archivo
        if archivo_path in self.visores_abiertos:
            try:
                ventana = self.visores_abiertos[archivo_path]
                ventana.deiconify()
                ventana.lift()
                ventana.focus_force()
                return
            except:
                del self.visores_abiertos[archivo_path]
        
        # Crear nueva ventana
        visor_window = tk.Toplevel(self.root)
        visor_window.title(f"📖 Visor de log: {nombre_archivo}")
        visor_window.geometry("1000x700")
        
        # Guardar referencia
        self.visores_abiertos[archivo_path] = visor_window
        
        def on_closing():
            if archivo_path in self.visores_abiertos:
                del self.visores_abiertos[archivo_path]
            visor_window.destroy()
        
        visor_window.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Frame principal
        main_frame = ttk.Frame(visor_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Barra de herramientas
        toolbar_frame = ttk.Frame(main_frame)
        toolbar_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(toolbar_frame, text=f"Archivo: {nombre_archivo}", 
                 font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        
        # Frame para búsqueda
        search_frame = ttk.Frame(toolbar_frame)
        search_frame.pack(side=tk.RIGHT)
        
        ttk.Label(search_frame, text="Buscar:").pack(side=tk.LEFT, padx=(0, 5))
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=25)
        search_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        def buscar_texto():
            texto = search_var.get().strip()
            if texto:
                self.buscar_en_texto_visor(text_area, texto)
        
        def buscar_siguiente():
            texto = search_var.get().strip()
            if texto:
                self.buscar_siguiente_visor(text_area, texto)
        
        ttk.Button(search_frame, text="🔍 Buscar", 
                  command=buscar_texto).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(search_frame, text="▶ Siguiente", 
                  command=buscar_siguiente).pack(side=tk.LEFT)
        
        # Área de texto con scroll
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        text_area = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, 
                                             font=('Consolas', 9), undo=True)
        text_area.pack(fill=tk.BOTH, expand=True)
        
        # Configurar tags para resaltado
        text_area.tag_config('resaltado', background='yellow', foreground='black')
        text_area.tag_config('seleccionado', background='orange', foreground='black')
        
        # Barra de estado
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        status_label = ttk.Label(status_frame, text="Cargando...")
        status_label.pack(side=tk.LEFT)
        
        # Botones de acción
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="📋 Copiar todo", 
                  command=lambda: self.copiar_texto_visor(text_area, status_label)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="❌ Cerrar", 
                  command=on_closing).pack(side=tk.RIGHT, padx=5)
        
        # Cargar contenido del archivo
        self.cargar_log_en_visor(archivo_path, text_area, status_label)
        
        # Enfocar en el campo de búsqueda
        search_entry.focus_set()
    
    def cargar_log_en_visor(self, archivo_path, text_widget, status_label):
        """Cargar contenido del log en el visor"""
        text_widget.delete(1.0, tk.END)
        
        try:
            with open(archivo_path, 'r', encoding='utf-8', errors='ignore') as f:
                contenido = f.read()
                text_widget.insert(1.0, contenido)
            
            # Contar líneas
            num_lineas = contenido.count('\n') + 1
            tamano = os.path.getsize(archivo_path)
            
            if tamano < 1024:
                tamano_str = f"{tamano} B"
            elif tamano < 1024 * 1024:
                tamano_str = f"{tamano/1024:.1f} KB"
            else:
                tamano_str = f"{tamano/(1024*1024):.1f} MB"
            
            status_label.config(
                text=f"Líneas: {num_lineas:,} | Tamaño: {tamano_str} | Codificación: UTF-8"
            )
            
        except Exception as e:
            text_widget.insert(1.0, f"❌ ERROR AL LEER EL ARCHIVO:\n{str(e)}\n\n")
            text_widget.insert(tk.END, f"Ruta: {archivo_path}")
            status_label.config(text=f"Error: {str(e)}")
    
    def buscar_en_texto_visor(self, text_widget, texto):
        """Buscar texto en el visor y resaltarlo"""
        text_widget.tag_remove('resaltado', '1.0', tk.END)
        text_widget.tag_remove('seleccionado', '1.0', tk.END)
        
        if not texto:
            return
        
        contador = 0
        start_pos = '1.0'
        
        while True:
            start_pos = text_widget.search(texto, start_pos, stopindex=tk.END, 
                                          nocase=True, regexp=False)
            if not start_pos:
                break
            
            end_pos = f"{start_pos}+{len(texto)}c"
            text_widget.tag_add('resaltado', start_pos, end_pos)
            start_pos = end_pos
            contador += 1
        
        if contador > 0:
            primera = text_widget.search(texto, '1.0', stopindex=tk.END, 
                                       nocase=True, regexp=False)
            if primera:
                end_pos = f"{primera}+{len(texto)}c"
                text_widget.tag_add('seleccionado', primera, end_pos)
                text_widget.see(primera)
    
    def buscar_siguiente_visor(self, text_widget, texto):
        """Buscar siguiente ocurrencia del texto"""
        if not texto:
            return
        
        current_pos = text_widget.index(tk.INSERT)
        start_pos = text_widget.search(texto, current_pos, stopindex=tk.END, 
                                      nocase=True, regexp=False)
        
        if not start_pos:
            start_pos = text_widget.search(texto, '1.0', stopindex=tk.END, 
                                          nocase=True, regexp=False)
        
        if start_pos:
            text_widget.tag_remove('seleccionado', '1.0', tk.END)
            end_pos = f"{start_pos}+{len(texto)}c"
            text_widget.tag_add('seleccionado', start_pos, end_pos)
            text_widget.see(start_pos)
            text_widget.mark_set(tk.INSERT, end_pos)
    
    def copiar_texto_visor(self, text_widget, status_label):
        """Copiar texto del visor al portapapeles"""
        texto = text_widget.get(1.0, tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(texto)
        status_label.config(text="Texto copiado al portapapeles")
    
    def copiar_informacion(self):
        """Copiar información del archivo seleccionado"""
        seleccion = self.tree.selection()
        if seleccion:
            item = seleccion[0]
            valores = self.tree.item(item, 'values')
            texto = f"Archivo: {valores[0]}\nEstado: {valores[1]}\nModificación: {valores[2]}\nÚltima fecha: {valores[3]}\nErrores: {valores[4]}"
            
            self.root.clipboard_clear()
            self.root.clipboard_append(texto)
            messagebox.showinfo("Información", "Datos copiados al portapapeles")
    
    def eliminar_resultado(self):
        """Eliminar resultado seleccionado del Treeview"""
        seleccion = self.tree.selection()
        if seleccion:
            item = seleccion[0]
            indice = self.tree.index(item)
            
            if indice < len(self.datos_archivos):
                self.datos_archivos.pop(indice)
                self.tree.delete(item)
                self.detalle_text.delete(1.0, tk.END)
                self.btn_ver_log.config(state='disabled')
                self.btn_abrir_carpeta.config(state='disabled')
    
    def aplicar_filtro(self, *args):
        """Aplicar filtro a los resultados"""
        filtro = self.filtro_var.get()
        
        for item in self.tree.get_children():
            tags = self.tree.item(item, 'tags')
            mostrar = True
            
            if filtro == "Correcto" and "Correcto" not in tags:
                mostrar = False
            elif filtro == "Error" and "Error" not in tags:
                mostrar = False
            elif filtro == "Hoy" and "Hoy" not in tags:
                mostrar = False
            elif filtro == "Ayer" and "Ayer" not in tags:
                mostrar = False
            elif filtro == "Antiguos" and "Antiguos" not in tags:
                mostrar = False
            
            if mostrar:
                self.tree.attach(item, '', 'end')
            else:
                self.tree.detach(item)
    
    def busqueda_global(self):
        """Buscar texto en todos los logs"""
        if not self.datos_archivos:
            messagebox.showwarning("Advertencia", "Primero ejecuta un análisis")
            return
        
        buscar_window = tk.Toplevel(self.root)
        buscar_window.title("Buscar texto en logs")
        buscar_window.geometry("600x500")
        
        ttk.Label(buscar_window, text="🔍 BUSCAR TEXTO EN TODOS LOS LOGS", 
                 font=('Arial', 11, 'bold')).pack(pady=(10, 5))
        
        # Frame para entrada
        entrada_frame = ttk.Frame(buscar_window)
        entrada_frame.pack(pady=10, padx=20, fill=tk.X)
        
        ttk.Label(entrada_frame, text="Texto a buscar:").pack(anchor=tk.W)
        self.buscar_texto_var = tk.StringVar()
        buscar_entry = ttk.Entry(entrada_frame, textvariable=self.buscar_texto_var, width=40)
        buscar_entry.pack(fill=tk.X, pady=(5, 10))
        
        # Opciones de búsqueda
        opciones_frame = ttk.Frame(buscar_window)
        opciones_frame.pack(pady=10, padx=20, fill=tk.X)
        
        self.buscar_cs = tk.BooleanVar(value=False)
        self.buscar_regex = tk.BooleanVar(value=False)
        
        ttk.Checkbutton(opciones_frame, text="Diferenciar mayúsculas/minúsculas", 
                       variable=self.buscar_cs).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(opciones_frame, text="Usar expresiones regulares", 
                       variable=self.buscar_regex).pack(anchor=tk.W, pady=2)
        
        # Resultados
        ttk.Label(buscar_window, text="Resultados:").pack(anchor=tk.W, padx=20, pady=(10, 5))
        resultados_frame = ttk.Frame(buscar_window)
        resultados_frame.pack(padx=20, pady=(0, 10), fill=tk.BOTH, expand=True)
        
        resultados_text = scrolledtext.ScrolledText(resultados_frame, wrap=tk.WORD)
        resultados_text.pack(fill=tk.BOTH, expand=True)
        
        def ejecutar_busqueda():
            texto = self.buscar_texto_var.get().strip()
            if not texto:
                messagebox.showwarning("Advertencia", "Ingresa un texto para buscar")
                return
            
            resultados_text.delete(1.0, tk.END)
            resultados_text.insert(1.0, f"Buscando '{texto}' en {len(self.datos_archivos)} archivos...\n\n")
            buscar_window.update()
            
            total_encontrados = 0
            archivos_con_resultados = 0
            
            for resultado in self.datos_archivos:
                try:
                    with open(resultado['archivo'], 'r', encoding='utf-8', errors='ignore') as f:
                        lineas = f.readlines()
                    
                    coincidencias = []
                    for i, linea in enumerate(lineas, 1):
                        buscar_texto = texto if self.buscar_cs.get() else texto.lower()
                        linea_buscar = linea if self.buscar_cs.get() else linea.lower()
                        
                        if self.buscar_regex.get():
                            try:
                                import re
                                flags = 0 if self.buscar_cs.get() else re.IGNORECASE
                                if re.search(texto, linea, flags):
                                    coincidencias.append(i)
                            except:
                                resultados_text.insert(tk.END, f"❌ Expresión regular inválida en {resultado['nombre']}\n")
                                break
                        else:
                            if buscar_texto in linea_buscar:
                                coincidencias.append(i)
                    
                    if coincidencias:
                        resultados_text.insert(tk.END, 
                            f"✅ {resultado['nombre']}: {len(coincidencias)} ocurrencias (líneas: {', '.join(map(str, coincidencias[:10]))}{'...' if len(coincidencias) > 10 else ''})\n")
                        archivos_con_resultados += 1
                        total_encontrados += len(coincidencias)
                    else:
                        resultados_text.insert(tk.END, f"❌ {resultado['nombre']}: No encontrado\n")
                        
                except Exception as e:
                    resultados_text.insert(tk.END, f"❌ Error en {resultado['nombre']}: {str(e)}\n")
            
            resultados_text.insert(tk.END, f"\n{'='*50}\n")
            resultados_text.insert(tk.END, 
                f"Búsqueda completada.\n"
                f"Total archivos: {len(self.datos_archivos)}\n"
                f"Archivos con coincidencias: {archivos_con_resultados}\n"
                f"Total coincidencias: {total_encontrados}\n")
        
        # Botones
        btn_frame = ttk.Frame(buscar_window)
        btn_frame.pack(pady=(0, 10), padx=20, fill=tk.X)
        
        ttk.Button(btn_frame, text="🔍 Buscar", 
                  command=ejecutar_busqueda).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="📋 Copiar resultados", 
                  command=lambda: self.copiar_resultados_busqueda(resultados_text)).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="❌ Cerrar", 
                  command=buscar_window.destroy).pack(side=tk.RIGHT)
        
        # Enfocar en el campo de búsqueda
        buscar_entry.focus_set()
        buscar_entry.bind('<Return>', lambda e: ejecutar_busqueda())
    
    def copiar_resultados_busqueda(self, text_widget):
        """Copiar resultados de búsqueda al portapapeles"""
        texto = text_widget.get(1.0, tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(texto)
        messagebox.showinfo("Información", "Resultados copiados al portapapeles")
    
    def exportar_csv(self):
        """Exportar resultados a CSV"""
        if not self.datos_archivos:
            messagebox.showwarning("Advertencia", "No hay datos para exportar")
            return
        
        archivo = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")]
        )
        
        if archivo:
            try:
                with open(archivo, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f, delimiter=';')
                    
                    # Escribir encabezado
                    writer.writerow([
                        'Archivo', 'Ruta', 'Estado', 'Modificación', 
                        'Última fecha log', 'Tamaño', 'Errores encontrados'
                    ])
                    
                    # Escribir datos
                    for resultado in self.datos_archivos:
                        writer.writerow([
                            resultado['nombre'],
                            resultado['archivo'],
                            resultado['estado'],
                            resultado['modificacion'],
                            resultado['ultima_fecha_log'],
                            resultado['tamano'],
                            len(resultado['errores'])
                        ])
                
                messagebox.showinfo("Éxito", f"CSV exportado a:\n{archivo}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo exportar: {str(e)}")
    
    def generar_reporte_personalizado(self):
        """Generar reporte personalizado con campos seleccionables"""
        if not self.datos_archivos:
            messagebox.showwarning("Advertencia", "No hay datos para generar reporte")
            return
        
        # Crear ventana de selección de campos
        reporte_window = tk.Toplevel(self.root)
        reporte_window.title("Generar Reporte Personalizado")
        reporte_window.geometry("400x500")
        
        ttk.Label(reporte_window, text="Selecciona los campos a incluir:", 
                 font=('Arial', 10, 'bold')).pack(pady=10)
        
        # Variables para checkboxes
        campos = {
            'archivo': tk.BooleanVar(value=True),
            'ruta': tk.BooleanVar(value=False),
            'estado': tk.BooleanVar(value=True),
            'modificacion': tk.BooleanVar(value=True),
            'ultima_fecha': tk.BooleanVar(value=True),
            'tamano': tk.BooleanVar(value=True),
            'conteo_errores': tk.BooleanVar(value=True),
            'detalle_errores': tk.BooleanVar(value=True),
            'linea_error': tk.BooleanVar(value=True),
            'timestamp_error': tk.BooleanVar(value=True)
        }
        
        # Checkboxes
        for texto, var in [
            ("Nombre del archivo", 'archivo'),
            ("Ruta completa", 'ruta'),
            ("Estado (Correcto/Error)", 'estado'),
            ("Fecha de modificación", 'modificacion'),
            ("Última fecha en log", 'ultima_fecha'),
            ("Tamaño del archivo", 'tamano'),
            ("Número de errores", 'conteo_errores'),
            ("Detalles del error", 'detalle_errores'),
            ("Línea del error", 'linea_error'),
            ("Timestamp del error", 'timestamp_error')
        ]:
            cb = ttk.Checkbutton(reporte_window, text=texto, variable=campos[var])
            cb.pack(anchor=tk.W, padx=20, pady=2)
        
        # Frame para botones
        btn_frame = ttk.Frame(reporte_window)
        btn_frame.pack(pady=20)
        
        def generar():
            campos_seleccionados = [k for k, v in campos.items() if v.get()]
            
            if not campos_seleccionados:
                messagebox.showwarning("Advertencia", "Selecciona al menos un campo")
                return
            
            archivo = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Archivos de texto", "*.txt"), ("Archivos CSV", "*.csv")]
            )
            
            if archivo:
                self.crear_reporte(archivo, campos_seleccionados)
                reporte_window.destroy()
        
        ttk.Button(btn_frame, text="📄 Generar Reporte", 
                  command=generar).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="❌ Cancelar", 
                  command=reporte_window.destroy).pack(side=tk.RIGHT, padx=5)
    
    def crear_reporte(self, archivo, campos):
        """Crear archivo de reporte con campos seleccionados"""
        try:
            with open(archivo, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("REPORTE DE ANÁLISIS DE LOGS WINSCP\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total archivos analizados: {len(self.datos_archivos)}\n\n")
                
                for i, resultado in enumerate(self.datos_archivos, 1):
                    f.write(f"\n{'=' * 60}\n")
                    f.write(f"ARCHIVO {i}: {resultado['nombre']}\n")
                    f.write(f"{'=' * 60}\n\n")
                    
                    if 'archivo' in campos:
                        f.write(f"Nombre: {resultado['nombre']}\n")
                    if 'ruta' in campos:
                        f.write(f"Ruta: {resultado['archivo']}\n")
                    if 'estado' in campos:
                        f.write(f"Estado: {resultado['estado']}\n")
                    if 'modificacion' in campos:
                        f.write(f"Última modificación: {resultado['modificacion']}\n")
                    if 'ultima_fecha' in campos:
                        f.write(f"Última fecha en log: {resultado['ultima_fecha_log'] or 'No encontrada'}\n")
                    if 'tamano' in campos:
                        f.write(f"Tamaño: {resultado['tamano']}\n")
                    if 'conteo_errores' in campos:
                        f.write(f"Errores encontrados: {len(resultado['errores'])}\n")
                    
                    if resultado['errores'] and ('detalle_errores' in campos or 'linea_error' in campos or 'timestamp_error' in campos):
                        f.write("\n📋 DETALLES DE ERRORES:\n")
                        for j, error in enumerate(resultado['errores'], 1):
                            linea = f"{j}. "
                            if 'linea_error' in campos:
                                linea += f"Línea {error['linea']} | "
                            if 'timestamp_error' in campos:
                                linea += f"Hora: {error['timestamp'] or 'Sin timestamp'} | "
                            if 'detalle_errores' in campos:
                                linea += f"Mensaje: {error['mensaje']}"
                            f.write(linea + "\n")
                    
                    f.write("\n")
            
            messagebox.showinfo("Éxito", f"Reporte generado en:\n{archivo}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el reporte: {str(e)}")
    
    def limpiar_resultados(self):
        """Limpiar todos los resultados"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.detalle_text.delete(1.0, tk.END)
        self.datos_archivos = []
        self.btn_ver_log.config(state='disabled')
        self.btn_abrir_carpeta.config(state='disabled')
    
    def salir(self):
        """Salir del programa"""
        if messagebox.askyesno("Salir", "¿Estás seguro de que quieres salir?"):
            self.root.quit()

def main():
    """Función principal"""
    root = tk.Tk()
    app = WinSCPLogAnalyzerGUI(root)
    
    # Centrar ventana
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    root.mainloop()

if __name__ == "__main__":
    main()