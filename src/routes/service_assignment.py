from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
import datetime
import json
import os
import sys

# This blueprint will be registered in main.py
service_assignment_bp = Blueprint('service_assignment', __name__)

@service_assignment_bp.route('/process_service_request/<int:service_request_id>', methods=['POST'])
@login_required
def process_service_request(service_request_id):
    """
    Process a new service request by finding matching providers and sending alerts.
    This route should be called after a service request is created and payment is confirmed.
    """
    if not current_user.is_admin:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))
    
    # Import models from main.py (will be set when blueprint is registered)
    db = current_app.config['db']
    User = current_app.config['User']
    ServiceRequest = current_app.config['ServiceRequest']
    PricingConfig = current_app.config['PricingConfig']
    Notification = current_app.config['Notification']
    
    # Get the service request
    service_request = ServiceRequest.query.get(service_request_id)
    if not service_request:
        flash(f'Service request {service_request_id} not found.', 'danger')
        return redirect(url_for('admin_bp.dashboard'))
    
    # Check if the service request is in the correct state
    if service_request.status != 'Pending Assignment':
        flash(f'Service request {service_request_id} is not in "Pending Assignment" status.', 'warning')
        return redirect(url_for('admin_bp.dashboard'))
    
    # Get the current pricing config for commission calculation
    pricing_config = PricingConfig.query.first()
    if not pricing_config:
        flash('Pricing configuration not found.', 'danger')
        return redirect(url_for('admin_bp.dashboard'))
    
    # Import utility functions here to avoid circular imports
    from utils.service_assignment import find_matching_providers, send_service_alerts
    
    # Find matching providers
    matching_providers = find_matching_providers(service_request, db, User)
    
    if not matching_providers:
        # No matching providers found
        service_request.status = 'No Provider Available'
        db.session.commit()
        flash(f'No matching providers found for service request {service_request_id}.', 'warning')
        return redirect(url_for('admin_bp.dashboard'))
    
    # Send alerts to matching providers
    notifications_sent = send_service_alerts(service_request, matching_providers, db, Notification, pricing_config)
    
    flash(f'Service request {service_request_id} processed. {notifications_sent} providers notified.', 'success')
    return redirect(url_for('admin_bp.dashboard'))

@service_assignment_bp.route('/accept_service/<int:notification_id>', methods=['POST'])
@login_required
def accept_service(notification_id):
    """
    Allow a provider to accept a service request.
    The first provider to accept gets the service assigned.
    """
    if current_user.user_type != 'provider':
        flash('Only service providers can accept service requests.', 'danger')
        return redirect(url_for('main.home'))
    
    # Import models from main.py (will be set when blueprint is registered)
    db = current_app.config['db']
    ServiceRequest = current_app.config['ServiceRequest']
    Notification = current_app.config['Notification']
    
    # Get the notification
    notification = Notification.query.get(notification_id)
    if not notification:
        flash('Notification not found.', 'danger')
        return redirect(url_for('main.service_provider_home'))
    
    # Check if the notification belongs to the current provider
    if notification.provider_id != current_user.id:
        flash('Unauthorized access to this notification.', 'danger')
        return redirect(url_for('main.service_provider_home'))
    
    # Check if the notification is still in 'sent' status
    if notification.status != 'sent':
        flash(f'This service request has already been {notification.status}.', 'warning')
        return redirect(url_for('main.service_provider_home'))
    
    # Get the service request
    service_request = ServiceRequest.query.get(notification.service_request_id)
    if not service_request:
        flash('Service request not found.', 'danger')
        return redirect(url_for('main.service_provider_home'))
    
    # Check if the service request is still in 'Pending Assignment' status
    if service_request.status != 'Pending Assignment':
        flash(f'This service request is already {service_request.status}.', 'warning')
        return redirect(url_for('main.service_provider_home'))
    
    # Import utility function here to avoid circular imports
    from utils.service_assignment import update_service_status
    
    # Use the update_service_status utility to assign the service to this provider
    updated_request = update_service_status(
        service_request_id=service_request.id,
        new_status='Assigned',
        provider_id=current_user.id,
        db=db,
        ServiceRequest=ServiceRequest,
        Notification=Notification
    )
    
    if updated_request:
        flash('Service request accepted successfully! You have been assigned to this service.', 'success')
    else:
        flash('Failed to accept service request. It may have been assigned to another provider.', 'danger')
    
    return redirect(url_for('main.service_provider_home'))

