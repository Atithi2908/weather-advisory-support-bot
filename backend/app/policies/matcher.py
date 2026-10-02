"""Deterministic SOP matcher and conflict resolver.

Evaluates all loaded policies against the structured user intent and actual weather facts.
When multiple policies apply, resolves them deliberately by selecting the highest-severity
policy as the primary 'selected_sop' while retaining all 'matched_sops' in state for auditability.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.app.config import POLICIES_PATH
from backend.app.policies.evaluator import evaluate_policy
from backend.app.policies.loader import load_policies

SEVERITY_WEIGHTS = {
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
}


def build_evaluation_context(
    intent: Dict[str, Any],
    weather: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Combines user intent and factual weather numbers into a unified evaluation context."""
    context: Dict[str, Any] = {}

    # Copy intent attributes
    if intent:
        context["activity"] = intent.get("activity")
        context["location"] = intent.get("location")
        context["person_context"] = intent.get("person_context")
        context["time_context"] = intent.get("time_context")

    # Copy weather factual metrics
    if weather:
        for k in (
            "temperature",
            "wind_speed",
            "precipitation",
            "precipitation_probability",
            "uv_index",
            "relative_humidity",
            "wind_gusts",
        ):
            if k in weather:
                context[k] = weather[k]

    return context


def match_sops(
    intent: Dict[str, Any],
    weather: Optional[Dict[str, Any]],
    policies_path: Optional[Path | str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Matches context against all loaded policies.

    Args:
        intent: User intent dictionary containing activity, person_context, etc.
        weather: Ground-truth weather dictionary from Open-Meteo.
        policies_path: Optional custom path to policies file (defaults to POLICIES_PATH).

    Returns:
        Tuple of (matched_sops, selected_sop).
        If no policies match, returns ([], None).
    """
    if not weather:
        # Cannot evaluate safety policies without factual weather data
        return [], None

    policies = load_policies(policies_path)
    context = build_evaluation_context(intent, weather)

    matched: List[Dict[str, Any]] = []
    for policy in policies:
        if evaluate_policy(policy, context):
            matched.append(policy)

    if not matched:
        return [], None

    # Sort matching policies: override SOPs first, then severity descending (HIGH > MEDIUM > LOW),
    # then by ID for determinism. This ensures situational override SOPs always outrank
    # normal activity-specific advice.
    sorted_matches = sorted(
        matched,
        key=lambda p: (
            1 if p.get("override") else 0,  # Override SOPs first
            SEVERITY_WEIGHTS.get(str(p.get("severity", "")).upper(), 0),
            p.get("id", ""),
        ),
        reverse=True,
    )

    selected_sop = sorted_matches[0]
    return sorted_matches, selected_sop

