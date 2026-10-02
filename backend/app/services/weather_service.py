"""Open-Meteo Weather and Geocoding Service.

Responsible for:
1. Geocoding human-readable location names into latitude/longitude using Open-Meteo Geocoding API.
2. Fetching real-time weather metrics using Open-Meteo Forecast API.
"""

import difflib
from typing import Any, Dict, Optional
import requests

from backend.app.config import (
    HTTP_TIMEOUT_SECONDS,
    OPEN_METEO_FORECAST_URL,
    OPEN_METEO_GEOCODING_URL,
)


class WeatherServiceError(Exception):
    """Raised when an external API or network error occurs during weather or geocoding calls."""
    pass


# Common city alias dictionary to resolve common colloquial names and misspellings in Open-Meteo
CITY_ALIASES: Dict[str, str] = {
    "bangalore": "Bengaluru",
    "banglore": "Bengaluru",
    "bengalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "bombay": "Mumbai",
    "mumbai": "Mumbai",
    "calcutta": "Kolkata",
    "kolkata": "Kolkata",
    "madras": "Chennai",
    "chennai": "Chennai",
    "delhi": "Delhi",
    "new delhi": "New Delhi",
    "peking": "Beijing",
    "beijing": "Beijing",
    "gurgaon": "Gurugram",
    "gurugram": "Gurugram",
    "cochin": "Kochi",
    "kochi": "Kochi",
    "trivandrum": "Thiruvananthapuram",
    "thiruvananthapuram": "Thiruvananthapuram",
    "pune": "Pune",
    "hyderabad": "Hyderabad",
    "ahmedabad": "Ahmedabad",
    "jaipur": "Jaipur",
    "chandigarh": "Chandigarh",
    "mysore": "Mysuru",
    "mysuru": "Mysuru",
}


