"""
Script para empaquetar el Monitor de Archivos como .exe con icono personalizado
Ejecutar: python build_exe.py
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def limpiar_archivos_previos():
    """Limpiar builds anteriores"""
    carpetas_limpiar = ['build', 'dist', '__pycache__']
    archivos_limpiar = ['*.spec']
    
    print("🧹 Limpiando archivos previos...")
    
    for carpeta in carpetas_limpiar:
        if os.path.exists(carpeta):
            shutil.rmtree(carpeta)
            print(f"  ✓ Eliminada carpeta: {carpeta}")
    
    for patron in archivos_limpiar:
        for archivo in Path('.').glob(patron):
            archivo.unlink()
            print(f"  ✓ Eliminado archivo: {archivo}")

def obtener_nombre_script():
    """Obtener el nombre del script principal"""
    # Buscar el script principal (el que contiene la clase ContadorArchivosApp)
    for archivo in Path('.').glob('*.py'):
        # Excluir los scripts de build (nombres comunes)
        nombre_excluir = ['build_exe', 'build_exe_v4', 'setup', 'installer']
        if archivo.stem in nombre_excluir:
            continue
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
                if 'class ContadorArchivosApp' in contenido:
                    return archivo.stem
        except:
            continue
    return None

def crear_icono():
    """Verificar y preparar el icono para el ejecutable"""
    # Buscar el icono en la carpeta icons
    icono_paths = [
        Path('icons') / 'app_icon.ico',
        Path('icons') / 'app_icon.png',
        Path('app_icon.ico'),
        Path('icon.ico'),
        Path('icon.png')
    ]
    
    for icono_path in icono_paths:
        if icono_path.exists():
            print(f"  ✓ Icono encontrado: {icono_path}")
            return str(icono_path)
    
    print("  ⚠ No se encontró ningún icono (.ico o .png)")
    print("    Buscado en: icons/app_icon.ico, app_icon.ico, icon.ico")
    return None

def construir_ejecutable(nombre_script, icono_path):
    """Construir el ejecutable con PyInstaller"""
    
    # Configuración de PyInstaller
    config = {
        'onefile': True,  # Un solo archivo .exe
        'windowed': True,  # Sin consola (aplicación GUI)
        'name': 'MonitorArchivos',  # Nombre del ejecutable
        'icon': icono_path,  # Ruta al icono
        'hidden_imports': [
            'PyQt5.QtCore',
            'PyQt5.QtGui',
            'PyQt5.QtWidgets',
            'json',
            'os',
            'sys',
            'threading',
            'time',
            'subprocess',
            'shutil',
            'pathlib',
            'datetime'
        ],
        'datas': [],  # Datos adicionales
        'excludes': ['tkinter', 'matplotlib', 'numpy', 'pandas'],  # Excluir librerías no necesarias
    }
    
    # Construir comando
    cmd = [
        'pyinstaller',
        '--onefile' if config['onefile'] else '--onedir',
        '--windowed' if config['windowed'] else '--console',
        f'--name={config["name"]}',
        '--clean',  # Limpiar caché
        '--noconfirm',  # Sobrescribir sin preguntar
    ]
    
    # Añadir icono si existe
    if config['icon']:
        cmd.append(f'--icon={config["icon"]}')
        print(f"  ✓ Usando icono: {config['icon']}")
    
    # Añadir imports ocultos
    for imp in config['hidden_imports']:
        cmd.append(f'--hidden-import={imp}')
    
    # Añadir excludes
    for excl in config['excludes']:
        cmd.append(f'--exclude-module={excl}')
    
    # Añadir el script principal
    cmd.append(f'{nombre_script}.py')
    
    print(f"\n🚀 Construyendo ejecutable...")
    print(f"Comando: pyinstaller {' '.join(cmd[1:])}\n")
    
    # Ejecutar PyInstaller
    try:
        # Usar subprocess para capturar la salida
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(result.stdout)
            return True
        else:
            print("❌ Error en la construcción:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Excepción durante la construcción: {e}")
        return False

def crear_accesos_directos():
    """Crear accesos directos (Windows)"""
    if sys.platform != 'win32':
        return
    
    print("\n📌 Creando accesos directos...")
    
    exe_path = Path('dist') / 'MonitorArchivos.exe'
    if not exe_path.exists():
        print("  ✗ No se encontró el ejecutable")
        return
    
    try:
        import winshell
        from win32com.client import Dispatch
        
        # Acceso directo en el escritorio
        desktop = winshell.desktop()
        shortcut_path = Path(desktop) / 'MonitorArchivos.lnk'
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(str(shortcut_path))
        shortcut.Targetpath = str(exe_path.absolute())
        shortcut.WorkingDirectory = str(exe_path.parent.absolute())
        shortcut.IconLocation = str(exe_path.absolute())
        shortcut.save()
        
        print(f"  ✓ Acceso directo creado en: {shortcut_path}")
    except ImportError:
        print("  ⚠ No se pudo crear acceso directo (requiere pywin32 y winshell)")
        print("    Instalar con: pip install pywin32 winshell")
    except Exception as e:
        print(f"  ⚠ Error creando acceso directo: {e}")

def crear_archivo_batch():
    """Crear archivo batch para ejecutar el .exe"""
    batch_content = '''@echo off
title Monitor de Archivos
echo ========================================
echo    MONITOR DE ARCHIVOS
echo ========================================
echo.
echo Iniciando la aplicacion...
echo.
start "" "%~dp0dist\\MonitorArchivos.exe"
echo.
echo Aplicacion iniciada!
echo.
echo Puede cerrar esta ventana
echo.
timeout /t 3 > nul
'''
    
    with open('iniciar_monitor.bat', 'w', encoding='utf-8') as f:
        f.write(batch_content)
    
    print("  ✓ Archivo 'iniciar_monitor.bat' creado")

def crear_version_portable():
    """Crear una versión portable (carpeta con todos los archivos)"""
    print("\n📦 Creando version portable...")
    
    portable_dir = Path('MonitorArchivos_Portable')
    if portable_dir.exists():
        shutil.rmtree(portable_dir)
    
    portable_dir.mkdir()
    
    # Copiar el ejecutable
    exe_source = Path('dist') / 'MonitorArchivos.exe'
    exe_dest = portable_dir / 'MonitorArchivos.exe'
    if exe_source.exists():
        shutil.copy2(exe_source, exe_dest)
        print(f"  ✓ Ejecutable copiado")
    
    # Copiar icono si existe
    icono_source = Path('icons') / 'app_icon.ico'
    if icono_source.exists():
        icono_dest = portable_dir / 'app_icon.ico'
        shutil.copy2(icono_source, icono_dest)
        print(f"  ✓ Icono copiado")
    
    # Crear carpeta para configuración
    config_dir = portable_dir / 'config'
    config_dir.mkdir()
    
    # Crear archivo de ejecución rápida
    run_bat_content = '''@echo off
title Monitor de Archivos
echo Iniciando Monitor de Archivos...
start "" "MonitorArchivos.exe"
exit
'''
    
    with open(portable_dir / 'Iniciar.bat', 'w', encoding='utf-8') as f:
        f.write(run_bat_content)
    
    # Crear README
    readme_content = '''Monitor de Archivos - Version Portable
=====================================

📁 Estructura:
- MonitorArchivos.exe : Ejecutable principal
- Iniciar.bat         : Inicio rapido de la aplicacion
- config/            : Carpeta donde se guardaran los archivos de configuracion
- app_icon.ico       : Icono de la aplicacion

🔧 Instrucciones:
1. Ejecuta "Iniciar.bat" o directamente "MonitorArchivos.exe"
2. La configuracion se guardara automaticamente en la carpeta config/

💡 NOTAS IMPORTANTES:
- La primera ejecucion puede ser lenta mientras Windows analiza el archivo
- Si Windows Defender bloquea el archivo, es una falsa alarma comun
- Para evitar bloqueos, agrega una excepcion en Windows Defender
- Todos los archivos de configuracion se guardan dentro de esta carpeta
- Puedes mover esta carpeta a cualquier lugar del sistema
- Para desinstalar, simplemente elimina esta carpeta

⚙️ Requisitos:
- Windows 7 o superior
- No requiere instalacion adicional
- No requiere Python instalado

📞 Soporte:
Si encuentras algun problema, verifica que:
- Tengas permisos de escritura en la carpeta
- El antivirus no este bloqueando la aplicacion
- Las rutas que monitoreas sean accesibles
'''
    
    with open(portable_dir / 'README.txt', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"  ✓ Version portable creada en: {portable_dir}")

def crear_script_instalacion():
    """Crear script de instalación simple"""
    install_bat_content = '''@echo off
echo ========================================
echo    INSTALADOR DE MONITOR DE ARCHIVOS
echo ========================================
echo.
echo Instalando Monitor de Archivos...
echo.

:: Crear carpeta de programas
if not exist "%ProgramFiles%\\MonitorArchivos" (
    mkdir "%ProgramFiles%\\MonitorArchivos"
    echo Carpeta creada en ProgramFiles
)

:: Copiar archivos
xcopy /E /I "MonitorArchivos_Portable" "%ProgramFiles%\\MonitorArchivos"

:: Crear acceso directo en escritorio
set SCRIPT="%TEMP%\\crear_acceso.vbs"
echo Set oShell = CreateObject("WScript.Shell") > %SCRIPT%
echo strDesktop = oShell.SpecialFolders("Desktop") >> %SCRIPT%
echo Set oLink = oShell.CreateShortcut(strDesktop ^& "\\MonitorArchivos.lnk") >> %SCRIPT%
echo oLink.TargetPath = "%ProgramFiles%\\MonitorArchivos\\MonitorArchivos.exe" >> %SCRIPT%
echo oLink.WorkingDirectory = "%ProgramFiles%\\MonitorArchivos" >> %SCRIPT%
echo oLink.Save >> %SCRIPT%
cscript /nologo %SCRIPT%
del %SCRIPT%

echo.
echo ========================================
echo    INSTALACION COMPLETADA
echo ========================================
echo.
echo El Monitor de Archivos ha sido instalado
echo Puedes ejecutarlo desde el acceso directo en el escritorio
echo.
pause
'''
    
    with open('Instalar.bat', 'w', encoding='utf-8') as f:
        f.write(install_bat_content)
    
    print("  ✓ Script de instalacion 'Instalar.bat' creado")

def verificar_requisitos():
    """Verificar que todas las dependencias estén instaladas"""
    print("🔍 Verificando requisitos...")
    
    try:
        import PyQt5
        # Intentar obtener versión de PyQt5.QtCore
        try:
            from PyQt5.QtCore import QT_VERSION_STR
            print(f"  ✓ PyQt5: {QT_VERSION_STR}")
        except:
            print(f"  ✓ PyQt5 instalado")
    except ImportError:
        print("  ✗ PyQt5 no esta instalado")
        print("    Instalar con: pip install PyQt5")
        return False
    
    try:
        import PyInstaller
        print(f"  ✓ PyInstaller instalado")
    except ImportError:
        print("  ✗ PyInstaller no esta instalado")
        print("    Instalar con: pip install pyinstaller")
        return False
    
    # Verificar script principal
    nombre_script = obtener_nombre_script()
    if not nombre_script:
        print("  ✗ No se encontro el script principal")
        print("    Asegurate de tener el script en esta carpeta")
        return False
    
    print(f"  ✓ Script encontrado: {nombre_script}.py")
    
    # Verificar icono
    icono = crear_icono()
    if icono:
        print(f"  ✓ Icono encontrado: {icono}")
    else:
        print("  ⚠ No se encontro icono, se usara el por defecto")
        print("    Para usar icono personalizado, coloca 'icons/app_icon.ico'")
    
    return True, nombre_script, icono

def main():
    """Función principal"""
    print("=" * 60)
    print("     EMPAQUETADOR DE MONITOR DE ARCHIVOS")
    print("     Con Icono Personalizado")
    print("=" * 60)
    print()
    
    # Verificar requisitos
    requisitos_ok, nombre_script, icono_path = verificar_requisitos()
    if not requisitos_ok:
        print("\n❌ No se cumplen los requisitos. Por favor, instala las dependencias faltantes.")
        input("\nPresiona Enter para salir...")
        return
    
    # Limpiar archivos previos
    limpiar_archivos_previos()
    
    # Construir ejecutable
    print("\n" + "=" * 60)
    print("     INICIANDO CONSTRUCCION")
    print("=" * 60)
    
    if construir_ejecutable(nombre_script, icono_path):
        print("\n" + "=" * 60)
        print("     ✅ ¡CONSTRUCCION EXITOSA!")
        print("=" * 60)
        print(f"📁 Ubicacion del ejecutable: {os.path.abspath('dist/MonitorArchivos.exe')}")
        
        # Crear accesos directos (solo Windows)
        if sys.platform == 'win32':
            try:
                crear_accesos_directos()
            except Exception as e:
                print(f"  ⚠ No se pudieron crear los accesos directos: {e}")
        
        # Crear batch file
        crear_archivo_batch()
        
        # Crear version portable
        crear_version_portable()
        
        # Crear script de instalacion
        crear_script_instalacion()
        
        print("\n" + "=" * 60)
        print("     📦 ARCHIVOS GENERADOS")
        print("=" * 60)
        print("""
