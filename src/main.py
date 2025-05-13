import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required

app = Flask(__name__,
            static_folder=os.path.join(os.path.dirname(__file__), 'static'),
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'))

app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'a_very_secret_key_that_should_be_changed_in_production_v2')

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# LoginManager initialization
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
    user_type = db.Column(db.String(20), nullable=False, default='customer') # customer or provider
    is_admin = db.Column(db.Boolean, default=False) # For admin panel

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ServiceRequest(db.Model):
    __tablename__ = 'service_requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Nullable for guest requests
    guest_name = db.Column(db.String(100), nullable=True) # For guest checkout
    guest_phone = db.Column(db.String(20), nullable=True)  # For guest checkout
    current_location = db.Column(db.String(255), nullable=False)
    destination = db.Column(db.String(255), nullable=False)
    vehicle_type = db.Column(db.String(50), nullable=False)
    vehicle_other = db.Column(db.String(100))
    vehicle_details = db.Column(db.String(255))
    status = db.Column(db.String(50), default='Pending Payment') # e.g., Pending Payment, Paid, Assigned, En Route, Completed, Cancelled
    price = db.Column(db.Float)
    provider_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('service_requests_made', lazy='dynamic'))
    provider = db.relationship('User', foreign_keys=[provider_id], backref=db.backref('service_requests_assigned', lazy='dynamic'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes (Blueprint 'main' for modularity) ---
from flask import Blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    return render_template('home.html')

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
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully. You can now sign in.', 'success')
        return redirect(url_for('main.signin'))
    return render_template('signup.html')

@main_bp.route('/signin', methods=['GET', 'POST'])
def signin():
    if current_user.is_authenticated:
        if current_user.user_type == 'provider':
            return redirect(url_for('main.service_provider_home'))
        elif current_user.is_admin:
             return redirect(url_for('admin_bp.dashboard')) # Redirect admin to admin dashboard
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

@main_bp.route('/service_provider_home')
@login_required
def service_provider_home():
    if current_user.user_type != 'provider' or current_user.is_admin:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))
    return render_template('service_provider_home.html', provider=current_user)

@main_bp.route('/service_request', methods=['GET'])
def service_request(): # Removed @login_required
    is_guest_request = request.args.get("guest") == "True"
    
    if not is_guest_request and not current_user.is_authenticated:
        flash("Please sign in to request a service or continue as a guest.", "info")
        # Redirect to signin but allow to come back here if they sign in
        return redirect(url_for('main.signin', next=url_for('main.service_request')))

    if current_user.is_authenticated and current_user.user_type == 'provider':
        flash('Service providers cannot request services.', 'warning')
        return redirect(url_for('main.service_provider_home'))
    
    return render_template('service_request.html', guest_mode=is_guest_request)

@main_bp.route('/submit_service_request', methods=['POST'])
def submit_service_request(): # Removed @login_required
    is_guest_checkout = request.form.get("guest_checkout") == "true"
    user_id = None
    guest_name_form = None
    guest_phone_form = None

    if not is_guest_checkout:
        if not current_user.is_authenticated:
            flash("Authentication required to submit a request. Please sign in or use the guest option.", "danger")
            return redirect(url_for('main.signin', next=url_for('main.service_request')))
        if current_user.user_type == 'provider':
            flash('Service providers cannot request services.', 'warning')
            return redirect(url_for('main.service_provider_home'))
        user_id = current_user.id
    else: # Guest checkout
        guest_name_form = request.form.get('guest_name')
        guest_phone_form = request.form.get('guest_phone')
        if not guest_name_form or not guest_phone_form:
            flash('Guest name and phone number are required for guest checkout.', 'danger')
            return redirect(url_for('main.service_request', guest="True"))

    current_location = request.form.get('current_location')
    destination = request.form.get('destination')
    vehicle_type = request.form.get('vehicle_type')
    vehicle_other = request.form.get('vehicle_other') if vehicle_type == 'other' else None
    vehicle_details = request.form.get('vehicle_details')

    if not all([current_location, destination, vehicle_type]):
        flash('Please complete all required fields in the form (location, destination, vehicle type).', 'danger')
        if is_guest_checkout:
            return redirect(url_for('main.service_request', guest="True"))
        else:
            return redirect(url_for('main.service_request'))

    estimated_price = 50.00 # Fixed placeholder price in EUR

    new_request = ServiceRequest(
        user_id=user_id,
        guest_name=guest_name_form,
        guest_phone=guest_phone_form,
        current_location=current_location,
        destination=destination,
        vehicle_type=vehicle_type,
        vehicle_other=vehicle_other,
        vehicle_details=vehicle_details,
        price=estimated_price,
        status='Pending Payment'
    )
    db.session.add(new_request)
    db.session.commit()

    # Simulate payment
    new_request.status = 'Paid'
    db.session.commit()

    if is_guest_checkout:
        flash(f'Guest request received (ID: {new_request.id}). Price: €{estimated_price:.2f}. Status: {new_request.status}. We will contact you at {guest_phone_form}.', 'success')
        return redirect(url_for('main.home')) 
    else:
        flash(f'Request received (ID: {new_request.id}). Price: €{estimated_price:.2f}. Status: {new_request.status}. Tow truck assignment is simulated.', 'success')
        return redirect(url_for('main.user_home'))

