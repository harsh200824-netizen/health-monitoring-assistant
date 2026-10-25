import requests


def search_health_information(query):
    """Search for health information from an external source."""

    url = "https://clinicaltables.nlm.nih.gov/api/conditions/v3/search"

    params = {
        "terms": query,
        "maxList": 5
    }

    response = requests.get(
        url,
        params=params,
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    return {
        "query": query,
        "results": data[3]
    }


def get_weather(city):
    """Get current weather information for a city."""

    url = "https://wttr.in/" + city

    params = {
        "format": "j1"
    }

    response = requests.get(
        url,
        params=params,
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    current = data["current_condition"][0]

    return {
        "city": city,
        "temperature": current["temp_C"],
        "humidity": current["humidity"],
        "weather": current["weatherDesc"][0]["value"]
    }

def get_air_quality(city):
    """Get air quality information for a city."""

    url = "https://air-quality-api.open-meteo.com/v1/air-quality"

    # Coordinates for Delhi
    coordinates = {
        "Delhi": (28.6139, 77.2090)
    }

    if city not in coordinates:
        return {
            "error": "City not supported yet"
        }

    latitude, longitude = coordinates[city]

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide"
    }

    response = requests.get(
        url,
        params=params,
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    return {
        "city": city,
        "pm10": data["current"]["pm10"],
        "pm2_5": data["current"]["pm2_5"],
        "carbon_monoxide": data["current"]["carbon_monoxide"],
        "nitrogen_dioxide": data["current"]["nitrogen_dioxide"]
    }