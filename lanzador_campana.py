# lanzador_campana.py
# -*- coding: utf-8 -*-
import pymysql
import os
import time
import socket
import pwd
import subprocess
import shutil
import json
from multiprocessing import Semaphore
import re

# Rutas
PATH_CONFIG = '/var/www/html/ivr_adminlte/includes/config.json'
PATH_SOUNDS = "/var/lib/asterisk/sounds/custom/ivr/"
PATH_CALLS_TMP = "/tmp/ivr/"
PATH_CALLS_TMPA = "/tmp/ivr/calls/"
PATH_CALLS_FINAL = "/var/spool/asterisk/outgoing/"
LOG_PATH = "/var/www/html/ivr_adminlte/logs/resumen_live.log"

# Crear directorios si no existen
def crear_directorio_con_permisos(ruta, modo=0o775, propietario='asterisk', grupo='asterisk'):
    if not os.path.exists(ruta):
        os.makedirs(ruta, exist_ok=True)
    uid = pwd.getpwnam(propietario).pw_uid
    gid = pwd.getpwnam(grupo).pw_gid
    os.chown(ruta, uid, gid)
    os.chmod(ruta, modo)

crear_directorio_con_permisos(PATH_SOUNDS)
crear_directorio_con_permisos(PATH_CALLS_TMP)
crear_directorio_con_permisos(PATH_CALLS_FINAL)

# UID/GID para permisos
uid_asterisk = pwd.getpwnam('asterisk').pw_uid
gid_asterisk = pwd.getpwnam('asterisk').pw_gid

def log_en_vivo(texto):
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {texto}\n")

def internet_activo():
    try:
        socket.setdefaulttimeout(3)
        host = socket.gethostbyname("translate.google.com")
        s = socket.create_connection((host, 443), 2)
        s.close()
        return True
    except:
        return False

def canales_activos():
    result = os.popen("asterisk -rx 'core show channels concise' | grep '^Local/' | wc -l").read()
    try:
        return int(result.strip())
    except:
        return 0

