from os import environ as env

from typing import Any, Dict, List, Optional, Union
from pydantic import AnyHttpUrl, validator

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"

    PROJECT_NAME: str = "Whisper API"
    PROJECT_VERSION: str = "0.1.0"
    SECRET_KEY: str = env.get("SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = env.get("ACCESS_TOKEN_EXPIRE_MINUTES")

    SERVER_NAME: str = env.get("SERVER_NAME")
    SERVER_HOST: AnyHttpUrl = env.get("SERVER_HOST")

    POSTGRES_SERVER: str = env.get("POSTGRES_SERVER")
    POSTGRES_USER: str = env.get("POSTGRES_USER")
    POSTGRES_PASSWORD: str = env.get("POSTGRES_PASSWORD")
    POSTGRES_DB: str = env.get("POSTGRES_DB")
    POSTGRES_DATABASE_URL: str = env.get("POSTGRES_DATABASE_URL")
    TEST_DATABASE_URL: str = env.get("TEST_DATABASE_URL")

    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = ["http://localhost:3000"]

    @validator("SECRET_KEY", pre=True)
    def secret_key_must_be_set(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if not v:
            raise ValueError("SECRET_KEY must be set")
        return v

    @validator("SERVER_NAME", pre=True)
    def server_name_must_be_set(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if not v:
            raise ValueError("SERVER_NAME must be set")
        return v

    @validator("SERVER_HOST", pre=True)
    def server_host_must_be_set(
        cls, v: Optional[str], values: Dict[str, Any]
    ) -> AnyHttpUrl:
        if not v:
            raise ValueError("SERVER_HOST must be set")
        return v

    @validator("POSTGRES_SERVER", pre=True)
    def postgres_server_must_be_set(
        cls, v: Optional[str], values: Dict[str, Any]
    ) -> str:
        if not v:
            raise ValueError("POSTGRES_SERVER must be set")
        return v

    @validator("POSTGRES_USER", pre=True)
    def postgres_user_must_be_set(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if not v:
            raise ValueError("POSTGRES_USER must be set")
        return v

    @validator("POSTGRES_PASSWORD", pre=True)
    def postgres_password_must_be_set(
        cls, v: Optional[str], values: Dict[str, Any]
    ) -> str:
        if not v:
            raise ValueError("POSTGRES_PASSWORD must be set")
        return v

    @validator("POSTGRES_DB", pre=True)
    def postgres_db_must_be_set(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if not v:
            raise ValueError("POSTGRES_DB must be set")
        return v

    @validator("POSTGRES_DATABASE_URL", pre=True)
    def postgres_db_url_must_be_set(
        cls, v: Optional[str], values: Dict[str, Any]
    ) -> str:
        if not v:
            raise ValueError("POSTGRES_DATABASE_URL must be set")
        return v


settings = Settings()
