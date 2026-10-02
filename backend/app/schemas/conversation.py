"""Pydantic schemas for conversations, messages, and advisories."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    title: Optional[str] = Field(default=None, description="Optional conversation title")


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    created_at: datetime


class AdvisoryRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_query: str
    location: Optional[str] = None
    resolved_location_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    weather_metrics: Optional[Dict[str, Any]] = None
    activity: Optional[str] = None
    person_context: Optional[str] = None
    selected_sop: Optional[Dict[str, Any]] = None
    matched_sops: Optional[List[Dict[str, Any]]] = None
    severity: Optional[str] = None
    generated_response: Optional[str] = None
    created_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = 0


class ConversationDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageOut] = []
    advisories: List[AdvisoryRecordOut] = []
