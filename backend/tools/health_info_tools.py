"""LangChain tools that wrap the external APIs for the chatbot agent."""

from langchain_core.tools import tool

from backend.services.api_services import (
    search_health_information,
    get_weather,
    get_air_quality,
    search_drug_label,
)
from backend.services.http_client import ExternalAPIError


@tool
def health_information_tool(query: str) -> str:
    """Look up health conditions related to a term (e.g. 'diabetes'). Returns related condition names only, not explanations."""
    try:
        result = search_health_information(query)
    except ExternalAPIError as exc:
        return f"Could not look that up right now ({exc.message})."
    except Exception as exc:
        return f"Could not look that up right now ({exc})."

    names = []
    for item in result["results"]:
        # The API may return ["Name"] or [["Name"]]; flatten either form
        if isinstance(item, list):
            names.extend(str(x) for x in item if x)
        elif item:
            names.append(str(item))

    if not names:
        return f"No related health conditions found for '{query}'."
    return "Related conditions: " + ", ".join(names)

@tool
def weather_tool(city: str) -> str:
    """Get the current weather for a city. Use when the user asks about weather."""
    try:
        w = get_weather(city)
    except ExternalAPIError as exc:
        return f"Could not get the weather ({exc.message})."
    return (
        f"Weather in {w['city']}: {w['description']}, "
        f"{w['temperature_c']} C, humidity {w['humidity_percent']}%."
    )


@tool
def air_quality_tool(city: str) -> str:
    """Get current air quality (PM2.5, PM10, CO, NO2) for any city. Use when the user asks about air or pollution."""
    try:
        a = get_air_quality(city)
    except ExternalAPIError as exc:
        return f"Could not get air quality ({exc.message})."
    return (
        f"Air quality in {a['city']}: PM2.5 {a['pm2_5']}, PM10 {a['pm10']}, "
        f"CO {a['carbon_monoxide']}, NO2 {a['nitrogen_dioxide']} (ug/m3)."
    )


@tool
def drug_label_tool(drug_name: str) -> str:
    """Look up the official FDA label summary for a medicine (purpose, warnings, dosage). Never give personal dosing advice."""
    try:
        d = search_drug_label(drug_name)
    except ExternalAPIError as exc:
        return f"Could not find label information ({exc.message})."
    return (
        f"{d['drug']} - Purpose: {d['purpose']} | Warnings: {d['warnings']} | "
        f"Dosage: {d['dosage_and_administration']}. {d['note']}"
    )