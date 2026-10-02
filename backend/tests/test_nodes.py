"""Unit tests for individual LangGraph nodes."""

from unittest.mock import patch
import pytest

from backend.app.graph.state import WeatherState
from backend.app.nodes.fetch_weather import fetch_weather_node
from backend.app.nodes.generate_response import generate_response_node
from backend.app.nodes.handle_error import handle_error_node
from backend.app.nodes.match_sop import match_sop_node
from backend.app.nodes.no_guidance import no_guidance_node
from backend.app.nodes.resolve_location import resolve_location_node
from backend.app.nodes.understand_query import understand_query_node
from backend.app.services.weather_service import WeatherServiceError


def test_understand_query_extraction():
    """Verify understand_query extracts activity, location, and time context."""
    state: WeatherState = {
        "user_query": "Can I cycle in Bangalore today?",
        "conversation_history": [],
    }
    result = understand_query_node(state)
    assert result["activity"] == "cycling"
    assert result["location"] == "Bangalore"
    assert result["time_context"] == "today"


def test_understand_query_followup_retention():
    """Verify follow-up query retains previous activity and location."""
    state: WeatherState = {
        "user_query": "What about this evening?",
        "activity": "cycling",
        "location": "Bangalore",
        "conversation_history": [
            {"role": "user", "content": "Can I cycle in Bangalore today?"},
            {"role": "assistant", "content": "Weather is clear."},
        ],
    }
    result = understand_query_node(state)
    assert result["activity"] == "cycling"
    assert result["location"] == "Bangalore"
    assert result["time_context"] == "this evening"


def test_resolve_location_missing():
    """Verify missing location sets an error and does not invent coordinates."""
    state: WeatherState = {"location": None}
    result = resolve_location_node(state)
    assert result["latitude"] is None
    assert result["longitude"] is None
    assert "No location was specified" in result["error"]


def test_resolve_location_not_found():
    """Verify unresolvable location sets an error honestly."""
    state: WeatherState = {"location": "AtlantisNonExistentXYZ99"}
    result = resolve_location_node(state)
    assert result["latitude"] is None
    assert result["longitude"] is None
    assert "Could not find coordinates" in result["error"]


def test_resolve_location_success():
    """Verify valid location returns coordinates and canonical name."""
    state: WeatherState = {"location": "Bangalore"}
    result = resolve_location_node(state)
    assert result["latitude"] is not None
    assert result["longitude"] is not None
    assert "Bengaluru" in result["resolved_location_name"]
    assert result["error"] is None


def test_fetch_weather_missing_coords():
    """Verify fetch_weather handles missing coordinates without crashing."""
    state: WeatherState = {"latitude": None, "longitude": None}
    result = fetch_weather_node(state)
    assert result["weather"] is None
    assert "geographic coordinates are missing" in result["error"]


def test_fetch_weather_service_failure():
    """Verify fetch_weather handles WeatherServiceError gracefully."""
    state: WeatherState = {"latitude": 12.97, "longitude": 77.59}
    with patch(
        "backend.app.nodes.fetch_weather.default_weather_service.get_current_weather",
        side_effect=WeatherServiceError("API timeout"),
    ):
        result = fetch_weather_node(state)
        assert result["weather"] is None
        assert "Weather service temporarily unavailable" in result["error"]


def test_generate_response_preserves_weather_facts():
    """Verify generate_response includes exact numeric metrics from state."""
    sample_weather = {
        "temperature": 29.5,
        "wind_speed": 12.4,
        "precipitation": 1.2,
        "precipitation_probability": 45,
        "uv_index": 5.0,
        "relative_humidity": 70,
        "time": "2026-10-01T12:00",
    }
    state: WeatherState = {
        "user_query": "Can I cycle in Bangalore today?",
        "activity": "cycling",
        "location": "Bangalore",
        "resolved_location_name": "Bengaluru, Karnataka, India",
        "time_context": "today",
        "weather": sample_weather,
        "conversation_history": [],
    }
    result = generate_response_node(state)
    response_text = result["response"]
    assert "29.5" in response_text
    assert "12.4" in response_text
    assert "1.2" in response_text
    assert "45" in response_text
    assert len(result["conversation_history"]) == 2


def test_handle_error_node():
    """Verify handle_error formats user-facing message and records turn."""
    state: WeatherState = {
        "user_query": "Is it nice in Atlantis?",
        "location": "Atlantis",
        "error": "Could not find coordinates for location 'Atlantis'.",
        "conversation_history": [],
    }
    result = handle_error_node(state)
    assert "could not find or resolve the location 'Atlantis'" in result["response"]
    assert len(result["conversation_history"]) == 2


def test_match_sop_node_found():
    """Verify match_sop_node identifies matching policy and primary selected SOP."""
    from backend.app.nodes.match_sop import match_sop_node
    state: WeatherState = {
        "activity": "cycling",
        "weather": {
            "temperature": 25.0,
            "wind_speed": 45.0,
        },
    }
    result = match_sop_node(state)
    assert result["selected_sop"] is not None
    assert result["selected_sop"]["id"] == "SOP-01"
    assert result["policy_error"] is None
    assert len(result["matched_sops"]) >= 1


def test_match_sop_node_no_match():
    """Verify match_sop_node returns empty matches and None when no policy applies."""
    from backend.app.nodes.match_sop import match_sop_node
    state: WeatherState = {
        "activity": "reading_indoors",
        "weather": {
            "temperature": 20.0,
            "wind_speed": 10.0,
        },
    }
    result = match_sop_node(state)
    assert result["selected_sop"] is None
    assert result["matched_sops"] == []
    assert result["policy_error"] is None


