"""Node: no_guidance

Invoked when no SOP matches the user activity and current weather facts.
Strictly avoids inventing generic safety advice or declaring an activity 'safe'.
States honestly that no formal safety policy covers the query under current conditions.
"""

import logging
from typing import Any, Dict
from langchain_core.messages import HumanMessage, SystemMessage

from backend.app.graph.state import WeatherState
from backend.app.services.llm_service import get_chat_model, sanitize_llm_error

logger = logging.getLogger("weather_advisory.nodes.no_guidance")

SYSTEM_PROMPT = """You are the Weather-Advisory Support Bot.
Current Status: NO STANDARD OPERATING PROCEDURE (SOP) POLICY MATCHES THIS REQUEST.

CRITICAL POLICY COMPLIANCE & SAFETY RULES:
1. State clearly that NO formal safety policy or SOP guideline covers this activity under the observed conditions.
2. Report the factual weather conditions accurately using ONLY the supplied metrics. NEVER alter, modify, or round numbers.
3. NEVER provide generic safety advice, clearance, or assurances (e.g. do NOT say "You're safe", "You are good to go", "It looks completely safe", or "Conditions are safe").
4. No SOP = No safety recommendation. Remain strictly informative, neutral, and factual.
5. Do NOT invent safety guidelines or conditions.
"""


def _format_deterministic_no_guidance(
    activity: str | None,
    location: str | None,
    resolved_name: str | None,
    time_context: str | None,
    weather: Dict[str, Any],
) -> str:
    """Deterministic response when no SOP applies and LLM is unavailable."""
    loc_display = resolved_name or location or "the requested location"
    act_display = f" for '{activity}'" if activity else ""
    time_display = f" ({time_context})" if time_context else ""

    temp = weather.get("temperature")
    wind = weather.get("wind_speed")
    precip = weather.get("precipitation")
    precip_prob = weather.get("precipitation_probability")
    uv = weather.get("uv_index")
    humidity = weather.get("relative_humidity")
    obs_time = weather.get("time")

    lines = [
        f"Weather report for {loc_display}{act_display}{time_display}:",
        f"- Temperature: {temp}°C",
        f"- Wind Speed: {wind} km/h",
        f"- Precipitation: {precip} mm",
        f"- Precipitation Probability: {precip_prob}%",
        f"- UV Index: {uv}",
        f"- Relative Humidity: {humidity}%",
    ]
    forecast_window = weather.get("forecast_window")
    if forecast_window:
        lines.append(f"- Time window: {forecast_window}")
    elif obs_time:
        lines.append(f"- Time of observation: {obs_time}")

    lines.append(
        "\nSafety Advisory:\n"
        "No formal Standard Operating Procedure (SOP) guideline applies to this activity "
        "under the current conditions. In accordance with policy safety protocols, no safety "
        "clearance or generic safety recommendation is provided."
    )
    return "\n".join(lines)


def no_guidance_node(state: WeatherState) -> Dict[str, Any]:
    """LangGraph node formatting honest response when no SOP policy matches."""
    query = state.get("user_query", "")
    activity = state.get("activity")
    location = state.get("location")
    resolved_name = state.get("resolved_location_name")
    time_context = state.get("time_context")
    weather = state.get("weather") or {}
    history = list(state.get("conversation_history") or [])

    chat_model = get_chat_model()

    if chat_model and weather:
        context_text = (
            f"User Question: \"{query}\"\n"
            f"Location: {resolved_name or location}\n"
            f"Activity: {activity or 'unspecified'}\n"
            f"Time Context: {time_context or 'unspecified'}\n"
            f"Weather Data: Temp={weather.get('temperature')}°C, Wind={weather.get('wind_speed')} km/h, "
            f"Precipitation={weather.get('precipitation')} mm, RainProb={weather.get('precipitation_probability')}%, "
            f"UV={weather.get('uv_index')}.\n"
            "Status: NO MATCHING SOP FOUND. State that no formal SOP applies and provide NO safety clearance."
        )
        try:
            ai_msg = chat_model.invoke(
                [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=context_text),
                ]
            )
            raw_text = ai_msg.content if isinstance(ai_msg.content, str) else str(ai_msg.content)
            raw_lower = raw_text.lower()

            # Safety Guardrail: Reject any fabricated safety clearance
            forbidden = [
                "user safety: safe",
                "you are safe",
                "you're safe",
                "completely safe",
                "conditions are safe",
                "good to go",
                "safe to proceed",
            ]
            has_forbidden = any(f in raw_lower for f in forbidden)
            has_no_sop_stated = ("no formal" in raw_lower or "no standard operating procedure" in raw_lower or "no sop" in raw_lower or "no guideline" in raw_lower)

            if has_forbidden or not has_no_sop_stated:
                logger.info(
                    "LLM response attempted to grant generic safety clearance or omitted no-SOP status. "
                    "Enforcing authoritative deterministic no-guidance response."
                )
                response_text = _format_deterministic_no_guidance(
                    activity, location, resolved_name, time_context, weather
                )
            else:
                response_text = raw_text.strip()
        except Exception as e:
            logger.warning(
                f"OpenRouter LLM request failed ({sanitize_llm_error(e)}). "
                "Falling back to deterministic factual response."
            )
            response_text = _format_deterministic_no_guidance(
                activity, location, resolved_name, time_context, weather
            )
    else:
        response_text = _format_deterministic_no_guidance(
            activity, location, resolved_name, time_context, weather
        )

    updated_history = list(history)
    updated_history.append({"role": "user", "content": query})
    updated_history.append({"role": "assistant", "content": response_text})

    return {
        "response": response_text,
        "conversation_history": updated_history,
    }
