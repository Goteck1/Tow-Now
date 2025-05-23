# src/routes/api.py
from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user
from src import db
from src.models import User, ServiceRequest
from src.models.pricing_logic import calculate_dynamic_price

api_bp = Blueprint("api_bp", __name__, url_prefix="/api")

# ---------- Health ----------
@api_bp.route("/health")
def health_check():
    return jsonify({"status": "ok"})

# ---------- Users ----------
@api_bp.route("/users", methods=["GET"])
@login_required
def api_users():
    if not current_user.is_admin:
        abort(403)
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])

# … COPIA aquí los demás endpoints /api/users/<id>, /api/service_requests, /api/pricing/calculate, etc.
