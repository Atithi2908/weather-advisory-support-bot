"""Node: fetch_weather

Retrieves factual weather metrics using Open-Meteo Forecast API.
Handles:
- Current weather (today / now / unspecified)
- Future time windows (tomorrow, this evening, tonight, etc.) via hourly forecast
- Service/network failure
- Does not hallucinate or fabricate weather metrics
"""

from typing import Any, Dict
from backend.app.graph.state import WeatherState
from backend.app.services.weather_service import (
    WeatherServiceError,
    default_weather_service,
)

def _needs_hourly_lookup(time_context: str | None) -> bool:
    """Determine if the time_context requires hourly forecast/historical data rather than current real-time observation."""
    if not time_context:
        return False
    tc = time_context.lower().strip()
    if tc in ("now", "right now", "currently", "current", "today"):
        return False
    return True


def fetch_weather_node(state: WeatherState) -> Dict[str, Any]:
    """LangGraph node to fetch weather conditions using coordinates and time context in state."""
    lat = state.get("latitude")
    lon = state.get("longitude")
    time_context = state.get("time_context")

    if lat is None or lon is None:
        return {
            "weather": None,
            "error": "Cannot fetch weather because geographic coordinates are missing.",
        }

    try:
        if _needs_hourly_lookup(time_context):
            weather_data = default_weather_service.get_forecast_weather(
                latitude=float(lat),
                longitude=float(lon),
                time_context=time_context,
            )
        else:
            weather_data = default_weather_service.get_current_weather(
                latitude=float(lat),
                longitude=float(lon),
            )
    except WeatherServiceError as e:
        return {
            "weather": None,
            "error": f"Weather service temporarily unavailable: {e}",
        }
    except Exception as e:
        return {
            "weather": None,
            "error": f"Unexpected error while fetching weather data: {e}",
        }

    return {
        "weather": weather_data,
        "error": None,
    }
