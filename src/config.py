import os
from datetime import timedelta

class Config:
    # Básico
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_key')

    # Configuración del entorno
    ENV = os.environ.get('FLASK_ENV', 'production')
    DEBUG = ENV == 'development'

    # Base de datos
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    _raw_db_url = os.environ.get('DATABASE_URL')

    if _raw_db_url and _raw_db_url.startswith('postgres://'):
        _raw_db_url = _raw_db_url.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_DATABASE_URI = _raw_db_url or 'sqlite:///app.db'

    # Archivos subidos
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'src', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

    # Sesiones (opcional, si lo usas)
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
