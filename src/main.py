import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, Blueprint
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
import datetime

# --- App and DB Setup ---
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), 'static')
)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'a_very_secret_key_that_should_be_changed_in_production_v2_fixed')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', "postgresql://townow_db_user:JYglVB26lGurbXdGemaj3EgkillpKV0N@dpg-d0hgfb3uibrs739ni9tg-a/townow_db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Login Manager ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'main.signin'
login_manager.login_message = "Please sign in to access this page, or continue as a guest if available."
login_manager.login_message_category = "info"

# --- Database Models ---
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    user_type = db.Column(db.String(20), nullable=False, default='customer') # 'customer', 'provider', 'admin'
    is_admin = db.Column(db.Boolean, default=False)
    # Provider-specific fields
    service_zones_json = db.Column(db.Text, nullable=True)
    accepted_vehicle_types_json = db.Column(db.Text, nullable=True)
    is_available = db.Column(db.Boolean, nullable=True, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_service_zones(self):
        if self.service_zones_json:
            try:
                return json.loads(self.service_zones_json)
            except json.JSONDecodeError:
                return []
        return []

    def set_service_zones(self, zones_list):
        self.service_zones_json = json.dumps(zones_list)

    def get_accepted_vehicle_types(self):
        if self.accepted_vehicle_types_json:
            try:
                return json.loads(self.accepted_vehicle_types_json)
            except json.JSONDecodeError:
                return []
        return []

    def set_accepted_vehicle_types(self, vehicle_types_list):
        self.accepted_vehicle_types_json = json.dumps(vehicle_types_list)

class ServiceRequest(db.Model):
    __tablename__ = 'service_requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    guest_name = db.Column(db.String(100), nullable=True)
    guest_phone = db.Column(db.String(20), nullable=True)
    current_location = db.Column(db.String(255), nullable=False)
    current_location_zone = db.Column(db.String(50), nullable=True)
    destination = db.Column(db.String(255), nullable=False)
    destination_zone = db.Column(db.String(50), nullable=True)
    vehicle_type = db.Column(db.String(50), nullable=False)
    vehicle_other = db.Column(db.String(100))
    vehicle_details = db.Column(db.String(255))
    status = db.Column(db.String(50), default='Pending Payment')
    price = db.Column(db.Float)
    price_breakdown_json = db.Column(db.Text, nullable=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('service_requests_made', lazy='dynamic'))
    provider = db.relationship('User', foreign_keys=[provider_id], backref=db.backref('service_requests_assigned', lazy='dynamic'))

class PricingConfig(db.Model):
    __tablename__ = 'pricing_config'
    id = db.Column(db.Integer, primary_key=True)
    fixed_base_fare = db.Column(db.Float, nullable=False, default=10.0)
    fare_per_km = db.Column(db.Float, nullable=False, default=1.2)
    fare_per_minute = db.Column(db.Float, nullable=False, default=0.3)
    vehicle_types_json = db.Column(db.Text, nullable=False)
    time_coefficients_json = db.Column(db.Text, nullable=False)
    traffic_coefficient = db.Column(db.Float, nullable=False, default=1.3)
    admin_commission_percentage = db.Column(db.Float, nullable=False, default=0.25)
    base_unit_zone_fallback = db.Column(db.Float, nullable=True, default=50.0)
    zones_json = db.Column(db.Text, nullable=True)
    weights_zone_fallback_json = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def default_vehicle_types(self):
        return json.dumps({
            "sedan": 1.0, "suv": 1.3, "truck": 1.5, "motorcycle": 0.8,
            "van": 1.4, "electric": 1.2, "other": 1.2
        })

    def default_time_coefficients(self):
        return json.dumps({
            "peak_hours": {"coef": 1.2, "ranges": [[7, 10], [16, 19]]},
            "night_hours": {"coef": 1.5, "ranges": [[22, 24], [0, 6]]},
            "off_peak": {"coef": 1.0}
        })
    
    def default_zones(self):
        return json.dumps({
            "D1": { "origin": 1.3, "destination": 1.2 }, "D2": { "origin": 1.3, "destination": 1.2 },
            "D3": { "origin": 1.2, "destination": 1.1 }, "D4": { "origin": 1.3, "destination": 1.2 },
            "D5": { "origin": 1.2, "destination": 1.1 }, "D6": { "origin": 1.2, "destination": 1.1 },
            "D6W": { "origin": 1.2, "destination": 1.1 }, "D7": { "origin": 1.2, "destination": 1.1 },
            "D8": { "origin": 1.2, "destination": 1.1 }, "D9": { "origin": 1.2, "destination": 1.1 },
            "D10": { "origin": 1.1, "destination": 1.0 }, "D11": { "origin": 1.1, "destination": 1.0 },
            "D12": { "origin": 1.1, "destination": 1.0 }, "D13": { "origin": 1.1, "destination": 1.0 },
            "D14": { "origin": 1.1, "destination": 1.0 }, "D15": { "origin": 1.1, "destination": 1.0 },
            "D16": { "origin": 1.1, "destination": 1.0 }, "D17": { "origin": 1.1, "destination": 1.0 },
            "D18": { "origin": 1.2, "destination": 1.1 }, "D20": { "origin": 1.2, "destination": 1.1 },
            "D22": { "origin": 1.2, "destination": 1.1 }, "D24": { "origin": 1.3, "destination": 1.2 },
            "Lucan": { "origin": 1.0, "destination": 1.0 }, "Swords": { "origin": 1.0, "destination": 1.0 },
            "Malahide": { "origin": 1.1, "destination": 1.1 }, "Blanchardstown": { "origin": 1.1, "destination": 1.1 },
            "Baldoyle": { "origin": 1.1, "destination": 1.1 }, "Portmarnock": { "origin": 1.1, "destination": 1.1 },
            "Skerries": { "origin": 1.4, "destination": 1.4 }, "Howth": { "origin": 1.3, "destination": 1.3 },
            "Clondalkin": { "origin": 1.2, "destination": 1.1 }, "Tallaght": { "origin": 1.3, "destination": 1.2 },
            "Rathfarnham": { "origin": 1.2, "destination": 1.1 }, "Balbriggan": { "origin": 1.5, "destination": 1.5 },
            "Bray": { "origin": 1.5, "destination": 1.5 }, "Maynooth": { "origin": 1.6, "destination": 1.6 },
            "Outside": { "origin": 2.0, "destination": 2.0 }
        })

    def default_weights_zone_fallback(self):
        return json.dumps({
            "origin_zone": 0.25, "destination_zone": 0.25, "traffic": 0.25, "time": 0.25
        })

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Notification model ---
from models.notification import init_notification_model
Notification = init_notification_model(db)

# --- Database Initialization ---
def initialize_database():
    with app.app_context():
        db.create_all()
        # Default admin
        if not User.query.filter_by(email='admin@townow.local').first():
            admin_user = User(fullname='Admin User', email='admin@townow.local', user_type='admin', is_admin=True)
            admin_user.set_password('adminpass')
            db.session.add(admin_user)
            print("Default admin user created.")

        # Default pricing config
        if not PricingConfig.query.first():
            default_config = PricingConfig(
                fixed_base_fare=10.0,
                fare_per_km=1.2,
                fare_per_minute=0.3,
                traffic_coefficient=1.3,
                admin_commission_percentage=0.25,
                base_unit_zone_fallback=50.0
            )
            default_config.vehicle_types_json = default_config.default_vehicle_types()
            default_config.time_coefficients_json = default_config.default_time_coefficients()
            default_config.zones_json = default_config.default_zones()
            default_config.weights_zone_fallback_json = default_config.default_weights_zone_fallback()
            db.session.add(default_config)
            print("Default pricing configuration initialized.")

        db.session.commit()
initialize_database()

# --- Helper Function ---
def calculate_provider_profit(total_price, admin_commission_percentage):
    if admin_commission_percentage < 0 or admin_commission_percentage > 1:
        pass
    provider_share = 1 - admin_commission_percentage
    return round(total_price * provider_share, 2)

# --- Pricing logic ---
from pricing_logic import calculate_dynamic_price

app.config['db'] = db
app.config['User'] = User
app.config['ServiceRequest'] = ServiceRequest
app.config['PricingConfig'] = PricingConfig
app.config['Notification'] = Notification

# --- Main Blueprint (UNIFICADO) ---
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    return render_template('home.html')

@main_bp.route('/contact')
def contact():
    return render_template('contact.html')

@main_bp.route('/qa')
def qa():
    return render_template('qa.html')

@main_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        user_type = request.form.get('user_type')

        if not all([fullname, email, password, confirm_password, user_type]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('main.signup'))
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('main.signup'))
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email address is already registered.', 'warning')
            return redirect(url_for('main.signup'))
        new_user = User(fullname=fullname, email=email, user_type=user_type)
        new_user.set_password(password)
        if user_type == 'provider':
            new_user.service_zones_json = json.dumps([])
            new_user.accepted_vehicle_types_json = json.dumps([])
            new_user.is_available = True
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully. You can now sign in.', 'success')
        return redirect(url_for('main.signin'))
    return render_template('signup.html')

