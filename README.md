# Weather-Advisory Support Bot (Phase 3 — Production Web App, Persistence, Auth & Evaluation)

An intelligent, production-ready outdoor weather advisory web application orchestrating conversational intent understanding, deterministic geocoding, live meteorological data retrieval via Open-Meteo, a data-driven **Standard Operating Procedure (SOP) safety policy engine**, persistent PostgreSQL/SQLite storage, JWT-based user authentication, and an automated **LLM-Judge evaluation suite**.

---

## 1. Safety Architecture Principle

> **AUTHORITATIVE POLICY PRINCIPLE**:  
> The deterministic SOP engine is authoritative for safety policy matching. The LLM is **NEVER** responsible for deciding whether a safety condition is true or determining risk clearance. The LLM acts strictly as a natural-language explanation and formatting layer grounded directly in live weather metrics and deterministic policy directives.

```text
               Weather API (Open-Meteo)
                         │
                         ▼
             Deterministic SOP Engine
                         │
                         ▼
             Structured Safety Decision
                         │
                         ▼
             LLM Response Generator
                         │
                         ▼
             Human-Readable Explanation
```

When no SOP applies (`matched_sops == []`), the system strictly issues an honest **No-Guidance** response. The system and frontend are prevented from hallucinating or providing generic safety clearances such as *"You're safe"* or *"Conditions are good to go"*.

---

## 2. End-to-End System Architecture & LangGraph Flow

```text
                                  User Query
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │  understand_query   │ (Extract location, activity, time window, person context)
                            └──────────┬──────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │  resolve_location   │ (Deterministic geocoding via Open-Meteo)
                            └──────────┬──────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │    fetch_weather    │ (Live forecast/current weather metrics from Open-Meteo)
                            └──────────┬──────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │     match_sops      │ (Deterministic condition evaluation from sops.json)
                            └──────────┬──────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         ▼                             ▼                             ▼
  [Location/API Error]         [SOP Matched]                   [No SOP Matched]
         │                             │                             │
         ▼                             ▼                             ▼
┌───────────────────┐        ┌───────────────────┐        ┌────────────────────┐
│   handle_error    │        │ generate_response │        │    no_guidance     │
│  (Honest Failure) │        │ (Grounded LLM/    │        │  (Honest Guardrail │
│                   │        │  Deterministic)   │        │   No Clearance)    │
└───────────────────┘        └───────────────────┘        └────────────────────┘
```

---

## 3. SOP Policy Engine & Rules

- **Deterministic 12-Policy SOP Engine**: Authors authoritative outdoor safety directives with multi-condition evaluation across weather metrics and intent categories (`outdoor_exercise`, `travel`, `vulnerable_groups`, `leisure`, `situational_override`).
- **Situational Override Rule**: Policies marked with `"override": true` (e.g. `SOP-12: Thunderstorm / Severe Weather Override`) outrank standard activity-specific rules regardless of the individual activity.
- **Conflict Resolution Strategy**: When multiple SOPs match simultaneously (e.g., cycling in strong wind with high UV):
  1. Situational Override SOPs (`override: true`) take first priority.
  2. Highest severity level takes precedence (`HIGH > MEDIUM > LOW`).
  3. Tie-breaking is deterministic by SOP ID.
  4. All matched SOPs are preserved and returned in `matched_sops` so the user and UI have full transparency.
- **Date/Time Semantics**:
  - `today` / current: Evaluates real-time current weather metrics.
  - `tomorrow` / `this evening` / `this afternoon`: Queries Open-Meteo hourly forecast intervals for the requested date/time window and computes representative aggregate metrics (e.g., maximum UV, peak wind speed, maximum precipitation probability).
