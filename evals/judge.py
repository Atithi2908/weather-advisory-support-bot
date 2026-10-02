"""LLM-Judge implementation for evaluating generated advisories against ground truth."""

from typing import Any, Dict
from langchain_core.messages import HumanMessage, SystemMessage

from backend.app.services.llm_service import get_chat_model
from evals.schema import EvalScenario, JudgeResult

JUDGE_SYSTEM_PROMPT = """You are an expert impartial evaluation judge for an outdoor weather advisory AI system.
Your job is to objectively score an assistant's generated response against known ground-truth criteria.

EVALUATION CRITERIA (Score 1 to 5 for each):
1. weather_factuality: Did the response state the actual weather values without modification or estimation?
2. sop_correctness: Did the response correctly cite the expected SOP ID (e.g. SOP-01), or correctly communicate that no SOP applies if expected was null?
3. severity_correctness: Did the response correctly reflect the expected risk severity level (LOW, MEDIUM, HIGH, or None)?
4. advice_preservation: Did the response communicate the official recommendation accurately?
5. hallucination_free: Did the response avoid inventing numbers, unauthorized SOP rules, or unbacked safety clearance?
6. relevance: Did the response address the specific user query and activity?
7. completeness: Is the advisory comprehensive and clearly formatted?

PASSING THRESHOLD:
Set 'passed' to True if all individual scores are >= 4. Otherwise set 'passed' to False.
Provide a clear, concise justification in 'reason'.
"""


def _deterministic_rule_based_judge(
    scenario: EvalScenario,
    actual_result: Dict[str, Any],
) -> JudgeResult:
    """Programmatic judge scoring used for offline testing and deterministic CI runs."""
    response_text = str(actual_result.get("response", "")).lower()
    expected = scenario.expected
    selected_sop = actual_result.get("selected_sop") or {}

    weather_score = 5
    # Verify required numbers
    if expected.must_contain_numbers:
        for num in expected.must_contain_numbers:
            if str(num).lower() not in response_text:
                weather_score = 2
                break

    sop_score = 5
    if expected.selected_sop_id:
        if expected.selected_sop_id.lower() not in response_text:
            sop_score = 1
        elif selected_sop.get("id") != expected.selected_sop_id:
            sop_score = 2
    else:
        # Expected no SOP
        if selected_sop or "no formal standard operating procedure" not in response_text:
            sop_score = 2

    severity_score = 5
    if expected.severity:
        if expected.severity.lower() not in response_text:
            severity_score = 2
    else:
        if "severity: high" in response_text or "severity: medium" in response_text:
            severity_score = 2

    advice_score = 5
    if expected.advice_keywords:
        matched_kw = sum(1 for kw in expected.advice_keywords if kw.lower() in response_text)
        if matched_kw == 0:
            advice_score = 2
        elif matched_kw < len(expected.advice_keywords):
            advice_score = 4

    hallucination_score = 5
    if expected.must_not_contain:
        for forbidden in expected.must_not_contain:
            if forbidden.lower() in response_text:
                hallucination_score = 1
                break

    relevance_score = 5 if expected.activity and (expected.activity.lower() in response_text or expected.activity.lower() in str(actual_result.get("activity", "")).lower()) else 4
    completeness_score = 5 if len(response_text) > 80 else 3

    passed = all(
        s >= 4
        for s in (
            weather_score,
            sop_score,
            severity_score,
            advice_score,
            hallucination_score,
            relevance_score,
            completeness_score,
        )
    )

    reason = (
        f"Automated evaluation: Weather={weather_score}/5, SOP={sop_score}/5, "
        f"Severity={severity_score}/5, Advice={advice_score}/5, "
        f"HallucinationFree={hallucination_score}/5, Relevance={relevance_score}/5, "
        f"Completeness={completeness_score}/5."
    )

    return JudgeResult(
        passed=passed,
        weather_factuality=weather_score,
        sop_correctness=sop_score,
        severity_correctness=severity_score,
        advice_preservation=advice_score,
        hallucination_free=hallucination_score,
        relevance=relevance_score,
        completeness=completeness_score,
        reason=reason,
    )


def evaluate_with_judge(
    scenario: EvalScenario,
    actual_result: Dict[str, Any],
) -> JudgeResult:
    """Evaluates an actual LangGraph result against an evaluation scenario."""
    chat_model = get_chat_model()

    if chat_model:
        prompt_content = (
            f"EVALUATION TARGET:\n"
            f"Scenario: {scenario.name} (ID: {scenario.id})\n"
            f"User Query: \"{scenario.query}\"\n"
            f"Ground-Truth Weather Data: {scenario.weather}\n\n"
            f"EXPECTED CRITERIA:\n"
            f"- Expected SOP ID: {scenario.expected.selected_sop_id}\n"
            f"- Expected Severity: {scenario.expected.severity}\n"
            f"- Expected Advice Keywords: {scenario.expected.advice_keywords}\n"
            f"- Must Contain Numbers: {scenario.expected.must_contain_numbers}\n"
            f"- Must NOT Contain: {scenario.expected.must_not_contain}\n\n"
            f"ACTUAL ASSISTANT RESPONSE:\n"
            f"\"{actual_result.get('response', '')}\"\n\n"
            f"ACTUAL GRAPH STATE:\n"
            f"Activity: {actual_result.get('activity')}, "
            f"Selected SOP: {actual_result.get('selected_sop')}, "
            f"Matched SOPs: {actual_result.get('matched_sops')}\n\n"
            "Please score this output and produce the structured JudgeResult."
        )

        try:
            structured_judge = chat_model.with_structured_output(JudgeResult)
            return structured_judge.invoke(
                [
                    SystemMessage(content=JUDGE_SYSTEM_PROMPT),
                    HumanMessage(content=prompt_content),
                ]
            )
        except Exception:
            return _deterministic_rule_based_judge(scenario, actual_result)

    return _deterministic_rule_based_judge(scenario, actual_result)
