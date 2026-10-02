"""Deterministic condition and policy evaluator.

Evaluates data-driven SOP conditions against:
- Factual weather metrics (temperature, wind_speed, precipitation, etc.)
- User intent (activity, person_context, time_context)

All evaluations are deterministic in Python. The LLM does NOT make policy decisions.
"""

from typing import Any, Dict, List, Optional, Set

# Direct synonym sets for specific activities
SYNONYMS: Dict[str, Set[str]] = {
    "cycling": {"cycling", "cycle", "cyclist", "bike", "biking", "bicycle"},
    "running": {"running", "run", "runner", "jogging", "jog"},
    "walking": {"walking", "walk", "walker", "stroll"},
    "hiking": {"hiking", "hike"},
    "swimming": {"swimming", "swim"},
    "two_wheeler": {
        "two_wheeler", "two-wheeler", "two wheeler", "scooter",
        "moped", "motorcycle", "motorbike",
    },
    "park": {"park", "playground", "play area", "garden"},
    "picnic": {"picnic", "outing", "cookout", "barbecue", "bbq"},
    "travel": {"travel", "traveling", "commute", "commuting", "transit", "driving", "drive"},
}

# Broad category groups that encompass multiple specific activities
CATEGORY_GROUPS: Dict[str, Set[str]] = {
    "outdoor_exercise": {
        "cycling", "cycle", "bike", "biking", "bicycle",
        "running", "run", "jogging", "jog",
        "walking", "walk", "hiking", "hike",
        "swimming", "swim", "football", "soccer",
        "tennis", "cricket", "exercise", "workout",
        "outdoor_exercise", "training",
    },
    "travel": {
        "travel", "traveling", "commute", "commuting", "transit",
        "drive", "driving", "two_wheeler", "motorcycle", "scooter",
        "cycling", "road trip",
    },
    "outdoor": {
        "cycling", "cycle", "bike", "biking", "running", "run",
        "jogging", "walking", "walk", "hiking", "swimming", "park",
        "picnic", "football", "cricket", "tennis", "travel",
        "two_wheeler", "outdoor", "sightseeing", "camping", "leisure",
    },
}

PERSON_TAXONOMY: Dict[str, Set[str]] = {
    "child": {"child", "children", "kid", "kids", "baby", "toddler", "infant"},
    "elderly": {"elderly", "senior", "seniors", "older adult", "grandparents", "grandpa", "grandma"},
    "solo": {"solo", "alone"},
    "family": {"family"},
}


def _matches_activity(actual: Optional[str], target: str) -> bool:
    """Checks whether an actual activity string matches a target category or activity."""
    if not actual:
        return False
    act = actual.lower().strip()
    tgt = target.lower().strip()

    if act == tgt:
        return True

    # 1. If target is a broad category (e.g. 'outdoor_exercise', 'outdoor', 'travel')
    if tgt in CATEGORY_GROUPS and act in CATEGORY_GROUPS[tgt]:
        return True

    # 2. If target is a specific activity with synonyms (e.g. target='cycling', actual='bike')
    if tgt in SYNONYMS and act in SYNONYMS[tgt]:
        return True

    # 3. If actual maps to a synonym set containing target
    if act in SYNONYMS and tgt in SYNONYMS[act]:
        return True

    return False


def _matches_person(actual: Optional[str], target: str) -> bool:
    """Checks whether an actual person context matches target person group."""
    if not actual:
        return False
    person = actual.lower().strip()
    tgt = target.lower().strip()

    if person == tgt:
        return True

    if tgt in PERSON_TAXONOMY and person in PERSON_TAXONOMY[tgt]:
        return True

    return False


def evaluate_condition(condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """Evaluates a single condition dictionary against the combined context.

    Args:
        condition: Dictionary with 'field', 'operator', and 'value'.
        context: Flat or combined dictionary containing weather metrics and intent.

    Returns:
        True if the condition is satisfied, False otherwise.
    """
    field = condition["field"]
    op = condition["operator"].strip().lower()
    target_val = condition["value"]

    actual_val = context.get(field)

    # Activity matching
    if field == "activity":
        if op in ("equals", "=="):
            if isinstance(target_val, list):
                return any(_matches_activity(str(actual_val), str(t)) for t in target_val)
            return _matches_activity(str(actual_val), str(target_val))
        elif op in ("not_equals", "!="):
            return not _matches_activity(str(actual_val), str(target_val))
        elif op == "in" and isinstance(target_val, list):
            return any(_matches_activity(str(actual_val), str(t)) for t in target_val)
        elif op == "contains":
            return bool(actual_val and str(target_val).lower() in str(actual_val).lower())

    # Person context matching
    if field == "person_context":
        if op in ("equals", "=="):
            return _matches_person(str(actual_val), str(target_val))
        elif op in ("not_equals", "!="):
            return not _matches_person(str(actual_val), str(target_val))
        elif op == "in" and isinstance(target_val, list):
            return any(_matches_person(str(actual_val), str(t)) for t in target_val)

    # If actual value is None for numeric weather fields, condition fails
    if actual_val is None:
        return False

    # Numeric comparisons
    try:
        num_actual = float(actual_val)
    except (ValueError, TypeError):
        num_actual = None

    if num_actual is not None:
        if op == ">":
            return num_actual > float(target_val)
        elif op == ">=":
            return num_actual >= float(target_val)
        elif op == "<":
            return num_actual < float(target_val)
        elif op == "<=":
            return num_actual <= float(target_val)
        elif op in ("==", "equals"):
            return abs(num_actual - float(target_val)) < 1e-6
        elif op in ("!=", "not_equals"):
            return abs(num_actual - float(target_val)) >= 1e-6
        elif op == "between":
            if isinstance(target_val, (list, tuple)) and len(target_val) == 2:
                low, high = float(target_val[0]), float(target_val[1])
                return low <= num_actual <= high
        elif op == "in" and isinstance(target_val, (list, tuple)):
            return any(abs(num_actual - float(t)) < 1e-6 for t in target_val)

    # Fallback string comparison for other fields
    str_actual = str(actual_val).strip().lower()
    str_target = str(target_val).strip().lower()

    if op in ("equals", "=="):
        return str_actual == str_target
    elif op in ("not_equals", "!="):
        return str_actual != str_target
    elif op == "contains":
        return str_target in str_actual
    elif op == "in" and isinstance(target_val, (list, tuple)):
        return str_actual in [str(t).strip().lower() for t in target_val]

    return False


def evaluate_policy(policy: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """Evaluates whether an SOP policy applies to the given context.

    All conditions in the policy must evaluate to True (logical AND).

    Args:
        policy: The validated SOP dictionary.
        context: Context containing weather facts and user intent.

    Returns:
        True if all conditions match, False otherwise.
    """
    conditions = policy.get("conditions", [])
    if not conditions:
        return False

    for cond in conditions:
        if not evaluate_condition(cond, context):
            return False

    return True
