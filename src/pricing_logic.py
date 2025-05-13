# -*- coding: utf-8 -*-
"""
Dynamic Pricing Logic for TowNow using Mapbox Matrix API
"""
import datetime
import requests
import os

# --- Pricing Configuration ---
MAPBOX_ACCESS_TOKEN = os.environ.get("MAPBOX_ACCESS_TOKEN", "pk.eyJ1Ijoiam9hcXVpbmFsZSIsImEiOiJjbWFtbXh0OXkwbHdzMmtzZGpudXFreTdkIn0.o8lo9--pdwMvJrnz_rKuKg")

PRICING_CONFIG = {
    # New tariffs for distance/duration based pricing
    "fixed_base_fare": 10.0,
    "fare_per_km": 1.2,
    "fare_per_minute": 0.3,

    # Existing coefficients (vehicle, time, traffic)
    "vehicle_types": {
        "sedan": 1.0, 
        "suv": 1.3,   
        "truck": 1.5, 
        "motorcycle": 0.8,
        "van": 1.4, 
        "electric": 1.2, 
        "other": 1.2 
    },
    "time_coefficients": {
        "peak_hours": {
            "coef": 1.2,
            "ranges": [[7, 10], [16, 19]] 
        },
        "night_hours": {
            "coef": 1.5,
            "ranges": [[22, 24], [0, 6]] 
        },
        "off_peak": {
            "coef": 1.0
        }
    },
    "traffic_coefficient": 1.3, # This might be implicitly handled by mapbox/driving-traffic or could be an additional multiplier

    # Zone-based configuration (will be deprecated by distance/time calculation but kept for reference or fallback)
    "base_unit_zone_fallback": 50.0, # Fallback if Matrix API fails
    "zones": {
        "D1": { "origin": 1.3, "destination": 1.2 },
        "D2": { "origin": 1.3, "destination": 1.2 },
        "D3": { "origin": 1.2, "destination": 1.1 },
        "D4": { "origin": 1.3, "destination": 1.2 },
        "D5": { "origin": 1.2, "destination": 1.1 },
        "D6": { "origin": 1.2, "destination": 1.1 },
        "D6W": { "origin": 1.2, "destination": 1.1 },
        "D7": { "origin": 1.2, "destination": 1.1 },
        "D8": { "origin": 1.2, "destination": 1.1 },
        "D9": { "origin": 1.2, "destination": 1.1 },
        "D10": { "origin": 1.1, "destination": 1.0 },
        "D11": { "origin": 1.1, "destination": 1.0 },
        "D12": { "origin": 1.1, "destination": 1.0 },
        "D13": { "origin": 1.1, "destination": 1.0 },
        "D14": { "origin": 1.1, "destination": 1.0 },
        "D15": { "origin": 1.1, "destination": 1.0 },
        "D16": { "origin": 1.1, "destination": 1.0 },
        "D17": { "origin": 1.1, "destination": 1.0 },
        "D18": { "origin": 1.2, "destination": 1.1 },
        "D20": { "origin": 1.2, "destination": 1.1 },
        "D22": { "origin": 1.2, "destination": 1.1 },
        "D24": { "origin": 1.3, "destination": 1.2 },
        "Lucan": { "origin": 1.0, "destination": 1.0 },
        "Swords": { "origin": 1.0, "destination": 1.0 },
        "Malahide": { "origin": 1.1, "destination": 1.1 },
        "Blanchardstown": { "origin": 1.1, "destination": 1.1 },
        "Baldoyle": { "origin": 1.1, "destination": 1.1 },
        "Portmarnock": { "origin": 1.1, "destination": 1.1 },
        "Skerries": { "origin": 1.4, "destination": 1.4 },
        "Howth": { "origin": 1.3, "destination": 1.3 },
        "Clondalkin": { "origin": 1.2, "destination": 1.1 },
        "Tallaght": { "origin": 1.3, "destination": 1.2 },
        "Rathfarnham": { "origin": 1.2, "destination": 1.1 },
        "Balbriggan": { "origin": 1.5, "destination": 1.5 },
        "Bray": { "origin": 1.5, "destination": 1.5 },
        "Maynooth": { "origin": 1.6, "destination": 1.6 },
        "Outside": { "origin": 2.0, "destination": 2.0 } 
    },
    "weights_zone_fallback": {
        "origin_zone": 0.25,
        "destination_zone": 0.25,
        "traffic": 0.25,
        "time": 0.25
    }
}

def get_time_coefficient(current_dt=None):
    if current_dt is None:
        current_dt = datetime.datetime.now()
    current_hour = current_dt.hour
    time_config = PRICING_CONFIG["time_coefficients"]
    for period_name, details in time_config.items():
        if period_name == "off_peak":
            continue
        for r in details["ranges"]:
            start_hour, end_hour = r
            if start_hour <= end_hour:
                if start_hour <= current_hour < end_hour:
                    return details["coef"], period_name
            else: 
                if start_hour <= current_hour < 24 or 0 <= current_hour < end_hour:
                    return details["coef"], period_name
    return time_config["off_peak"]["coef"], "off_peak"

