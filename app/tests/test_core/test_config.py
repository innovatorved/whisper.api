from app.core.config import settings


def test_settings():
    assert settings.API_V1_STR == "/api/v1"
    assert settings.PROJECT_NAME == "Whisper API"
