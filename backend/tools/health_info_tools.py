from langchain.tools import tool

from backend.services.api_services import (
    search_health_information,
    get_weather,
    get_air_quality
)


@tool
def health_information_tool(query: str):
    """Search external health information for a condition or health topic."""
    return search_health_information(query)


@tool
def weather_tool(city: str):
    """Get current weather information for a city."""
    return get_weather(city)


@tool
def air_quality_tool(city: str):
    """Get current air-quality information for a city."""
    return get_air_quality(city)