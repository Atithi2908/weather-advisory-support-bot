"""LangGraph workflow definition for Weather Advisory Support Bot (Phase 2)."""

from typing import Any, Literal, Optional
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from backend.app.graph.state import WeatherState
from backend.app.nodes.fetch_weather import fetch_weather_node
from backend.app.nodes.generate_response import generate_response_node
from backend.app.nodes.handle_error import handle_error_node
from backend.app.nodes.match_sop import match_sop_node
from backend.app.nodes.no_guidance import no_guidance_node
from backend.app.nodes.resolve_location import resolve_location_node
from backend.app.nodes.understand_query import understand_query_node


def route_after_location(
    state: WeatherState,
) -> Literal["fetch_weather", "handle_error"]:
    """Conditional router evaluating location resolution success."""
    if state.get("error") or state.get("latitude") is None or state.get("longitude") is None:
        return "handle_error"
    return "fetch_weather"


def route_after_weather(
    state: WeatherState,
) -> Literal["match_sop", "handle_error"]:
    """Conditional router evaluating weather API retrieval success."""
    if state.get("error") or not state.get("weather"):
        return "handle_error"
    return "match_sop"


def route_after_sop(
    state: WeatherState,
) -> Literal["generate_response", "no_guidance"]:
    """Conditional router checking if an applicable SOP was matched."""
    if state.get("selected_sop"):
        return "generate_response"
    return "no_guidance"


def create_weather_graph(checkpointer: Optional[Any] = None):
    """Constructs and compiles the Phase 2 LangGraph state machine.

    Args:
        checkpointer: Optional LangGraph checkpointer (defaults to in-memory MemorySaver).

    Returns:
        Compiled LangGraph runnable workflow.
    """
    workflow = StateGraph(WeatherState)

    # Register workflow nodes
    workflow.add_node("understand_query", understand_query_node)
    workflow.add_node("resolve_location", resolve_location_node)
    workflow.add_node("fetch_weather", fetch_weather_node)
    workflow.add_node("match_sop", match_sop_node)
    workflow.add_node("generate_response", generate_response_node)
    workflow.add_node("no_guidance", no_guidance_node)
    workflow.add_node("handle_error", handle_error_node)

    # Wire graph edges
    workflow.add_edge(START, "understand_query")
    workflow.add_edge("understand_query", "resolve_location")

    # Conditional routing after location resolution
    workflow.add_conditional_edges(
        "resolve_location",
        route_after_location,
        {
            "fetch_weather": "fetch_weather",
            "handle_error": "handle_error",
        },
    )

    # Conditional routing after weather retrieval
    workflow.add_conditional_edges(
        "fetch_weather",
        route_after_weather,
        {
            "match_sop": "match_sop",
            "handle_error": "handle_error",
        },
    )

    # Conditional routing after SOP matching
    workflow.add_conditional_edges(
        "match_sop",
        route_after_sop,
        {
            "generate_response": "generate_response",
            "no_guidance": "no_guidance",
        },
    )

    # Terminal nodes connect to END
    workflow.add_edge("generate_response", END)
    workflow.add_edge("no_guidance", END)
    workflow.add_edge("handle_error", END)

    if checkpointer is None:
        checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)
