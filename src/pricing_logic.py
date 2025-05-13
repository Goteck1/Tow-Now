# -*- coding: utf-8 -*-
"""
Dynamic Pricing Logic for TowNow
"""
import datetime

# --- Pricing Configuration ---
# This configuration can be moved to a separate JSON file or environment variables for easier management.
PRICING_CONFIG = {
    "base_unit": 50.0,
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
        "Outside": { "origin": 2.0, "destination": 2.0 } # Default for zones not listed
    },
    "vehicle_types": {
        "sedan": 1.0, # Sedan / Hatchback / Compact Car
        "suv": 1.3,   # SUV / 4x4 / Small Van
        "truck": 1.5, # Large Van / Pickup Truck / Light Commercial
        "motorcycle": 0.8,
        "van": 1.4, # This could be an alias for suv or truck, or a distinct category
        "electric": 1.2, # Assuming this is a general type, could be combined with others
        "other": 1.2 # Default for 'other' vehicle type
    },
    "time_coefficients": {
        "peak_hours": {
            "coef": 1.2,
            "ranges": [[7, 10], [16, 19]] # 7:00-9:59 AM, 16:00-18:59 PM
        },
        "night_hours": {
            "coef": 1.5,
            "ranges": [[22, 24], [0, 6]] # 22:00-23:59 PM, 0:00-5:59 AM
        },
        "off_peak": {
            "coef": 1.0
        }
    },
    "traffic_coefficient": 1.3, # Fixed for now
    "weights": {
        "origin_zone": 0.25,
        "destination_zone": 0.25,
        "traffic": 0.25,
        "time": 0.25
    }
}

def get_time_coefficient(current_dt=None):
    """Determines the time coefficient based on the current hour."""
    if current_dt is None:
        current_dt = datetime.datetime.now()
    current_hour = current_dt.hour

    time_config = PRICING_CONFIG["time_coefficients"]

    for period_name, details in time_config.items():
        if period_name == "off_peak": # off_peak is the default if no other range matches
            continue
        for r in details["ranges"]:
            start_hour, end_hour = r
            if start_hour <= end_hour: # e.g., 7-10
                if start_hour <= current_hour < end_hour:
                    return details["coef"], period_name
            else: # e.g., 22-6 (spans midnight)
                if start_hour <= current_hour < 24 or 0 <= current_hour < end_hour:
                    return details["coef"], period_name
    return time_config["off_peak"]["coef"], "off_peak"

def calculate_dynamic_price(origin_zone_name, destination_zone_name, vehicle_type_key, current_dt=None):
    """
    Calculates the dynamic price for a tow service.

    Args:
        origin_zone_name (str): Name of the origin zone (e.g., "D1", "Lucan").
        destination_zone_name (str): Name of the destination zone.
        vehicle_type_key (str): Key for the vehicle type (e.g., "sedan", "suv").
        current_dt (datetime.datetime, optional): The current datetime. Defaults to now().

    Returns:
        dict: Contains the calculated price and a breakdown of the calculation.
              e.g., {"price": 75.50, "breakdown": {...}}
    """
    cfg = PRICING_CONFIG
    base_unit = cfg["base_unit"]

    # Get zone coefficients (default to "Outside" if not found)
    coef_origin_zone = cfg["zones"].get(origin_zone_name, cfg["zones"]["Outside"])["origin"]
    coef_destination_zone = cfg["zones"].get(destination_zone_name, cfg["zones"]["Outside"])["destination"]

    # Get vehicle coefficient (default to "other" if not found)
    coef_vehicle = cfg["vehicle_types"].get(vehicle_type_key, cfg["vehicle_types"]["other"])

    # Get time coefficient
    coef_time, time_period_name = get_time_coefficient(current_dt)

    # Traffic coefficient (fixed for now)
    coef_traffic = cfg["traffic_coefficient"]

    # Weights
    weights = cfg["weights"]
    weight_origin_zone = weights["origin_zone"]
    weight_destination_zone = weights["destination_zone"]
    weight_traffic = weights["traffic"]
    weight_time = weights["time"]
    
    # Normalize weights (optional, if they don't sum to 1, though current ones do)
    total_weight = sum(weights.values())
    if total_weight != 1.0:
        # This is a simple normalization. If you want to ensure they always sum to 1
        # and one changes, the others would need to adjust proportionally, which is more complex.
        # For now, we assume the configured weights are intended as relative importances.
        pass # Or raise an error, or normalize. Current weights sum to 1.

    # Calculate the weighted sum of coefficients
    weighted_sum_factors = (
        coef_origin_zone * weight_origin_zone +
        coef_destination_zone * weight_destination_zone +
        coef_traffic * weight_traffic +
        coef_time * weight_time
    )

    # Calculate final price
    price = base_unit * weighted_sum_factors * coef_vehicle

    breakdown = {
        "base_unit": base_unit,
        "origin_zone_name": origin_zone_name,
        "coef_origin_zone": coef_origin_zone,
        "weight_origin_zone": weight_origin_zone,
        "destination_zone_name": destination_zone_name,
        "coef_destination_zone": coef_destination_zone,
        "weight_destination_zone": weight_destination_zone,
        "coef_traffic": coef_traffic,
        "weight_traffic": weight_traffic,
        "time_period_name": time_period_name,
        "coef_time": coef_time,
        "weight_time": weight_time,
        "weighted_sum_factors_before_vehicle_coef": weighted_sum_factors,
        "vehicle_type_key": vehicle_type_key,
        "coef_vehicle": coef_vehicle,
        "calculated_price_raw": price,
        "calculated_price_rounded": round(price, 2)
    }

    return {"price": round(price, 2), "breakdown": breakdown}

