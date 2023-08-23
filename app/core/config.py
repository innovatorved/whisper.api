from os import environ as env
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"

    PROJECT_NAME: str = "Whisper API"
    PROJECT_VERSION: str = "0.1.0"
    SECRET_KEY: str = env.get("SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = (
        env.get("ACCESS_TOKEN_EXPIRE_MINUTES") or 60 * 24 * 7
    )

    SERVER_NAME: str = env.get("SERVER_NAME")
    SERVER_HOST: AnyHttpUrl = env.get("SERVER_HOST")

    POSTGRES_DATABASE_URL: str = env.get("POSTGRES_DATABASE_URL")
    TEST_DATABASE_URL: str = env.get("POSTGRES_DATABASE_URL")

    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:8000",
    ]

    @field_validator("SECRET_KEY")
    def secret_key_must_be_set(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if not v:
            raise ValueError("SECRET_KEY must be set")
        return v

    @field_validator("SERVER_NAME")
    def server_name_must_be_set(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if not v:
            raise ValueError("SERVER_NAME must be set")
        return v

    @field_validator("SERVER_HOST")
    def server_host_must_be_set(
        cls, v: Optional[str], values: Dict[str, Any]
    ) -> AnyHttpUrl:
        if not v:
            raise ValueError("SERVER_HOST must be set")
        return v

    @field_validator("POSTGRES_DATABASE_URL")
    def postgres_db_url_must_be_set(
        cls, v: Optional[str], values: Dict[str, Any]
    ) -> str:
        if not v:
            raise ValueError("POSTGRES_DATABASE_URL must be set")
        return v


settings = Settings()
