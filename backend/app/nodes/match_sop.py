"""Node: match_sop

Evaluates all loaded SOP policies against the user intent and actual weather metrics.
Performs deterministic matching and severity ranking.
Stores matched_sops and selected_sop in LangGraph state.
"""

from typing import Any, Dict

from backend.app.graph.state import WeatherState
from backend.app.policies.loader import PolicyValidationError
from backend.app.policies.matcher import match_sops


def match_sop_node(state: WeatherState) -> Dict[str, Any]:
    """LangGraph node to evaluate SOPs against current intent and weather facts."""
    intent = {
        "activity": state.get("activity"),
        "person_context": state.get("person_context"),
        "time_context": state.get("time_context"),
        "location": state.get("location"),
    }
    weather = state.get("weather")

    try:
        matched_sops, selected_sop = match_sops(intent=intent, weather=weather)
        policy_error = None
    except PolicyValidationError as e:
        matched_sops, selected_sop = [], None
        policy_error = f"Policy validation error: {e}"
    except Exception as e:
        matched_sops, selected_sop = [], None
        policy_error = f"Unexpected error during policy evaluation: {e}"

    return {
        "matched_sops": matched_sops,
        "selected_sop": selected_sop,
        "policy_error": policy_error,
    }
