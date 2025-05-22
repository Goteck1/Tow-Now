import os
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from datetime import datetime

#Crear la aplicacion
from src import create_app, db
app = create_app()

# Importar modelos después de crear la aplicación
from src.models.user import User
from src.models.service_request import ServiceRequest
from src.models.pricing_logic import calculate_price  # Asumiendo que tienes esta función

from src.routes import main_bp, user_bp, admin_bp, service_assignment_bp, client_notifications_bp

# --- Flask App Factory Pattern ---
app = create_app()
migrate = Migrate(app, db)

# --- User Loader for Flask-Login ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Error Handlers ---
@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# --- Home Route (Redirección) ---
@app.route("/")
def root():
    return redirect(url_for("main.home"))

# --- Static Files Serving (for development) ---
@app.route('/static/<path:filename>')
def staticfiles(filename):
    return app.send_static_file(filename)

# --- API: Health Check ---
@app.route("/api/health")
def health_check():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})

# --- API: Get All Users (Admin Only) ---
@app.route("/api/users", methods=["GET"])
@login_required
def api_users():
    if not current_user.is_admin:
        abort(403)
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])

# --- API: Get User by ID (Admin or Owner) ---
@app.route("/api/users/<int:user_id>", methods=["GET"])
@login_required
def api_user_detail(user_id):
    if not current_user.is_admin and current_user.id != user_id:
        abort(403)
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())

# --- API: Update User (Self or Admin) ---
@app.route("/api/users/<int:user_id>", methods=["PUT"])
@login_required
def api_user_update(user_id):
    if not current_user.is_admin and current_user.id != user_id:
        abort(403)
    user = User.query.get_or_404(user_id)
    data = request.json
    if "fullname" in data:
        user.fullname = data["fullname"]
    if "phone" in data:
        user.phone = data["phone"]
    db.session.commit()
    return jsonify(user.to_dict())

# --- API: Delete User (Admin Only) ---
@app.route("/api/users/<int:user_id>", methods=["DELETE"])
@login_required
def api_user_delete(user_id):
    if not current_user.is_admin:
        abort(403)
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"deleted": True})

# --- API: Create Service Request ---
@app.route("/api/service_requests", methods=["POST"])
def api_create_service_request():
    data = request.json
    if current_user.is_authenticated:
        user_id = current_user.id
        guest_name = None
        guest_phone = None
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
        status="pending"
    )
    db.session.add(req)
    db.session.commit()
    return jsonify(req.to_dict()), 201

# --- API: List Service Requests (Own or Admin) ---
@app.route("/api/service_requests", methods=["GET"])
@login_required
def api_get_service_requests():
    if current_user.is_admin:
        requests = ServiceRequest.query.order_by(ServiceRequest.created_at.desc()).all()
    else:
        requests = ServiceRequest.query.filter_by(user_id=current_user.id).order_by(ServiceRequest.created_at.desc()).all()
    return jsonify([r.to_dict() for r in requests])

# --- API: Get Service Request by ID ---
@app.route("/api/service_requests/<int:request_id>", methods=["GET"])
@login_required
def api_get_service_request(request_id):
    req = ServiceRequest.query.get_or_404(request_id)
    if not current_user.is_admin and req.user_id != current_user.id:
        abort(403)
    return jsonify(req.to_dict())

# --- API: Update Service Request (Admin Only) ---
@app.route("/api/service_requests/<int:request_id>", methods=["PUT"])
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

# --- API: Delete Service Request (Admin Only) ---
@app.route("/api/service_requests/<int:request_id>", methods=["DELETE"])
@login_required
def api_delete_service_request(request_id):
    if not current_user.is_admin:
        abort(403)
    req = ServiceRequest.query.get_or_404(request_id)
    db.session.delete(req)
    db.session.commit()
    return jsonify({"deleted": True})