def lanzar_campana(campana_id, MAX_CANALES, INTENSIDAD, grupo_id):
    if not internet_activo():
        log_en_vivo(f"[{campana_id}] No hay internet.")
        return

    # Leer config
    with open(PATH_CONFIG) as f:
        dbconfig = json.load(f)

    conn = pymysql.connect(
        host=dbconfig['host'],
        user=dbconfig['user'],
        password=dbconfig['password'],
        database=dbconfig['database']
    )
    cursor = conn.cursor()

    # Marcar campaña como en ejecución
    cursor.callproc("marcar_campana_ejecucion", (campana_id,))
    conn.commit()

    semaforo = Semaphore(MAX_CANALES)

    try:
        cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;")
        cursor.execute("CALL obtener_detalle_campana_para_marcar(%s, %s, %s)", (grupo_id, INTENSIDAD, MAX_CANALES))
        registros = cursor.fetchall()
        
        for id_reg, telefono, texto, uidnew, nombre, ruta_audio, audio_ivr, grupo_id  in registros:

            # Espera mientras no haya canales disponibles
            while canales_activos() >= MAX_CANALES:
                time.sleep(1)
                log_en_vivo(f"[{grupo_id}] [ID {id_reg}] Esperando canal libre...")

            # Control de concurrencia
            with semaforo:
                if not texto and not ruta_audio:
                    continue

                log_en_vivo(f"[{grupo_id}] [ID {id_reg}] Procesando registro...")

                try:
                    # Convertir audio_ivr desde bytes a entero si es necesario
                    audio_ivr = int.from_bytes(audio_ivr, 'little') if isinstance(audio_ivr, bytes) else int(audio_ivr)
                    log_en_vivo(f"[{audio_ivr}] [ID {id_reg}] Inicio")
                    log_en_vivo(f"[{grupo_id}] Verificando uso de audio. audio_ivr={audio_ivr}, ruta_audio={ruta_audio}")

                    # Determinar si se debe usar audio pregrabado o texto
                    usar_audio = audio_ivr == 1 and ruta_audio is not None and ruta_audio.strip() != ''

                    # Preparar nombres y rutas de archivos
                    nombre_sanitizado = re.sub(r'[^\w\-]', '_', nombre)
                    filename = f"mensaje_{id_reg}"
                    ruta_mp3 = f"{PATH_CALLS_TMP}{filename}.mp3"
                    ruta_wav = f"{PATH_SOUNDS}{filename}.wav"
                    ruta_call_tmp = f"{PATH_CALLS_TMPA}{filename}.call"

                    # === Lógica si es AUDIO ===
                    if usar_audio:
                        ruta_audio_absoluta = os.path.join("/var/www/html/ivr_adminlte/", ruta_audio)
                        log_en_vivo(f"Esta es la ruta previa: [{ruta_audio_absoluta}]")
                        if not os.path.isfile(ruta_audio_absoluta):
                            log_en_vivo(f"[{nombre}] Error: MP3 original no existe: {ruta_audio_absoluta}")
                            continue

                        shutil.copy(ruta_audio_absoluta, ruta_mp3)
                        os.chown(ruta_mp3, uid_asterisk, gid_asterisk)
                        os.chmod(ruta_mp3, 0o664)

                        # Convertir a WAV
                        os.system(f"ffmpeg -y -i {ruta_mp3} -ar 8000 -ac 1 -ab 16k -f wav {ruta_wav} >/dev/null 2>&1")
                        if not os.path.isfile(ruta_wav):
                            log_en_vivo(f"[{nombre}] Error: No se pudo convertir el audio")
                            continue
                    
                        os.chown(ruta_wav, uid_asterisk, gid_asterisk)
                        os.chmod(ruta_wav, 0o664)

                    # === Lógica si es TEXTO ===
                    else:
                        if not texto or not texto.strip():
                            log_en_vivo(f"[{nombre}] Error: Texto vacío, no se puede generar audio.")
                            continue
                        
                        comando = ["pico2wave", "-l", "es-ES", "-w", ruta_wav, texto]
                        try:
                            subprocess.run(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True)
                            log_en_vivo(f"[{nombre}] ✅ Audio generado")
                        except subprocess.CalledProcessError as e:
                            log_en_vivo(f"[{nombre}] ❌ Error al generar Audio. STDERR: {e.stderr.strip()}")
                            continue

                        if not os.path.exists(ruta_wav):
                            log_en_vivo(f"[{nombre}] Error: WAV no se generó el Audio")
                            continue

                        os.chown(ruta_wav, uid_asterisk, gid_asterisk)
                        os.chmod(ruta_wav, 0o664)

                    # Crear el archivo .call
                    with open(ruta_call_tmp, 'w') as f:
                        f.write(f'Channel: Local/{telefono}@salida-tts\n')
                        f.write(f'Set: numero_destino={telefono}\n')
                        f.write('MaxRetries: 1\n')
                        f.write('RetryTime: 60\n')
                        f.write('WaitTime: 30\n')
                        f.write('Context: salida-tts\n')
                        f.write('Extension: s\n')
                        f.write('Priority: 1\n')
                        f.write(f'CallerID: IVR-{uidnew}\n')
                        f.write(f'Setvar: audiofile={filename}\n')
                        f.write(f'Setvar: userfield=IVR-{uidnew}\n')

                    os.chown(ruta_call_tmp, uid_asterisk, gid_asterisk)
                    os.chmod(ruta_call_tmp, 0o664)
                    
                    log_en_vivo(f"[📞 {nombre}] .call preparado en {ruta_call_tmp}.")

                    # Marcar detalle como ENVIADO
                    cursor.callproc("marcar_detalle_enviado", (id_reg,))
                    conn.commit()

                    log_en_vivo(f"[{nombre}] Llamada programada para el número {telefono}")
                except Exception as e:
                    log_en_vivo(f"[{nombre}] Error final: {e}")
                finally:
                    semaforo.release()

    finally:
        cursor.callproc("liberar_campana", (grupo_id,))
        conn.commit()
        cursor.close()
        conn.close()
