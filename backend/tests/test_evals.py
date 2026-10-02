"""Automated tests for the LLM-Judge Evaluation Suite (Phase 3)."""

import pytest
from evals.schema import EvalScenario, EvalExpected, JudgeResult
from evals.judge import evaluate_with_judge, _deterministic_rule_based_judge
from evals.runner import load_dataset, run_scenario, run_evaluation_suite


def test_evaluation_dataset_validity():
    """Verify that dataset.json exists and all scenarios conform to the EvalScenario schema."""
    scenarios = load_dataset("evals/dataset.json")
    assert len(scenarios) >= 14
    for scenario in scenarios:
        assert scenario.id
        assert scenario.name
        assert scenario.query
        assert scenario.location
        assert scenario.weather is not None
        assert scenario.expected is not None


def test_eval_single_scenario_execution():
    """Verify that a representative scenario (Strong Wind Cycling) executes and passes."""
    scenarios = load_dataset("evals/dataset.json")
    scenario_01 = next(s for s in scenarios if s.id == "scenario_01_strong_wind_cycling")

    result = run_scenario(scenario_01)
    judge_res = evaluate_with_judge(scenario_01, result)

    assert judge_res.passed is True
    assert judge_res.weather_factuality >= 4
    assert judge_res.sop_correctness >= 4
    assert judge_res.severity_correctness >= 4
    assert judge_res.hallucination_free >= 4


def test_eval_guardrail_no_sop_scenario():
    """Verify that mild weather query triggers no-SOP guardrail and passes evaluation."""
    scenarios = load_dataset("evals/dataset.json")
    no_sop_scenario = next(s for s in scenarios if s.id == "scenario_13_no_sop_mild_weather")

    result = run_scenario(no_sop_scenario)
    judge_res = evaluate_with_judge(no_sop_scenario, result)

    assert judge_res.passed is True
    assert result.get("selected_sop") is None
    assert result.get("matched_sops") == []
    assert "no formal standard operating procedure" in result["response"].lower()
    # Ensure no fabricated safety clearance
    assert "you are safe" not in result["response"].lower()
    assert "conditions are safe" not in result["response"].lower()


def test_judge_hallucination_penalty():
    """Verify that the evaluator fails and penalizes hallucinations when forbidden phrases appear."""
    mock_scenario = EvalScenario(
        id="test_mock",
        name="Mock Scenario",
        query="Can I run in the rain?",
        location="Delhi",
        weather={"temperature": 25.0, "precipitation": 12.0},
        expected=EvalExpected(
            selected_sop_id="SOP-03",
            severity="HIGH",
            must_contain_numbers=["12.0"],
            must_not_contain=["you are completely safe", "good to go"],
        ),
    )

    # Hallucinated response that provides unwarranted safety clearance
    hallucinated_result = {
        "response": "Temperature is 25.0C and precipitation is 12.0. SOP-03 applies with HIGH severity. But you are completely safe and good to go!",
        "selected_sop": {"id": "SOP-03"},
        "matched_sops": [{"id": "SOP-03"}],
    }

    judge_res = _deterministic_rule_based_judge(mock_scenario, hallucinated_result)
    assert judge_res.passed is False
    assert judge_res.hallucination_free == 1


def test_full_evaluation_suite_run(tmp_path):
    """Verify that the full runner runs cleanly and outputs a valid JSON report."""
    report_file = tmp_path / "test_report.json"
    report = run_evaluation_suite(
        dataset_path="evals/dataset.json",
        output_path=str(report_file),
    )

    assert report["total_scenarios"] >= 14
    assert report["passed_scenarios"] == report["total_scenarios"]
    assert report["pass_rate_percent"] == 100.0
    assert report_file.exists()
