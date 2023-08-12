from typing import Any, Dict, List, Optional, Union
from pydantic import AnyHttpUrl, BaseSettings, validator


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Whisper API"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    SERVER_NAME: str
    SERVER_HOST: AnyHttpUrl
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

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
    def server_host_must_be_set(cls, v: Optional[str], values: Dict[str, Any]) -> AnyHttpUrl:
        if not v:
            raise ValueError("SERVER_HOST must be set")
        return v

    @validator("POSTGRES_SERVER", pre=True)
    def postgres_server_must_be_set(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if not v:
            raise ValueError("POSTGRES_SERVER must be set")
        return v

    @validator("POSTGRES_USER", pre=True)
    def postgres_user_must_be_set(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if not v:
            raise ValueError("POSTGRES_USER must be set")
        return v

    @validator("POSTGRES_PASSWORD", pre=True)
    def postgres_password_must_be_set(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if not v:
            raise ValueError("POSTGRES_PASSWORD must be set")
        return v

    @validator("POSTGRES_DB", pre=True)
    def postgres_db_must_be_set(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if not v:
            raise ValueError("POSTGRES_DB must be set")
        return v


settings = Settings()