# --- API: Calculate Price ---
@app.route("/api/pricing/calculate", methods=["POST"])
def api_pricing_calculate():
    data = request.json
    # Asume que tienes una función calculate_price en pricing_logic.py
    price = calculate_price(
        current_location=data["current_location"],
        destination=data["destination"],
        vehicle_type=data["vehicle_type"]
    )
    return jsonify({"price": price})

# --- User Account: Profile Page ---
@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", user=current_user)

# --- User Account: Edit Profile ---
@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        fullname = request.form.get("fullname")
        phone = request.form.get("phone")
        if fullname:
            current_user.fullname = fullname
        if phone:
            current_user.phone = phone
        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("profile"))
    return render_template("edit_profile.html", user=current_user)

# --- User Account: Change Password ---
@app.route("/profile/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")
        if not current_user.check_password(old_password):
            flash("Current password is incorrect.", "danger")
            return redirect(url_for("change_password"))
        current_user.set_password(new_password)
        db.session.commit()
        flash("Password changed successfully.", "success")
        return redirect(url_for("profile"))
    return render_template("change_password.html")

# --- Admin: Dashboard ---
@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        abort(403)
    total_users = User.query.count()
    total_requests = ServiceRequest.query.count()
    pending_requests = ServiceRequest.query.filter_by(status="pending").count()
    completed_requests = ServiceRequest.query.filter_by(status="completed").count()
    return render_template("admin/dashboard.html",
                           total_users=total_users,
                           total_requests=total_requests,
                           pending_requests=pending_requests,
                           completed_requests=completed_requests)

# --- Admin: List All Service Requests ---
@app.route("/admin/requests")
@login_required
def admin_requests():
    if not current_user.is_admin:
        abort(403)
    requests = ServiceRequest.query.order_by(ServiceRequest.created_at.desc()).all()
    return render_template("admin/requests.html", requests=requests)

# --- Admin: List Users ---
@app.route("/admin/users")
@login_required
def admin_users():
    if not current_user.is_admin:
        abort(403)
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users)

# --- Admin: Assign Provider to Request ---
@app.route("/admin/assign_provider/<int:request_id>", methods=["POST"])
@login_required
def admin_assign_provider(request_id):
    if not current_user.is_admin:
        abort(403)
    req = ServiceRequest.query.get_or_404(request_id)
    provider_id = request.form.get("provider_id")
    if provider_id:
        req.assigned_provider_id = int(provider_id)
        req.status = "assigned"
        db.session.commit()
        flash("Provider assigned.", "success")
    return redirect(url_for("admin_requests"))

# --- Admin: Update Pricing Logic (demostrativo, asume hay lógica y template) ---
@app.route("/admin/pricing", methods=["GET", "POST"])
@login_required
def admin_pricing():
    if not current_user.is_admin:
        abort(403)
    if request.method == "POST":
        # Aquí iría lógica para actualizar parámetros de pricing_logic.py
        flash("Pricing logic updated (demo).", "success")
    return render_template("admin/pricing.html")

# --- File Upload Example (User Profile Image) ---
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/profile/upload_image", methods=["POST"])
@login_required
def upload_profile_image():
    file = request.files.get("profile_image")
    if file and allowed_file(file.filename):
        filename = secure_filename(f"{current_user.id}_{file.filename}")
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)
        current_user.profile_image = filename
        db.session.commit()
        flash("Profile image updated.", "success")
    return redirect(url_for("profile"))

# --- CLI Commands: DB creation and test seeding ---
@app.cli.command("create-db")
def create_db():
    db.create_all()
    print("Database tables created.")

@app.cli.command("seed-db")
def seed_db():
    from src.models.user import User
    if not User.query.filter_by(email="admin@townow.com").first():
        admin = User(fullname="Admin TowNow", email="admin@townow.com", user_type="admin", is_admin=True)
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
        print("Admin user created.")
    else:
        print("Admin user already exists.")

# --- Run ---
if __name__ == "__main__":
    app.run(debug=True)
