"""Integration tests for the LangGraph workflow corresponding to Step 12 requirements."""

from unittest.mock import patch
import pytest

from backend.app.graph.workflow import create_weather_graph
from backend.app.services.weather_service import WeatherServiceError


@pytest.fixture
def graph():
    """Create a fresh compiled graph instance for each test."""
    return create_weather_graph()


def test_normal_query_bangalore_cycling(graph):
    """Test 1: Normal query flow.
    
    Query: 'Can I cycle in Bangalore today?'
    Verifies:
    - query understood (activity=cycling, location=Bangalore)
    - Bangalore resolved to real coordinates
    - live weather fetched directly from Open-Meteo
    - response generated with factual weather numbers
    - no error in final state
    """
    config = {"configurable": {"thread_id": "test-1-bangalore"}}
    result = graph.invoke(
        {"user_query": "Can I cycle in Bangalore today?"},
        config=config,
    )

    assert result["activity"] == "cycling"
    assert result["location"] == "Bangalore"
    assert "Bengaluru" in result["resolved_location_name"]
    assert result["latitude"] is not None
    assert result["longitude"] is not None
    assert result["weather"] is not None
    assert "temperature" in result["weather"]
    assert "wind_speed" in result["weather"]
    assert result["response"] is not None
    assert result["error"] is None

    # Verify weather facts are embedded in response
    temp_str = str(result["weather"]["temperature"])
    assert temp_str in result["response"]


def test_different_activity_delhi_picnic(graph):
    """Test 2: Different activity flow.
    
    Query: 'Is it a good day for a picnic in Delhi?'
    Verifies:
    - activity identified as picnic
    - location resolved to Delhi
    - live weather fetched successfully
    - response generated
    """
    config = {"configurable": {"thread_id": "test-2-delhi"}}
    result = graph.invoke(
        {"user_query": "Is it a good day for a picnic in Delhi?"},
        config=config,
    )

    assert result["activity"] == "picnic"
    assert "delhi" in result["location"].lower()
    assert result["latitude"] is not None
    assert result["longitude"] is not None
    assert result["weather"] is not None
    assert result["response"] is not None
    assert result["error"] is None


def test_location_failure_invalid_city(graph):
    """Test 3: Location failure handling.
    
    Query with nonexistent location.
    Verifies:
    - location resolution fails honestly
    - no fabricated coordinates
    - weather is None
    - error branch reached and polite explanation provided
    """
    config = {"configurable": {"thread_id": "test-3-invalid-loc"}}
    result = graph.invoke(
        {"user_query": "Can I go for a run in AtlantisNeverlandCity123456789?"},
        config=config,
    )

    assert result.get("latitude") is None
    assert result.get("longitude") is None
    assert result.get("weather") is None
    assert result.get("error") is not None
    assert "could not find coordinates" in result.get("error", "").lower()
    assert "could not find or resolve the location" in result.get("response", "").lower()


def test_weather_api_failure_simulation(graph):
    """Test 4: Weather API failure handling.
    
    Simulates weather service timeout or outage.
    Verifies:
    - location is resolved successfully
    - weather failure triggers conditional error edge
    - weather is None (not fabricated)
    - honest explanation returned to the user
    """
    config = {"configurable": {"thread_id": "test-4-weather-failure"}}

    with patch(
        "backend.app.nodes.fetch_weather.default_weather_service.get_current_weather",
        side_effect=WeatherServiceError("Open-Meteo connection timed out"),
    ):
        result = graph.invoke(
            {"user_query": "Can I cycle in Bangalore today?"},
            config=config,
        )

        assert result["latitude"] is not None
        assert result["longitude"] is not None
        assert result["weather"] is None
        assert result["error"] is not None
        assert "temporarily unavailable" in result["error"]
        assert "weather service could not be reached" in result["response"].lower()


def test_conversational_followup_session_context(graph):
    """Test 5: Conversational follow-up in the same session.
    
    Turn 1: 'Can I cycle in Bangalore today?'
    Turn 2: 'What about this evening?'
    Verifies:
    - session retains location (Bangalore) and activity (cycling)
    - updates time context (this evening)
    - conversation history grows across turns
    """
    config = {"configurable": {"thread_id": "test-5-session-memory"}}

    # Turn 1
    r1 = graph.invoke(
        {"user_query": "Can I cycle in Bangalore today?"},
        config=config,
    )
    assert r1["activity"] == "cycling"
    assert r1["location"] == "Bangalore"
    assert r1["time_context"] == "today"
    assert len(r1["conversation_history"]) == 2

    # Turn 2: Follow-up without repeating activity or location
    r2 = graph.invoke(
        {"user_query": "What about this evening?"},
        config=config,
    )
    assert r2["activity"] == "cycling"  # Retained
    assert r2["location"] == "Bangalore"  # Retained
    assert r2["time_context"] == "this evening"  # Updated
    assert "Bengaluru" in r2["resolved_location_name"]
    assert r2["weather"] is not None
    assert len(r2["conversation_history"]) == 4  # Both turns stored
