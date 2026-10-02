"""Node: generate_response

Generates a natural-language response incorporating the factual weather metrics and
the selected Standard Operating Procedure (SOP) safety policy.
Strictly preserves the exact numeric values from Open-Meteo and does not allow
the LLM to invent, override, or alter safety guidance.
"""

import logging
from typing import Any, Dict, List, Optional
from langchain_core.messages import HumanMessage, SystemMessage

from backend.app.graph.state import WeatherState
from backend.app.services.llm_service import get_chat_model, sanitize_llm_error

logger = logging.getLogger("weather_advisory.nodes.generate_response")

SYSTEM_PROMPT = """You are the Weather-Advisory Support Bot.
Your job is to communicate the weather conditions and the formal Standard Operating Procedure (SOP) safety advisory to the user.

STRICT POLICY COMPLIANCE & SAFETY RULES:
1. Ground your response STRICTLY on the provided factual weather data and policy context.
2. State the exact numeric values provided (temperature, wind speed, precipitation, etc.). NEVER alter, modify, or round them.
3. NEVER invent weather values or conditions.
4. Clearly identify the applicable SOP: Explicitly state the Selected SOP identifier (e.g. SOP-01), name, and severity level (LOW, MEDIUM, or HIGH).
5. Communicate the official SOP advice accurately and preserve its directive.
6. NEVER invent an SOP, NEVER change the selected SOP, and NEVER alter the severity level.
7. NEVER override deterministic policy decisions or provide unsupported generic safety clearances (e.g. do NOT say "You're safe" or "You're good to go").
8. If additional matching SOPs are provided, briefly note them for complete auditability.
9. Use ONLY the supplied weather data and policy information.
"""


def _format_deterministic_sop_response(
    query: str,
    activity: Optional[str],
    location: Optional[str],
    resolved_name: Optional[str],
    time_context: Optional[str],
    person_context: Optional[str],
    weather: Dict[str, Any],
    selected_sop: Dict[str, Any],
    matched_sops: List[Dict[str, Any]],
) -> str:
    """Deterministic factual response incorporating the selected SOP and weather metrics."""
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

    sop_id = selected_sop.get("id", "SOP")
    sop_name = selected_sop.get("name", "Safety Policy")
    severity = selected_sop.get("severity", "MEDIUM")
    advice = selected_sop.get("advice", "")

    lines.append("\nSafety Policy Assessment:")
    lines.append(f"• Applicable Guideline: {sop_id} — {sop_name}")
    lines.append(f"• Severity Level: {severity}")
    lines.append(f"• Official Recommendation: {advice}")

    # Note any secondary matching SOPs
    other_sops = [s for s in matched_sops if s.get("id") != sop_id]
    if other_sops:
        other_summary = ", ".join(f"{s.get('id')} ({s.get('severity')})" for s in other_sops)
        lines.append(f"• Additional Matched Guidelines: {other_summary}")

    return "\n".join(lines)


def generate_response_node(state: WeatherState) -> Dict[str, Any]:
    """LangGraph node to generate the assistant response grounded in weather and selected SOP."""
    query = state.get("user_query", "")
    activity = state.get("activity")
    location = state.get("location")
    resolved_name = state.get("resolved_location_name")
    time_context = state.get("time_context")
    person_context = state.get("person_context")
    weather = state.get("weather") or {}
    selected_sop = state.get("selected_sop") or {}
    matched_sops = state.get("matched_sops") or []
    history = list(state.get("conversation_history") or [])

    chat_model = get_chat_model()

    if chat_model and weather and selected_sop:
        sop_id = selected_sop.get("id", "SOP")
        sop_name = selected_sop.get("name", "Safety Policy")
        sop_sev = selected_sop.get("severity", "MEDIUM")
        sop_adv = selected_sop.get("advice", "")

        weather_summary = (
            f"Location: {resolved_name or location}\n"
            f"Activity: {activity or 'unspecified'}\n"
            f"Time Context: {time_context or 'unspecified'}\n"
            f"Person Context: {person_context or 'unspecified'}\n"
            f"Actual Weather Data from Open-Meteo:\n"
            f"- Temperature: {weather.get('temperature')}°C\n"
            f"- Wind Speed: {weather.get('wind_speed')} km/h\n"
            f"- Precipitation: {weather.get('precipitation')} mm\n"
            f"- Precipitation Probability: {weather.get('precipitation_probability')}%\n"
            f"- UV Index: {weather.get('uv_index')}\n"
            f"- Relative Humidity: {weather.get('relative_humidity')}%\n\n"
            f"Selected Safety Policy (SOP):\n"
            f"- ID: {sop_id}\n"
            f"- Name: {sop_name}\n"
            f"- Severity: {sop_sev}\n"
            f"- Advice: {sop_adv}\n"
        )
        if len(matched_sops) > 1:
            others = [f"{s.get('id')} ({s.get('name')})" for s in matched_sops if s.get('id') != sop_id]
            weather_summary += f"- Additional Matching Policies: {', '.join(others)}\n"

        user_content = (
            f"User Question: \"{query}\"\n\n"
            f"Live Weather Facts & Deterministic Policy Directives:\n{weather_summary}\n"
            "Compose a comprehensive response for the user explaining the exact weather conditions "
            f"and communicating the authoritative safety directive from {sop_id} ({sop_name}). "
            "State the exact weather numbers and quote or cite the official recommendation clearly. "
            "Do NOT state that conditions are safe or provide unauthorized clearance."
        )

        try:
            ai_message = chat_model.invoke(
                [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=user_content),
                ]
            )
            raw_text = ai_message.content if isinstance(ai_message.content, str) else str(ai_message.content)
            response_text = raw_text.strip()

            # Safety Guardrail: ensure the response explicitly mentions the selected SOP ID
            if sop_id.lower() not in response_text.lower():
                response_text = (
                    f"Safety Policy Assessment:\n"
                    f"• Applicable Guideline: {sop_id} — {sop_name}\n"
                    f"• Severity Level: {sop_sev}\n"
                    f"• Official Recommendation: {sop_adv}\n\n"
                    f"{response_text}"
                )

        except Exception as e:
            logger.warning(
                f"OpenRouter LLM request failed ({sanitize_llm_error(e)}). "
                "Falling back to deterministic grounded response."
            )
            response_text = _format_deterministic_sop_response(
                query, activity, location, resolved_name, time_context, person_context, weather, selected_sop, matched_sops
            )
    else:
        response_text = _format_deterministic_sop_response(
            query, activity, location, resolved_name, time_context, person_context, weather, selected_sop, matched_sops
        )

    # Append to session conversation history
    updated_history = list(history)
    updated_history.append({"role": "user", "content": query})
    updated_history.append({"role": "assistant", "content": response_text})

    return {
        "response": response_text,
        "conversation_history": updated_history,
    }
