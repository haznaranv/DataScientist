import sqlite3 as qlite
import libsql_client
from  pathlib import Path
from datetime import datetime


db= Path("bbdd/tracker_bbdd.db")
# Hallamos la ruta absoluta del proyecto

BASE_DIR=Path(__file__).resolve().parent.parent

# añadimos en la ruta absoluta la carpeta donde se guarda la bbdd
PATH_BBDD= BASE_DIR / "bbdd" / "tracker_bbdd.db"

# conexion a la BBDD
conn=qlite.connect(PATH_BBDD)
cursor= conn.cursor()

cursor.execute("SELECT * FROM FECHAS")
print(cursor.fetchall())

fecha_Actual=datetime.now().date()

print (fecha_Actual)

conn.close()
