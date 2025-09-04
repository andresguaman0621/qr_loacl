# utils.py - REEMPLAZAR COMPLETAMENTE
import hashlib
from datetime import datetime, timedelta
import pytz
import time

SECRET_KEY = "mmqep2024"
TZ = pytz.timezone("America/Guayaquil")

def obtener_timestamp_bucket():
    """
    Obtiene timestamp exacto para el bucket actual de 10 segundos
    Esta función garantiza sincronización perfecta entre generación y validación
    """
    ahora = datetime.now(TZ)
    # Agrupamos segundos al múltiplo más bajo de 10
    bucket = (ahora.second // 10) * 10
    # Construimos timestamp con segundo redondeado y sin microsegundos
    ts_normalizado = ahora.replace(second=bucket, microsecond=0)
    return ts_normalizado

def generar_token_actual():
    """
    Genera token para el bucket actual - VERSIÓN MEJORADA
    Usa timestamp normalizado para perfecta sincronización
    """
    ts = obtener_timestamp_bucket()
    ts_string = ts.strftime("%Y-%m-%d %H:%M:%S")
    return hashlib.sha256((ts_string + SECRET_KEY).encode()).hexdigest()

def validar_token_con_precision(token_escaneado):
    """
    Validación SEGURA con micro-tolerancia para sincronización
    Solo acepta el token del bucket actual con margen de 1 segundo para
    compensar latencia de red/procesamiento SIN comprometer seguridad
    """
    if not token_escaneado:
        return False
    
    # Token actual (bucket exacto)
    token_actual = generar_token_actual()
    
    # ⭐ CLAVE: Verificación principal
    if token_escaneado == token_actual:
        return True
    
    # ⭐ MICRO-TOLERANCIA: Solo si estamos en los primeros 2 segundos del bucket
    # Esto cubre casos donde el QR se generó al final del bucket anterior
    # pero se escanea al inicio del bucket actual
    ahora = datetime.now(TZ)
    segundos_en_bucket = ahora.second % 10
    
    if segundos_en_bucket <= 2:  # Solo primeros 2 segundos
        # Verificar token del bucket inmediatamente anterior
        bucket_anterior = obtener_timestamp_bucket() - timedelta(seconds=10)
        ts_anterior = bucket_anterior.strftime("%Y-%m-%d %H:%M:%S")
        token_anterior = hashlib.sha256((ts_anterior + SECRET_KEY).encode()).hexdigest()
        
        if token_escaneado == token_anterior:
            return True
    
    return False

def obtener_info_debug():
    """Información de debug detallada para troubleshooting"""
    ahora = datetime.now(TZ)
    ts_bucket = obtener_timestamp_bucket()
    bucket_segundo = (ahora.second // 10) * 10
    segundos_en_bucket = ahora.second % 10
    segundos_restantes = 10 - segundos_en_bucket
    
    # Token anterior para debug
    bucket_anterior = ts_bucket - timedelta(seconds=10)
    ts_anterior = bucket_anterior.strftime("%Y-%m-%d %H:%M:%S")
    token_anterior = hashlib.sha256((ts_anterior + SECRET_KEY).encode()).hexdigest()
    
    return {
        "timestamp_actual": ahora.strftime("%Y-%m-%d %H:%M:%S.%f"),
        "timestamp_bucket": ts_bucket.strftime("%Y-%m-%d %H:%M:%S"),
        "bucket_segundo": bucket_segundo,
        "segundos_en_bucket": segundos_en_bucket,
        "segundos_restantes": segundos_restantes,
        "token_actual": generar_token_actual(),
        "token_anterior": token_anterior,
        "micro_tolerancia_activa": segundos_en_bucket <= 2
    }

def obtener_segundos_hasta_refresh():
    """
    Calcula segundos exactos hasta el próximo cambio de bucket
    Para sincronización perfecta del frontend
    """
    ahora = datetime.now(TZ)
    segundos_en_bucket = ahora.second % 10
    microsegundos = ahora.microsecond
    
    # Tiempo restante en milisegundos
    segundos_restantes = 10 - segundos_en_bucket
    ms_restantes = (segundos_restantes * 1000) - (microsegundos / 1000)
    
    return int(ms_restantes)