"""LangGraph State definition for the Weather Advisory Support Bot."""

from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class WeatherState(TypedDict, total=False):
    """Typed state representing the conversational context and weather data pipeline.
    
    Fields:
        user_query: The latest user question or message.
        activity: Extracted outdoor activity (e.g., 'cycling', 'picnic', 'running').
        location: Extracted target location name (e.g., 'Bangalore', 'Delhi').
        latitude: Resolved geographic latitude coordinate.
        longitude: Resolved geographic longitude coordinate.
        resolved_location_name: Canonical location name returned by geocoding service.
        time_context: Temporal context (e.g., 'today', 'this evening', 'tomorrow').
        person_context: Demographic or personal context (e.g., 'child', 'elderly', 'solo').
        weather: Structured factual weather data retrieved directly from Open-Meteo.
        response: Final textual response generated for the user.
        error: Explanatory error message if a step fails (e.g. location unresolved).
        conversation_history: List of prior turns [{'role': 'user'|'assistant', 'content': '...'}].
    """

    user_query: str
    activity: Optional[str]
    location: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    resolved_location_name: Optional[str]
    time_context: Optional[str]
    person_context: Optional[str]
    weather: Optional[Dict[str, Any]]
    matched_sops: Optional[List[Dict[str, Any]]]
    selected_sop: Optional[Dict[str, Any]]
    policy_error: Optional[str]
    response: Optional[str]
    error: Optional[str]
    conversation_history: List[Dict[str, str]]
