
# lanzador_campana.py
# -*- coding: utf-8 -*-
import pymysql, os, time, socket, pwd, subprocess, shutil, json, re
from multiprocessing import Semaphore

PATH_CONFIG = '/var/www/html/ivr_adminlte/includes/config.json'
PATH_SOUNDS = "/var/lib/asterisk/sounds/custom/ivr/"
PATH_CALLS_TMP = "/tmp/ivr/"
PATH_CALLS_TMPA = "/tmp/ivr/calls/"
PATH_CALLS_FINAL = "/var/spool/asterisk/outgoing/"
LOG_PATH = "/var/www/html/ivr_adminlte/logs/resumen_live.log"

def crear_directorio_con_permisos(ruta, modo=0o775, propietario='asterisk', grupo='asterisk'):
    if not os.path.exists(ruta):
        os.makedirs(ruta, exist_ok=True)
    uid = pwd.getpwnam(propietario).pw_uid
    gid = pwd.getpwnam(grupo).pw_gid
    os.chown(ruta, uid, gid)
    os.chmod(ruta, modo)

for path in [PATH_SOUNDS, PATH_CALLS_TMP, PATH_CALLS_TMPA, PATH_CALLS_FINAL]:
    crear_directorio_con_permisos(path)

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

def lanzar_campana(campana_id, MAX_CANALES, INTENSIDAD, grupo_id):
    if not internet_activo():
        log_en_vivo(f"[{campana_id}] No hay internet.")
        return

    with open(PATH_CONFIG) as f:
        dbconfig = json.load(f)

    conn = pymysql.connect(**dbconfig)
    cursor = conn.cursor()
    cursor.callproc("marcar_campana_ejecucion", (campana_id,))
    conn.commit()

    try:
        cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;")
        cursor.execute("CALL obtener_detalle_campana_para_marcar(%s, %s, %s)", (grupo_id, INTENSIDAD, MAX_CANALES))
        registros = cursor.fetchall()

        for id_reg, telefono, texto, uidnew, nombre, ruta_audio, audio_ivr, grupo_id in registros:
            try:
                audio_ivr = int.from_bytes(audio_ivr, 'little') if isinstance(audio_ivr, bytes) else int(audio_ivr)
                usar_audio = audio_ivr == 1 and ruta_audio and ruta_audio.strip() != ''
                nombre_sanitizado = re.sub(r'[^\w\-]', '_', nombre)
                filename = f"mensaje_{campana_id}_{id_reg}"
                ruta_mp3 = f"{PATH_CALLS_TMP}{filename}.mp3"
                ruta_wav = f"{PATH_SOUNDS}{filename}.wav"
                ruta_call_tmp = f"{PATH_CALLS_TMPA}{filename}.call"

                if usar_audio:
                    ruta_audio_absoluta = os.path.join("/var/www/html/ivr_adminlte/", ruta_audio)
                    if not os.path.isfile(ruta_audio_absoluta):
                        log_en_vivo(f"[{nombre}] Error: MP3 original no existe: {ruta_audio_absoluta}")
                        continue
                    shutil.copy(ruta_audio_absoluta, ruta_mp3)
                    os.chown(ruta_mp3, uid_asterisk, gid_asterisk)
                    os.chmod(ruta_mp3, 0o664)
                    os.system(f"/usr/local/bin/ffmpeg -y -i {ruta_mp3} -ar 8000 -ac 1 -ab 16k -f wav {ruta_wav} >/dev/null 2>&1")
                    if not os.path.isfile(ruta_wav):
                        log_en_vivo(f"[{nombre}] Error: No se pudo convertir el audio")
                        continue
                else:
                    if not texto or not texto.strip():
                        log_en_vivo(f"[{nombre}] Error: Texto vacío.")
                        continue
                    comando = ["pico2wave", "-l", "es-ES", "-w", ruta_wav, texto]
                    try:
                        subprocess.run(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                    except subprocess.CalledProcessError as e:
                        log_en_vivo(f"[{nombre}] Error al generar Audio: {e.stderr.strip()}")
                        continue
                    if not os.path.exists(ruta_wav):
                        log_en_vivo(f"[{nombre}] Error: WAV no generado.")
                        continue

                os.chown(ruta_wav, uid_asterisk, gid_asterisk)
                os.chmod(ruta_wav, 0o664)

                with open(ruta_call_tmp, 'w') as f:
                    f.write(f'Channel: Local/{telefono}@salida-tts\n')
                    f.write(f'Set: numero_destino={telefono}\n')
                    f.write('MaxRetries: 1\nRetryTime: 60\nWaitTime: 60\n')
                    f.write('Context: salida-tts\nExtension: s\nPriority: 1\n')
                    f.write(f'CallerID: IVR-{uidnew}\n')
                    f.write(f'Setvar: audiofile={filename}\n')
                    f.write(f'Setvar: userfield=IVR-{uidnew}\n')

                cursor.callproc("marcar_detalle_enviado", (id_reg,))
                conn.commit()
                log_en_vivo(f"[{nombre}] Call preparado: {telefono}")
            except Exception as e:
                log_en_vivo(f"[{nombre}] Error: {e}")
    finally:
        cursor.callproc("liberar_campana", (grupo_id,))
        conn.commit()
        cursor.close()
        conn.close()
