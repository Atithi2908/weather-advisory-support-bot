"""Tests for user authentication, authorization, conversation persistence, and data isolation."""

import pytest
from fastapi.testclient import TestClient

from backend.app.api import app
from backend.app.db.base import Base, SessionLocal, engine
from backend.app.db.models import AdvisoryRecord, Conversation, Message, User

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_clean_db():
    """Ensure clean database tables for each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def register_helper(email="user@example.com", password="securepassword123"):
    """Helper to register a user and return the API response."""
    return client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )


def login_helper(email="user@example.com", password="securepassword123"):
    """Helper to login a user and return the API response."""
    return client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )


# ============================================================================
# Authentication Tests
# ============================================================================


def test_register_success():
    """Verify new user can register and receives a valid JWT token."""
    res = register_helper("alice@example.com", "pass123456")
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "alice@example.com"
    assert "id" in data["user"]


def test_register_duplicate_email():
    """Verify duplicate email registration returns 400 Bad Request."""
    register_helper("bob@example.com", "pass123456")
    res2 = register_helper("bob@example.com", "differentpass")
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"].lower()


def test_register_short_password():
    """Verify registration fails if password is too short (< 6 chars)."""
    res = register_helper("short@example.com", "123")
    assert res.status_code == 422


def test_login_success():
    """Verify registered user can login and receives valid token."""
    register_helper("carol@example.com", "mysecretpassword")
    res = login_helper("carol@example.com", "mysecretpassword")
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == "carol@example.com"


def test_login_wrong_password():
    """Verify wrong password returns 401 Unauthorized."""
    register_helper("dave@example.com", "correctpassword")
    res = login_helper("dave@example.com", "wrongpassword")
    assert res.status_code == 401
    assert "invalid email or password" in res.json()["detail"].lower()


def test_login_nonexistent_user():
    """Verify nonexistent email returns 401 Unauthorized."""
    res = login_helper("ghost@example.com", "anypassword")
    assert res.status_code == 401


def test_get_current_user_profile():
    """Verify /auth/me returns profile of authenticated user."""
    reg = register_helper("eve@example.com", "password123").json()
    token = reg["access_token"]

    res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["email"] == "eve@example.com"


def test_protected_route_missing_or_invalid_token():
    """Verify 401 Unauthorized on missing, malformed, or fake tokens."""
    # Missing token
    res1 = client.get("/auth/me")
    assert res1.status_code == 401

    # Fake token
    res2 = client.get("/auth/me", headers={"Authorization": "Bearer fake.invalid.token"})
    assert res2.status_code == 401


# ============================================================================
# Authorization & Conversation Isolation Tests
# ============================================================================


def test_create_and_list_conversations():
    """Verify authenticated user can create and list conversations."""
    reg = register_helper("frank@example.com", "password123").json()
    token = reg["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create two conversations
    c1 = client.post("/conversations", json={"title": "Trip to Bangalore"}, headers=headers).json()
    c2 = client.post("/conversations", json={"title": "Delhi Marathon"}, headers=headers).json()

    assert c1["title"] == "Trip to Bangalore"
    assert c2["title"] == "Delhi Marathon"

    # List conversations
    res = client.get("/conversations", headers=headers)
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 2
    titles = [x["title"] for x in items]
    assert "Trip to Bangalore" in titles
    assert "Delhi Marathon" in titles


def test_cross_user_conversation_isolation():
    """Verify User A CANNOT read, access, or delete User B's conversation."""
    user_a = register_helper("user_a@example.com", "password123").json()
    user_b = register_helper("user_b@example.com", "password123").json()

    headers_a = {"Authorization": f"Bearer {user_a['access_token']}"}
    headers_b = {"Authorization": f"Bearer {user_b['access_token']}"}

    # User A creates a conversation
    conv_a = client.post("/conversations", json={"title": "Private User A Chat"}, headers=headers_a).json()
    conv_a_id = conv_a["id"]

    # User B attempts to GET User A's conversation -> 403 Forbidden
    res_get = client.get(f"/conversations/{conv_a_id}", headers=headers_b)
    assert res_get.status_code == 403

    # User B attempts to DELETE User A's conversation -> 403 Forbidden
    res_del = client.delete(f"/conversations/{conv_a_id}", headers=headers_b)
    assert res_del.status_code == 403

    # Verify conversation still exists for User A
    res_verify = client.get(f"/conversations/{conv_a_id}", headers=headers_a)
    assert res_verify.status_code == 200

    # User A deletes their own conversation -> 204 No Content
    res_del_own = client.delete(f"/conversations/{conv_a_id}", headers=headers_a)
    assert res_del_own.status_code == 204


# ============================================================================
# Persistent Advisory & Message History Tests
# ============================================================================


def test_authenticated_advisory_persists_messages_and_records():
    """Verify POST /advisory persists user and assistant messages, plus AdvisoryRecord."""
    user = register_helper("weather_fan@example.com", "password123").json()
    headers = {"Authorization": f"Bearer {user['access_token']}"}

    # Query without conversation_id creates a new conversation automatically
    res = client.post(
        "/advisory",
        json={"query": "Is it a good day for a picnic in Delhi?"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    conv_id = data["conversation_id"]
    assert conv_id is not None
    assert data["activity"] == "picnic"

    # Inspect conversation details
    detail_res = client.get(f"/conversations/{conv_id}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()

    # Verify 2 messages persisted (user and assistant)
    assert len(detail["messages"]) == 2
    assert detail["messages"][0]["role"] == "user"
    assert "picnic in Delhi" in detail["messages"][0]["content"]
    assert detail["messages"][1]["role"] == "assistant"

    # Verify AdvisoryRecord persisted
    assert len(detail["advisories"]) == 1
    adv = detail["advisories"][0]
    assert adv["activity"] == "picnic"
    assert adv["location"] == "Delhi"
    assert adv["weather_metrics"] is not None
    assert "temperature" in adv["weather_metrics"]


def test_conversation_continuation_maintains_context():
    """Verify follow-up query in existing conversation uses persistent history."""
    user = register_helper("cyclist@example.com", "password123").json()
    headers = {"Authorization": f"Bearer {user['access_token']}"}

    # Turn 1
    r1 = client.post(
        "/advisory",
        json={"query": "Can I cycle in Bangalore today?"},
        headers=headers,
    ).json()
    conv_id = r1["conversation_id"]

    # Turn 2: Follow-up passing conversation_id
    r2 = client.post(
        "/advisory",
        json={"query": "What about this evening?", "conversation_id": conv_id},
        headers=headers,
    ).json()

    assert r2["conversation_id"] == conv_id
    assert r2["activity"] == "cycling"  # Retained from context!
    assert r2["location"] == "Bangalore"  # Retained from context!

    # Check conversation messages count (4 total: 2 user, 2 assistant)
    detail = client.get(f"/conversations/{conv_id}", headers=headers).json()
    assert len(detail["messages"]) == 4
    assert len(detail["advisories"]) == 2
