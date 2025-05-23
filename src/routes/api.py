# src/routes/api.py
from datetime import datetime
from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user
from src import db
from src.models import User, ServiceRequest
from src.models.pricing_logic import calculate_dynamic_price

api_bp = Blueprint("api_bp", __name__, url_prefix="/api")

# ---------- Health ----------
@api_bp.route("/health")
def health_check():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})

# ---------- Users ----------
@api_bp.route("/users", methods=["GET"])
@login_required
def api_users():
    if not current_user.is_admin:
        abort(403)
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])

@api_bp.route("/users/<int:user_id>", methods=["GET"])
@login_required
def api_user_detail(user_id):
    if not current_user.is_admin and current_user.id != user_id:
        abort(403)
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())

@api_bp.route("/users/<int:user_id>", methods=["PUT"])
@login_required
def api_user_update(user_id):
    if not current_user.is_admin and current_user.id != user_id:
        abort(403)
    user = User.query.get_or_404(user_id)
    data = request.json
    user.fullname = data.get("fullname", user.fullname)
    user.phone = data.get("phone", user.phone)
    db.session.commit()
    return jsonify(user.to_dict())

@api_bp.route("/users/<int:user_id>", methods=["DELETE"])
@login_required
def api_user_delete(user_id):
    if not current_user.is_admin:
        abort(403)
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"deleted": True})

# ---------- Service Requests ----------
@api_bp.route("/service_requests", methods=["POST"])
def api_create_service_request():
    data = request.json
    if current_user.is_authenticated:
        user_id = current_user.id
        guest_name = guest_phone = None
    else:
        user_id = None
        guest_name = data.get("guest_name")
        guest_phone = data.get("guest_phone")

    req = ServiceRequest(
        user_id=user_id,
        guest_name=guest_name,
        guest_phone=guest_phone,
        current_location=data["current_location"],
        current_location_zone=data.get("current_location_zone"),
        destination=data["destination"],
        vehicle_type=data.get("vehicle_type"),
        status="pending",
    )
    db.session.add(req)
    db.session.commit()
    return jsonify(req.to_dict()), 201

@api_bp.route("/service_requests", methods=["GET"])
@login_required
def api_get_service_requests():
    if current_user.is_admin:
        requests = ServiceRequest.query.order_by(ServiceRequest.created_at.desc()).all()
    else:
        requests = ServiceRequest.query.filter_by(user_id=current_user.id).order_by(
            ServiceRequest.created_at.desc()
        ).all()
    return jsonify([r.to_dict() for r in requests])

@api_bp.route("/service_requests/<int:request_id>", methods=["GET"])
@login_required
def api_get_service_request(request_id):
    req = ServiceRequest.query.get_or_404(request_id)
    if not current_user.is_admin and req.user_id != current_user.id:
        abort(403)
    return jsonify(req.to_dict())

@api_bp.route("/service_requests/<int:request_id>", methods=["PUT"])
@login_required
def api_update_service_request(request_id):
    if not current_user.is_admin:
        abort(403)
    req = ServiceRequest.query.get_or_404(request_id)
    data = request.json
    for key in ["status", "assigned_provider_id", "current_location", "destination", "vehicle_type"]:
        if key in data:
            setattr(req, key, data[key])
    db.session.commit()
    return jsonify(req.to_dict())

@api_bp.route("/service_requests/<int:request_id>", methods=["DELETE"])
@login_required
def api_delete_service_request(request_id):
    if not current_user.is_admin:
        abort(403)
    req = ServiceRequest.query.get_or_404(request_id)
    db.session.delete(req)
    db.session.commit()
    return jsonify({"deleted": True})

# ---------- Pricing ----------
@api_bp.route("/pricing/calculate", methods=["POST"])
def api_pricing_calculate():
    data = request.json
    result = calculate_dynamic_price(
        origin_coords=data["current_location"],
        destination_coords=data["destination"],
        vehicle_type_key=data["vehicle_type"],
        pricing_cfg_obj=None,  # deberás pasar una instancia de PricingConfig si la tienes
    )
    return jsonify(result)
