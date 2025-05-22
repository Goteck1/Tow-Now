# -*- coding: utf-8 -*-
"""
Dynamic Pricing Logic for TowNow using Mapbox Matrix API
Reads configuration from a database object.
"""
from src import db 
import datetime
import requests
import os
import json # Ensure json is imported

MAPBOX_ACCESS_TOKEN = os.environ.get("MAPBOX_ACCESS_TOKEN", "pk.eyJ1Ijoiam9hcXVpbmFsZSIsImEiOiJjbWFtbXh0OXkwbHdzMmtzZGpudXFreTdkIn0.o8lo9--pdwMvJrnz_rKuKg")

def get_time_coefficient(time_coefficients_config, current_dt=None):
    """
    Determines the time coefficient based on the current time and configured periods.
    time_coefficients_config (dict): Parsed JSON from PricingConfig.time_coefficients_json.
    current_dt (datetime.datetime, optional): The current datetime. Defaults to now().
    """
    if current_dt is None:
        current_dt = datetime.datetime.now()
    current_hour = current_dt.hour
    
    # time_coefficients_config is already a dict here
    for period_name, details in time_coefficients_config.items():
        if period_name == "off_peak":
            continue # off_peak is the fallback
        if "ranges" not in details or "coef" not in details:
            continue # Skip malformed entries

        for r in details["ranges"]:
            try:
                start_hour, end_hour = int(r[0]), int(r[1])
                if start_hour <= end_hour:
                    if start_hour <= current_hour < end_hour:
                        return details["coef"], period_name
                else: # Overnight range (e.g., 22:00 to 06:00)
                    if start_hour <= current_hour < 24 or 0 <= current_hour < end_hour:
                        return details["coef"], period_name
            except (ValueError, TypeError, IndexError):
                # Log this error ideally, skip malformed range
                continue 
                
    return time_coefficients_config.get("off_peak", {}).get("coef", 1.0), "off_peak"

def get_route_details_from_mapbox(origin_coords, destination_coords):
    """
    Fetches route distance and duration from Mapbox Matrix API.
    origin_coords: tuple (longitude, latitude)
    destination_coords: tuple (longitude, latitude)
    """
    if not MAPBOX_ACCESS_TOKEN:
        return None, None, "Mapbox Access Token not configured"
        
    coords_str = f"{origin_coords[0]},{origin_coords[1]};{destination_coords[0]},{destination_coords[1]}"
    profile = "mapbox/driving-traffic"
    annotations = "distance,duration"
    url = f"https://api.mapbox.com/directions-matrix/v1/{profile}/{coords_str}?annotations={annotations}&access_token={MAPBOX_ACCESS_TOKEN}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") == "Ok":
            duration_seconds = data["durations"][0][1]
            distance_meters = data["distances"][0][1]
            
            if duration_seconds is None or distance_meters is None:
                return None, None, "No route found between the points (Mapbox)"
            return distance_meters, duration_seconds, None
        else:
            return None, None, data.get("message", "Mapbox API error")
    except requests.exceptions.RequestException as e:
        return None, None, f"Mapbox request failed: {str(e)}"
    except (KeyError, IndexError) as e:
        return None, None, f"Error parsing Mapbox response: {str(e)}"

