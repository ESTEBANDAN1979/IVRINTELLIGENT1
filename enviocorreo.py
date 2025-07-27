import pymysql
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Cargar configuración DB
with open('/var/www/html/ivr_adminlte/includes/config.json') as f:
    config = json.load(f)

# Conexión a la base de datos
conn = pymysql.connect(
    host=config['host'],
    user=config['user'],
    password=config['password'],
    database=config['database']
)
cursor = conn.cursor()

# Consultar conteo por estado
cursor.execute("""
    SELECT estado, COUNT(*) FROM detalle_campana
    GROUP BY estado
""")
resultados = cursor.fetchall()
cursor.close()
conn.close()

# Colores e íconos para cada estado
estilos = {
    'PENDIENTE': {'color': '#f0ad4e', 'icono': '⏳'},     # naranja
    'ERROR':     {'color': '#d9534f', 'icono': '❌'},     # rojo
    'CONTESTADA':{'color': '#5cb85c', 'icono': '✅'},     # verde
    'NO CONTESTADA': {'color': '#6c757d', 'icono': '📴'}, # gris
    'REINTENTAR':{'color': '#0275d8', 'icono': '🔁'},     # azul
    'ELIMINADO': {'color': '#292b2c', 'icono': '🗑️'},    # negro
}

# Armar tabla en HTML
fecha = datetime.now().strftime('%Y-%m-%d %H:%M')
tabla = f"""
<h2 style="color:#2c3e50;">📊 Resumen de llamadas IVR</h2>
<p><strong>Fecha de corte:</strong> {fecha}</p>
<table style="border-collapse:collapse;width:60%;font-family:sans-serif;">
  <thead>
    <tr>
      <th style="border:1px solid #ccc;padding:8px;background:#f8f8f8;">Estado</th>
      <th style="border:1px solid #ccc;padding:8px;background:#f8f8f8;">Total</th>
    </tr>
  </thead>
  <tbody>
"""

total_general = 0
for estado, total in resultados:
    estilo = estilos.get(estado.upper(), {'color': '#999', 'icono': '❓'})
    tabla += f"""
    <tr>
      <td style="border:1px solid #ccc;padding:8px;color:white;background:{estilo['color']}">
        {estilo['icono']} {estado}
      </td>
      <td style="border:1px solid #ccc;padding:8px;text-align:center;">{total}</td>
    </tr>
    """
    total_general += total

tabla += f"""
    <tr>
      <td style="border:1px solid #ccc;padding:8px;font-weight:bold;background:#f0f0f0;">Total general</td>
      <td style="border:1px solid #ccc;padding:8px;font-weight:bold;text-align:center;">{total_general}</td>
    </tr>
  </tbody>
</table>
"""

# Datos del correo
remitente = "admicion@sistecpn.ecosystemasec-ec.com"
destinatario = "estan.osorio@ecosystememas-ec.com"
asunto = "📞 Reporte de llamadas IVR - " + fecha

msg = MIMEMultipart()
msg['From'] = remitente
msg['To'] = destinatario
msg['Subject'] = asunto
msg.attach(MIMEText(tabla, 'html'))

# Enviar correo
try:
    server = smtplib.SMTP('p14245.use145.mysecurecloudhostp.com', 587)
    server.starttls()
    server.login(remitente, 'X*9989045643678gtsdgjgf._a0a56a4')
    server.sendmail(remitente, destinatario, msg.as_string())
    server.quit()
    print("Correo enviado correctamente.")
except Exception as e:
    print("Error al enviar correo:", e)
