"""Unit tests for Open-Meteo WeatherService."""

from unittest.mock import MagicMock, patch
import pytest
import requests

from backend.app.services.weather_service import (
    WeatherService,
    WeatherServiceError,
)


def test_geocode_success():
    """Verify successful geocoding returns coordinates and canonical name."""
    service = WeatherService()
    result = service.geocode_location("Delhi")
    assert result is not None
    assert "latitude" in result
    assert "longitude" in result
    assert result["latitude"] is not None
    assert result["longitude"] is not None
    assert "Delhi" in result["name"]


def test_geocode_alias_bangalore():
    """Verify alias mapping for Bangalore resolves to Bengaluru in Karnataka, India."""
    service = WeatherService()
    result = service.geocode_location("Bangalore")
    assert result is not None
    assert result["name"] == "Bengaluru"
    assert result["country"] == "India"
    assert abs(result["latitude"] - 12.97) < 0.1
    assert abs(result["longitude"] - 77.59) < 0.1


def test_geocode_nonexistent_location():
    """Verify nonexistent location returns None without fabricating coordinates."""
    service = WeatherService()
    result = service.geocode_location("NonExistentFakeCityXYZ99999")
    assert result is None


def test_geocode_empty_string():
    """Verify empty or blank query returns None immediately."""
    service = WeatherService()
    assert service.geocode_location("") is None
    assert service.geocode_location("   ") is None


def test_geocode_network_failure():
    """Verify network errors raise WeatherServiceError."""
    service = WeatherService()
    with patch("requests.get", side_effect=requests.ConnectionError("Connection failed")):
        with pytest.raises(WeatherServiceError) as exc_info:
            service.geocode_location("Delhi")
        assert "Failed to connect" in str(exc_info.value)


def test_get_current_weather_success():
    """Verify fetching live weather returns expected structured fields."""
    service = WeatherService()
    # Coordinates for Bengaluru
    weather = service.get_current_weather(latitude=12.97194, longitude=77.59369)
    assert weather is not None
    assert "temperature" in weather
    assert "wind_speed" in weather
    assert "precipitation" in weather
    assert "precipitation_probability" in weather
    assert "uv_index" in weather
    assert "units" in weather
    assert weather["units"]["temperature"] == "°C"
    assert weather["units"]["wind_speed"] == "km/h"


def test_get_current_weather_network_failure():
    """Verify network error during forecast fetch raises WeatherServiceError."""
    service = WeatherService()
    with patch("requests.get", side_effect=requests.Timeout("Request timed out")):
        with pytest.raises(WeatherServiceError) as exc_info:
            service.get_current_weather(latitude=12.97, longitude=77.59)
        assert "Failed to fetch forecast" in str(exc_info.value)
