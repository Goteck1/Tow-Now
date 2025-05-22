# src/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

# 1) Importación RELATIVA; Config vive en este mismo paquete.
from .config import Config

# 2) Extensiones se instancian una sola vez a nivel módulo.
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()          # sin argumentos; se enlazará luego con init_app()

def create_app(config_class: type = Config) -> Flask:
    # 3) Crea la aplicación
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 4) Inicializa extensiones
    db.init_app(app)
    migrate.init_app(app, db)        # ahora sí les pasamos app y db
    login_manager.init_app(app)

    # 5) Configura LoginManager
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    # 6) Registra blueprints
    from src.routes import (
        main_bp,
        user_bp,
        admin_bp,
        service_assignment_bp,
        client_notifications_bp,
    )
    app.register_blueprint(main_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(service_assignment_bp)
    app.register_blueprint(client_notifications_bp)

    # Crea carpeta de uploads si no existe
    import os
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    return app
