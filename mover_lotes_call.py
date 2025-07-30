
# mover_lotes_call.py
# -*- coding: utf-8 -*-
import os, shutil, time, pymysql, json
from datetime import datetime

PATH_CALLS_TMP = "/tmp/ivr/calls/"
PATH_CALLS_FINAL = "/var/spool/asterisk/outgoing/"
LOG_PATH = "/var/www/html/ivr_adminlte/logs/mover_lotes.log"
PATH_CONFIG = "/var/www/html/ivr_adminlte/includes/config.json"

PAUSA_ENTRE_MOVIMIENTOS = 1
PAUSA_SIN_CANAL = 3
MAX_POR_LOTE = 5

def log(texto):
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {texto}\n")

def canales_activos():
    try:
        result = os.popen("asterisk -rx 'core show channels concise' | grep '^Local/' | wc -l").read()
        return int(result.strip())
    except:
        return 0

def obtener_limite_canales():
    try:
        with open(PATH_CONFIG) as f:
            dbconfig = json.load(f)
        conn = pymysql.connect(**dbconfig)
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(max_canales) FROM campanas WHERE ejecutando=1 AND esatdo='ACTIVA'")
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()
        return int(resultado[0]) if resultado[0] else 5
    except Exception as e:
        log(f"⚠️ Error al obtener canales máximos: {e}")
        return 5

def mover_por_lotes():
    log("🚚 Iniciando movimiento de .call")
    while True:
        activos = canales_activos()
        limite = obtener_limite_canales()
        disponibles = max(0, limite - activos)

        if disponibles == 0:
            log(f"⏳ Esperando canales disponibles: {activos}/{limite}")
            time.sleep(PAUSA_SIN_CANAL)
            continue

        archivos = sorted([f for f in os.listdir(PATH_CALLS_TMP) if f.endswith('.call')])
        if not archivos:
            log("✅ Todos los archivos .call han sido procesados.")
            break

        mover_n = min(disponibles, MAX_POR_LOTE, len(archivos))
        for archivo in archivos[:mover_n]:
            origen = os.path.join(PATH_CALLS_TMP, archivo)
            destino = os.path.join(PATH_CALLS_FINAL, archivo)
            try:
                shutil.move(origen, destino)
                log(f"📞 Movido: {archivo} | Canales usados: {activos}, límite: {limite}")
                time.sleep(PAUSA_ENTRE_MOVIMIENTOS)
            except Exception as e:
                log(f"❌ Error al mover {archivo}: {e}")
                time.sleep(1)
    log("🏁 Movimiento de .call finalizado.")

if __name__ == "__main__":
    mover_por_lotes()
