"""CLI Runner for the Automated LLM-Judge Evaluation Suite."""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.graph.workflow import create_weather_graph
from evals.judge import evaluate_with_judge
from evals.schema import EvalScenario, JudgeResult


def load_dataset(dataset_path: str) -> List[EvalScenario]:
    """Loads and validates evaluation scenarios from a JSON dataset."""
    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"Evaluation dataset not found at: {dataset_path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return [EvalScenario.model_validate(item) for item in data]


def run_scenario(scenario: EvalScenario) -> Dict[str, Any]:
    """Executes a single evaluation scenario deterministically through the LangGraph workflow."""
    graph = create_weather_graph()

    mock_weather = {
        **scenario.weather,
        "wind_gusts": scenario.weather.get("wind_gusts", scenario.weather.get("wind_speed", 0.0)),
        "weather_code": 0,
        "time": "2026-10-02T12:00",
        "units": {
            "temperature": "°C",
            "wind_speed": "km/h",
            "precipitation": "mm",
            "precipitation_probability": "%",
            "relative_humidity": "%",
            "uv_index": "",
        },
    }

    mock_geocode = {
        "name": scenario.location,
        "latitude": 12.9716,
        "longitude": 77.5946,
        "country": "India",
        "admin1": "State",
        "timezone": "Asia/Kolkata",
        "resolved_name": f"{scenario.location}, India",
    }

    with patch(
        "backend.app.nodes.resolve_location.default_weather_service.geocode_location",
        return_value=mock_geocode,
    ), patch(
        "backend.app.nodes.fetch_weather.default_weather_service.get_current_weather",
        return_value=mock_weather,
    ), patch(
        "backend.app.nodes.fetch_weather.default_weather_service.get_forecast_weather",
        return_value=mock_weather,
    ):
        config = {"configurable": {"thread_id": f"eval-{scenario.id}"}}
        result = graph.invoke(
            {"user_query": scenario.query},
            config=config,
        )

    return result


def run_evaluation_suite(
    dataset_path: str = "evals/dataset.json",
    output_path: str = "evals/latest_report.json",
) -> Dict[str, Any]:
    """Runs all evaluation scenarios and produces a detailed summary report."""
    scenarios = load_dataset(dataset_path)
    results = []
    passed_count = 0

    print("=" * 70)
    print(f"RUNNING AUTOMATED LLM-JUDGE EVALUATION SUITE ({len(scenarios)} scenarios)")
    print("=" * 70)

    for i, scenario in enumerate(scenarios, start=1):
        print(f"[{i}/{len(scenarios)}] Running: {scenario.name} ({scenario.id})...", end=" ")
        actual_result = run_scenario(scenario)
        judge_res: JudgeResult = evaluate_with_judge(scenario, actual_result)

        if judge_res.passed:
            passed_count += 1
            print("PASSED")
        else:
            print("FAILED")
            print(f"    Reason: {judge_res.reason}")

        results.append(
            {
                "scenario_id": scenario.id,
                "scenario_name": scenario.name,
                "query": scenario.query,
                "expected": scenario.expected.model_dump(),
                "actual_response": actual_result.get("response"),
                "actual_selected_sop": actual_result.get("selected_sop"),
                "actual_matched_sops": actual_result.get("matched_sops"),
                "judge_score": judge_res.model_dump(),
            }
        )

    total = len(scenarios)
    pass_rate = (passed_count / total * 100) if total > 0 else 0.0

    # Calculate average dimension scores
    avg_scores = {
        "weather_factuality": sum(r["judge_score"]["weather_factuality"] for r in results) / total,
        "sop_correctness": sum(r["judge_score"]["sop_correctness"] for r in results) / total,
        "severity_correctness": sum(r["judge_score"]["severity_correctness"] for r in results) / total,
        "advice_preservation": sum(r["judge_score"]["advice_preservation"] for r in results) / total,
        "hallucination_free": sum(r["judge_score"]["hallucination_free"] for r in results) / total,
        "relevance": sum(r["judge_score"]["relevance"] for r in results) / total,
        "completeness": sum(r["judge_score"]["completeness"] for r in results) / total,
    }

    report = {
        "total_scenarios": total,
        "passed_scenarios": passed_count,
        "pass_rate_percent": round(pass_rate, 2),
        "average_dimension_scores": {k: round(v, 2) for k, v in avg_scores.items()},
        "results": results,
    }

    print("-" * 70)
    print("EVALUATION SUMMARY:")
    print(f"Total Scenarios: {total}")
    print(f"Passed: {passed_count}/{total} ({pass_rate:.1f}%)")
    print("\nAverage Dimension Scores (1-5 Scale):")
    for dim, score in avg_scores.items():
        print(f"  - {dim:<25}: {score:.2f} / 5.0")
    print("=" * 70)

    # Save report
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Detailed evaluation report saved to: {out_file.resolve()}\n")

    return report


run_evaluations = run_evaluation_suite


def main():
    parser = argparse.ArgumentParser(description="LLM-Judge Evaluation Suite Runner")
    parser.add_argument("--dataset", default="evals/dataset.json", help="Path to evaluation dataset")
    parser.add_argument("--output", default="evals/latest_report.json", help="Path to output report")
    args = parser.parse_args()

    report = run_evaluations(dataset_path=args.dataset, output_path=args.output)
    if report["passed_scenarios"] < report["total_scenarios"]:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
