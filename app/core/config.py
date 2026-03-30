"""
Application configuration — loaded from environment variables.
"""

from os import environ as env
from dotenv import load_dotenv

load_dotenv()

from typing import Any, Dict, List, Optional, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── API ────────────────────────────────────────────────────────
    API_V1_STR: str = "/v1"

    PROJECT_NAME: str = "Whisper Speech-to-Text API"
    PROJECT_VERSION: str = "2.0.0"

    # ── Security ───────────────────────────────────────────────────
    SECRET_KEY: str = env.get("SECRET_KEY", "")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        env.get("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7)
    )

    # ── Server ─────────────────────────────────────────────────────
    SERVER_NAME: str = env.get("SERVER_NAME", "whisper.api")
    SERVER_HOST: AnyHttpUrl = env.get("SERVER_HOST", "http://localhost:7860")

    # ── Database ───────────────────────────────────────────────────
    DATABASE_URL: str = env.get("DATABASE_URL", "sqlite:///./whisper.db")
    TEST_DATABASE_URL: str = env.get("TEST_DATABASE_URL", "sqlite:///./test.db")

    # ── CORS ───────────────────────────────────────────────────────
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:8000",
        "http://localhost:7860",
    ]

    # ── Transcription ──────────────────────────────────────────────
    MAX_CONCURRENT_TRANSCRIPTIONS: int = int(
        env.get("MAX_CONCURRENT_TRANSCRIPTIONS", 2)
    )
    WHISPER_BINARY_PATH: str = env.get("WHISPER_BINARY_PATH", "./binary/whisper-cli")
    MODELS_DIR: str = env.get("MODELS_DIR", "./models")

    # ── Streaming ──────────────────────────────────────────────────
    STREAM_CHUNK_DURATION_MS: int = int(
        env.get("STREAM_CHUNK_DURATION_MS", 2000)
    )

    # ── Validators ─────────────────────────────────────────────────

    @field_validator("SECRET_KEY")
    def secret_key_must_be_set(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if not v:
            raise ValueError("SECRET_KEY must be set")
        return v

    @field_validator("DATABASE_URL")
    def db_url_must_be_set(
        cls, v: Optional[str], values: Dict[str, Any]
    ) -> str:
        if not v:
            raise ValueError("DATABASE_URL must be set")
        return v


settings = Settings()
