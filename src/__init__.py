from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()

def create_app(config_object=None):
    app = Flask(__name__)

    # Configurar la aplicación
    if config_object:
        app.config.from_object(config_object)
    else:
        # Config por defecto, puedes ajustar esto según tu config.py
        app.config.from_pyfile("config.py", silent=True)

    # Inicializar extensiones
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "main.signin"
    login_manager.login_message = "Please sign in to access this page, or continue as a guest if available."
    login_manager.login_message_category = "info"

    # Importar y registrar Blueprints
    from .routes.main import main_bp
    from .routes.user import user_bp
    from .routes.admin import admin_bp
    from .routes.service_assignment import service_assignment_bp
    from .routes.client_notifications import client_notifications_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(user_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(service_assignment_bp, url_prefix="/service")
    app.register_blueprint(client_notifications_bp, url_prefix="/client")

    # Configurar el loader de usuario para Flask-Login
    from .models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app
