# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Flask-based QR code attendance system that generates time-sensitive QR codes for secure check-ins. The system uses a 10-second token rotation mechanism with micro-tolerances to prevent replay attacks while accommodating network latency.

## Development Commands

- **Run the application**: `python app.py` (runs on port 5050)
- **Install dependencies**: `pip install -r requirements.txt`
- **Activate virtual environment**: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)

## Architecture

### Core Components

- **app.py**: Main Flask application with routes for QR generation, validation, and registration
- **utils.py**: Token generation and validation logic with timestamp bucketing
- **db.py**: Database connection utilities (PostgreSQL via psycopg2, though app.py uses PyMySQL)
- **templates/**: HTML templates for UI (index.html, qr.html, registros.html)

### Security Model

The system uses a "bucket-based" token system:
- Tokens are generated using SHA256 hash of (timestamp + SECRET_KEY)
- Timestamps are normalized to 10-second buckets (e.g., 13:45:10, 13:45:20, etc.)
- Micro-tolerance: Accepts previous bucket token only in first 2 seconds of current bucket
- This prevents replay attacks while handling network/processing delays

### Database Schema

- **Table**: `registros_new`
- **Fields**: `id`, `cedula`, `token`, `fecha_hora`
- **Note**: There's a mismatch - `db.py` configures PostgreSQL but `app.py` uses PyMySQL for MySQL

### Authentication

- HTTP Basic Auth for admin routes (/qr, /qr_image, /api/timing, /debug/token)
- Username: "admin", Password: "MMqep2025"
- Public routes: /, /registros, /registrar

## Key Technical Details

### Environment Variables
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- Timezone: "America/Guayaquil"
- Secret key: "mmqep2024" (hardcoded in utils.py)

### Token Lifecycle
1. `generar_token_actual()` creates token for current 10-second bucket
2. `validar_token_con_precision()` validates with micro-tolerance
3. Frontend auto-refreshes QR every 10 seconds using `/api/timing`

### Frontend Features
- Real-time QR code scanner using html5-qrcode library
- Cedula validation (10 digits)
- Auto-refresh mechanism to prevent stale QR codes
- Responsive design with background image

## Database Configuration Issue

**Important**: The codebase has inconsistent database configuration:
- `db.py` uses psycopg2 for PostgreSQL
- `app.py` uses pymysql for MySQL
- When working with database code, clarify which database system is actually being used