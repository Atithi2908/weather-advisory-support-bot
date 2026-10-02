"""Pydantic schemas for advisory queries and responses."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AdvisoryRequest(BaseModel):
    query: str = Field(..., description="User's outdoor weather or activity question.")
    conversation_id: Optional[str] = Field(
        default=None,
        description="Optional persistent conversation ID to continue a thread.",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Legacy/optional session ID for in-memory session continuity.",
    )


class QueryResponse(BaseModel):
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None
    response: str
    message: Optional[str] = None
    activity: Optional[str] = None
    location: Optional[str] = None
    resolved_location_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    weather: Optional[Dict[str, Any]] = None
    selected_sop: Optional[Dict[str, Any]] = None
    matched_sops: Optional[List[Dict[str, Any]]] = None
    severity: Optional[str] = None
    person_context: Optional[str] = None
    error: Optional[str] = None
