import os
import datetime
import json
from flask import current_app

def find_matching_providers(service_request, db, User):
    """
    Find providers that match the service request's zone and vehicle type.
    
    Args:
        service_request: The ServiceRequest object
        db: SQLAlchemy database instance
        User: User model class
        
    Returns:
        List of User objects (providers) that match the criteria
    """
    # Get all available providers
    available_providers = User.query.filter_by(
        user_type='provider',
        is_available=True
    ).all()
    
    matching_providers = []
    
    for provider in available_providers:
        # Get provider's service zones and accepted vehicle types
        provider_zones = provider.get_service_zones()
        provider_vehicle_types = provider.get_accepted_vehicle_types()
        
        # Check if provider serves the origin zone
        zone_match = False
        if service_request.current_location_zone in provider_zones:
            zone_match = True
        
        # Check if provider accepts the vehicle type
        vehicle_match = False
        if service_request.vehicle_type in provider_vehicle_types:
            vehicle_match = True
        
        # If both zone and vehicle type match, add provider to the list
        if zone_match and vehicle_match:
            matching_providers.append(provider)
    
    return matching_providers

def send_service_alerts(service_request, matching_providers, db, Notification, pricing_config):
    """
    Send alerts to matching providers about a new service request.
    
    Args:
        service_request: The ServiceRequest object
        matching_providers: List of User objects (providers) that match the criteria
        db: SQLAlchemy database instance
        Notification: Notification model class
        pricing_config: PricingConfig object for calculating provider profit
        
    Returns:
        Number of notifications sent
    """
    notifications_sent = 0
    
    # Calculate provider profit
    provider_profit = calculate_provider_profit(service_request.price, pricing_config.admin_commission_percentage)
    
    for provider in matching_providers:
        # Create notification for each matching provider
        notification = Notification(
            service_request_id=service_request.id,
            provider_id=provider.id,
            status='sent'
        )
        
        db.session.add(notification)
        notifications_sent += 1
        
        # Here you would add code to send actual notifications (email, push, etc.)
        # For now, we'll just log it
        current_app.logger.info(
            f"Alert sent to provider {provider.id} ({provider.fullname}) for service request {service_request.id}. "
            f"Total price: €{service_request.price:.2f}, Provider profit: €{provider_profit:.2f}"
        )
        
        # Future enhancement: Send email notification
        # send_email_notification(
        #     to_email=provider.email,
        #     subject=f"New Service Request #{service_request.id}",
        #     template="new_service_request.html",
        #     context={
        #         "provider_name": provider.fullname,
        #         "service_request_id": service_request.id,
        #         "current_location": service_request.current_location,
        #         "destination": service_request.destination,
        #         "vehicle_type": service_request.vehicle_type,
        #         "price": service_request.price,
        #         "provider_profit": provider_profit,
        #         "accept_url": f"/accept_service/{notification.id}"
        #     }
        # )
    
    db.session.commit()
    return notifications_sent

def calculate_provider_profit(total_price, admin_commission_percentage):
    """
    Calculate provider's profit based on total price and admin commission.
    
    Args:
        total_price: Total price of the service
        admin_commission_percentage: Commission percentage (0-1) taken by admin
        
    Returns:
        Provider's profit amount
    """
    if admin_commission_percentage < 0 or admin_commission_percentage > 1:
        # Invalid commission, use a default or log an error
        admin_commission_percentage = 0.25  # Default 25%
    
    provider_share = 1 - admin_commission_percentage
    return round(total_price * provider_share, 2)

def check_expired_service_requests(db, ServiceRequest, Notification, expiry_minutes=5):
    """
    Check for service requests that have been in 'Pending Assignment' status 
    for longer than the specified time and mark them as 'No Provider Available'.
    
    Args:
        db: SQLAlchemy database instance
        ServiceRequest: ServiceRequest model class
        Notification: Notification model class
        expiry_minutes: Minutes after which a request is considered expired
        
    Returns:
        List of expired service request IDs that were updated
    """
    # Calculate the cutoff time
    cutoff_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=expiry_minutes)
    
    # Find service requests that are still pending assignment and older than the cutoff time
    expired_requests = ServiceRequest.query.filter(
        ServiceRequest.status == 'Pending Assignment',
        ServiceRequest.created_at < cutoff_time
    ).all()
    
    expired_request_ids = []
    
    for request in expired_requests:
        # Update the request status
        request.status = 'No Provider Available'
        expired_request_ids.append(request.id)
        
        # Mark all notifications for this request as expired
        notifications = Notification.query.filter_by(
            service_request_id=request.id,
            status='sent'
        ).all()
        
        for notification in notifications:
            notification.status = 'expired'
        
        # Here you would add code to notify the client
        # For now, we'll just log it
        current_app.logger.info(
            f"Service request {request.id} expired after {expiry_minutes} minutes. "
            f"Status updated to 'No Provider Available'."
        )
        
        # Future enhancement: Send email notification to client
        # if request.user_id:  # Registered user
        #     user = User.query.get(request.user_id)
        #     if user:
        #         send_email_notification(
        #             to_email=user.email,
        #             subject=f"Service Request #{request.id} Update",
        #             template="service_request_expired.html",
        #             context={
        #                 "user_name": user.fullname,
        #                 "service_request_id": request.id,
        #                 "current_location": request.current_location,
        #                 "destination": request.destination
        #             }
        #         )
        # elif request.guest_phone:  # Guest user
        #     # Could send SMS notification here
        #     pass
    
    db.session.commit()
    return expired_request_ids