def get_route_details_from_mapbox(origin_coords, destination_coords):
    """
    Fetches route distance and duration from Mapbox Matrix API.
    origin_coords: tuple (longitude, latitude)
    destination_coords: tuple (longitude, latitude)
    """
    coords_str = f"{origin_coords[0]},{origin_coords[1]};{destination_coords[0]},{destination_coords[1]}"
    # Using mapbox/driving-traffic for more realistic ETAs if available, fallback to mapbox/driving
    profile = "mapbox/driving-traffic" 
    # To request both distance and duration
    annotations = "distance,duration"
    url = f"https://api.mapbox.com/directions-matrix/v1/{profile}/{coords_str}?annotations={annotations}&access_token={MAPBOX_ACCESS_TOKEN}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status() # Raise an exception for HTTP errors
        data = response.json()
        
        if data.get("code") == "Ok":
            # Durations are [origin][destination] in seconds
            # Distances are [origin][destination] in meters
            # For a single origin and single destination, we expect durations[0][1] and distances[0][1]
            # (assuming source=0, destination=1 in the matrix of two points)
            duration_seconds = data["durations"][0][1] # From origin (index 0) to destination (index 1)
            distance_meters = data["distances"][0][1]
            
            if duration_seconds is None or distance_meters is None:
                # No route found between the points
                return None, None, "No route found"
                
            return distance_meters, duration_seconds, None # distance, duration, error
        else:
            return None, None, data.get("message", "Mapbox API error")
    except requests.exceptions.RequestException as e:
        return None, None, str(e)
    except (KeyError, IndexError) as e:
        return None, None, f"Error parsing Mapbox response: {str(e)}"

def calculate_dynamic_price(origin_coords, destination_coords, vehicle_type_key, current_dt=None):
    """
    Calculates the dynamic price for a tow service using Mapbox Matrix API for distance/duration.
    origin_coords: tuple (longitude, latitude)
    destination_coords: tuple (longitude, latitude)
    vehicle_type_key (str): Key for the vehicle type (e.g., "sedan", "suv").
    current_dt (datetime.datetime, optional): The current datetime. Defaults to now().
    """
    cfg = PRICING_CONFIG
    distance_m, duration_s, error = get_route_details_from_mapbox(origin_coords, destination_coords)

    breakdown = {
        "origin_coordinates": origin_coords,
        "destination_coordinates": destination_coords,
        "vehicle_type_key": vehicle_type_key,
        "mapbox_api_error": error,
        "distance_meters": distance_m,
        "duration_seconds": duration_s,
    }

    if error or distance_m is None or duration_s is None:
        # Fallback to a simplified or fixed price if Mapbox API fails or no route
        # For now, let's return an error state or a very high price to indicate issue
        # Or, implement the old zone-based logic as a fallback here if desired.
        breakdown["calculation_status"] = "Error or no route, using fixed error price"
        # Returning a high, distinct price to signal an issue, or handle as error upstream
        return {"price": 999.99, "breakdown": breakdown, "error": error or "No route/distance data"}

    distance_km = distance_m / 1000.0
    duration_minutes = duration_s / 60.0

    # Get vehicle coefficient
    coef_vehicle = cfg["vehicle_types"].get(vehicle_type_key, cfg["vehicle_types"]["other"])
    # Get time coefficient
    coef_time, time_period_name = get_time_coefficient(current_dt)
    # Traffic coefficient (can be adjusted or made dynamic)
    coef_traffic = cfg["traffic_coefficient"]

    # New formula calculation
    price_calculated = (
        cfg["fixed_base_fare"] +
        (distance_km * cfg["fare_per_km"]) +
        (duration_minutes * cfg["fare_per_minute"])
    )
    
    final_price = price_calculated * coef_vehicle * coef_time * coef_traffic
    
    breakdown.update({
        "calculation_status": "Success",
        "distance_km": round(distance_km, 2),
        "duration_minutes": round(duration_minutes, 2),
        "fixed_base_fare": cfg["fixed_base_fare"],
        "fare_per_km": cfg["fare_per_km"],
        "fare_per_minute": cfg["fare_per_minute"],
        "price_before_coefficients": round(price_calculated, 2),
        "coef_vehicle": coef_vehicle,
        "time_period_name": time_period_name,
        "coef_time": coef_time,
        "coef_traffic": coef_traffic,
        "final_price_raw": final_price,
        "final_price_rounded": round(final_price, 2)
    })

    return {"price": round(final_price, 2), "breakdown": breakdown}

# Example Usage (for testing)
if __name__ == "__main__":
    # Dublin City Centre (approx)
    origin = (-6.2603, 53.3498) # Longitude, Latitude
    # Dublin Airport (approx)
    destination = (-6.2499, 53.4264)
    
    print(f"MAPBOX_ACCESS_TOKEN: {MAPBOX_ACCESS_TOKEN[:10]}...") # Check if token is loaded

    price_details_1 = calculate_dynamic_price(origin, destination, "sedan")
    print(f"Test Case 1 (City Centre to Airport, Sedan, Auto Time): Price: €{price_details_1.get('price')} Error: {price_details_1.get('error')}")
    if price_details_1.get("breakdown"):
        print("Breakdown 1:", price_details_1["breakdown"])

    # Test with a night time
    night_time = datetime.datetime(2024, 5, 10, 23, 0) # 11:00 PM
    price_details_2 = calculate_dynamic_price(origin, destination, "suv", current_dt=night_time)
    print(f"Test Case 2 (City Centre to Airport, SUV, Night Time 11:00 PM): Price: €{price_details_2.get('price')} Error: {price_details_2.get('error')}")
    if price_details_2.get("breakdown"):
        print("Breakdown 2:", price_details_2["breakdown"])

    # Test with potentially no route (e.g., across an ocean - use local points that might fail if needed)
    # For this example, let's use very distant points that are unlikely to have a driving route
    # origin_far = (-74.0060, 40.7128) # New York
    # destination_far = (151.2093, -33.8688) # Sydney
    # price_details_3 = calculate_dynamic_price(origin_far, destination_far, "sedan")
    # print(f"Test Case 3 (NY to Sydney, Sedan): Price: €{price_details_3.get("price")}, Error: {price_details_3.get("error")}")
    # if price_details_3.get("breakdown"):
        # print("Breakdown 3:", price_details_3["breakdown"])

