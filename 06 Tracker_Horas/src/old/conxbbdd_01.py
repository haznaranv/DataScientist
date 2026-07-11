import sqlite3 as qlite
import libsql_client
import pathlib
import datetime



path_db=pathlib.PurePath('/bbdd')
path_bbdd=path_db/'tracker_bbdd.db'



#url="file:{path_bbdd}"
conn=qlite.connect('bbdd/tracker_bbdd.db')
cursor=conn.cursor()

if cursor:
    print('conexion satisfactoria')
    cursor.execute("select * from fechas")
    r=cursor.fetchone()
    tuple(r)
    filas=cursor.fetchall()
    for lel in filas:
        print (lel)
    
    
    print ("Las columnas son :", r.keys)
    conn.close()