def calculate_dynamic_price(origin_coords, destination_coords, vehicle_type_key, pricing_config_db_object, current_dt=None):
    """
    Calculates the dynamic price using Mapbox Matrix API and DB-stored configuration.
    pricing_config_db_object: The PricingConfig model instance from the database.
    """
    if not pricing_config_db_object:
        return {"price": 999.98, "breakdown": {}, "error": "Pricing configuration not loaded"}

    # Parse JSON fields from the database object
    try:
        vehicle_types_cfg = json.loads(pricing_config_db_object.vehicle_types_json)
        time_coefficients_cfg = json.loads(pricing_config_db_object.time_coefficients_json)
    except json.JSONDecodeError as e:
        return {"price": 999.97, "breakdown": {}, "error": f"Invalid JSON in pricing configuration: {str(e)}"}

    distance_m, duration_s, mapbox_error = get_route_details_from_mapbox(origin_coords, destination_coords)

    breakdown = {
        "origin_coordinates": origin_coords,
        "destination_coordinates": destination_coords,
        "vehicle_type_key": vehicle_type_key,
        "mapbox_api_error": mapbox_error,
        "distance_meters": distance_m,
        "duration_seconds": duration_s,
    }

    if mapbox_error or distance_m is None or duration_s is None:
        breakdown["calculation_status"] = "Error or no route, Mapbox API issue"
        return {"price": 999.99, "breakdown": breakdown, "error": mapbox_error or "No route/distance data from Mapbox"}

    distance_km = distance_m / 1000.0
    duration_minutes = duration_s / 60.0

    coef_vehicle = vehicle_types_cfg.get(vehicle_type_key, vehicle_types_cfg.get("other", 1.0)) # Fallback to other, then 1.0
    coef_time, time_period_name = get_time_coefficient(time_coefficients_cfg, current_dt)
    coef_traffic = pricing_config_db_object.traffic_coefficient

    price_calculated = (
        pricing_config_db_object.fixed_base_fare +
        (distance_km * pricing_config_db_object.fare_per_km) +
        (duration_minutes * pricing_config_db_object.fare_per_minute)
    )
    
    final_price = price_calculated * coef_vehicle * coef_time * coef_traffic
    
    breakdown.update({
        "calculation_status": "Success",
        "distance_km": round(distance_km, 2),
        "duration_minutes": round(duration_minutes, 2),
        "fixed_base_fare": pricing_config_db_object.fixed_base_fare,
        "fare_per_km": pricing_config_db_object.fare_per_km,
        "fare_per_minute": pricing_config_db_object.fare_per_minute,
        "price_before_coefficients": round(price_calculated, 2),
        "coef_vehicle": coef_vehicle,
        "time_period_name": time_period_name,
        "coef_time": coef_time,
        "coef_traffic": coef_traffic,
        "final_price_raw": final_price,
        "final_price_rounded": round(final_price, 2)
    })

    return {"price": round(final_price, 2), "breakdown": breakdown, "error": None}

# Example Usage (for testing - requires a mock or real DB object)
if __name__ == "__main__":
    print("This script is intended to be used as a module.")
    print("To test calculate_dynamic_price, you need to provide a PricingConfig object.")
    
    # Mock PricingConfig object for local testing (mimicking DB structure)
    class MockPricingConfig:
        def __init__(self):
            self.fixed_base_fare = 10.0
            self.fare_per_km = 1.2
            self.fare_per_minute = 0.3
            self.traffic_coefficient = 1.3
            self.vehicle_types_json = json.dumps({
                "sedan": 1.0, "suv": 1.3, "truck": 1.5, "motorcycle": 0.8,
                "van": 1.4, "electric": 1.2, "other": 1.2
            })
            self.time_coefficients_json = json.dumps({
                "peak_hours": {"coef": 1.2, "ranges": [[7, 10], [16, 19]]},
                "night_hours": {"coef": 1.5, "ranges": [[22, 24], [0, 6]]},
                "off_peak": {"coef": 1.0}
            })

    mock_config = MockPricingConfig()

    origin = (-6.2603, 53.3498) # Dublin City Centre
    destination = (-6.2499, 53.4264) # Dublin Airport
    
    print(f"MAPBOX_ACCESS_TOKEN: {MAPBOX_ACCESS_TOKEN[:10]}..." if MAPBOX_ACCESS_TOKEN else "MAPBOX_ACCESS_TOKEN not set!")

    price_details_1 = calculate_dynamic_price(origin, destination, "sedan", mock_config)
    print(f"Test Case 1 (Sedan, Auto Time): Price: €{price_details_1.get('price')} Error: {price_details_1.get('error')}")
    if price_details_1.get("breakdown"):
        print("Breakdown 1:", json.dumps(price_details_1["breakdown"], indent=2))

    night_time = datetime.datetime(2024, 5, 10, 23, 0) # 11:00 PM
    price_details_2 = calculate_dynamic_price(origin, destination, "suv", mock_config, current_dt=night_time)
    print(f"Test Case 2 (SUV, Night Time 11:00 PM): Price: €{price_details_2.get('price')} Error: {price_details_2.get('error')}")
    if price_details_2.get("breakdown"):
        print("Breakdown 2:", json.dumps(price_details_2["breakdown"], indent=2))
