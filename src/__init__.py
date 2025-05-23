# src/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

from .config import Config

# ---------- instancias únicas ----------
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

# ---------- factory ----------
def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    # inicializar extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # ajustes de Flask-Login
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    # registrar blueprints
    from src.routes import (
        main_bp,
        user_bp,
        admin_bp,
        api_bp,  
        service_assignment_bp,
        client_notifications_bp,
    )
    app.register_blueprint(main_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(service_assignment_bp)
    app.register_blueprint(client_notifications_bp)
    app.register_blueprint(api_bp)

        # ---- DEBUG: imprimir rutas una vez en los logs ----
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        app.logger.info("ROUTE  ->  %-40s  ENDPOINT -> %s", rule.rule, rule.endpoint)

    # carpeta de uploads
    import os
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # user_loader
    from src.models import User

    @login_manager.user_loader
    def load_user(user_id: str | int):
        return User.query.get(int(user_id))

    # carga de modelos para Alembic
    with app.app_context():
        import src.models  # noqa: F401

    # health-check
    @app.route("/health")
    def health():
        return "pong", 200

    return app
