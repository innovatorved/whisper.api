import io
from fastapi.testclient import TestClient
from app.main import app
from app.api.endpoints.listen import detect_stream_chunk_format, resolve_stream_encoding

from app.core.database import SessionLocal
from app.core.models.ApiKey import ApiKey, generate_bearer_token

client = TestClient(app)

# Dummy test file
dummy_wav_content = b"RIFFx\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"

def get_auth_token():
    db = SessionLocal()
    try:
        token_string = generate_bearer_token()
        new_key = ApiKey(token=token_string, name="pytest_key")
        db.add(new_key)
        db.commit()
        return token_string
    finally:
        db.close()

def test_listen_unauthorized():
    response = client.post("/v1/listen", files={"file": ("test.wav", io.BytesIO(dummy_wav_content), "audio/wav")})
    assert response.status_code == 401

def test_listen_invalid_auth_format():
    response = client.post(
        "/v1/listen",
        headers={"Authorization": "Bearer invalid"},
        files={"file": ("test.wav", io.BytesIO(dummy_wav_content), "audio/wav")}
    )
    assert response.status_code == 401
    assert "Invalid Authorization format" in response.json()["detail"]

def test_models_endpoint():
    response = client.get("/v1/models")
    assert response.status_code == 200
    assert "models" in response.json()
    assert "count" in response.json()
    assert isinstance(response.json()["models"], list)

# We mock actual transcription since it requires whisper-cli to be present in CI environment
def test_listen_invalid_model():
    token = get_auth_token()
    response = client.post(
        "/v1/listen?model=invalid.model",
        headers={"Authorization": f"Token {token}"},
        files={"file": ("test.wav", io.BytesIO(dummy_wav_content), "audio/wav")}
    )
    assert response.status_code == 400
    assert "Unknown model" in response.json()["detail"]

def test_listen_url_request():
    token = get_auth_token()
    response = client.post(
        "/v1/listen?model=tiny.en",
        headers={"Authorization": f"Token {token}"},
        json={"url": "https://example.com/audio.wav"}
    )
    # Fails because download will fail (invalid URL), but passes auth and model validation
    assert response.status_code == 400
    assert "Failed to download audio" in response.json()["detail"]


def test_listen_websocket_with_query_token_connects():
    token = get_auth_token()
    with client.websocket_connect(f"/v1/listen?token={token}&model=tiny.en&language=en") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "Metadata"
        ws.send_json({"type": "CloseStream"})


def test_listen_websocket_with_subprotocol_token_connects():
    token = get_auth_token()
    with client.websocket_connect(
        "/v1/listen?model=tiny.en&language=en",
        subprotocols=["token", token],
    ) as ws:
        msg = ws.receive_json()
        assert msg["type"] == "Metadata"
        ws.send_json({"type": "CloseStream"})


def test_listen_websocket_with_deepgram_style_subprotocols_connects():
    token = get_auth_token()
    with client.websocket_connect(
        "/v1/listen?model=tiny.en&language=en",
        subprotocols=["token", token, "x-deepgram-session-id", "session-123"],
    ) as ws:
        assert ws.accepted_subprotocol == "token"
        msg = ws.receive_json()
        assert msg["type"] == "Metadata"
        ws.send_json({"type": "CloseStream"})


def test_listen_websocket_with_non_leading_token_pair_connects():
    token = get_auth_token()
    with client.websocket_connect(
        "/v1/listen?model=tiny.en&language=en",
        subprotocols=["x-deepgram-session-id", "session-123", "token", token],
    ) as ws:
        msg = ws.receive_json()
        assert msg["type"] == "Metadata"
        ws.send_json({"type": "CloseStream"})


def test_detect_stream_chunk_format_webm_signature():
    data = b"\x1A\x45\xDF\xA3" + b"\x00" * 32
    assert detect_stream_chunk_format(data) == "webm"


def test_detect_stream_chunk_format_wav_signature():
    data = b"RIFF" + b"\x00\x00\x00\x00" + b"WAVE" + b"\x00" * 16
    assert detect_stream_chunk_format(data) == "wav"


def test_resolve_stream_encoding_auto_uses_detected():
    assert resolve_stream_encoding("auto", "ogg") == "ogg"


def test_resolve_stream_encoding_auto_defaults_pcm():
    assert resolve_stream_encoding("auto", None) == "linear16"


def test_resolve_stream_encoding_linear16_falls_back_to_detected_container():
    assert resolve_stream_encoding("linear16", "webm") == "webm"
