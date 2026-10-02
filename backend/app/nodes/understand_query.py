"""Node: understand_query

Interprets the user's natural-language question, extracting:
- activity
- location
- time_context
- person_context

Supports conversational follow-up memory within the session.
Does NOT make safety decisions or fabricate weather data.
"""

import logging
import re
from typing import Any, Dict, Optional
from langchain_core.messages import HumanMessage, SystemMessage

from backend.app.graph.state import WeatherState
from backend.app.services.llm_service import (
    QueryUnderstandingResult,
    get_chat_model,
    sanitize_llm_error,
)

logger = logging.getLogger("weather_advisory.nodes.understand_query")

SYSTEM_PROMPT = """You are an intent extraction component for an outdoor weather advisory bot.
Your job is ONLY to extract the user's intended activity, location, time context, and person context.

CRITICAL RULES:
1. Do NOT make any safety decisions or evaluate risks (e.g. whether it is safe to cycle).
2. Do NOT guess or hallucinate a location if none is mentioned and none exists in the prior context.
3. If this is a follow-up query (e.g., "What about this evening?" or "Can I still do that?"), RETAIN the previous activity and location from the prior context unless the user explicitly specified a new one.
4. Extract the clean city/place name for location (e.g., "Bangalore", "Delhi", "London").
"""


def _normalize_activity(act: Optional[str]) -> Optional[str]:
    """Normalize extracted activity to canonical keyword for SOP evaluation."""
    if not act:
        return None
    a = act.lower().strip()
    if a in ("cycle", "bike", "biking", "bicycle", "cycling"):
        return "cycling"
    if a in ("run", "jog", "jogging", "runner", "running"):
        return "running"
    if a in ("walk", "stroll", "walking"):
        return "walking"
    if a in ("hike", "hiking"):
        return "hiking"
    if a in ("swim", "swimming"):
        return "swimming"
    if a in ("outdoor workout", "outdoor exercise", "exercise", "workout", "outdoor_exercise"):
        return "outdoor_exercise"
    if a in ("two-wheeler", "two wheeler", "scooter", "motorcycle", "motorbike", "two_wheeler"):
        return "two_wheeler"
    if a in ("commute", "commuting", "transit", "travel", "traveling"):
        return "travel"
    return a


def _fallback_intent_extraction(
    query: str,
    prior_activity: Optional[str] = None,
    prior_location: Optional[str] = None,
) -> QueryUnderstandingResult:
    """Rule-based extractor used when LLM credentials are not provided or for offline tests."""
    q_lower = query.lower()
    extracted_activity = None

    # Common outdoor activities & transport categories
    if re.search(r"\b(outdoor\s+(?:exercise|workout)|workout|exercise)\b", q_lower):
        extracted_activity = "outdoor_exercise"
    elif re.search(r"\b(two[- ]wheeler|scooter|motorcycle|motorbike|moped)\b", q_lower):
        extracted_activity = "two_wheeler"
    elif re.search(r"\b(commute|commuting|transit|travel|traveling)\b", q_lower):
        extracted_activity = "travel"
    else:
        activities = [
            "cycling", "cycle", "biking", "bike",
            "running", "run", "jogging", "jog",
            "picnic", "park", "walking", "walk",
            "hiking", "hike", "swimming", "swim",
            "football", "soccer", "cricket", "tennis",
            "golf", "boating", "sightseeing", "camping",
            "outdoor", "outside",
        ]
        for act in activities:
            if re.search(r"\b" + re.escape(act) + r"\b", q_lower):
                # Normalize variations like cycle -> cycling, bike -> cycling
                if act in ("cycle", "bike", "biking"):
                    extracted_activity = "cycling"
                elif act in ("run", "jog", "jogging"):
                    extracted_activity = "running"
                elif act in ("walk",):
                    extracted_activity = "walking"
                elif act in ("hike",):
                    extracted_activity = "hiking"
                elif act in ("swim",):
                    extracted_activity = "swimming"
                elif act in ("outside", "outdoor"):
                    extracted_activity = "outdoor"
                else:
                    extracted_activity = act
                break

    # If no activity in current query, retain prior activity from context
    activity = extracted_activity or prior_activity

    # Check known cities first to prevent accidental capture of trailing time words (e.g. 'Bangalore today')
    extracted_location = None
    known_cities = [
        "bangalore", "bengaluru", "delhi", "new delhi", "mumbai", "kolkata",
        "chennai", "hyderabad", "pune", "ahmedabad", "jaipur", "paris",
        "london", "tokyo", "new york", "seattle", "san francisco", "chicago",
        "berlin", "singapore", "sydney", "dubai", "toronto", "boston",
    ]
    for city in known_cities:
        if re.search(r"\b" + re.escape(city) + r"\b", q_lower):
            extracted_location = city.title()
            break

    # If no known city matched, try pattern matching: "in <City>", "near <City>", "at <City>", "around <City>"
    if not extracted_location:
        loc_match = re.search(
            r"\b(?:in|near|around|at)\s+([A-Za-z0-9_-]+(?:\s+[A-Za-z0-9_-]+)?)\b",
            query,
            re.IGNORECASE,
        )
        if loc_match:
            cand = loc_match.group(1).strip()
            # Clean off trailing temporal words if accidentally captured
            for time_word in ["today", "tomorrow", "tommorrow", "yesterday", "tonight", "this", "now", "afternoon", "evening", "morning"]:
                cand = re.sub(rf"\b{time_word}\b", "", cand, flags=re.IGNORECASE).strip()
            # Exclude common stop words and articles
            if cand and cand.lower() not in (
                "the", "a", "an", "park", "kid", "child", "children", "my", "our", "a run", "a walk", "a bike",
            ):
                extracted_location = cand

    # If no location in current query, retain prior location from context
    location = extracted_location or prior_location

    # Time context extraction with typo tolerance and past/future support
    time_context = None

    # Specific compound time expressions first
    if re.search(r"\b(?:yesterday\s+morning|yday\s+morning)\b", q_lower):
        time_context = "yesterday morning"
    elif re.search(r"\b(?:yesterday\s+afternoon|yday\s+afternoon)\b", q_lower):
        time_context = "yesterday afternoon"
    elif re.search(r"\b(?:yesterday\s+evening|yday\s+evening)\b", q_lower):
        time_context = "yesterday evening"
    elif re.search(r"\b(?:yesterday\s+night|yday\s+night)\b", q_lower):
        time_context = "yesterday night"
    elif re.search(r"\b(?:yesterday|yday|previous\s+day|last\s+day)\b", q_lower):
        time_context = "yesterday"
    elif re.search(r"\b(?:day\s+after\s+tomorrow|overmorrow|in\s+2\s+days)\b", q_lower):
        time_context = "day after tomorrow"
    elif re.search(r"\b(?:to[m]+o[r]+ow\s+morning|tmrw\s+morning|2morrow\s+morning)\b", q_lower):
        time_context = "tomorrow morning"
    elif re.search(r"\b(?:to[m]+o[r]+ow\s+afternoon|tmrw\s+afternoon|2morrow\s+afternoon)\b", q_lower):
        time_context = "tomorrow afternoon"
    elif re.search(r"\b(?:to[m]+o[r]+ow\s+evening|tmrw\s+evening|2morrow\s+evening)\b", q_lower):
        time_context = "tomorrow evening"
    elif re.search(r"\b(?:to[m]+o[r]+ow\s+night|tmrw\s+night|2morrow\s+night)\b", q_lower):
        time_context = "tomorrow night"
    elif re.search(r"\b(?:to[m]+o[r]+ow|tmrw|2morrow)\b", q_lower):
        time_context = "tomorrow"
    elif re.search(r"\b(?:this\s+evening)\b", q_lower):
        time_context = "this evening"
    elif re.search(r"\b(?:this\s+afternoon)\b", q_lower):
        time_context = "this afternoon"
    elif re.search(r"\b(?:this\s+morning)\b", q_lower):
        time_context = "this morning"
    elif re.search(r"\b(?:tonight|this\s+night)\b", q_lower):
        time_context = "tonight"
    elif re.search(r"\b(?:this\s+weekend|weekend)\b", q_lower):
        time_context = "this weekend"
    elif re.search(r"\b(?:today|right\s+now|now|currently)\b", q_lower):
        time_context = "today"

    # Person context
    person_context = None
    if re.search(r"\b(kid|kids|child|children|baby|toddler)\b", q_lower):
        person_context = "child"
    elif re.search(r"\b(elderly|senior|seniors|grandparents|grandmother|grandfather|grandma|grandpa)\b", q_lower):
        person_context = "elderly"
    elif re.search(r"\b(solo|alone)\b", q_lower):
        person_context = "solo"
    elif re.search(r"\b(family)\b", q_lower):
        person_context = "family"

    return QueryUnderstandingResult(
        activity=activity,
        location=location,
        time_context=time_context,
        person_context=person_context,
    )


