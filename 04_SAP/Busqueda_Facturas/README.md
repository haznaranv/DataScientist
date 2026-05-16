¿COmo funciona?
- en un fichero especifico en donde llegan muchos registros, existen registros que tienen como patron inicial
"CA" seguido de codigos, solo se extraen los codigos y contando espacios especificos cogemos las ordenes
- despues de coger dichos datos, las une por orden:
Ordenes_Facturas
con la finalidad de realizar una busqueda en SAP
- Despues de montar en una fila la informacion necesaria se realiza la busqueda obteniendo
el numero de idoc.
- si existiera registros que no tienen idocs , se separa y se guardan en otro fichero, diferentes de los que 
si tienen.
- La conexion se realiza a traves de un LinkServer