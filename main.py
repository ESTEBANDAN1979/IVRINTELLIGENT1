# main.py
import pymysql
import json
import time
import datetime
from multiprocessing import Process
from lanzador_campana import lanzar_campana

# Log para depuración general
with open("/var/log/ivr/ejecucion_main.log", "a") as log:
    log.write(f"🕒 Lanzado: {datetime.datetime.now()}\n")

# Ruta de log para sistema
LOG_PATH = "/var/www/html/ivr_adminlte/logs/resumen_live.log"

# Función para registrar eventos
def log_en_vivo(texto):
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {texto}\n")

# Cargar configuración DB
with open('/var/www/html/ivr_adminlte/includes/config.json') as f:
    dbconfig = json.load(f)

# Conectar a MySQL
conn = pymysql.connect(
    host=dbconfig['host'],
    user=dbconfig['user'],
    password=dbconfig['password'],
    database=dbconfig['database']
)
cursor = conn.cursor()

# Obtener campañas activas
try:
    cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;")
    cursor.execute("CALL obtener_varias_campanas_activas")
    campanas = cursor.fetchall()
except Exception as e:
    log_en_vivo(f"❌ Error al obtener campañas activas: {e}")
    campanas = []

# Procesar campañas
if not campanas:
    log_en_vivo("🚫 No hay campañas activas disponibles.")
else:
    procesos = []
    for campana in campanas:
        campana_id, max_canales, intensidad, grupo_id = campana
        log_en_vivo(f"🚀 Lanzando campaña ID {campana_id} con {max_canales} canales.")
        p = Process(target=lanzar_campana, args=(campana_id, max_canales, intensidad, grupo_id))
        p.start()
        procesos.append(p)

    for p in procesos:
        p.join()

# Cierre de recursos
cursor.close()
conn.close()
