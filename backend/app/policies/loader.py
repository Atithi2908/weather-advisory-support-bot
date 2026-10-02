"""SOP policy loader and schema validator.

Loads policies from external JSON file (default: policies/sops.json).
Performs structural and field-level validation to prevent malformed policies.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.config import POLICIES_PATH


class PolicyValidationError(Exception):
    """Raised when an SOP definition is structurally invalid or missing required attributes."""
    pass


VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH"}
VALID_OPERATORS = {
    ">", ">=", "<", "<=", "==", "!=",
    "equals", "not_equals", "contains", "in", "between",
}


def validate_condition(cond: Any, sop_id: str, index: int) -> None:
    """Validates a single condition dictionary."""
    if not isinstance(cond, dict):
        raise PolicyValidationError(
            f"Policy '{sop_id}' condition #{index} must be a dictionary, got {type(cond).__name__}."
        )

    for req_key in ("field", "operator", "value"):
        if req_key not in cond:
            raise PolicyValidationError(
                f"Policy '{sop_id}' condition #{index} is missing required field '{req_key}'."
            )

    op = str(cond["operator"]).strip()
    if op not in VALID_OPERATORS:
        raise PolicyValidationError(
            f"Policy '{sop_id}' condition #{index} has unsupported operator '{op}'. "
            f"Valid operators: {sorted(VALID_OPERATORS)}"
        )

    if op == "between":
        val = cond["value"]
        if not (isinstance(val, (list, tuple)) and len(val) == 2):
            raise PolicyValidationError(
                f"Policy '{sop_id}' condition #{index} operator 'between' requires a 2-element list [min, max]."
            )


def validate_policy(policy: Any, index: int) -> Dict[str, Any]:
    """Validates an individual SOP dictionary."""
    if not isinstance(policy, dict):
        raise PolicyValidationError(
            f"Policy entry #{index} must be a dictionary, got {type(policy).__name__}."
        )

    required_fields = ["id", "name", "category", "severity", "conditions", "advice"]
    for field in required_fields:
        if field not in policy or policy[field] is None:
            raise PolicyValidationError(
                f"Policy entry #{index} is missing required field '{field}'."
            )
        if isinstance(policy[field], str) and not policy[field].strip():
            raise PolicyValidationError(
                f"Policy entry #{index} has empty string for required field '{field}'."
            )

    sop_id = str(policy["id"]).strip()
    sev = str(policy["severity"]).strip().upper()
    if sev not in VALID_SEVERITIES:
        raise PolicyValidationError(
            f"Policy '{sop_id}' has invalid severity '{policy['severity']}'. "
            f"Must be one of {sorted(VALID_SEVERITIES)}."
        )

    conditions = policy["conditions"]
    if not isinstance(conditions, list) or len(conditions) == 0:
        raise PolicyValidationError(
            f"Policy '{sop_id}' conditions must be a non-empty list."
        )

    for i, cond in enumerate(conditions):
        validate_condition(cond, sop_id, i)

    return policy


def load_policies(filepath: Optional[Path | str] = None) -> List[Dict[str, Any]]:
    """Loads and validates all SOP definitions from a JSON file.

    Args:
        filepath: Optional custom Path to policies JSON file. Defaults to POLICIES_PATH.

    Returns:
        List of validated SOP dictionaries.

    Raises:
        PolicyValidationError: If the file is missing, invalid JSON, or fails schema validation.
    """
    target_path = Path(filepath) if filepath else POLICIES_PATH

    if not target_path.exists():
        raise PolicyValidationError(
            f"Policy file not found at: {target_path.resolve()}"
        )

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise PolicyValidationError(
            f"Malformed JSON in policy file '{target_path}': {e}"
        ) from e
    except Exception as e:
        raise PolicyValidationError(
            f"Could not read policy file '{target_path}': {e}"
        ) from e

    if not isinstance(data, list):
        raise PolicyValidationError(
            f"Root of policy file '{target_path}' must be a JSON list of policies, got {type(data).__name__}."
        )

    validated_policies: List[Dict[str, Any]] = []
    seen_ids = set()

    for idx, item in enumerate(data):
        validated = validate_policy(item, idx)
        sop_id = validated["id"]
        if sop_id in seen_ids:
            raise PolicyValidationError(
                f"Duplicate policy ID '{sop_id}' detected in '{target_path}'."
            )
        seen_ids.add(sop_id)
        validated_policies.append(validated)

    return validated_policies
