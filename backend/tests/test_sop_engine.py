"""Phase 2 tests for the Standard Operating Procedure (SOP) safety engine."""

import json
from pathlib import Path
from unittest.mock import patch
import pytest

from backend.app.graph.workflow import create_weather_graph
from backend.app.policies.evaluator import evaluate_condition, evaluate_policy
from backend.app.policies.loader import PolicyValidationError, load_policies
from backend.app.policies.matcher import match_sops
from backend.app.services.weather_service import WeatherServiceError


# ============================================================================
# Unit Tests: Loader and Evaluator
# ============================================================================


def test_loader_loads_all_sops():
    """Verify default policies file loads at least 10 SOPs with 3+ categories."""
    policies = load_policies()
    assert len(policies) >= 10

    categories = {p["category"] for p in policies}
    assert len(categories) >= 3
    assert "outdoor_exercise" in categories
    assert "travel" in categories
    assert "vulnerable_groups" in categories

    severities = {p["severity"] for p in policies}
    assert "HIGH" in severities
    assert "MEDIUM" in severities
    assert "LOW" in severities


def test_loader_validation_rejects_malformed_policy(tmp_path):
    """Verify loader raises PolicyValidationError on invalid schemas."""
    bad_policy = [
        {
            "id": "BAD-01",
            "name": "Missing Severity and Conditions",
        }
    ]
    bad_file = tmp_path / "bad.json"
    bad_file.write_text(json.dumps(bad_policy), encoding="utf-8")

    with pytest.raises(PolicyValidationError):
        load_policies(bad_file)


def test_condition_evaluator_operators():
    """Verify generic condition evaluator across various operators."""
    ctx = {
        "temperature": 35.5,
        "wind_speed": 42.0,
        "activity": "cycling",
        "person_context": "child",
    }

    # Numeric operators
    assert evaluate_condition({"field": "wind_speed", "operator": ">", "value": 40}, ctx) is True
    assert evaluate_condition({"field": "wind_speed", "operator": "<", "value": 40}, ctx) is False
    assert evaluate_condition({"field": "temperature", "operator": ">=", "value": 35.5}, ctx) is True
    assert evaluate_condition({"field": "temperature", "operator": "between", "value": [30, 40]}, ctx) is True
    assert evaluate_condition({"field": "temperature", "operator": "between", "value": [10, 20]}, ctx) is False

    # String & taxonomy operators
    assert evaluate_condition({"field": "activity", "operator": "equals", "value": "cycling"}, ctx) is True
    assert evaluate_condition({"field": "activity", "operator": "equals", "value": "outdoor_exercise"}, ctx) is True
    assert evaluate_condition({"field": "person_context", "operator": "equals", "value": "child"}, ctx) is True


# ============================================================================
# Step 19 Requirement Tests: Policy Matcher and Workflow Integration
# ============================================================================


def test_sop_01_strong_wind_cycling():
    """Test 1: Strong wind + cycling -> triggers SOP-01 with HIGH severity."""
    intent = {"activity": "cycling"}
    weather = {"wind_speed": 45.0, "temperature": 26.0}
    matched, selected = match_sops(intent, weather)

    assert selected is not None
    assert selected["id"] == "SOP-01"
    assert selected["severity"] == "HIGH"
    assert "strong winds create a severe safety" in selected["advice"].lower()


def test_sop_02_high_uv_outdoor_exercise():
    """Test 2: High UV + outdoor exercise -> triggers SOP-02 (MEDIUM severity)."""
    intent = {"activity": "running"}  # running is an outdoor_exercise
    weather = {"uv_index": 9.0, "temperature": 28.0, "wind_speed": 10.0}
    matched, selected = match_sops(intent, weather)

    assert selected is not None
    assert any(p["id"] == "SOP-02" for p in matched)
    assert selected["id"] == "SOP-02"
    assert selected["severity"] == "MEDIUM"


def test_sop_05_travel_high_rain():
    """Test 3: Travel + high rain probability -> triggers SOP-05 (MEDIUM severity)."""
    intent = {"activity": "travel"}
    weather = {"precipitation_probability": 85, "precipitation": 2.0}
    matched, selected = match_sops(intent, weather)

    assert selected is not None
    assert selected["id"] == "SOP-05"
    assert selected["severity"] == "MEDIUM"
    assert "transit delays" in selected["advice"].lower()


def test_sop_08_child_high_uv():
    """Test 4: Child + high UV -> triggers SOP-08 (HIGH severity)."""
    intent = {"activity": "park", "person_context": "child"}
    weather = {"uv_index": 8.5, "precipitation_probability": 10}
    matched, selected = match_sops(intent, weather)

    assert selected is not None
    # SOP-08 is HIGH severity for children under UV >= 8
    assert any(p["id"] == "SOP-08" for p in matched)
    assert selected["id"] == "SOP-08"
    assert selected["severity"] == "HIGH"


