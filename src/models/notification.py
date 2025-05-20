import datetime
from flask import current_app

# Accede al db que definiste en app.config en main.py
db = current_app.config.get('db')

class Notification(db.Model):
    """
    Model for storing notifications sent to providers about service requests.
    Used for tracking which providers have been notified about a service request
    and their response status.
    """
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    service_request_id = db.Column(db.Integer, db.ForeignKey('service_requests.id'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Notification status: 'sent', 'viewed', 'accepted', 'rejected', 'expired'
    status = db.Column(db.String(20), nullable=False, default='sent')

    # Timestamps for tracking
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    viewed_at = db.Column(db.DateTime, nullable=True)
    responded_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    service_request = db.relationship('ServiceRequest', backref=db.backref('notifications', lazy='dynamic'))
    provider = db.relationship('User', backref=db.backref('notifications_received', lazy='dynamic'))

    def __repr__(self):
        return f'<Notification {self.id} for ServiceRequest {self.service_request_id} to Provider {self.provider_id}>'

    def to_dict(self):
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