def update_service_status(service_request_id, new_status, provider_id=None, db=None, ServiceRequest=None, Notification=None):
    """
    Update the status of a service request and handle related logic.
    
    Args:
        service_request_id: ID of the service request to update
        new_status: New status to set
        provider_id: ID of the provider updating the status (if applicable)
        db: SQLAlchemy database instance
        ServiceRequest: ServiceRequest model class
        Notification: Notification model class (optional, required for 'Assigned' status)
        
    Returns:
        Updated ServiceRequest object or None if not found
    """
    # Valid status transitions
    valid_statuses = [
        'Pending Assignment',  # Initial status after payment
        'Assigned',            # Provider accepted the request
        'En Route',            # Provider is on the way
        'Arrived',             # Provider arrived at pickup location
        'In Progress',         # Service is in progress
        'Completed',           # Service completed successfully
        'Cancelled',           # Service cancelled by client or provider
        'No Provider Available' # No provider accepted within timeout
    ]
    
    if new_status not in valid_statuses:
        current_app.logger.error(f"Invalid status: {new_status}")
        return None
    
    service_request = ServiceRequest.query.get(service_request_id)
    if not service_request:
        current_app.logger.error(f"Service request {service_request_id} not found")
        return None
    
    # Special handling for 'Assigned' status
    if new_status == 'Assigned' and provider_id:
        # Check if this provider has a notification for this request
        if Notification is None:
            current_app.logger.error("Notification model is required for 'Assigned' status")
            return None
            
        notification = Notification.query.filter_by(
            service_request_id=service_request_id,
            provider_id=provider_id,
            status='sent'
        ).first()
        
        if not notification:
            current_app.logger.error(
                f"Provider {provider_id} cannot accept request {service_request_id}: "
                f"No active notification found"
            )
            return None
        
        # Check if request is still pending assignment
        if service_request.status != 'Pending Assignment':
            current_app.logger.error(
                f"Service request {service_request_id} cannot be assigned: "
                f"Current status is {service_request.status}"
            )
            return None
        
        # Assign the provider
        service_request.provider_id = provider_id
        
        # Update the notification
        notification.status = 'accepted'
        notification.responded_at = datetime.datetime.utcnow()
        
        # Mark other notifications as 'rejected' since another provider accepted
        other_notifications = Notification.query.filter(
            Notification.service_request_id == service_request_id,
            Notification.provider_id != provider_id,
            Notification.status == 'sent'
        ).all()
        
        for other_notification in other_notifications:
            other_notification.status = 'rejected'
            other_notification.responded_at = datetime.datetime.utcnow()
    
    # Update the service request status
    service_request.status = new_status
    service_request.updated_at = datetime.datetime.utcnow()
    
    db.session.commit()
    
    # Here you would add code to notify the client about the status change
    # For now, we'll just log it
    current_app.logger.info(
        f"Service request {service_request_id} status updated to '{new_status}'"
    )
    
    # Future enhancement: Send email notification to client about status change
    # if service_request.user_id:  # Registered user
    #     user = User.query.get(service_request.user_id)
    #     if user:
    #         send_email_notification(
    #             to_email=user.email,
    #             subject=f"Service Request #{service_request.id} Update",
    #             template="service_request_status_update.html",
    #             context={
    #                 "user_name": user.fullname,
    #                 "service_request_id": service_request.id,
    #                 "status": new_status,
    #                 "provider_name": provider.fullname if provider_id else None
    #             }
    #         )
    # elif service_request.guest_phone:  # Guest user
    #     # Could send SMS notification here
    #     pass
    
    return service_request
