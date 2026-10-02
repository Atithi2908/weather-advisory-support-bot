"""Application configuration loaded from environment variables and .env files."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Search for .env in current directory, parent (backend), or project root
_current_dir = Path(__file__).resolve().parent
_candidates = [
    _current_dir / ".env",
    _current_dir.parent / ".env",
    _current_dir.parent.parent / ".env",
]
for _env_path in _candidates:
    if _env_path.is_file():
        load_dotenv(dotenv_path=_env_path, override=False)
        break
else:
    # Fallback to default load_dotenv searching upward
    load_dotenv()

# Database Configuration (PostgreSQL in production, SQLite for local dev/testing)
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./weather_advisory.db")

# Authentication & Security
JWT_SECRET: str = os.getenv("JWT_SECRET", "weather-advisory-super-secret-key-change-in-production")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_MINUTES: int = int(os.getenv("JWT_EXPIRATION_MINUTES", "1440"))

# Frontend CORS Configuration
FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

# LLM Configuration (OpenRouter OpenAI-compatible API)
_raw_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
if _raw_key:
    _raw_key = _raw_key.strip().strip('"').strip("'")
LLM_API_KEY: str | None = _raw_key if _raw_key else None
LLM_MODEL: str = os.getenv("LLM_MODEL", "openrouter/free") or "openrouter/free"
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1") or "https://openrouter.ai/api/v1"

# Open-Meteo API Endpoints (No API key required)
OPEN_METEO_GEOCODING_URL: str = os.getenv(
    "OPEN_METEO_GEOCODING_URL", "https://geocoding-api.open-meteo.com/v1/search"
)
OPEN_METEO_FORECAST_URL: str = os.getenv(
    "OPEN_METEO_FORECAST_URL", "https://api.open-meteo.com/v1/forecast"
)

# Policies file location (JSON format)
POLICIES_PATH: Path = Path(
    os.getenv(
        "POLICIES_PATH",
        str(_current_dir.parent.parent / "policies" / "sops.json"),
    )
)

# Network configuration
HTTP_TIMEOUT_SECONDS: int = int(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))
