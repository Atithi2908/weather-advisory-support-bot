"""Pydantic schemas for the automated LLM-Judge evaluation suite."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvalExpected(BaseModel):
    activity: Optional[str] = None
    selected_sop_id: Optional[str] = None
    severity: Optional[str] = None
    matched_sop_ids: Optional[List[str]] = None
    advice_keywords: Optional[List[str]] = None
    must_contain_numbers: Optional[List[str]] = None
    must_not_contain: Optional[List[str]] = None


class EvalScenario(BaseModel):
    id: str
    name: str
    query: str
    location: str
    weather: Dict[str, Any]
    expected: EvalExpected


class JudgeResult(BaseModel):
    """Structured evaluation score produced by the LLM-Judge for a generated advisory."""

    passed: bool = Field(..., description="Overall pass/fail determination based on criteria scores.")
    weather_factuality: int = Field(..., ge=1, le=5, description="Accurate reproduction of actual weather metrics (1-5)")
    sop_correctness: int = Field(..., ge=1, le=5, description="Correct identification of the applicable SOP or no-SOP state (1-5)")
    severity_correctness: int = Field(..., ge=1, le=5, description="Accurate communication of risk severity (LOW/MED/HIGH) (1-5)")
    advice_preservation: int = Field(..., ge=1, le=5, description="Fidelity to the official SOP safety recommendation (1-5)")
    hallucination_free: int = Field(..., ge=1, le=5, description="Absence of fabricated numbers or unsupported claims (1-5)")
    relevance: int = Field(..., ge=1, le=5, description="Directly addresses the user query and activity context (1-5)")
    completeness: int = Field(..., ge=1, le=5, description="Thorough coverage of weather facts, assessment, and advice (1-5)")
    reason: str = Field(..., description="Detailed justification for the scores and evaluation judgment.")
