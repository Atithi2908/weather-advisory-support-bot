"""Node: resolve_location

Resolves the user's location string into geographic coordinates using Open-Meteo Geocoding API.
Handles:
- Successful geocoding
- Unknown/unresolvable location (no coordinates fabricated)
- API/network failure
"""

from typing import Any, Dict
from backend.app.graph.state import WeatherState
from backend.app.services.weather_service import (
    WeatherServiceError,
    default_weather_service,
)


def resolve_location_node(state: WeatherState) -> Dict[str, Any]:
    """LangGraph node to geocode the extracted location into latitude/longitude."""
    location = state.get("location")

    if not location or not str(location).strip():
        return {
            "latitude": None,
            "longitude": None,
            "resolved_location_name": None,
            "weather": None,
            "error": "No location was specified. Please provide a city or locality name.",
        }

    try:
        geo = default_weather_service.geocode_location(str(location).strip())
    except WeatherServiceError as e:
        return {
            "latitude": None,
            "longitude": None,
            "resolved_location_name": None,
            "weather": None,
            "error": f"Unable to reach location service: {e}",
        }
    except Exception as e:
        return {
            "latitude": None,
            "longitude": None,
            "resolved_location_name": None,
            "weather": None,
            "error": f"Unexpected error while resolving location: {e}",
        }

    if not geo:
        return {
            "latitude": None,
            "longitude": None,
            "resolved_location_name": None,
            "weather": None,
            "error": f"Could not find coordinates for location '{location}'. Please check the spelling or specify a nearby city.",
        }

    return {
        "latitude": geo["latitude"],
        "longitude": geo["longitude"],
        "resolved_location_name": geo.get("resolved_name", location),
        "error": None,
    }
