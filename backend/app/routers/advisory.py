"""Advisory endpoints integrating LangGraph workflow with database persistence."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.auth.deps import get_optional_current_user
from backend.app.db.base import get_db
from backend.app.db.models import AdvisoryRecord, Conversation, Message, User, utc_now
from backend.app.graph.workflow import create_weather_graph
from backend.app.schemas.advisory import AdvisoryRequest, QueryResponse

router = APIRouter(tags=["Advisory"])

# Shared LangGraph workflow instance
graph = create_weather_graph()


@router.post("/advisory", response_model=QueryResponse)
@router.post("/api/advisory", response_model=QueryResponse, include_in_schema=False)
def handle_advisory_query(
    payload: AdvisoryRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> QueryResponse:
    """Execute weather advisory pipeline for a user query.

    If authenticated:
    - Automatically loads prior conversation history.
    - Creates a conversation if none specified.
    - Persists user and assistant messages to database.
    - Saves structured AdvisoryRecord (weather facts, matched SOPs, selected SOP, severity).

    If unauthenticated:
    - Operates with in-memory session persistence (backward-compatible).
    """
    clean_query = payload.query.strip()
    if not clean_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty.",
        )

    conversation_id = payload.conversation_id
    prior_history = []

    # 1. Handle authenticated persistent conversation
    if current_user:
        if conversation_id:
            conversation = (
                db.query(Conversation)
                .filter(Conversation.id == conversation_id)
                .first()
            )
            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found.",
                )
            if conversation.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have access to this conversation.",
                )
        else:
            # Create a new conversation thread with clean title derived from query
            auto_title = clean_query[:40].strip()
            if len(clean_query) > 40:
                auto_title += "..."
            conversation = Conversation(
                user_id=current_user.id,
                title=auto_title or "Weather Advisory",
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            conversation_id = conversation.id

        # Load prior conversation history from database
        for msg in conversation.messages:
            prior_history.append({"role": msg.role, "content": msg.content})

        thread_id = conversation.id
    else:
        # Unauthenticated / test execution: use supplied session_id or generate one
        thread_id = payload.session_id or f"api-session-{uuid.uuid4().hex[:8]}"

    # 2. Invoke LangGraph workflow
    config = {"configurable": {"thread_id": thread_id}}
    input_state = {
        "user_query": clean_query,
        "conversation_history": prior_history,
    }

    try:
        result = graph.invoke(input_state, config=config)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LangGraph advisory workflow execution failed: {e}",
        )

    response_text = result.get("response", "No response generated.")

    # 3. Persist messages and advisory record if user is authenticated
    if current_user and conversation_id:
        user_msg = Message(
            conversation_id=conversation_id,
            role="user",
            content=clean_query,
        )
        assistant_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=response_text,
        )
        db.add(user_msg)
        db.add(assistant_msg)

        selected_sop = result.get("selected_sop")
        severity = selected_sop.get("severity") if selected_sop else None

        advisory_record = AdvisoryRecord(
            conversation_id=conversation_id,
            user_query=clean_query,
            location=result.get("location"),
            resolved_location_name=result.get("resolved_location_name"),
            latitude=result.get("latitude"),
            longitude=result.get("longitude"),
            weather_metrics=result.get("weather"),
            activity=result.get("activity"),
            person_context=result.get("person_context"),
            selected_sop=selected_sop,
            matched_sops=result.get("matched_sops"),
            severity=severity,
            generated_response=response_text,
        )
        db.add(advisory_record)

        # Update conversation timestamp
        db.query(Conversation).filter(Conversation.id == conversation_id).update({"updated_at": utc_now()})
        db.commit()

    selected_sop_data = result.get("selected_sop")
    severity_val = selected_sop_data.get("severity") if selected_sop_data else None

    return QueryResponse(
        conversation_id=conversation_id,
        session_id=thread_id,
        response=response_text,
        message=response_text,
        activity=result.get("activity"),
        location=result.get("location"),
        resolved_location_name=result.get("resolved_location_name"),
        latitude=result.get("latitude"),
        longitude=result.get("longitude"),
        weather=result.get("weather"),
        selected_sop=selected_sop_data,
        matched_sops=result.get("matched_sops"),
        severity=severity_val,
        person_context=result.get("person_context"),
        error=result.get("error"),
    )
