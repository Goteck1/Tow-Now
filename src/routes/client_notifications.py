from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
import datetime
import json

# This blueprint will be registered in main.py
client_notifications_bp = Blueprint('client_notifications', __name__)

@client_notifications_bp.route('/client/notifications')
@login_required
def client_notifications():
    """
    Display notifications for the client.
    Shows service request status updates and other important notifications.
    """
    if current_user.user_type != 'customer':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))
    
    # Import models from main.py (will be set when blueprint is registered)
    ServiceRequest = current_app.config['ServiceRequest']
    User = current_app.config['User']
    
    # Get all service requests for this client
    service_requests = ServiceRequest.query.filter_by(user_id=current_user.id).order_by(
        ServiceRequest.updated_at.desc()
    ).all()
    
    # Prepare notifications data
    notifications = []
    for request in service_requests:
        # Get provider info if assigned
        provider_name = "Not assigned"
        if request.provider_id:
            provider = User.query.get(request.provider_id)
            if provider:
                provider_name = provider.fullname
        
        # Create notification object
        notification = {
            'id': request.id,
            'type': 'service_update',
            'status': request.status,
            'current_location': request.current_location,
            'destination': request.destination,
            'vehicle_type': request.vehicle_type,
            'price': request.price,
            'provider_name': provider_name,
            'created_at': request.created_at,
            'updated_at': request.updated_at,
            'is_new': (datetime.datetime.utcnow() - request.updated_at).total_seconds() < 86400  # 24 hours
        }
        notifications.append(notification)
    
    return render_template('client/notifications.html', notifications=notifications)

@client_notifications_bp.route('/client/service_details/<int:service_request_id>')
@login_required
def client_service_details(service_request_id):
    """
    Display detailed information about a service request for the client.
    """
    if current_user.user_type != 'customer':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))
    
    # Import models from main.py (will be set when blueprint is registered)
    ServiceRequest = current_app.config['ServiceRequest']
    User = current_app.config['User']
    
    # Get the service request
    service_request = ServiceRequest.query.get(service_request_id)
    if not service_request:
        flash('Service request not found.', 'danger')
        return redirect(url_for('client_notifications_bp.client_notifications'))
    
    # Check if the service request belongs to the current user
    if service_request.user_id != current_user.id:
        flash('Unauthorized access to this service request.', 'danger')
        return redirect(url_for('client_notifications_bp.client_notifications'))
    
    # Get provider info if assigned
    provider = None
    if service_request.provider_id:
        provider = User.query.get(service_request.provider_id)
    
    # Parse price breakdown if available
    price_breakdown = None
    if service_request.price_breakdown_json:
        try:
            price_breakdown = json.loads(service_request.price_breakdown_json)
        except json.JSONDecodeError:
            price_breakdown = None
    
    return render_template('client/service_details.html', 
                          service_request=service_request, 
                          provider=provider,
                          price_breakdown=price_breakdown)