@main_bp.route('/signin', methods=['GET', 'POST'])
def signin():
    if current_user.is_authenticated:
        if current_user.user_type == 'provider' and not current_user.is_admin:
            return redirect(url_for('main.service_provider_home'))
        elif current_user.is_admin:
            return redirect(url_for('admin_bp.dashboard'))
        else:
            return redirect(url_for('main.user_home'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Sign in successful.', 'success')
            if user.is_admin:
                return redirect(url_for('admin_bp.dashboard'))
            elif user.user_type == 'provider':
                return redirect(url_for('main.service_provider_home'))
            else:
                return redirect(url_for('main.user_home'))
        else:
            flash('Incorrect email or password.', 'danger')
    return render_template('signin.html')

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been signed out.', 'info')
    return redirect(url_for('main.home'))

@main_bp.route('/user_home')
@login_required
def user_home():
    if current_user.user_type != 'customer' or current_user.is_admin:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))
    return render_template('user_home.html', user=current_user)

@main_bp.route('/provider_profile', methods=['GET', 'POST'])
@login_required
def provider_profile():
    if current_user.user_type != 'provider' or current_user.is_admin:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))
    pricing_config = PricingConfig.query.first()
    all_zones = []
    all_vehicle_types = {}
    if pricing_config:
        try:
            zones_data = json.loads(pricing_config.zones_json)
            all_zones = list(zones_data.keys())
            vehicle_types_data = json.loads(pricing_config.vehicle_types_json)
            all_vehicle_types = vehicle_types_data
        except (json.JSONDecodeError, AttributeError):
            pass
    if request.method == 'POST':
        selected_zones = request.form.getlist('service_zones')
        selected_vehicle_types = request.form.getlist('vehicle_types')
        is_available = 'is_available' in request.form
        current_user.set_service_zones(selected_zones)
        current_user.set_accepted_vehicle_types(selected_vehicle_types)
        current_user.is_available = is_available
        db.session.commit()
        flash('Provider profile updated successfully!', 'success')
        return redirect(url_for('main.provider_profile'))
    provider_zones = current_user.get_service_zones()
    provider_vehicle_types = current_user.get_accepted_vehicle_types()
    return render_template('provider_profile.html',
        provider=current_user,
        all_zones=all_zones,
        provider_zones=provider_zones,
        all_vehicle_types=all_vehicle_types,
        provider_vehicle_types=provider_vehicle_types)

