import sqlite3 as qlite
from  pathlib import Path
from datetime import datetime

class conectarBD():
    def __init__(self, ruta_BD, nombd):
        self.ruta_BD=ruta_BD
        self.nombd=nombd
        self.conn=None
        self.cursor=None
    
    def rutaBD(self):
        """
        Ruta de la Base de Datos, generalmente estara en alguna carpeta de programa
        """
        MAIN_PATH= Path(__file__).resolve().parent.parent
        BD_PATH= MAIN_PATH / self.ruta_BD / self.nombd
        return BD_PATH
        
    def conectarBD(self):
        ruta=self.rutaBD()
        self.conn=qlite.connect(ruta)
        self.cursor=self.conn.cursor()
        return self.conn
    
    def cerrarBD(self):
        if self.conn:
            self.conn.close()
            print("conexion cerrada exitosament")
        else:
            print("Error de conexion a la Base de datos")

    def consultaBD(self, query, params=None):
        if not self.conn:
            self.conectarBD()
        
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        return self.cursor.fetchall()





def main():
    bd=conectarBD("bbdd", "tracker_bbdd.db")
    print(bd.rutaBD())
    bd.conectarBD()
    resultado=bd.consultaBD("SELECT * FROM FECHAS")
    for x in resultado:
        print(x)

    bd.cerrarBD()



if __name__=="__main__":
    main()
