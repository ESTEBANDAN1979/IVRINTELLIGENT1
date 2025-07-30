
# verificador_estado.py
import os, pymysql, time
PATH_SOUNDS = "/var/lib/asterisk/sounds/custom/ivr/"
PATH_CALL = "/var/spool/asterisk/outgoing/"
LOG_PATH = "/var/www/html/ivr_adminlte/logs/resumen_live.log"

def log_en_vivo(texto):
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {texto}\n")

def verificar_resultado_llamada(cursor, uidnew, telefono):
    clid_buscar = f"IVR-{uidnew}"
    log_en_vivo(f"[DEBUG] Buscando en CDR clid: {clid_buscar}")
    for intento in range(3):
        cursor.execute("""
            SELECT disposition, billsec, clid, duration, calldate, dst, dcontext
            FROM asteriskcdrdb.cdr 
            WHERE (clid = %s AND DATE(calldate)= CURDATE())
            AND calldate< DATE_SUB(now(), INTERVAL 5 MINUTE )
            AND dcontext='salida-tts' 
            ORDER BY calldate DESC
            LIMIT 1
        """, (clid_buscar,))
        row = cursor.fetchone()
        if row: break
        time.sleep(5)
    if not row:
        log_en_vivo(f"[UID {uidnew}] No se encontró registro en CDR.")
        return "ERROR", uidnew, None, telefono

    disposition, billsec, clid, duration, calldate, dst, dcontext = row
    log_en_vivo(f"[UID {uidnew}] Resultado: {disposition}, {billsec}s, {duration}s, {calldate}, {dst}, {dcontext}")
    uid_sin_prefijo = clid.replace("IVR-", "")
    mapping = {
        "ANSWERED": "CONTESTADA",
        "NO ANSWER": "NO CONTESTADA",
        "FAILED": "FALLIDA",
        "BUSY": "BUZON",
        "CONGESTION": "LLAMADA"
    }
    return mapping.get(disposition, "ERROR"), uid_sin_prefijo, calldate, dst

def verificar_estado():
    conn = pymysql.connect(host='localhost', user='ivruser', password='ivrpass', database='ivr')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, uidnew, nombre, telefono
            FROM detalle_campana
            WHERE estado = 'ENVIADO' 
            ORDER BY id ASC
            LIMIT 1000
        """)
        pendientes = cursor.fetchall()
        for id_reg, uidnew, nombre, telefono in pendientes:
            try:
                estado_llamada, uid_limpio, fecha_llamada, telefono_dst = verificar_resultado_llamada(cursor, uidnew, telefono)
                cursor.execute("""
                    UPDATE detalle_campana
                    SET estado = %s, fecha_ultima_llamada = %s
                    WHERE uidnew = %s AND telefono = %s
                """, (estado_llamada, fecha_llamada, uid_limpio, telefono_dst))
                conn.commit()
                log_en_vivo(f"[ID {id_reg}] Estado actualizado a {estado_llamada}")

                if estado_llamada in ['CONTESTADA', 'FALLIDA', 'BUZON', 'LLAMADA']:
                    nombre_audio = f"mensaje_*_{id_reg}.wav"
                    ruta_audio = os.path.join(PATH_SOUNDS, nombre_audio)
                    ruta_call = os.path.join(PATH_CALL, f"mensaje_*_{id_reg}.call")
                    if os.path.exists(ruta_audio): os.remove(ruta_audio)
                    if os.path.exists(ruta_call): os.remove(ruta_call)
                    log_en_vivo(f"[ID {id_reg}] Archivos eliminados tras llamada")
            except Exception as e:
                log_en_vivo(f"[ID {id_reg}] Error verificando: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    verificar_estado()