@main_bp.route('/service_provider_home')
@login_required
def service_provider_home():
    if current_user.user_type != 'provider' or current_user.is_admin:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))
    return render_template('service_provider_home.html', provider=current_user)

@main_bp.route('/service_request', methods=['GET'])
def service_request():
    is_guest = request.args.get('guest') == 'True'
    return render_template('service_request.html', guest=is_guest)

@main_bp.route('/submit_service_request', methods=['POST'])
def submit_service_request():
    is_guest_checkout = 'guest_checkout' in request.form
    user_id = None
    guest_name_form = None
    guest_phone_form = None
    if not is_guest_checkout:
        if not current_user.is_authenticated:
            flash('Please sign in or continue as guest to request a service.', 'warning')
            return redirect(url_for('main.service_request'))
        if current_user.user_type == 'provider':
            flash('Service providers cannot request services.', 'warning')
            return redirect(url_for('main.service_provider_home'))
        user_id = current_user.id
    else:
        guest_name_form = request.form.get('guest_name')
        guest_phone_form = request.form.get('guest_phone')
        if not guest_name_form or not guest_phone_form:
            flash('Guest name and phone are required for guest checkout.', 'danger')
            return redirect(url_for('main.service_request', guest="True"))

    current_location_full = request.form.get('current_location_address')
    destination_full = request.form.get('destination_address')
    vehicle_type = request.form.get('vehicle_type')
    vehicle_other = request.form.get('vehicle_other') if vehicle_type == 'other' else None
    vehicle_details = request.form.get('vehicle_details')
    try:
        origin_lng = float(request.form.get('current_location_lng'))
        origin_lat = float(request.form.get('current_location_lat'))
        dest_lng = float(request.form.get('destination_lng'))
        dest_lat = float(request.form.get('destination_lat'))
    except (TypeError, ValueError):
        flash('Invalid location coordinates. Please re-select locations.', 'danger')
        redirect_url = url_for('main.service_request', guest="True") if is_guest_checkout else url_for('main.service_request')
        return redirect(redirect_url)
    current_location_zone_form = request.form.get('current_location_zone', 'Outside')
    destination_zone_form = request.form.get('destination_zone', 'Outside')
    if not all([current_location_full, destination_full, vehicle_type, origin_lng, origin_lat, dest_lng, dest_lat]):
        flash('Please complete all required fields (locations, vehicle type, and ensure coordinates are set).', 'danger')
        redirect_url = url_for('main.service_request', guest="True") if is_guest_checkout else url_for('main.service_request')
        return redirect(redirect_url)
    origin_coords = (origin_lng, origin_lat)
    destination_coords = (dest_lng, dest_lat)
    try:
        current_pricing_config = PricingConfig.query.first()
        if not current_pricing_config:
            return jsonify({"error": "Pricing configuration not found in database at submission."}), 500
        price_data = calculate_dynamic_price(origin_coords, destination_coords, vehicle_type, current_pricing_config)
        if price_data.get("error"):
            app.logger.error(f"Error from pricing logic: {price_data.get('error')} - Breakdown: {price_data.get('breakdown')}")
            flash(f"Error calculating service price: {price_data.get('error')}. Please try again or contact support.", 'danger')
            redirect_url = url_for('main.service_request', guest="True") if is_guest_checkout else url_for('main.service_request')
            return redirect(redirect_url)
        estimated_price = price_data['price']
        price_breakdown_str = json.dumps(price_data['breakdown'])
    except Exception as e:
        app.logger.error(f"Error calculating price during submission: {e}")
        flash('Error calculating service price. Please try again or contact support.', 'danger')
        redirect_url = url_for('main.service_request', guest="True") if is_guest_checkout else url_for('main.service_request')
        return redirect(redirect_url)
    new_request = ServiceRequest(
        user_id=user_id,
        guest_name=guest_name_form,
        guest_phone=guest_phone_form,
        current_location=current_location_full,
        current_location_zone=current_location_zone_form,
        destination=destination_full,
        destination_zone=destination_zone_form,
        vehicle_type=vehicle_type,
        vehicle_other=vehicle_other,
        vehicle_details=vehicle_details,
        price=estimated_price,
        price_breakdown_json=price_breakdown_str,
        status='Pending Assignment'
    )
    db.session.add(new_request)
    db.session.commit()
    # Iniciar proceso de asignación
    from utils.service_assignment import find_matching_providers, send_service_alerts
    matching_providers = find_matching_providers(new_request, db, User)
    if matching_providers:
        notifications_sent = send_service_alerts(new_request, matching_providers, db, Notification, current_pricing_config)
        app.logger.info(f"Solicitud {new_request.id}: {notifications_sent} proveedores notificados.")
    else:
        new_request.status = 'No Provider Available'
        db.session.commit()
        app.logger.warning(f"Solicitud {new_request.id}: No hay proveedores disponibles que coincidan.")
    if is_guest_checkout:
        flash(f'Guest request received (ID: {new_request.id}). Price: €{estimated_price:.2f}. Status: {new_request.status}. We will contact you at {guest_phone_form}. Searching for providers...', 'success')
        return redirect(url_for('main.home')) 
    else:
        flash(f'Request received (ID: {new_request.id}). Price: €{estimated_price:.2f}. Status: {new_request.status}. Searching for providers...', 'success')
        return redirect(url_for('main.user_home'))