1. Ejecutable principal:
   📁 dist/MonitorArchivos.exe

2. Version Portable (carpeta completa):
   📁 MonitorArchivos_Portable/
   ├── MonitorArchivos.exe
   ├── Iniciar.bat
   ├── README.txt
   ├── app_icon.ico
   └── config/

3. Scripts utiles:
   📄 iniciar_monitor.bat  - Inicio rapido
   📄 Instalar.bat          - Instalador simple

4. Acceso directo en el escritorio (Windows):
   🖥️ MonitorArchivos.lnk
        """)
        
        print("=" * 60)
        print("     📝 INSTRUCCIONES FINALES")
        print("=" * 60)
        print("""
✅ PARA USAR:
   • Version portable: Ejecuta 'MonitorArchivos_Portable/Iniciar.bat'
   • Version instalada: Ejecuta 'Instalar.bat' como administrador
   • Directamente: Ejecuta 'dist/MonitorArchivos.exe'

⚠ NOTA IMPORTANTE:
   • La primera ejecucion puede ser lenta mientras Windows lo analiza
   • Si Windows Defender bloquea el archivo, es una falsa alarma
   • Para evitar bloqueos, agrega una excepcion en Windows Defender
   • La configuracion se guarda automaticamente en la carpeta config/

🎯 DISTRIBUCION:
   • Para distribuir, copia la carpeta 'MonitorArchivos_Portable/'
   • El programa no requiere instalacion adicional
   • Funciona en Windows 7, 8, 10, 11
        """)
        
    else:
        print("\n" + "=" * 60)
        print("     ❌ ERROR EN LA CONSTRUCCION")
        print("=" * 60)
        print("""
Posibles soluciones:
1. Verifica que todas las dependencias esten instaladas:
   pip install --upgrade pyinstaller pyqt5

2. Prueba con el comando manual:
   pyinstaller --onefile --windowed --icon=icons/app_icon.ico --name=MonitorArchivos tu_script.py

3. Si el problema persiste, intenta sin icono:
   pyinstaller --onefile --windowed --name=MonitorArchivos tu_script.py

4. Verifica que el archivo icono sea valido (formato .ico)
        """)
    
    input("\nPresiona Enter para salir...")

if __name__ == "__main__":
    main()