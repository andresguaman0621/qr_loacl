# db.py
import os
import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    'host':     os.getenv('DB_HOST', 'localhost'),
    'port':     int(os.getenv('DB_PORT', 5432)),
    'user':     os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'root'),
    'dbname':   os.getenv('DB_NAME', 'mmqepgob_qr'),
}

def get_db_connection():
    return psycopg2.connect(cursor_factory=RealDictCursor, **DB_CONFIG)