# Example Usage (for testing)
if __name__ == "__main__":
    # Test case 1: D1 to D2, Sedan, current time (assume off-peak for simplicity if run outside peak/night)
    price_details_1 = calculate_dynamic_price("D1", "D2", "sedan")
    print(f"Test Case 1 (D1 to D2, Sedan, Auto Time): Price: €{price_details_1['price']}")
    # print("Breakdown 1:", price_details_1['breakdown'])

    # Test case 2: Lucan to Swords, SUV, specific peak time
    peak_time = datetime.datetime(2024, 5, 10, 8, 30) # 8:30 AM on a Friday
    price_details_2 = calculate_dynamic_price("Lucan", "Swords", "suv", current_dt=peak_time)
    print(f"Test Case 2 (Lucan to Swords, SUV, Peak Time 8:30 AM): Price: €{price_details_2['price']}")
    # print("Breakdown 2:", price_details_2['breakdown'])

    # Test case 3: Unknown zone to D4, Truck, specific night time
    night_time = datetime.datetime(2024, 5, 10, 23, 0) # 11:00 PM
    price_details_3 = calculate_dynamic_price("UnknownZone", "D4", "truck", current_dt=night_time)
    print(f"Test Case 3 (UnknownZone to D4, Truck, Night Time 11:00 PM): Price: €{price_details_3['price']}")
    # print("Breakdown 3:", price_details_3['breakdown'])
    
    # Test case 4: D18 to Clondalkin, Motorcycle, specific off-peak time
    off_peak_time = datetime.datetime(2024, 5, 10, 14, 0) # 2:00 PM
    price_details_4 = calculate_dynamic_price("D18", "Clondalkin", "motorcycle", current_dt=off_peak_time)
    print(f"Test Case 4 (D18 to Clondalkin, Motorcycle, Off-Peak 2:00 PM): Price: €{price_details_4['price']}")
    # print("Breakdown 4:", price_details_4['breakdown'])

    # Test case 5: Skerries to Balbriggan, Van, specific night time (across midnight)
    night_time_across_midnight = datetime.datetime(2024, 5, 11, 1, 30) # 1:30 AM
    price_details_5 = calculate_dynamic_price("Skerries", "Balbriggan", "van", current_dt=night_time_across_midnight)
    print(f"Test Case 5 (Skerries to Balbriggan, Van, Night Time 1:30 AM): Price: €{price_details_5['price']}")
    # print("Breakdown 5:", price_details_5['breakdown'])

