import socket
import pymysql
import time

# --- CONFIGURACIÓN ---
HOST = '127.0.0.1'
PORT = 5038
USER = 'admin'
SECRET = 'Ecosystemcpn.22'

DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASS = 'Ecosystemcpn.22'
DB_NAME = 'ivr'

LOG_PATH = '/var/www/html/ivr_adminlte/logs/estado_llamadas.log'  # Ruta para guardar eventos

# --- FUNCIÓN LOG ---
def log_evento(texto):
    with open(LOG_PATH, "a") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {texto}\n")

# --- ACTUALIZAR ESTADO ---
def actualizar_estado_por_userfield(neuwid, estado):
    try:
        conn = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)
        cursor = conn.cursor()
        sql = "UPDATE detalle_campana SET estado = %s WHERE neuwid = %s"
        cursor.execute(sql, (estado, neuwid))
        conn.commit()
        print(f"✅ Actualizado {neuwid} a {estado}")
        log_evento(f"Actualizado {neuwid} a {estado}")
    except Exception as e:
        print(f"❌ Error MySQL: {e}")
        log_evento(f"Error al actualizar {neuwid}: {e}")
    finally:
        conn.close()

# --- ESCUCHAR AMI ---
def escuchar_ami():
    try:
        s = socket.socket()
        s.connect((HOST, PORT))
        s.settimeout(10)  # Si no hay respuesta en 10s, lanza excepción

        # LOGIN
        login_msg = f"""Action: Login
Username: {USER}
Secret: {SECRET}

"""
        s.send(login_msg.encode())
        time.sleep(0.5)

        # Activar eventos
        s.send(b"Action: Events\nEventMask: on\n\n")
        print("🎧 Conexión establecida con AMI. Esperando eventos...\n")
        log_evento("Conectado al AMI y esperando eventos...")

        buffer = ""
        while True:
            try:
                data = s.recv(4096).decode(errors='ignore')
                if not data:
                    raise Exception("❌ AMI desconectado o no responde.")
                buffer += data

                while "\n\n" in buffer:
                    evento, buffer = buffer.split("\n\n", 1)

                    if "Event: CDR" in evento:
                        userfield = None
                        disposition = None

                        for linea in evento.split("\n"):
                            if "UserField:" in linea:
                                userfield = linea.split(":", 1)[1].strip()
                            if "Disposition:" in linea:
                                disposition = linea.split(":", 1)[1].strip()

                        if userfield and disposition and userfield.startswith("IVR-"):
                            neuwid = userfield.replace("IVR-", "")
                            estado = "CONTESTADA" if disposition == "ANSWERED" else "NO_CONTESTADA"
                            print(f"📞 Llamada {neuwid} => {estado}")
                            log_evento(f"Recibido CDR: {neuwid} => {estado}")
                            actualizar_estado_por_userfield(neuwid, estado)

            except socket.timeout:
                print("⏳ Esperando eventos...")
                s.send(b"Action: Ping\n\n")  # Mantener viva la conexión
                continue
            except Exception as e:
                print(f"❌ Error escuchando AMI: {e}")
                log_evento(f"Error conexión AMI: {e}")
                break

    except Exception as e:
        print(f"❌ No se pudo conectar al AMI: {e}")
        log_evento(f"Error al conectar al AMI: {e}")

# --- EJECUCIÓN ---
if __name__ == '__main__':
    try:
        escuchar_ami()
    except KeyboardInterrupt:
        print("🛑 Finalizado por el usuario")
        log_evento("Script terminado manualmente.")
