from flask import Blueprint, jsonify, request, render_template
from src import db                       # ← la única instancia
from src.models import User              # ← modelo desde el paquete
from src.utils.geocode import reverse_geocode_osm

user_bp = Blueprint("user_bp", __name__)   # usa el mismo nombre que registras

# ---------- CRUD de usuarios ----------

@user_bp.route("/users", methods=["GET"])
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

@user_bp.route("/users", methods=["POST"])
def create_user():
    data = request.json
    user = User(username=data["username"], email=data["email"])
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201

@user_bp.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())

@user_bp.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.json
    user.username = data.get("username", user.username)
    user.email = data.get("email", user.email)
    db.session.commit()
    return jsonify(user.to_dict())

@user_bp.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return "", 204

# ---------- Solicitud de grúa ----------

@user_bp.route("/submit_service_request", methods=["POST"])
def submit_service_request():
    current_location_raw = request.form.get("current_location")
    destination         = request.form.get("destination")
    vehicle_type        = request.form.get("vehicle_type")

    # Si vienen coordenadas GPS, haz reverse-geocoding
    if current_location_raw and current_location_raw.startswith("Lat:"):
        try:
            lat, lon = (float(s.strip()) for s in
                        current_location_raw.replace("Lat:", "")
                                            .replace("Lon:", "")
                                            .split(","))
            current_location = reverse_geocode_osm(lat, lon)
        except Exception as e:
            print("Error geocoding:", e)
            current_location = "Unknown"
    else:
        current_location = current_location_raw or "Unknown"

    return render_template(
        "confirmation.html",
        direccion=current_location,
        destino=destination,
        vehiculo=vehicle_type,
    )
