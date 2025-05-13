import requests

def reverse_geocode_osm(lat, lon):
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "format": "json",
        "lat": lat,
        "lon": lon,
        "zoom": 18,
        "addressdetails": 1
    }
    headers = {
        "User-Agent": "TowNowApp/1.0"
    }

    response = requests.get(url, params=params, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get("display_name", "Unknown location")
    else:
        return "Unknown location"
