from app.core.config import settings


def test_settings():
    assert settings.API_V1_STR == "/api/v1"
    assert settings.PROJECT_NAME == "My FastAPI Project"
    assert settings.SQLALCHEMY_DATABASE_URI == "sqlite:///./test.db"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
