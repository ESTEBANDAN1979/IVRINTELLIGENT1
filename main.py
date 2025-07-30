
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pymysql, json, subprocess, time, datetime
from multiprocessing import Process
from lanzador_campana import lanzar_campana

LOG_PATH = "/var/www/html/ivr_adminlte/logs/resumen_live.log"

def log_en_vivo(texto):
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {texto}\n")

with open("/var/log/ivr/ejecucion_main.log", "a") as log:
    log.write(f"🕒 Lanzado: {datetime.datetime.now()}\n")

with open('/var/www/html/ivr_adminlte/includes/config.json') as f:
    dbconfig = json.load(f)

conn = pymysql.connect(**dbconfig)
cursor = conn.cursor()

cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;")
cursor.execute("CALL obtener_varias_campanas_activas")
campanas = cursor.fetchall()

if not campanas:
    log_en_vivo("🔍 No hay campañas activas disponibles.")
else:
    procesos = []
    for campana in campanas:
        campana_id, max_canales, intensidad, grupo_id = campana
        log_en_vivo(f"🚀 Lanzando campaña ID {campana_id}...")
        p = Process(target=lanzar_campana, args=(campana_id, max_canales, intensidad, grupo_id))
        p.start()
        procesos.append(p)
    for p in procesos:
        p.join()

cursor.close()
conn.close()

subprocess.Popen(["python3", "/var/www/html/ivr_adminlte/scripts/mover_lotes_call.py"])
