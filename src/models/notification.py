from src import db
from flask_sqlalchemy import SQLAlchemy
import datetime
import json



def init_notification_model(db_instance):
    """
    Initialize the Notification model with the SQLAlchemy instance.
    This function should be called from main.py after the db is created.
    """
    global db
    db = db_instance
    
    # Return the Notification class to be used in the application
    return Notification

class Notification:
    """
    Model for storing notifications sent to providers about service requests.
    Used for tracking which providers have been notified about a service request
    and their response status.
    
    Note: This is a class definition that will be converted to a SQLAlchemy model
    when init_notification_model is called.
    """
    __tablename__ = 'notifications'
    
    # These attributes will become SQLAlchemy columns when the model is initialized
    id = None  # db.Column(db.Integer, primary_key=True)
    service_request_id = None  # db.Column(db.Integer, db.ForeignKey('service_requests.id'), nullable=False)
    provider_id = None  # db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = None  # db.Column(db.String(20), nullable=False, default='sent')
    created_at = None  # db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = None  # db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    viewed_at = None  # db.Column(db.DateTime, nullable=True)
    responded_at = None  # db.Column(db.DateTime, nullable=True)
    
    # Relationships will be defined when the model is initialized
    service_request = None  # db.relationship('ServiceRequest', backref=db.backref('notifications', lazy='dynamic'))
    provider = None  # db.relationship('User', backref=db.backref('notifications_received', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Notification {self.id} for ServiceRequest {self.service_request_id} to Provider {self.provider_id}>'
    
    def to_dict(self):
        """Convert notification to dictionary for API responses"""
        return {
            'id': self.id,
            'service_request_id': self.service_request_id,
            'provider_id': self.provider_id,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'viewed_at': self.viewed_at.isoformat() if self.viewed_at else None,
            'responded_at': self.responded_at.isoformat() if self.responded_at else None
        }

# When the db instance is set, this will be the actual SQLAlchemy model
Notification = type('Notification', (object,), dict(Notification.__dict__))