def test_no_guidance_node():
    """Verify no_guidance_node states no guideline applies and avoids generic safety advice."""
    from backend.app.nodes.no_guidance import no_guidance_node
    sample_weather = {
        "temperature": 21.0,
        "wind_speed": 8.0,
        "precipitation": 0.0,
        "precipitation_probability": 5,
        "uv_index": 2.0,
        "relative_humidity": 50,
        "time": "2026-10-01T12:00",
    }
    state: WeatherState = {
        "user_query": "Can I read a book in the garden?",
        "activity": "gardening",
        "location": "Bangalore",
        "resolved_location_name": "Bengaluru, Karnataka, India",
        "weather": sample_weather,
        "matched_sops": [],
        "selected_sop": None,
        "conversation_history": [],
    }
    result = no_guidance_node(state)
    resp = result["response"]
    assert "No formal Standard Operating Procedure (SOP) guideline applies" in resp
    assert "no safety clearance or generic safety recommendation" in resp
    assert len(result["conversation_history"]) == 2


def test_generate_response_openrouter_call_simulation():
    """Verify that when OpenRouter/LLM returns a response, it is used directly."""
    from unittest.mock import MagicMock
    from langchain_core.messages import AIMessage

    mock_chat = MagicMock()
    mock_chat.invoke.return_value = AIMessage(
        content="OpenRouter Advisory: Temperature is 28.0°C and Wind is 45.0 km/h. SOP-01 applies with HIGH severity: Avoid cycling."
    )

    state: WeatherState = {
        "user_query": "Can I cycle in Bangalore today?",
        "activity": "cycling",
        "location": "Bangalore",
        "weather": {"temperature": 28.0, "wind_speed": 45.0},
        "selected_sop": {"id": "SOP-01", "name": "Strong Wind Cycling", "severity": "HIGH", "advice": "Avoid cycling."},
        "matched_sops": [{"id": "SOP-01", "name": "Strong Wind Cycling", "severity": "HIGH"}],
        "conversation_history": [],
    }

    with patch("backend.app.nodes.generate_response.get_chat_model", return_value=mock_chat):
        result = generate_response_node(state)
        assert "OpenRouter Advisory" in result["response"]
        assert mock_chat.invoke.called


def test_generate_response_llm_failure_graceful_fallback():
    """Verify that if OpenRouter fails with an API error or timeout, the system gracefully falls back to deterministic SOP response."""
    from unittest.mock import MagicMock

    mock_chat = MagicMock()
    mock_chat.invoke.side_effect = RuntimeError("OpenRouter 401 Unauthorized: Invalid API key")

    state: WeatherState = {
        "user_query": "Can I cycle in Bangalore today?",
        "activity": "cycling",
        "location": "Bangalore",
        "weather": {"temperature": 28.0, "wind_speed": 45.0},
        "selected_sop": {"id": "SOP-01", "name": "Strong Wind Cycling", "severity": "HIGH", "advice": "Avoid cycling because strong winds create a severe safety risk."},
        "matched_sops": [{"id": "SOP-01"}],
        "conversation_history": [],
    }

    with patch("backend.app.nodes.generate_response.get_chat_model", return_value=mock_chat):
        result = generate_response_node(state)
        # Did not crash
        assert result["response"] is not None
        # Factual weather and deterministic SOP are present
        assert "28.0" in result["response"]
        assert "45.0" in result["response"]
        assert "SOP-01" in result["response"]
        assert "Avoid cycling" in result["response"]


def test_no_guidance_llm_failure_graceful_fallback():
    """Verify that no_guidance handles LLM failure gracefully without crashing or fabricating safety clearance."""
    from unittest.mock import MagicMock

    mock_chat = MagicMock()
    mock_chat.invoke.side_effect = ConnectionError("OpenRouter network timeout")

    state: WeatherState = {
        "user_query": "Can I play chess in Bangalore today?",
        "activity": "chess",
        "location": "Bangalore",
        "weather": {"temperature": 22.0, "wind_speed": 10.0},
        "matched_sops": [],
        "selected_sop": None,
        "conversation_history": [],
    }

    with patch("backend.app.nodes.no_guidance.get_chat_model", return_value=mock_chat):
        result = no_guidance_node(state)
        assert result["response"] is not None
        assert "No formal Standard Operating Procedure (SOP) guideline applies" in result["response"]
        assert "you are safe" not in result["response"].lower()


def test_sanitize_llm_error_does_not_leak_keys():
    """Verify that sanitize_llm_error redacts tokens and keys from error messages."""
    from backend.app.services.llm_service import sanitize_llm_error

    err_with_bearer = Exception("Failed request with Authorization: Bearer sk-or-v1-abcdef1234567890")
    sanitized = sanitize_llm_error(err_with_bearer)
    assert "sk-or-v1-abcdef1234567890" not in sanitized
    assert "[REDACTED]" in sanitized


def test_understand_query_yesterday_and_typos():
    """Verify understand_query handles yesterday and tomorrow misspellings."""
    # Test tomorrow typo
    res1 = understand_query_node({"user_query": "what about tommorrow?", "activity": "cycling", "location": "Bangalore"})
    assert res1["time_context"] == "tomorrow"
    assert res1["activity"] == "cycling"
    assert res1["location"] == "Bangalore"

    # Test yesterday
    res2 = understand_query_node({"user_query": "what about yesterday?", "activity": "cycling", "location": "Bangalore"})
    assert res2["time_context"] == "yesterday"

    # Test yesterday afternoon
    res3 = understand_query_node({"user_query": "what about yesterday afternoon in Delhi?"})
    assert res3["time_context"] == "yesterday afternoon"
    assert res3["location"] == "Delhi"