def test_multiple_matching_sops_highest_severity_selected():
    """Test 5: Multiple matching SOPs are ranked and resolved to highest severity."""
    # Cycling with wind > 40 (SOP-01: HIGH) AND UV >= 8 (SOP-02: MEDIUM)
    intent = {"activity": "cycling"}
    weather = {"wind_speed": 44.0, "uv_index": 9.0, "temperature": 30.0}
    matched, selected = match_sops(intent, weather)

    matched_ids = [p["id"] for p in matched]
    assert "SOP-01" in matched_ids
    assert "SOP-02" in matched_ids
    assert len(matched) >= 2

    # Primary selected SOP MUST be the highest severity (SOP-01: HIGH)
    assert selected["id"] == "SOP-01"
    assert selected["severity"] == "HIGH"


def test_no_sop_matched_honestly_no_guidance():
    """Test 6: When no SOP applies, no guidance is selected and no generic safety advice is given."""
    intent = {"activity": "chess"}
    weather = {"temperature": 21.0, "wind_speed": 10.0, "uv_index": 2.0, "precipitation_probability": 0}
    matched, selected = match_sops(intent, weather)

    assert matched == []
    assert selected is None

    # End-to-end graph verification
    graph = create_weather_graph()
    mock_weather_data = {
        "temperature": 21.0,
        "wind_speed": 10.0,
        "precipitation": 0.0,
        "precipitation_probability": 0,
        "uv_index": 2.0,
        "relative_humidity": 50,
        "time": "2026-10-01T12:00",
    }
    with patch(
        "backend.app.nodes.fetch_weather.default_weather_service.get_current_weather",
        return_value=mock_weather_data,
    ):
        result = graph.invoke(
            {"user_query": "Can I play chess in Bangalore today?"},
            config={"configurable": {"thread_id": "test-no-sop"}},
        )

        assert result["selected_sop"] is None
        assert result["matched_sops"] == []
        assert "No formal Standard Operating Procedure (SOP) guideline applies" in result["response"]
        # Ensure it does NOT invent positive/generic safety clearance
        assert "you are safe" not in result["response"].lower()
        assert "completely safe" not in result["response"].lower()


def test_dynamic_new_sop_without_code_changes(tmp_path):
    """Test 7 & Step 18: Adding an 12th SOP via data file dynamically without changing Python code."""
    existing_policies = load_policies()

    # Define a brand new policy: SOP-13 Extreme Cold Warning
    new_sop = {
        "id": "SOP-13",
        "name": "Extreme Cold Warning",
        "category": "outdoor_exercise",
        "description": "Sub-zero conditions create severe hypothermia risk.",
        "severity": "HIGH",
        "conditions": [
            {
                "field": "temperature",
                "operator": "<=",
                "value": 0
            },
            {
                "field": "activity",
                "operator": "equals",
                "value": "outdoor"
            }
        ],
        "advice": "Avoid outdoor activities due to severe frostbite and hypothermia danger."
    }
    augmented_policies = existing_policies + [new_sop]
    custom_policy_file = tmp_path / "custom_sops.json"
    custom_policy_file.write_text(json.dumps(augmented_policies), encoding="utf-8")

    # Match with freezing weather
    intent = {"activity": "running"}
    weather = {"temperature": -5.0, "wind_speed": 10.0}
    matched, selected = match_sops(intent, weather, policies_path=custom_policy_file)

    assert selected is not None
    assert selected["id"] == "SOP-13"
    assert selected["name"] == "Extreme Cold Warning"
    assert selected["severity"] == "HIGH"
    assert "hypothermia danger" in selected["advice"]


def test_weather_api_failure_prevents_sop_evaluation():
    """Test 8: API failure still handles honestly without SOP evaluation or data fabrication."""
    graph = create_weather_graph()
    with patch(
        "backend.app.nodes.fetch_weather.default_weather_service.get_current_weather",
        side_effect=WeatherServiceError("API Gateway Timeout"),
    ):
        result = graph.invoke(
            {"user_query": "Can I cycle in Bangalore today?"},
            config={"configurable": {"thread_id": "test-api-fail-sop"}},
        )

        assert result["weather"] is None
        assert result.get("selected_sop") is None
        assert "weather service could not be reached" in result["response"].lower()


def test_exact_weather_grounding():
    """Test 9: Matcher and response use exact decimal weather values without rounding/altering."""
    exact_wind = 43.2
    exact_temp = 31.7
    mock_weather = {
        "temperature": exact_temp,
        "wind_speed": exact_wind,
        "precipitation": 0.0,
        "precipitation_probability": 10,
        "uv_index": 3.0,
        "relative_humidity": 60,
        "time": "2026-10-01T14:00",
    }

    graph = create_weather_graph()
    with patch(
        "backend.app.nodes.fetch_weather.default_weather_service.get_current_weather",
        return_value=mock_weather,
    ):
        result = graph.invoke(
            {"user_query": "Can I cycle in Bangalore today?"},
            config={"configurable": {"thread_id": "test-exact-grounding"}},
        )

        assert result["selected_sop"] is not None
        assert result["selected_sop"]["id"] == "SOP-01"
        # Exact numbers must be present in response text
        assert "43.2" in result["response"]
        assert "31.7" in result["response"]
        assert "SOP-01" in result["response"]
        assert "HIGH" in result["response"]