- **Adding a New SOP (Zero-Code Extensibility)**:
  Reviewers or administrators can add a new SOP simply by adding a JSON object to [`policies/sops.json`](file:///c:/Users/atith/weather-advisory-bot/policies/sops.json) without modifying any Python control flow, LangGraph nodes, or frontend code. The engine validates schema, evaluates new conditions dynamically, and surfaces the new advisory immediately.

---

## 4. Tech Stack

- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, Lucide Icons
- **Backend**: Python 3.12, FastAPI, LangGraph, LangChain Core, Pydantic V2
- **Database & ORM**: SQLAlchemy 2.0, Alembic 1.13, PostgreSQL / SQLite
- **Authentication**: PyJWT, Bcrypt, Passlib
- **External Data**: Open-Meteo Geocoding & Forecast APIs (No API key needed)
- **Testing & Evals**: Pytest, Automated LLM-Judge Runner

---

## 5. Directory Structure

```text
weather-advisory-bot/
├── backend/
│   ├── alembic/
│   │   ├── versions/
│   │   │   └── 0e247cd1d5eb_initial_schema.py   # Database migration
│   │   ├── env.py
│   │   └── script.py.mako
│   ├── app/
│   │   ├── auth/
│   │   │   ├── deps.py                          # get_current_user dependency
│   │   │   └── security.py                      # Bcrypt hashing & JWT management
│   │   ├── db/
│   │   │   ├── base.py                          # Engine, SessionLocal, get_db
│   │   │   └── models.py                        # User, Conversation, Message, AdvisoryRecord
│   │   ├── graph/
│   │   │   ├── state.py                         # WeatherState definition
│   │   │   └── workflow.py                      # LangGraph StateGraph
│   │   ├── nodes/                               # Workflow node functions
│   │   ├── policies/                            # SOP loader, evaluator, matcher
│   │   ├── routers/
│   │   │   ├── auth.py                          # /auth/register, /auth/login, /auth/me
│   │   │   ├── conversations.py                 # /conversations CRUD
│   │   │   └── advisory.py                      # /advisory endpoint
│   │   ├── schemas/                             # Pydantic request/response schemas
│   │   ├── services/                            # Open-Meteo & LLM clients
│   │   ├── api.py                               # FastAPI application & CORS
│   │   ├── config.py                            # App settings
│   │   └── main.py                              # CLI runner
│   ├── tests/
│   │   ├── test_api.py                          # Health check & public API tests
│   │   ├── test_auth_and_conversations.py       # Auth & conversation persistence tests
│   │   ├── test_evals.py                        # Evaluation suite tests
│   │   ├── test_nodes.py                        # Individual graph node tests
│   │   ├── test_sop_engine.py                   # Deterministic SOP engine tests
│   │   ├── test_weather_service.py              # Open-Meteo client tests
│   │   └── test_workflow.py                     # LangGraph workflow tests
│   └── requirements.txt
├── evals/
│   ├── dataset.json                             # 14 evaluation scenarios
│   ├── judge.py                                 # LLM-judge & rule-based judge
│   ├── runner.py                                # Evaluation CLI runner
│   ├── schema.py                                # Pydantic eval schemas
│   └── latest_report.json                       # Latest evaluation report
├── frontend/
│   ├── src/
│   │   ├── app/                                 # App router (page.tsx, login, register)
│   │   ├── components/                          # Header, Sidebar, ChatArea, AdvisoryCard
│   │   ├── lib/                                 # API client & AuthContext
│   │   └── types/                               # TypeScript interfaces
│   ├── package.json
│   └── tailwind.config.js
├── policies/
│   └── sops.json                                # 11 Authoritative SOP definitions
├── alembic.ini
├── main.py
└── pytest.ini
```

---

## 6. Database Schema

The database model is designed for PostgreSQL and supports SQLite for local dev/testing:

```text
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     User        │       │  Conversation   │       │     Message     │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │◄─────┐│ id (PK)         │◄─────┐│ id (PK)         │
│ email (Unique)  │      └┤ user_id (FK)    │      └┤ conversation_id │
│ password_hash   │       │ title           │       │ role            │
│ created_at      │       │ created_at      │       │ content         │
└─────────────────┘       │ updated_at      │       │ created_at      │
                          └────────┬────────┘       └─────────────────┘
                                   │
                                   ▼
                          ┌────────────────────────┐
                          │     AdvisoryRecord     │
                          ├────────────────────────┤
                          │ id (PK)                │
                          │ conversation_id (FK)   │
                          │ user_query             │
                          │ location               │
                          │ weather_metrics (JSON) │
                          │ activity               │
                          │ person_context         │
                          │ selected_sop (JSON)    │
                          │ matched_sops (JSON)    │
                          │ severity               │
                          │ generated_response     │
                          │ created_at             │
                          └────────────────────────┘
```

---

## 7. Setup & Run Instructions

### 7.1 Prerequisites
- Python 3.12+
- Node.js 18+ and npm
- (Optional) PostgreSQL database (defaults to SQLite out of the box)

### 7.2 Backend Setup

1. **Create and activate a virtual environment**:
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   # Linux/macOS:
   source .venv/bin/activate
   ```

2. **Install backend dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```

4. **Run database migrations**:
   ```bash
   alembic upgrade head
   ```

5. **Start the FastAPI backend server**:
   ```bash
   uvicorn backend.app.api:app --reload --port 8000
   ```
   API Documentation is available at: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### 7.3 Frontend Setup

1. **Navigate to `frontend/`**:
   ```bash
   cd frontend
   ```

2. **Install frontend dependencies**:
   ```bash
   npm install
   ```

3. **Configure frontend environment**:
   Ensure `frontend/.env.local` contains:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

4. **Run the Next.js development server**:
   ```bash
   npm run dev
   ```
   Access the web dashboard at: [http://localhost:3000](http://localhost:3000)

5. **Build for production**:
   ```bash
   npm run build
   npm run start
   ```

---

## 8. OpenRouter Setup

To connect the Weather Advisory Support Bot to real LLM generation via OpenRouter:

1. Copy `.env.example` to `.env` (or open the generated `.env` in the project root):
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and set your OpenRouter API key:
   ```env
   LLM_API_KEY=sk-or-v1-...
   ```
3. **No other LLM configuration is required!** All other OpenRouter defaults are automatically wired:
   - `LLM_MODEL=openrouter/free`
   - `LLM_BASE_URL=https://openrouter.ai/api/v1`
4. Run the backend:
   ```bash
   uvicorn backend.app.api:app --reload --port 8000
   ```
5. Run the frontend:
   ```bash
   cd frontend && npm run dev
   ```

---

## 9. Running Automated Tests

Run the full automated test suite (60 tests across all components):

```bash
pytest backend/tests/ -v
```

### Test Coverage Highlights:
- **Phase 2 Regression Tests**: All 39 original tests continue passing unchanged.
- **OpenRouter LLM Integration**: Real API client configuration, call simulation, graceful fallback on error, and token leak sanitization tests.
- **Authentication**: Registration, duplicate rejection, short password handling, login validation, bad password rejection, token verification.
- **Cross-User Authorization**: Strict test ensuring User A cannot retrieve or delete User B's conversations.
- **Conversation Persistence**: Multi-turn dialogue continuation retaining session location and activity.
- **SOP Engine & Guardrails**: Exact matching, multiple matches with highest severity resolution, and no-SOP safety guardrail.

---

## 10. Running the LLM-Judge Evaluation Suite

The evaluation suite executes 14 representative scenarios against the graph and scores them across 7 quality dimensions:

```bash
python evals/runner.py
```

### Evaluation Dimensions:
1. `weather_factuality`: Accurate preservation of exact weather numbers.
2. `sop_correctness`: Correct SOP ID or correct identification of no-SOP state.
3. `severity_correctness`: Accurate communication of risk severity (HIGH/MEDIUM/LOW/None).
4. `advice_preservation`: Strict adherence to official recommendation text.
5. `hallucination_free`: Complete absence of fabricated numbers or unsupported safety clearances.
6. `relevance`: Direct response addressing user query and activity context.
7. `completeness`: Thorough weather summary and assessment.

Results are displayed in the terminal and saved to `evals/latest_report.json`.

---

## 10. Example API Requests

### 10.1 User Registration
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "analyst@example.com", "password": "securepassword123"}'
```

### 10.2 User Login
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "analyst@example.com", "password": "securepassword123"}'
```
Response:
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user": {
    "id": "76652ee9-6be5-4cf4-9133-c283ce93f93f",
    "email": "analyst@example.com",
    "created_at": "2026-10-02T10:30:00"
  }
}
```

### 10.3 Advisory Query (Authenticated)
```bash
curl -X POST http://localhost:8000/advisory \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"query": "Can I cycle in Bangalore today?"}'
```
Response:
```json
{
  "conversation_id": "80ff2ce0-9852-47d3-9bc0-d79044cf48f2",
  "message": "Weather report for Bangalore, India for 'cycling'...\n\nSafety Policy Assessment:\n• Applicable Guideline: SOP-01 — Strong Wind Cycling\n• Severity Level: HIGH\n• Official Recommendation: Avoid cycling because strong winds create a severe safety and stability risk.",
  "location": "Bangalore",
  "activity": "cycling",
  "weather": {
    "temperature": 27.5,
    "wind_speed": 44.0,
    "precipitation_probability": 10,
    "uv_index": 4.0,
    "relative_humidity": 65
  },
  "selected_sop": {
    "id": "SOP-01",
    "name": "Strong Wind Cycling",
    "severity": "HIGH",
    "advice": "Avoid cycling because strong winds create a severe safety and stability risk."
  },
  "matched_sops": [
    {
      "id": "SOP-01",
      "name": "Strong Wind Cycling",
      "severity": "HIGH"
    }
  ],
  "severity": "HIGH"
}
```

---

## 11. Security & Compliance Verification

- **Password Safety**: Stored exclusively as one-way salted bcrypt hashes.
- **Data Isolation**: Endpoints verify user ownership before reading or modifying any conversation.
- **SQL Injection Prevention**: Parameterized queries via SQLAlchemy ORM.
- **CORS Protection**: Restricted to configured origins (`FRONTEND_URL`).
- **No Secret Leakage**: Credentials and keys are configured via environment variables and excluded by `.gitignore`.