@main_bp.route('/service_provider_dashboard')
@login_required
def service_provider_dashboard():
    if current_user.user_type != 'provider' or current_user.is_admin:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))
    active_requests_data = []
    return render_template('service_provider_dashboard.html', active_requests=active_requests_data, provider=current_user)

@main_bp.route('/calculate_price', methods=['GET'])
def get_price_estimate():
    try:
        origin_lng = request.args.get('origin_lng', type=float)
        origin_lat = request.args.get('origin_lat', type=float)
        dest_lng = request.args.get('dest_lng', type=float)
        dest_lat = request.args.get('dest_lat', type=float)
        vehicle_type = request.args.get('vehicle_type')
        if not all([origin_lng, origin_lat, dest_lng, dest_lat, vehicle_type]):
            return jsonify({"error": "Missing required parameters: origin_lng, origin_lat, dest_lng, dest_lat, vehicle_type"}), 400
        origin_coords = (origin_lng, origin_lat)
        destination_coords = (dest_lng, dest_lat)
        current_pricing_config = PricingConfig.query.first()
        if not current_pricing_config:
            return jsonify({"error": "Pricing configuration not found in database."}), 500
        price_details = calculate_dynamic_price(origin_coords, destination_coords, vehicle_type, current_pricing_config)
        if price_details.get("price") and not price_details.get("error"):
            price_details["provider_profit_estimate"] = calculate_provider_profit(
                price_details["price"],
                current_pricing_config.admin_commission_percentage
            )
            price_details["admin_commission_percentage"] = current_pricing_config.admin_commission_percentage
        return jsonify(price_details)
    except ValueError:
        return jsonify({"error": "Invalid coordinate format. Longitude and latitude must be numbers."}), 400
    except Exception as e:
        app.logger.error(f"Error calculating price: {e}")
        return jsonify({"error": "Could not calculate price", "details": str(e)}), 500

# --- Register Blueprints ---
from routes.admin import admin_bp
from routes.service_assignment import service_assignment_bp
from routes.client_notifications import client_notifications_bp

#-app.register_blueprint(main_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(service_assignment_bp, url_prefix='/service')
app.register_blueprint(client_notifications_bp, url_prefix='/client')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
