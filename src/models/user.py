from src import db 
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    user_type = db.Column(db.String(20), nullable=False, default='customer')  # 'customer', 'provider', 'admin'
    is_admin = db.Column(db.Boolean, default=False)

    # Provider-specific fields (nullable if user is not a provider)
    service_zones_json = db.Column(db.Text, nullable=True)  # JSON string for list of zones, e.g., ["D1", "D2", "Lucan"]
    accepted_vehicle_types_json = db.Column(db.Text, nullable=True)  # JSON string for list of vehicle types, e.g., ["sedan", "suv"]
    is_available = db.Column(db.Boolean, nullable=True, default=True)  # Provider availability status

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

    def __repr__(self):
        return f'<User {self.fullname} ({self.email})>'

    def to_dict(self):
        data = {
            'id': self.id,
            'fullname': self.fullname,
            'email': self.email,
            'user_type': self.user_type,
            'is_admin': self.is_admin
        }
        
        # Add provider-specific fields if user is a provider
        if self.user_type == 'provider':
            data.update({
                'service_zones': self.get_service_zones(),
                'accepted_vehicle_types': self.get_accepted_vehicle_types(),
                'is_available': self.is_available
            })
            
        return data
