import os
from datetime import timedelta

class Config:
    # Básico
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_key')
    
    # Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    database_url = os.environ.get('DATABASE_URL')
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = database_url or 'sqlite:///app.db'
    
    # Upload
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
