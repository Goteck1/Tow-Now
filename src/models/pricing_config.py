from src import db

class PricingConfig(db.Model):
    __tablename__ = "pricing_config"

    id                         = db.Column(db.Integer, primary_key=True)
    fixed_base_fare            = db.Column(db.Float, default=5.0)
    fare_per_km                = db.Column(db.Float, default=1.0)
    fare_per_minute            = db.Column(db.Float, default=0.5)
    traffic_coefficient        = db.Column(db.Float, default=1.0)
    admin_commission_percentage = db.Column(db.Float, default=10.0)

    # JSON strings con configuración dinámica
    vehicle_types_json         = db.Column(db.Text, default="{}")
    time_coefficients_json     = db.Column(db.Text, default="{}")

    def __repr__(self) -> str:  # útil para depurar
        return f"<PricingConfig id={self.id}>"
