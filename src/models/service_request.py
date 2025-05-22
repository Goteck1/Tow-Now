from src import db 

class ServiceRequest(db.Model):
    __tablename__ = 'service_requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    guest_name = db.Column(db.String(100), nullable=True)
    guest_phone = db.Column(db.String(20), nullable=True)
    current_location = db.Column(db.String(255), nullable=False)
    current_location_zone = db.Column(db.String(50), nullable=True)
    destination = db.Column(db.String(255), nullable=False)
    vehicle_type = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(30), nullable=False, default="pending") # e.g. pending, assigned, completed, cancelled
    assigned_provider_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now(), onupdate=db.func.now())
    # Puedes agregar otros campos según el crecimiento de la app

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'guest_name': self.guest_name,
            'guest_phone': self.guest_phone,
            'current_location': self.current_location,
            'current_location_zone': self.current_location_zone,
            'destination': self.destination,
            'vehicle_type': self.vehicle_type,
            'status': self.status,
            'assigned_provider_id': self.assigned_provider_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"<ServiceRequest id={self.id} user_id={self.user_id} status={self.status}>"
