import io
import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.core.models.ApiKey import ApiKey, generate_bearer_token

client = TestClient(app)

DUMMY_WAV = (
    b"RIFFx\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
    b"\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
)

SAMPLE_WHISPER_OJF = {
    "result": {"language": "en"},
    "transcription": [
        {
            "timestamps": {"from": "00:00:00,000", "to": "00:00:03,500"},
            "offsets": {"from": 0, "to": 3500},
            "text": " And so my fellow Americans",
            "tokens": [
                {
                    "text": "[_BEG_]",
                    "offsets": {"from": 0, "to": 0},
                    "id": 50363,
                    "p": 0.90,
                },
                {
                    "text": " And",
                    "offsets": {"from": 320, "to": 480},
                    "id": 400,
                    "p": 0.95,
                },
                {
                    "text": " so",
                    "offsets": {"from": 480, "to": 800},
                    "id": 523,
                    "p": 0.98,
                },
                {
                    "text": " my",
                    "offsets": {"from": 800, "to": 1100},
                    "id": 616,
                    "p": 0.97,
                },
                {
                    "text": " fellow",
                    "offsets": {"from": 1100, "to": 1600},
                    "id": 5891,
                    "p": 0.99,
                },
                {
                    "text": " Americans",
                    "offsets": {"from": 1600, "to": 3500},
                    "id": 4399,
                    "p": 0.96,
                },
                {
                    "text": "[_TT_175]",
                    "offsets": {"from": 3500, "to": 3500},
                    "id": 50539,
                    "p": 0.85,
                },
            ],
        }
    ],
}


def get_auth_token() -> str:
    db = SessionLocal()
    try:
        token_string = generate_bearer_token()
        new_key = ApiKey(token=token_string, name="pytest_openai_key")
        db.add(new_key)
        db.commit()
        return token_string
    finally:
        db.close()


def test_openai_transcriptions_missing_auth():
    res = client.post(
        "/v1/audio/transcriptions",
        files={"file": ("test.wav", io.BytesIO(DUMMY_WAV), "audio/wav")},
        data={"model": "whisper-1"},
    )
    assert res.status_code == 401


def test_openai_transcriptions_bearer_and_token_auth(monkeypatch):
    from app.api.endpoints import audio as audio_module

    async def fake_transcribe(**kwargs):
        return SAMPLE_WHISPER_OJF, "req-123"

    monkeypatch.setattr(audio_module, "transcribe_audio", fake_transcribe)
    monkeypatch.setattr(audio_module, "get_audio_duration", lambda _: 3.5)

    token = get_auth_token()

    # 1. Standard OpenAI Bearer token
    res_bearer = client.post(
        "/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.wav", io.BytesIO(DUMMY_WAV), "audio/wav")},
        data={"model": "whisper-1"},
    )
    assert res_bearer.status_code == 200
    assert res_bearer.json() == {"text": "And so my fellow Americans"}

    # 2. Deepgram-style Token header also accepted
    res_token = client.post(
        "/v1/audio/transcriptions",
        headers={"Authorization": f"Token {token}"},
        files={"file": ("test.wav", io.BytesIO(DUMMY_WAV), "audio/wav")},
        data={"model": "tiny.en"},
    )
    assert res_token.status_code == 200
    assert res_token.json() == {"text": "And so my fellow Americans"}


def test_openai_transcriptions_verbose_json_with_words(monkeypatch):
    from app.api.endpoints import audio as audio_module

    async def fake_transcribe(**kwargs):
        return SAMPLE_WHISPER_OJF, "req-verbose"

    monkeypatch.setattr(audio_module, "transcribe_audio", fake_transcribe)
    monkeypatch.setattr(audio_module, "get_audio_duration", lambda _: 3.5)

    token = get_auth_token()
    res = client.post(
        "/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.wav", io.BytesIO(DUMMY_WAV), "audio/wav")},
        data={
            "model": "whisper-1",
            "response_format": "verbose_json",
            "timestamp_granularities": ["word", "segment"],
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["task"] == "transcribe"
    assert body["language"] == "en"
    assert body["duration"] == 3.5
    assert body["text"] == "And so my fellow Americans"
    assert len(body["words"]) == 5
    assert body["words"][0] == {"word": "And", "start": 0.32, "end": 0.48}
    assert len(body["segments"]) == 1
    assert body["segments"][0]["start"] == 0.0
    assert body["segments"][0]["end"] == 3.5


def test_openai_transcriptions_text_srt_vtt_formats(monkeypatch):
    from app.api.endpoints import audio as audio_module

    async def fake_transcribe(**kwargs):
        fmt = kwargs.get("response_format")
        if fmt == "srt":
            return "1\n00:00:00,000 --> 00:00:03,500\nAnd so my fellow Americans\n", "req-srt"
        if fmt == "vtt":
            return "WEBVTT\n\n00:00:00.000 --> 00:00:03.500\nAnd so my fellow Americans\n", "req-vtt"
        return SAMPLE_WHISPER_OJF, "req-txt"

    monkeypatch.setattr(audio_module, "transcribe_audio", fake_transcribe)
    monkeypatch.setattr(audio_module, "get_audio_duration", lambda _: 3.5)

    token = get_auth_token()

    for fmt, expected_substr in [
        ("text", "And so my fellow Americans"),
        ("srt", "00:00:00,000 --> 00:00:03,500"),
        ("vtt", "WEBVTT"),
    ]:
        res = client.post(
            "/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.wav", io.BytesIO(DUMMY_WAV), "audio/wav")},
            data={"model": "whisper-1", "response_format": fmt},
        )
        assert res.status_code == 200
        assert expected_substr in res.text


def test_openai_translations_endpoint(monkeypatch):
    from app.api.endpoints import audio as audio_module

    captured = {}

    async def fake_transcribe(**kwargs):
        captured.update(kwargs)
        return SAMPLE_WHISPER_OJF, "req-trans"

    monkeypatch.setattr(audio_module, "transcribe_audio", fake_transcribe)
    monkeypatch.setattr(audio_module, "get_audio_duration", lambda _: 3.5)

    token = get_auth_token()
    res = client.post(
        "/v1/audio/translations",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.wav", io.BytesIO(DUMMY_WAV), "audio/wav")},
        data={"model": "whisper-1", "response_format": "verbose_json", "temperature": "0.2"},
    )
    assert res.status_code == 200
    assert captured["translate"] is True
    assert captured["temperature"] == 0.2
    assert res.json()["task"] == "translate"


def test_openai_invalid_model_and_format():
    token = get_auth_token()
    res_model = client.post(
        "/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.wav", io.BytesIO(DUMMY_WAV), "audio/wav")},
        data={"model": "nonexistent-model"},
    )
    assert res_model.status_code == 400
    assert "Unknown model" in res_model.json()["detail"]

    res_fmt = client.post(
        "/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.wav", io.BytesIO(DUMMY_WAV), "audio/wav")},
        data={"model": "whisper-1", "response_format": "invalid_fmt"},
    )
    assert res_fmt.status_code == 400
    assert "Unsupported response_format" in res_fmt.json()["detail"]
