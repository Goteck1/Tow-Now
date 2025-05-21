from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from src.main import db, User, ServiceRequest, PricingConfig

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')

def admin_required(f):
    """Decorator: Only allow access for logged-in admins."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("You must be an administrator to access this page.", "danger")
            return redirect(url_for("main.home"))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    user_count = User.query.count()
    request_count = ServiceRequest.query.count()
    return render_template('admin/dashboard.html', user_count=user_count, request_count=request_count)

@admin_bp.route('/manage_users')
@login_required
@admin_required
def manage_users():
    users = User.query.order_by(User.id.desc()).all()
    return render_template('admin/manage_users.html', users=users)

@admin_bp.route('/manage_requests')
@login_required
@admin_required
def manage_requests():
    requests = ServiceRequest.query.order_by(ServiceRequest.created_at.desc()).all()
    return render_template('admin/manage_requests.html', requests=requests)

@admin_bp.route('/manage_pricing', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_pricing():
    config = PricingConfig.query.first()
    if request.method == 'POST':
        config.fixed_base_fare = float(request.form.get('fixed_base_fare', config.fixed_base_fare))
        config.fare_per_km = float(request.form.get('fare_per_km', config.fare_per_km))
        config.fare_per_minute = float(request.form.get('fare_per_minute', config.fare_per_minute))
        config.traffic_coefficient = float(request.form.get('traffic_coefficient', config.traffic_coefficient))
        config.admin_commission_percentage = float(request.form.get('admin_commission_percentage', config.admin_commission_percentage))
        db.session.commit()
        flash("Pricing configuration updated successfully.", "success")
        return redirect(url_for('admin_bp.manage_pricing'))
    return render_template('admin/manage_pricing.html', config=config)
