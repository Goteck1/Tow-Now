# src/routes/main.py
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from flask_login import (
    login_required,
    current_user,
    login_user,
    logout_user,
)

from src import db

main_bp = Blueprint("main_bp", __name__)

# ---------- páginas públicas ----------------------------------------------

@main_bp.route("/")
def home():
    return render_template("home.html")


@main_bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        # procesar formulario de contacto
        name = request.form.get("name")
        email = request.form.get("email")
        subject = request.form.get("subject")
        message = request.form.get("message")
        # TODO: enviar correo o guardar msg
        flash("Thank you for contacting us! We will get back to you soon.", "success")
        return redirect(url_for("main_bp.contact"))
    return render_template("contact.html")


# ---------- autenticación --------------------------------------------------

@main_bp.route("/signin", methods=["GET", "POST"])
def signin():
    from src.models.user import User  # evita import circular

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Signed in successfully.", "success")
            return redirect(url_for("main_bp.home"))
        flash("Invalid email or password.", "danger")
    return render_template("signin.html")


@main_bp.route("/signup", methods=["GET", "POST"])
def signup():
    from src.models.user import User

    if request.method == "POST":
        fullname = request.form.get("fullname")
        email = request.form.get("email")
        password = request.form.get("password")
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "warning")
            return redirect(url_for("main_bp.signup"))
        user = User(fullname=fullname, email=email, user_type="customer")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Account created successfully. Please sign in.", "success")
        return redirect(url_for("main_bp.signin"))
    return render_template("signup.html")


@main_bp.route("/signout")
@login_required
def signout():
    logout_user()
    flash("Signed out successfully.", "info")
    return redirect(url_for("main_bp.home"))


# ---------- vistas de usuario ---------------------------------------------

@main_bp.route("/user_home")
@login_required
def user_home():
    return render_template("user_home.html")


@main_bp.route("/service_request", methods=["GET", "POST"])
@login_required
def service_request():
    """
    Página donde el usuario crea una solicitud de grúa.
    GET  -> muestra formulario (service_request.html)
    POST -> procesa la solicitud y guarda en la BD
    """
    from src.models.service_request import ServiceRequest

    if request.method == "POST":
        current_location = request.form.get("current_location")
        destination = request.form.get("destination")
        vehicle_type = request.form.get("vehicle_type")

        req = ServiceRequest(
            user_id=current_user.id,
            current_location=current_location,
            destination=destination,
            vehicle_type=vehicle_type,
            status="pending",
        )
        db.session.add(req)
        db.session.commit()

        flash("Service request submitted!", "success")
        return redirect(url_for("main_bp.user_home"))

    # método GET
    return render_template("service_request.html")


# ---------- otros ----------------------------------------------------------

@main_bp.route("/qa")
def qa():
    return render_template("qa.html")
