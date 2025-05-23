from .main import main_bp
from .user import user_bp
from .admin import admin_bp
from .service_assignment import service_assignment_bp
from .client_notifications import client_notifications_bp

__all__ = [
    "main_bp",
    "user_bp",
    "admin_bp",
    "api_bp",
    "service_assignment_bp",
    "client_notifications_bp",
]