class WeatherService:
    """Service client for Open-Meteo APIs."""

    def __init__(
        self,
        geocoding_url: str = OPEN_METEO_GEOCODING_URL,
        forecast_url: str = OPEN_METEO_FORECAST_URL,
        timeout_seconds: int = HTTP_TIMEOUT_SECONDS,
    ):
        self.geocoding_url = geocoding_url
        self.forecast_url = forecast_url
        self.timeout_seconds = timeout_seconds

    def geocode_location(self, location_name: str) -> Optional[Dict[str, Any]]:
        """Geocode a place name into coordinates using Open-Meteo Geocoding API.

        Args:
            location_name: Name of the city or locality (e.g., 'Bangalore', 'Delhi').

        Returns:
            Dict containing latitude, longitude, and canonical name, or None if no result.

        Raises:
            WeatherServiceError: If the remote API returns an error or is unreachable.
        """
        if not location_name or not location_name.strip():
            return None

        clean_name = location_name.strip()
        lower_name = clean_name.lower()

        # 1. Exact alias match
        search_query = CITY_ALIASES.get(lower_name)
        if not search_query:
            # 2. Fuzzy alias match for minor typos (e.g. 'banglore' -> 'bangalore' -> 'Bengaluru')
            close_matches = difflib.get_close_matches(
                lower_name, list(CITY_ALIASES.keys()), n=1, cutoff=0.75
            )
            if close_matches:
                search_query = CITY_ALIASES[close_matches[0]]
            else:
                search_query = clean_name

        params = {
            "name": search_query,
            "count": 5,
            "language": "en",
            "format": "json",
        }

        try:
            response = requests.get(
                self.geocoding_url,
                params=params,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            raise WeatherServiceError(
                f"Failed to connect to Open-Meteo geocoding service: {e}"
            ) from e
        except ValueError as e:
            raise WeatherServiceError(
                f"Invalid JSON received from Open-Meteo geocoding service: {e}"
            ) from e

        results = data.get("results")
        if not results:
            # If searched with alias and got nothing, or if original had no alias, try original
            if search_query != clean_name:
                params["name"] = clean_name
                try:
                    res2 = requests.get(
                        self.geocoding_url,
                        params=params,
                        timeout=self.timeout_seconds,
                    )
                    res2.raise_for_status()
                    results = res2.json().get("results")
                except requests.RequestException:
                    pass

        if not results:
            return None

        # Pick top matched result
        top = results[0]
        name = top.get("name", clean_name)
        country = top.get("country", "")
        admin1 = top.get("admin1", "")
        parts = [p for p in [name, admin1, country] if p]
        resolved_name = ", ".join(parts)

        return {
            "name": name,
            "latitude": float(top["latitude"]),
            "longitude": float(top["longitude"]),
            "country": country,
            "admin1": admin1,
            "timezone": top.get("timezone", "UTC"),
            "resolved_name": resolved_name,
        }

    def get_current_weather(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch current weather data for coordinates using Open-Meteo Forecast API.

        Args:
            latitude: Latitude coordinate.
            longitude: Longitude coordinate.

        Returns:
            Dictionary containing temperature, wind_speed, precipitation, etc.

        Raises:
            WeatherServiceError: If the remote API call fails or returns invalid data.
        """
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,relative_humidity_2m,precipitation,"
                "precipitation_probability,wind_speed_10m,wind_gusts_10m,uv_index,weather_code"
            ),
            "forecast_days": 1,
            "timezone": "auto",
        }

        try:
            response = requests.get(
                self.forecast_url,
                params=params,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            raise WeatherServiceError(
                f"Failed to fetch forecast from Open-Meteo: {e}"
            ) from e
        except ValueError as e:
            raise WeatherServiceError(
                f"Invalid JSON received from Open-Meteo forecast service: {e}"
            ) from e

        current = data.get("current")
        if not current:
            raise WeatherServiceError(
                "Open-Meteo response did not contain current weather data."
            )

        return {
            "temperature": current.get("temperature_2m"),
            "wind_speed": current.get("wind_speed_10m"),
            "precipitation": current.get("precipitation"),
            "precipitation_probability": current.get("precipitation_probability"),
            "uv_index": current.get("uv_index"),
            "relative_humidity": current.get("relative_humidity_2m"),
            "wind_gusts": current.get("wind_gusts_10m"),
            "weather_code": current.get("weather_code"),
            "time": current.get("time"),
            "units": {
                "temperature": "°C",
                "wind_speed": "km/h",
                "precipitation": "mm",
                "precipitation_probability": "%",
                "relative_humidity": "%",
                "uv_index": "",
            },
        }

    def get_forecast_weather(
        self,
        latitude: float,
        longitude: float,
        time_context: Optional[str] = None,
        timezone: str = "auto",
    ) -> Dict[str, Any]:
        """Fetch weather data for a past, present, or future time window using hourly Open-Meteo data.

        Supports time_context values like 'tomorrow', 'yesterday', 'tomorrow morning',
        'yesterday afternoon', 'this evening', 'this afternoon', 'tonight', 'day after tomorrow',
        'this weekend'.

        Args:
            latitude: Latitude coordinate.
            longitude: Longitude coordinate.
            time_context: Temporal context string (e.g. 'tomorrow', 'yesterday', 'this evening').
            timezone: Timezone string (default 'auto' lets Open-Meteo detect).

        Returns:
            Dictionary with aggregated weather metrics for the requested window.

        Raises:
            WeatherServiceError: If the remote API call fails.
        """
        from datetime import datetime, timedelta

        past_days = 3
        forecast_days = 7

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": (
                "temperature_2m,relative_humidity_2m,precipitation,"
                "precipitation_probability,wind_speed_10m,wind_gusts_10m,uv_index,weather_code"
            ),
            "past_days": past_days,
            "forecast_days": forecast_days,
            "timezone": timezone,
        }

        try:
            response = requests.get(
                self.forecast_url,
                params=params,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            raise WeatherServiceError(
                f"Failed to fetch forecast from Open-Meteo: {e}"
            ) from e
        except ValueError as e:
            raise WeatherServiceError(
                f"Invalid JSON received from Open-Meteo forecast service: {e}"
            ) from e

        hourly = data.get("hourly")
        if not hourly or not hourly.get("time"):
            raise WeatherServiceError(
                "Open-Meteo response did not contain hourly forecast data."
            )

        times = hourly["time"]
        # Parse first timestamp to determine base local date (which is past_days before today)
        first_time = datetime.fromisoformat(times[0])
        today = (first_time + timedelta(days=past_days)).date()

        # Determine target date and hour range based on time_context
        tc = (time_context or "").lower().strip()
        date_label = "today"
        if "yesterday" in tc or "yday" in tc:
            target_date = today - timedelta(days=1)
            date_label = "yesterday"
        elif "day before yesterday" in tc:
            target_date = today - timedelta(days=2)
            date_label = "day before yesterday"
        elif "day after tomorrow" in tc or "overmorrow" in tc:
            target_date = today + timedelta(days=2)
            date_label = "day after tomorrow"
        elif "tomorrow" in tc or "tmrw" in tc or "2morrow" in tc:
            target_date = today + timedelta(days=1)
            date_label = "tomorrow"
        elif "weekend" in tc:
            days_until_saturday = (5 - today.weekday()) % 7
            if days_until_saturday == 0 and today.weekday() != 5:
                days_until_saturday = 7
            target_date = today + timedelta(days=days_until_saturday)
            date_label = "this weekend"
        else:
            target_date = today
            date_label = "today"

        # Determine hour window
        if "morning" in tc:
            hour_start, hour_end = 6, 12
        elif "afternoon" in tc:
            hour_start, hour_end = 12, 17
        elif "evening" in tc:
            hour_start, hour_end = 17, 21
        elif "tonight" in tc or "night" in tc:
            hour_start, hour_end = 20, 24
        else:
            # Daytime window 08:00 - 18:00
            hour_start, hour_end = 8, 18

        # Filter hourly data to the target window
        indices = []
        for i, t in enumerate(times):
            dt = datetime.fromisoformat(t)
            if dt.date() == target_date and hour_start <= dt.hour < hour_end:
                indices.append(i)

        if not indices:
            raise WeatherServiceError(
                f"No hourly weather data available for '{time_context or 'requested window'}' "
                f"(date={target_date}, hours={hour_start:02d}:00–{hour_end:02d}:00)."
            )

        def _safe_avg(key: str) -> Optional[float]:
            vals = [hourly[key][i] for i in indices if hourly.get(key) and hourly[key][i] is not None]
            return round(sum(vals) / len(vals), 1) if vals else None

        def _safe_max(key: str) -> Optional[float]:
            vals = [hourly[key][i] for i in indices if hourly.get(key) and hourly[key][i] is not None]
            return max(vals) if vals else None

        def _safe_sum(key: str) -> Optional[float]:
            vals = [hourly[key][i] for i in indices if hourly.get(key) and hourly[key][i] is not None]
            return round(sum(vals), 1) if vals else None

        # Representative time is the middle of the window
        mid_idx = indices[len(indices) // 2]
        is_historical = target_date < today

        return {
            "temperature": _safe_avg("temperature_2m"),
            "wind_speed": _safe_max("wind_speed_10m"),
            "precipitation": _safe_sum("precipitation"),
            "precipitation_probability": _safe_max("precipitation_probability"),
            "uv_index": _safe_max("uv_index"),
            "relative_humidity": _safe_avg("relative_humidity_2m"),
            "wind_gusts": _safe_max("wind_gusts_10m"),
            "weather_code": hourly.get("weather_code", [None])[mid_idx] if hourly.get("weather_code") else None,
            "time": times[mid_idx],
            "forecast_window": f"{target_date} {hour_start:02d}:00–{hour_end:02d}:00 ({date_label.title()})",
            "is_historical": is_historical,
            "units": {
                "temperature": "°C",
                "wind_speed": "km/h",
                "precipitation": "mm",
                "precipitation_probability": "%",
                "relative_humidity": "%",
                "uv_index": "",
            },
        }


# Convenience module-level instances
default_weather_service = WeatherService()


def geocode_location(location_name: str) -> Optional[Dict[str, Any]]:
    """Module-level helper to geocode location using default weather service."""
    return default_weather_service.geocode_location(location_name)


def get_current_weather(latitude: float, longitude: float) -> Dict[str, Any]:
    """Module-level helper to fetch current weather using default weather service."""
    return default_weather_service.get_current_weather(latitude, longitude)