def understand_query_node(state: WeatherState) -> Dict[str, Any]:
    """LangGraph node to interpret the user query and extract structured intent."""
    query = state.get("user_query", "").strip()
    history = state.get("conversation_history") or []
    prior_activity = state.get("activity")
    prior_location = state.get("location")

    chat_model = get_chat_model()

    if chat_model:
        try:
            structured_llm = chat_model.with_structured_output(QueryUnderstandingResult)

            # Build messages including conversation history context
            messages = [SystemMessage(content=SYSTEM_PROMPT)]

            # Provide context of previous state if available
            context_summary = []
            if prior_location:
                context_summary.append(f"Prior location: {prior_location}")
            if prior_activity:
                context_summary.append(f"Prior activity: {prior_activity}")
            if context_summary:
                messages.append(
                    SystemMessage(
                        content=f"Context from current session:\n" + "\n".join(context_summary)
                    )
                )

            # Add recent turns for conversational continuity
            for turn in history[-4:]:
                role = turn.get("role")
                content = turn.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(HumanMessage(content=f"[Assistant answered]: {content}"))

            messages.append(HumanMessage(content=f"Current user query: {query}"))

            result: QueryUnderstandingResult = structured_llm.invoke(messages)
            extracted_activity = result.activity or prior_activity
            extracted_location = result.location or prior_location
            time_context = result.time_context
            person_context = result.person_context
        except Exception as e:
            # Fall back to rule-based parser on any LLM parsing or API exception
            logger.warning(
                f"OpenRouter intent extraction note ({sanitize_llm_error(e)}). "
                "Falling back to rule-based extractor."
            )
            fallback = _fallback_intent_extraction(query, prior_activity, prior_location)
            extracted_activity = fallback.activity
            extracted_location = fallback.location
            time_context = fallback.time_context
            person_context = fallback.person_context
    else:
        fallback = _fallback_intent_extraction(query, prior_activity, prior_location)
        extracted_activity = fallback.activity
        extracted_location = fallback.location
        time_context = fallback.time_context
        person_context = fallback.person_context

    extracted_activity = _normalize_activity(extracted_activity)

    return {
        "activity": extracted_activity,
        "location": extracted_location,
        "time_context": time_context,
        "person_context": person_context,
        "error": None,  # Reset prior transient error on new query
    }
