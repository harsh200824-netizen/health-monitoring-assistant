"""External health and wellness APIs.

Each function returns a plain dict on success, or raises ExternalAPIError.
Callers (the agent and routes) turn that into a readable message.
"""

from backend.services.http_client import ExternalAPIError, get_json


# 1. NLM Clinical Tables: search health conditions
def search_health_information(query):
    query = (query or "").strip()
    if not query:
        raise ExternalAPIError("NLM Clinical Tables", "search text is empty")

    data = get_json(
        "NLM Clinical Tables",
        "https://clinicaltables.nlm.nih.gov/api/conditions/v3/search",
        params={"terms": query, "maxList": 5},
    )

    # Response format: [total, codes, extra, display_names]
    if not isinstance(data, list) or len(data) < 4:
        raise ExternalAPIError("NLM Clinical Tables", "unexpected response format")

    names = []
    for item in data[3]:
        if isinstance(item, list):
            names.extend(str(x) for x in item if x)
        elif item:
            names.append(str(item))

    return {"query": query, "results": names}


# 2. Geocoding: turn a city name into coordinates (Open-Meteo, free)
def geocode_city(city):
    city = (city or "").strip()
    if not city:
        raise ExternalAPIError("Open-Meteo geocoding", "city name is empty")

    data = get_json(
        "Open-Meteo geocoding",
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1, "language": "en", "format": "json"},
    )

    results = data.get("results") or []
    if not results:
        raise ExternalAPIError("Open-Meteo geocoding", f"no place found for '{city}'")

    place = results[0]
    return {
        "name": place.get("name", city),
        "country": place.get("country", ""),
        "latitude": place["latitude"],
        "longitude": place["longitude"],
    }


# 3. wttr.in: current weather. The city is passed as a param, so it is URL-encoded.
def get_weather(city):
    city = (city or "").strip()
    if not city:
        raise ExternalAPIError("wttr.in", "city name is empty")

    data = get_json(
        "wttr.in",
        f"https://wttr.in/{city}",
        params={"format": "j1"},
    )

    try:
        current = data["current_condition"][0]
        return {
            "city": city,
            "temperature_c": current["temp_C"],
            "humidity_percent": current["humidity"],
            "description": current["weatherDesc"][0]["value"],
        }
    except (KeyError, IndexError, TypeError):
        raise ExternalAPIError("wttr.in", "unexpected response format")


# 4. Open-Meteo air quality: works for any city now, via geocoding.
def get_air_quality(city):
    city = (city or "").strip()
    place = geocode_city(city)

    data = get_json(
        "Open-Meteo air quality",
        "https://air-quality-api.open-meteo.com/v1/air-quality",
        params={
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide",
        },
    )

    try:
        current = data["current"]
    except (KeyError, TypeError):
        raise ExternalAPIError("Open-Meteo air quality", "unexpected response format")

    return {
        "city": place["name"],
        "country": place["country"],
        "pm10": current.get("pm10"),
        "pm2_5": current.get("pm2_5"),
        "carbon_monoxide": current.get("carbon_monoxide"),
        "nitrogen_dioxide": current.get("nitrogen_dioxide"),
    }


# 5. OpenFDA: official drug label information (no key needed for light use)
def search_drug_label(drug_name):
    drug_name = (drug_name or "").strip()
    if not drug_name:
        raise ExternalAPIError("OpenFDA", "drug name is empty")

    data = get_json(
        "OpenFDA",
        "https://api.fda.gov/drug/label.json",
        params={"search": f'openfda.generic_name:"{drug_name}"', "limit": 1},
    )

    results = data.get("results") or []
    if not results:
        raise ExternalAPIError("OpenFDA", f"no label found for '{drug_name}'")

    label = results[0]

    def first(field):
        values = label.get(field) or []
        return values[0][:600] if values else "Not listed"

    return {
        "drug": drug_name,
        "purpose": first("purpose"),
        "warnings": first("warnings"),
        "dosage_and_administration": first("dosage_and_administration"),
        "note": "Summarised from the FDA label. Read the leaflet or ask a pharmacist.",
    }