@service_assignment_bp.route('/update_service_status/<int:service_request_id>', methods=['POST'])
@login_required
def update_service_request_status(service_request_id):
    """
    Allow a provider to update the status of an assigned service request.
    Valid status transitions: Assigned -> En Route -> Arrived -> In Progress -> Completed
    """
    if current_user.user_type != 'provider':
        flash('Only service providers can update service status.', 'danger')
        return redirect(url_for('main.home'))
    
    # Import models from main.py (will be set when blueprint is registered)
    db = current_app.config['db']
    ServiceRequest = current_app.config['ServiceRequest']
    Notification = current_app.config['Notification']
    
    # Get the service request
    service_request = ServiceRequest.query.get(service_request_id)
    if not service_request:
        flash('Service request not found.', 'danger')
        return redirect(url_for('main.service_provider_home'))
    
    # Check if the service request is assigned to the current provider
    if service_request.provider_id != current_user.id:
        flash('You are not assigned to this service request.', 'danger')
        return redirect(url_for('main.service_provider_home'))
    
    # Get the new status from the form
    new_status = request.form.get('status')
    if not new_status:
        flash('No status provided.', 'danger')
        return redirect(url_for('main.service_provider_home'))
    
    # Valid status transitions
    valid_statuses = ['En Route', 'Arrived', 'In Progress', 'Completed', 'Cancelled']
    if new_status not in valid_statuses:
        flash(f'Invalid status: {new_status}', 'danger')
        return redirect(url_for('main.service_provider_home'))
    
    # Import utility function here to avoid circular imports
    from utils.service_assignment import update_service_status
    
    # Use the update_service_status utility to update the status
    updated_request = update_service_status(
        service_request_id=service_request.id,
        new_status=new_status,
        provider_id=current_user.id,
        db=db,
        ServiceRequest=ServiceRequest,
        Notification=Notification
    )
    
    if updated_request:
        flash(f'Service request status updated to {new_status} successfully!', 'success')
    else:
        flash('Failed to update service request status.', 'danger')
    
    return redirect(url_for('main.service_provider_home'))

@service_assignment_bp.route('/check_expired_requests', methods=['GET'])
def check_expired_requests():
    """
    Check for service requests that have been in 'Pending Assignment' status
    for longer than the specified time and mark them as 'No Provider Available'.
    This endpoint can be called by a cron job.
    """
    # Check for API key or other authentication if needed
    api_key = request.args.get('api_key')
    if not api_key or api_key != os.environ.get('SERVICE_ASSIGNMENT_API_KEY', 'default_key_for_development'):
        return jsonify({'error': 'Unauthorized access'}), 401
    
    # Import models from main.py (will be set when blueprint is registered)
    db = current_app.config['db']
    ServiceRequest = current_app.config['ServiceRequest']
    Notification = current_app.config['Notification']
    
    # Get expiry minutes from query parameter or use default
    expiry_minutes = request.args.get('expiry_minutes', 5, type=int)
    
    # Import utility function here to avoid circular imports
    from utils.service_assignment import check_expired_service_requests
    
    # Use the check_expired_service_requests utility
    expired_request_ids = check_expired_service_requests(
        db=db,
        ServiceRequest=ServiceRequest,
        Notification=Notification,
        expiry_minutes=expiry_minutes
    )
    
    return jsonify({
        'success': True,
        'expired_requests': expired_request_ids,
        'count': len(expired_request_ids)
    })
