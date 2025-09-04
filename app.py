# app.py - REEMPLAZAR COMPLETAMENTE
from flask import Flask, request, render_template, jsonify, send_file, make_response
from utils import generar_token_actual, validar_token_con_precision, obtener_info_debug, obtener_segundos_hasta_refresh
from datetime import datetime
import pytz
import csv, os, qrcode, logging
from io import BytesIO
from dotenv import load_dotenv
load_dotenv()
TZ = pytz.timezone("America/Guayaquil")

import pymysql
from pymysql.err import MySQLError

# Configurar logging para debug detallado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host':     os.getenv('DB_HOST', 'localhost'),
    'port':     int(os.getenv('DB_PORT', 3306)),
    'user':     os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'root'),
    'db':       os.getenv('DB_NAME', 'mmqepgob_qr'),
    'charset':  'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

auth = HTTPBasicAuth()

# Usuarios válidos:
users = {
    "admin": generate_password_hash("MMqep2025")
}

@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username

app = Flask(__name__)
RED_LOCAL = "192.168.1."

# Variable global para mantener el token vigente (para compatibilidad)
current_token = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/qr')
@auth.login_required
def qr():
    global current_token
    # Genera y almacena el token vigente
    current_token = generar_token_actual()
    
    # Log para debug con información de timing
    debug_info = obtener_info_debug()
    logger.info(f"🔄 Generando QR - Token: {current_token[:8]}... "
                f"Bucket: {debug_info['bucket_segundo']}s "
                f"Segundos restantes: {debug_info['segundos_restantes']}")
    
    # Timestamp para bustear cache con precisión de milisegundos
    bust = int(datetime.now().timestamp() * 1000)
    return render_template('qr.html', token=current_token, bust=bust)

@app.route('/qr_image')
@auth.login_required
def qr_image():
    global current_token
    # Siempre generar token fresco para garantizar sincronización
    current_token = generar_token_actual()
    
    # Genera la imagen del QR
    img = qrcode.make(current_token)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    
    # Headers anti-cache agresivos para evitar QR obsoletos
    resp = make_response(send_file(buf, mimetype="image/png"))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    resp.headers['Last-Modified'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
    
    return resp

@app.route('/api/timing')
@auth.login_required
def api_timing():
    """
    Endpoint para sincronización precisa del frontend
    Proporciona timing exacto para el próximo refresh
    """
    return jsonify({
        "ms_hasta_refresh": obtener_segundos_hasta_refresh(),
        "timestamp_servidor": datetime.now(TZ).isoformat()
    })

@app.route('/debug/token')
@auth.login_required
def debug_token():
    """Endpoint para debug - información detallada del estado"""
    debug_info = obtener_info_debug()
    debug_info['current_token_global'] = current_token[:8] + "..." if current_token else None
    debug_info['servidor_timestamp'] = datetime.now(TZ).isoformat()
    return jsonify(debug_info)

@app.route('/registros', methods=['GET'])
def ver_registros():
    cedula     = request.args.get('cedula', default="", type=str).strip()
    start_date = request.args.get('start_date', default="", type=str)
    end_date   = request.args.get('end_date', default="", type=str)

    hoy = datetime.now().strftime("%Y-%m-%d")
    if not start_date:
        start_date = hoy
    if not end_date:
        end_date = hoy

    where_clauses = ["fecha_hora BETWEEN %s AND %s"]
    params = [f"{start_date} 00:00:00", f"{end_date} 23:59:59"]

    if cedula:
        where_clauses.append("cedula = %s")
        params.append(cedula)

    where_sql = " AND ".join(where_clauses)
    sql = f"""
        SELECT id, cedula, token, fecha_hora
          FROM registros_new
         WHERE {where_sql}
         ORDER BY fecha_hora DESC
    """

    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(sql, params)
    registros = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('registros.html',
                           registros=registros,
                           cedula=cedula,
                           start_date=start_date,
                           end_date=end_date)

@app.route('/registrar', methods=['POST'])
def registrar():
    global current_token
    try:
        # --- 1) Extraer datos ---
        if request.is_json:
            data   = request.get_json(force=True)
            cedula = data.get('cedula')
            token  = data.get('token')
        else:
            cedula = request.form.get('cedula')
            token  = request.form.get('token')

        # Información de timing para debug
        debug_info = obtener_info_debug()
        
        # Log detallado del intento de registro
        logger.info(f"📱 Intento registro - Cédula: {cedula}, "
                   f"Token: {token[:8] if token else 'None'}... "
                   f"Bucket actual: {debug_info['bucket_segundo']}s "
                   f"Segundos en bucket: {debug_info['segundos_en_bucket']}")

        # --- 2) Validaciones ---
        if not cedula or not token:
            logger.warning(f"❌ Datos incompletos - Cédula: {cedula}, Token: {'Sí' if token else 'No'}")
            return jsonify(status="error", msg="Datos incompletos"), 400

        # ⭐ VALIDACIÓN SEGURA CON SINCRONIZACIÓN MEJORADA
        if not validar_token_con_precision(token):
            # Log detallado para debug del problema de timing
            logger.warning(f"❌ Token inválido para cédula {cedula}. "
                          f"Token recibido: {token[:8]}... "
                          f"Token actual: {debug_info['token_actual'][:8]}... "
                          f"Bucket segundo: {debug_info['bucket_segundo']} "
                          f"Segundos en bucket: {debug_info['segundos_en_bucket']} "
                          f"Micro-tolerancia activa: {debug_info['micro_tolerancia_activa']} "
                          f"Timestamp bucket: {debug_info['timestamp_bucket']}")
            return jsonify(status="error", msg="QR inválido o expirado"), 403

        # --- 3) Conexión a la base ---
        try:
            conn = get_db_connection()
        except MySQLError as e:
            logger.error(f"🔴 Fallo al conectar a la BD: {e}")
            return jsonify(status="error", msg="Error de conexión a la base de datos"), 500

        # --- 4) Inserción segura ---
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO registros_new (cedula, token, fecha_hora)
                VALUES (%s, %s, %s)
            """
            ts = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(sql, (cedula, token, ts))
            conn.commit()

        conn.close()
        
        # Log de éxito con información de timing
        logger.info(f"✅ Registro exitoso - Cédula: {cedula}, "
                   f"Timestamp: {ts}, "
                   f"Bucket usado: {debug_info['bucket_segundo']}s")
        
        return jsonify(status="ok"), 200

    except MySQLError as e:
        logger.error(f"🔴 MySQL Error en /registrar: {e}")
        return jsonify(status="error", msg="Error de base de datos"), 500

    except Exception as e:
        logger.exception(f"🔴 Error inesperado en /registrar: {e}")
        return jsonify(status="error", msg="Error interno del servidor"), 500

if __name__ == "__main__":
    logger.info("🚀 Iniciando servidor de timbrado con sincronización precisa...")
    logger.info("🔒 Modo seguro: Solo acepta tokens del bucket actual + micro-tolerancia de 2s")
    app.run(host="0.0.0.0", port=5050, debug=True)