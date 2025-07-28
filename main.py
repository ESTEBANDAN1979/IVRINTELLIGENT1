import pymysql
import json
import time  # Necesario para log
from multiprocessing import Process
from lanzador_campana import lanzar_campana


with open("/var/log/ivr/ejecucion_main.log", "a") as log:
    import datetime
    log.write(f"🕒 Lanzado: {datetime.datetime.now()}\n")

# Ruta de log
LOG_PATH = "/var/www/html/ivr_adminlte/logs/resumen_live.log"

# Leer configuración de base de datos
with open('/var/www/html/ivr_adminlte/includes/config.json') as f:
    dbconfig = json.load(f)

# Conexión a MySQL
conn = pymysql.connect(
    host=dbconfig['host'],
    user=dbconfig['user'],
    password=dbconfig['password'],
    database=dbconfig['database']
)
cursor = conn.cursor()

# Función para registrar logs
def log_en_vivo(texto):
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {texto}\n")

# Obtener campañas activas
#SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
#cursor.callproc("obtener_varias_campanas_activas")
#campanas = cursor.fetchall()
cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;")
cursor.execute("CALL obtener_varias_campanas_activas")
campanas = cursor.fetchall()

if not campanas:
    print("No hay campañas activas disponibles.")
    log_en_vivo(f"No hay campañas activas disponibles.")
else:
    procesos = []
    for campana in campanas:
        campana_id, max_canales, intensidad, grupo_id = campana
        print(f"Lanzando campaña ID {campana_id}...")
        log_en_vivo(f"Lanzando campaña ID {campana_id}...")
        p = Process(target=lanzar_campana, args=(campana_id, max_canales, intensidad, grupo_id))
        p.start()
        procesos.append(p)

    for p in procesos:
        p.join()

cursor.close()
conn.close()