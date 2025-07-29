import pymysql
import json
import time
from multiprocessing import Process
from lanzador_campana import lanzar_campana
import subprocess
import datetime

LOG_PATH = "/var/www/html/ivr_adminlte/logs/resumen_live.log"

# Función para registrar logs
def log_en_vivo(texto):
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {texto}\n")

log_en_vivo(f"🕒 Lanzado: {datetime.datetime.now()}")

# Leer configuración de base de datos
with open('/var/www/html/ivr_adminlte/includes/config.json') as f:
    dbconfig = json.load(f)

# Conexión
try:
    conn = pymysql.connect(
        host=dbconfig['host'],
        user=dbconfig['user'],
        password=dbconfig['password'],
        database=dbconfig['database']
    )
    cursor = conn.cursor()

    cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;")
    cursor.execute("CALL obtener_varias_campanas_activas")
    campanas = cursor.fetchall()

    if not campanas:
        log_en_vivo("❌ No hay campañas activas disponibles.")
    else:
        procesos = []
        for campana in campanas:
            campana_id, max_canales, intensidad, grupo_id = campana
            log_en_vivo(f"🚀 Lanzando campaña ID {campana_id} con grupo {grupo_id}")
            p = Process(target=lanzar_campana, args=(campana_id, max_canales, intensidad, grupo_id))
            p.start()
            procesos.append(p)

        # Esperar que todos los procesos terminen
        for p in procesos:
            p.join()

    # Ejecutar mover_lotes_call.py al final
    try:
        log_en_vivo("📦 Ejecutando mover_lotes_call.py desde main.py...")
        subprocess.Popen(["python3", "/var/www/html/ivr_adminlte/scripts/mover_lotes_call.py"])
    except Exception as e:
        log_en_vivo(f"❌ Error al ejecutar mover_lotes_call.py: {e}")

    cursor.close()
    conn.close()

except Exception as ex:
    log_en_vivo(f"❌ Error al conectar a la base de datos o ejecutar procesos: {ex}")
