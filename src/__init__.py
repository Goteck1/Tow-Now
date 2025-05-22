import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

# Importar configuración
from .config import Config
app.config.from_object(Config)

# Inicializar extensiones
db = SQLAlchemy()
login_manager = LoginManager()
migrate = None

def create_app(config_class: type = Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inicializar extensiones
    db.init_app(app)
    login_manager.init_app(app)
    migrate = Migrate(app, db)

    # Configurar login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # Registrar blueprints
    from src.routes import main_bp, user_bp, admin_bp, service_assignment_bp, client_notifications_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(service_assignment_bp)
    app.register_blueprint(client_notifications_bp)

    # Crear carpeta de uploads si no existe
    import os
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    return app
