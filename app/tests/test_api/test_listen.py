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
    # Fails on URL ingest (HTTP error, DNS, or policy) after auth and model validation
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert isinstance(detail, str)
    assert any(
        phrase in detail
        for phrase in (
            "Failed to download audio",
            "Could not resolve audio URL",
            "Invalid audio URL",
            "Audio URL must use http",
            "not allowed for security",
        )
    )


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


def test_listen_websocket_long_container_stream_uses_cumulative_decode(monkeypatch):
    """Regression test for long-running container (webm/ogg/...) streams.

    Container formats (webm/ogg/opus/mp4) cannot be decoded mid-stream by
    ffmpeg because clusters/pages reference state from the stream start. The
    handler must therefore use a cumulative-decode strategy: keep all bytes
    received so far, decode from the beginning each window, and emit only
    the *new* delta transcript past the last high-water mark.

    Without this, only the first chunk produces a transcript and every
    subsequent chunk silently returns empty.
    """
    import time as _time
    from app.api.endpoints import listen as listen_module

    seen_calls = []
    word_cursor = {"t": 0.0}

    async def fake_container_window(
        cumulative_data, container_format, request_id, model, language,
        translate, diarize, detect_language, committed_audio_seconds,
        is_final=False, speech_final=False,
    ):
        seen_calls.append({
            "cumulative_len": len(cumulative_data),
            "container_format": container_format,
            "committed_audio_seconds": committed_audio_seconds,
            "speech_final": speech_final,
        })
        word_cursor["t"] += 1.0
        full = word_cursor["t"]
        idx = len(seen_calls)
        final_msg = {
            "type": "Results",
            "channel_index": [0, 1],
            "duration": round(full - committed_audio_seconds, 2),
            "start": round(committed_audio_seconds, 2),
            "is_final": True,
            "speech_final": bool(speech_final),
            "channel": {"alternatives": [{
                "transcript": f"final-{idx}",
                "confidence": 0.9,
                "words": [],
            }]},
            "metadata": {"request_id": request_id, "model_info": {}},
            "from_finalize": False,
        }
        interim_msg = None if speech_final else {
            "type": "Results",
            "channel_index": [0, 1],
            "duration": 0.0,
            "start": round(full, 2),
            "is_final": False,
            "speech_final": False,
            "channel": {"alternatives": [{
                "transcript": f"interim-{idx}",
                "confidence": 0.9,
                "words": [],
            }]},
            "metadata": {"request_id": request_id, "model_info": {}},
            "from_finalize": False,
        }
        return {
            "_full_duration": full,
            "_new_committed": full,
            "_final_msg": final_msg,
            "_interim_msg": interim_msg,
        }

    monkeypatch.setattr(
        listen_module, "_process_container_window_safe", fake_container_window
    )
    monkeypatch.setattr(listen_module.settings, "STREAM_CHUNK_DURATION_MS", 1)

    token = get_auth_token()
    webm_header = b"\x1A\x45\xDF\xA3" + b"\x00" * 60
    headerless_chunk = b"\xA3\x42\x00" + b"\x11" * 4096

    received = []

    def drain_two(ws_):
        # Each window emits a finalized message and an interim message.
        for _ in range(2):
            received.append(ws_.receive_json())

    with client.websocket_connect(
        f"/v1/listen?token={token}&model=tiny.en&language=en&encoding=webm"
    ) as ws:
        meta = ws.receive_json()
        assert meta["type"] == "Metadata"

        ws.send_bytes(webm_header + b"\x22" * 4096)
        drain_two(ws)
        _time.sleep(0.05)

        for _ in range(3):
            ws.send_bytes(headerless_chunk)
            drain_two(ws)
            _time.sleep(0.05)

        ws.send_json({"type": "CloseStream"})
        # CloseStream produces one final-only message (no interim).
        received.append(ws.receive_json())

    assert len(seen_calls) >= 4, f"expected >=4 container windows, got {seen_calls}"

    cumulative_lens = [c["cumulative_len"] for c in seen_calls]
    assert cumulative_lens == sorted(cumulative_lens), (
        f"cumulative buffer must grow monotonically across windows: {cumulative_lens}"
    )
    assert cumulative_lens[-1] > cumulative_lens[0], (
        "later windows must contain strictly more bytes (cumulative decode)"
    )

    committed_marks = [c["committed_audio_seconds"] for c in seen_calls]
    assert committed_marks == sorted(committed_marks), (
        f"committed mark must be non-decreasing across windows: {committed_marks}"
    )

    assert seen_calls[-1]["speech_final"] is True, (
        "final window from CloseStream should set speech_final=True"
    )

    # Verify the on-the-wire protocol: the client sees alternating
    # is_final=True / is_final=False messages during streaming, and a
    # is_final=True with speech_final=True at the end.
    interim_count = sum(1 for m in received if m.get("is_final") is False)
    final_count = sum(1 for m in received if m.get("is_final") is True)
    assert interim_count >= 4, f"expected >=4 interim messages, got {interim_count}"
    assert final_count >= 5, f"expected >=5 finalized messages, got {final_count}"
    assert received[-1].get("speech_final") is True
    assert received[-1].get("is_final") is True
