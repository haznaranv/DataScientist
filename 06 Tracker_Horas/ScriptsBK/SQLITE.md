-- ----------------------------------------------------------
# Configuracion Tablas
-- ----------------------------------------------------------
#Fechas
CREATE TABLE "fechas" (
	"fecha"	TEXT,
	"año"	TEXT,
	"mes"	TEXT,
	"dia"	TEXT,
	"semana"	TEXT,
	PRIMARY KEY("fecha")
);

-- ----------------------------------------------------------
# Query recursiva para insertar dias en el año mas numero de semana 
# aquiempieza como inicio de semana el Lunes
WITH RECURSIVE dias2027(fecha) AS (
    SELECT DATE('2027-01-01')
    UNION ALL
    SELECT DATE(fecha, '+1 day')
    FROM dias2027
    WHERE fecha < DATE('2027-12-31')
)
INSERT INTO fechas (fecha, año, mes, dia, semana)
SELECT 
    strftime('%Y%m%d', fecha) as fecha,
    strftime('%Y', fecha) AS año,
    strftime('%m', fecha) AS mes,
    strftime('%d', fecha) AS dia,
    strftime('%V', fecha) AS semana  -- si empieza el lunes, si queremos que sea domingo %W
FROM dias2027;