@main_bp.route('/service_provider_dashboard')
@login_required
def service_provider_dashboard():
    if current_user.user_type != 'provider' or current_user.is_admin:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))
    
    # Placeholder data for active requests - replace with actual database query
    # active_requests = ServiceRequest.query.filter_by(provider_id=current_user.id, status_in=["Assigned", "En Route"]).all()
    active_requests_data = [
        {'id': 1, 'user': {'fullname':'Example Customer 1'}, 'guest_name': None, 'guest_phone': None, 'current_location': '123 Fake St, Dublin', 'destination': 'XYZ Garage', 'vehicle_type': 'Sedan', 'status': 'Assigned'},
        {'id': 2, 'user': None, 'guest_name': 'Guest User Example', 'guest_phone': '08X1234567', 'current_location': '742 Evergreen Terrace, Dublin', 'destination': 'Home', 'vehicle_type': 'SUV', 'status': 'En Route'}
    ]
    class DummyRequest:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            if kwargs.get('user'): 
                self.user = DummyUser(**kwargs.get('user', {}))
            else:
                self.user = None # For guest requests

    class DummyUser:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            
    active_requests = [DummyRequest(**req) for req in active_requests_data]

    return render_template('service_provider_dashboard.html', active_requests=active_requests, provider=current_user)

@main_bp.route('/qa')
def qa():
    return render_template('qa.html')

@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        # Basic logging of contact message, in a real app, save to DB or send email
        print(f"Contact Form Message: From {name} ({email}), Subject: {subject}, Message: {message}")
        flash('Thank you for your message. We will get back to you soon.', 'success')
        return redirect(url_for('main.contact'))
    return render_template('contact.html')

# --- Admin Panel Blueprint ---
admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin', template_folder='admin_templates')

# Decorator for admin-only routes
from functools import wraps
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("You do not have permission to access the admin panel.", "danger")
            return redirect(url_for('main.signin', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    # Placeholder data for admin dashboard
    user_count = User.query.count()
    request_count = ServiceRequest.query.count()
    return render_template('admin/dashboard.html', user_count=user_count, request_count=request_count)

@admin_bp.route('/users')
@admin_required
def manage_users():
    users = User.query.all()
    return render_template('admin/manage_users.html', users=users)

@admin_bp.route('/requests')
@admin_required
def manage_requests():
    requests_list = ServiceRequest.query.order_by(ServiceRequest.created_at.desc()).all()
    return render_template('admin/manage_requests.html', requests=requests_list)

# (More admin routes for editing/deleting users/requests, viewing DB details will be added here)

app.register_blueprint(main_bp)
app.register_blueprint(admin_bp)

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Ensure tables are created
        # Optional: Create a default admin user if one doesn't exist
        if not User.query.filter_by(email='admin@townow.local').first():
            admin_user = User(fullname='Admin User', email='admin@townow.local', user_type='admin', is_admin=True)
            admin_user.set_password('adminpass') # Change in production!
            db.session.add(admin_user)
            db.session.commit()
            print("Default admin user created: admin@townow.local / adminpass")

    app.run(host='0.0.0.0', port=5000, debug=True)

