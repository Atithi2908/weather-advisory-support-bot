"""Node: handle_error

Generates honest, informative error feedback when location resolution or weather retrieval fails.
Ensures fabricated data is never returned to the user.
"""

from typing import Any, Dict
from backend.app.graph.state import WeatherState


def handle_error_node(state: WeatherState) -> Dict[str, Any]:
    """LangGraph node to format failure responses and maintain conversation context."""
    error = state.get("error") or "An unexpected issue occurred while processing your request."
    query = state.get("user_query", "")
    location = state.get("location")
    history = list(state.get("conversation_history") or [])

    if location and "could not find coordinates" in error.lower():
        response_text = (
            f"I could not find or resolve the location '{location}'. "
            "Please check the spelling or provide a nearby city name."
        )
    elif "no location was specified" in error.lower():
        response_text = (
            "I couldn't identify a location in your request. "
            "Please specify a city or locality (e.g., 'Can I cycle in Bangalore today?')."
        )
    elif "weather service" in error.lower() or "open-meteo" in error.lower():
        response_text = (
            f"Weather information for '{location or 'your location'}' is currently unavailable "
            f"because the weather service could not be reached. Error: {error}"
        )
    else:
        response_text = f"Unable to complete your weather advisory request: {error}"

    updated_history = list(history)
    updated_history.append({"role": "user", "content": query})
    updated_history.append({"role": "assistant", "content": response_text})

    return {
        "response": response_text,
        "conversation_history": updated_history,
    }
