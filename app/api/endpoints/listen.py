"""
Speech-to-Text Listen Endpoint — Deepgram-compatible.

POST /v1/listen  → Pre-recorded audio transcription
WS   /v1/listen  → Live streaming audio transcription

Supports:
  - File upload (Content-Type: audio/*)
  - URL-based (Content-Type: application/json, body: {"url": "..."})
  - Query params: model, language, translate, diarize, utterances, etc.
"""

import asyncio
from datetime import datetime, timezone
import io
import json
import logging
import os
import struct
import uuid
import wave
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import PlainTextResponse

from app.core.config import settings
from app.core.database import get_db
from sqlalchemy.orm import Session
from app.core.models.ApiKey import ApiKey
from app.utils.constant import (
    DEFAULT_STREAM_CHUNK_DURATION_MS,
    STREAM_CHANNELS,
    STREAM_SAMPLE_RATE,
    STREAM_SAMPLE_WIDTH,
    SUPPORTED_AUDIO_CONTENT_TYPES,
    model_names,
)
from app.utils.utils import (
    compute_sha256,
    convert_audio_to_wav,
    create_wav_from_pcm,
    download_audio_from_url,
    get_audio_duration,
    parse_whisper_json_to_deepgram,
    save_audio_bytes,
    transcribe_audio,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Semaphore to limit concurrent transcriptions
_transcription_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_TRANSCRIPTIONS)

PCM_STREAM_ENCODINGS = {
    "linear16",
    "pcm",
    "pcm16",
    "pcm_s16le",
    "raw",
    "raw-pcm",
    "s16le",
}

STREAM_CONTAINER_ENCODINGS = {
    "wav": "wav",
    "webm": "webm",
    "ogg": "ogg",
    "opus": "opus",
    "mp3": "mp3",
    "flac": "flac",
    "mp4": "mp4",
    "m4a": "m4a",
}


# ═══════════════════════════════════════════════════════════════════════
# AUTH HELPER
# ═══════════════════════════════════════════════════════════════════════


def extract_api_key(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> str:
    """
    Extract and validate API key from the Authorization header.
    Supports: Authorization: Token <key>
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header. Use: Authorization: Token <your_api_key>",
        )
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "token":
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization format. Use: Authorization: Token <your_api_key>",
        )
    token = parts[1].strip()
    
    # Validate against DB
    record = db.query(ApiKey).filter(ApiKey.token == token).first()
    if not record:
        raise HTTPException(
            status_code=401,
            detail="Invalid or revoked API key",
        )
        
    return token


def extract_ws_api_key(websocket: WebSocket, query_token: Optional[str]) -> Optional[str]:
    """Extract API key from websocket query params, auth header, or subprotocol header."""
    if query_token:
        return query_token.strip()

    auth_header = websocket.headers.get("authorization")
    if auth_header:
        parts = auth_header.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() in {"token", "bearer"}:
            token = parts[1].strip()
            if token:
                return token

    # Browser clients often send API keys in subprotocols,
    # e.g. "token, <api_key>" and may include extra protocol pairs.
    subprotocol_header = websocket.headers.get("sec-websocket-protocol", "")
    if subprotocol_header:
        protocols = [p.strip() for p in subprotocol_header.split(",") if p.strip()]
        # Parse as key/value pairs and locate token-like keys anywhere in the list.
        i = 0
        while i + 1 < len(protocols):
            key = protocols[i].lower()
            value = protocols[i + 1].strip()
            if key in {"token", "bearer", "authorization"} and value:
                value_parts = value.split(" ", 1)
                if len(value_parts) == 2 and value_parts[0].lower() in {"token", "bearer"}:
                    value = value_parts[1].strip()
                if value:
                    return value
            i += 2

        # Fallback for malformed headers where token is followed by immediate value.
        for idx, value in enumerate(protocols[:-1]):
            if value.lower() in {"token", "bearer"}:
                return protocols[idx + 1].strip()

    return None


def select_ws_subprotocol(websocket: WebSocket) -> Optional[str]:
    """Select a safe subprotocol from what the client offered.

    Some browser clients close the socket if they offered subprotocols and the
    server does not select one. Prefer non-secret protocol keys when present.
    """
    subprotocol_header = websocket.headers.get("sec-websocket-protocol", "")
    if not subprotocol_header:
        return None

    offered = [p.strip() for p in subprotocol_header.split(",") if p.strip()]
    if not offered:
        return None

    preferred = {"token", "bearer", "authorization", "x-deepgram-session-id"}
    for protocol in offered:
        if protocol.lower() in preferred:
            return protocol

    # Fallback to first offered value to satisfy protocol negotiation.
    return offered[0]


def detect_stream_chunk_format(audio_data: bytes) -> Optional[str]:
    """Best-effort container/codec detection for websocket binary chunks."""
    if len(audio_data) < 4:
        return None

    if audio_data.startswith(b"RIFF") and len(audio_data) >= 12 and audio_data[8:12] == b"WAVE":
        return "wav"
    if audio_data.startswith(b"OggS"):
        return "ogg"
    if audio_data.startswith(b"fLaC"):
        return "flac"
    if audio_data.startswith(b"ID3"):
        return "mp3"
    if audio_data.startswith(b"\x1A\x45\xDF\xA3"):
        return "webm"
    if len(audio_data) >= 12 and audio_data[4:8] == b"ftyp":
        return "mp4"
    if audio_data.startswith(b"OpusHead"):
        return "opus"

    # MP3 frame sync (11111111 111xxxxx)
    if audio_data[0] == 0xFF and (audio_data[1] & 0xE0) == 0xE0:
        return "mp3"

    return None


def resolve_stream_encoding(
    requested_encoding: str,
    detected_encoding: Optional[str],
) -> str:
    """Resolve stream encoding, preferring explicit client intent over auto-detection."""
    normalized = (requested_encoding or "linear16").strip().lower()
    if normalized == "auto":
        if detected_encoding:
            return detected_encoding
        return "linear16"
    if normalized in PCM_STREAM_ENCODINGS and detected_encoding in STREAM_CONTAINER_ENCODINGS:
        return detected_encoding
    return normalized


# ═══════════════════════════════════════════════════════════════════════
# PRE-RECORDED AUDIO — POST /v1/listen
# ═══════════════════════════════════════════════════════════════════════


@router.post(
    "",
    summary="Transcribe Pre-Recorded Audio",
    description="Transcribe audio from a file upload or URL. Mirrors Deepgram's POST /v1/listen.",
    tags=["speech-to-text"],
)
async def listen_pre_recorded(
    request: Request,
    # Query parameters (Deepgram-style)
    model: str = Query("tiny.en", description="Model to use for transcription"),
    language: str = Query("en", description="BCP-47 language code"),
    translate: bool = Query(False, description="Translate to English"),
    diarize: bool = Query(False, description="Speaker diarization (stereo audio)"),
    punctuate: bool = Query(True, description="Add punctuation"),
    utterances: bool = Query(False, description="Split output into utterances"),
    smart_format: bool = Query(False, description="Apply smart formatting"),
    detect_language: bool = Query(False, description="Auto-detect language"),
    prompt: Optional[str] = Query(None, description="Initial prompt / custom vocabulary"),
    start: Optional[int] = Query(None, description="Start time offset in milliseconds"),
    process_duration: Optional[int] = Query(None, alias="duration", description="Duration to process in milliseconds"),
    response_format: str = Query("json", description="Output format (json, srt, vtt)"),
    # Auth
    api_key: str = Depends(extract_api_key),
):
    """
    Transcribe pre-recorded audio.

    **Two input methods:**
    1. **File upload**: Send audio bytes with `Content-Type: audio/wav` (or other audio type)
    2. **URL**: Send JSON body `{"url": "https://..."}` with `Content-Type: application/json`
    """
    # Validate model
    if model not in model_names:
        available = ", ".join(model_names.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Unknown model '{model}'. Available: {available}",
        )

    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()

    audio_path: str = ""
    needs_conversion = False

    try:
        if content_type == "application/json":
            # ── URL-based transcription ──
            body = await request.json()
            url = body.get("url")
            if not url or not isinstance(url, str):
                raise HTTPException(
                    status_code=400,
                    detail="Request body must contain a string 'url' field",
                )
            audio_path = await download_audio_from_url(url)
            needs_conversion = True

        elif content_type.startswith("multipart/form-data"):
            # ── Multipart file upload ──
            form = await request.form()
            file = form.get("file")
            if file is None:
                raise HTTPException(
                    status_code=400,
                    detail="No file found in multipart form data. Send file with key 'file'.",
                )
            audio_bytes = await file.read()
            max_upload = settings.MAX_AUDIO_UPLOAD_BYTES
            if len(audio_bytes) > max_upload:
                raise HTTPException(
                    status_code=413,
                    detail="Audio exceeds maximum upload size",
                )
            # Determine extension from filename or content type
            filename = getattr(file, "filename", "upload.wav") or "upload.wav"
            ext = filename.rsplit(".", 1)[-1] if "." in filename else "wav"
            audio_path = save_audio_bytes(audio_bytes, ext)
            needs_conversion = ext.lower() not in ("wav",)

        elif content_type in SUPPORTED_AUDIO_CONTENT_TYPES or content_type.startswith("audio/"):
            # ── Raw audio binary upload ──
            audio_bytes = await request.body()
            if not audio_bytes:
                raise HTTPException(
                    status_code=400,
                    detail="Empty audio body",
                )
            max_upload = settings.MAX_AUDIO_UPLOAD_BYTES
            if len(audio_bytes) > max_upload:
                raise HTTPException(
                    status_code=413,
                    detail="Audio exceeds maximum upload size",
                )
            # Map content type to extension
            ext_map = {
                "audio/wav": "wav", "audio/x-wav": "wav", "audio/wave": "wav",
                "audio/mp3": "mp3", "audio/mpeg": "mp3",
                "audio/ogg": "ogg", "audio/flac": "flac", "audio/x-flac": "flac",
                "audio/webm": "webm", "audio/mp4": "mp4",
                "audio/m4a": "m4a", "audio/x-m4a": "m4a",
            }
            ext = ext_map.get(content_type, "wav")
            audio_path = save_audio_bytes(audio_bytes, ext)
            needs_conversion = ext != "wav"
        else:
            raise HTTPException(
                status_code=415,
                detail=(
                    f"Unsupported Content-Type: {content_type}. "
                    "Use 'application/json' with {{\"url\": \"...\"}}, "
                    "'audio/*' with binary body, or 'multipart/form-data' with file upload."
                ),
            )

        # Convert to 16kHz mono WAV if needed
        if needs_conversion:
            converted_path = await convert_audio_to_wav(audio_path)
            # Clean up original if conversion produced a new file
            if converted_path != audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
            audio_path = converted_path

        # Compute metadata
        sha256 = compute_sha256(audio_path)
        duration = get_audio_duration(audio_path)

        # Run transcription with concurrency control
        async with _transcription_semaphore:
            whisper_output, request_id = await transcribe_audio(
                audio_path=audio_path,
                model=model,
                language=language,
                translate=translate,
                diarize=diarize,
                detect_language=detect_language,
                prompt=prompt,
                start_ms=start,
                duration_ms=process_duration,
                response_format=response_format,
            )

        # Handle subtitle exports directly
        if response_format in ("srt", "vtt"):
            media_type = "text/vtt" if response_format == "vtt" else "text/plain"
            return PlainTextResponse(content=whisper_output, media_type=media_type)

        # Transform to Deepgram-style response
        response = parse_whisper_json_to_deepgram(
            whisper_json=whisper_output,
            request_id=request_id,
            model=model,
            audio_duration=duration,
            include_utterances=utterances,
            sha256=sha256,
        )

        return response

    finally:
        # Cleanup audio file
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except OSError:
                pass


# ═══════════════════════════════════════════════════════════════════════
# LIVE STREAMING AUDIO — WS /v1/listen
# ═══════════════════════════════════════════════════════════════════════

# Minimum audio size for whisper-cli to produce output (0.5s of 16kHz 16-bit mono)
MIN_AUDIO_BYTES = int(STREAM_SAMPLE_RATE * STREAM_SAMPLE_WIDTH * 0.5)


def _fmt_ts(seconds: float) -> str:
    """Format a duration in seconds as `mm:ss.mmm` for human-friendly logs."""
    try:
        s = max(float(seconds), 0.0)
    except (TypeError, ValueError):
        return "00:00.000"
    minutes = int(s // 60)
    rem = s - minutes * 60
    return f"{minutes:02d}:{rem:06.3f}"


def _fmt_range(start: float, duration: float) -> str:
    """Format `[mm:ss.mmm → mm:ss.mmm]` for a transcript window."""
    try:
        s = float(start)
        d = float(duration)
    except (TypeError, ValueError):
        return "[00:00.000 → 00:00.000]"
    return f"[{_fmt_ts(s)} → {_fmt_ts(s + d)}]"


@router.websocket("")
async def listen_streaming(
    websocket: WebSocket,
    model: str = Query("tiny.en"),
    language: str = Query("en"),
    translate: bool = Query(False),
    diarize: bool = Query(False),
    detect_language: bool = Query(False),
    utterances: bool = Query(False),
    encoding: str = Query("linear16"),
    sample_rate: int = Query(STREAM_SAMPLE_RATE),
    # Optional token query param
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Live streaming audio transcription via WebSocket.

    Buffers incoming PCM audio data (16kHz, 16-bit, mono) and transcribes
    in chunks using whisper-cli. Returns Deepgram-compatible streaming results.
    """
    # 1. Extract token from Query, Authorization header, or subprotocols
    auth_token = extract_ws_api_key(websocket, token)

    if not auth_token:
        await websocket.close(
            code=4001,
            reason="Missing API token. Send '?token=...' query or 'Authorization: Token ...' header."
        )
        return

    # 2. Validate against DB
    record = db.query(ApiKey).filter(ApiKey.token == auth_token).first()
    if not record:
        await websocket.close(code=4001, reason="Invalid or revoked API key")
        return

    if model not in model_names:
        await websocket.close(code=4002, reason="Unknown model")
        return

    accepted_subprotocol = select_ws_subprotocol(websocket)
    await websocket.accept(subprotocol=accepted_subprotocol)
    if accepted_subprotocol:
        logger.info(f"[WS] Negotiated subprotocol: {accepted_subprotocol}")

    request_id = str(uuid.uuid4())
    requested_encoding = (encoding or "linear16").strip().lower()
    if requested_encoding != "auto" and requested_encoding not in PCM_STREAM_ENCODINGS and requested_encoding not in STREAM_CONTAINER_ENCODINGS:
        await websocket.close(
            code=4002,
            reason=(
                "Unsupported stream encoding. Use one of: "
                "linear16, pcm16, wav, webm, ogg, opus, mp3, flac, mp4, m4a, auto"
            ),
        )
        return

    if sample_rate <= 0:
        await websocket.close(code=4002, reason="sample_rate must be a positive integer")
        return

    audio_buffer = bytearray()
    # For container streams (webm/ogg/opus/mp4) we cannot decode arbitrary
    # mid-stream slices in isolation: clusters/pages/boxes only make sense
    # relative to the stream start. So we accumulate the full container stream
    # and re-decode it from the beginning on every window. To keep memory and
    # CPU bounded for long sessions, we cap the cumulative buffer at
    # CONTAINER_BUFFER_MAX_SECONDS / CONTAINER_BUFFER_MAX_BYTES.
    container_buffer = bytearray()
    container_format: Optional[str] = None
    # `committed_audio_seconds` marks the boundary up to which we have
    # already emitted a finalized (is_final=True) transcript for the client.
    # Each window we promote any whisper segment that ends before
    # (full_duration - STABILITY_LAG_SECONDS) into a finalized message,
    # advancing this watermark. The remaining tail is sent as interim
    # (is_final=False) and the client should replace its interim each window.
    committed_audio_seconds = 0.0
    chunk_start_time = 0.0
    total_duration = 0.0
    chunks_processed = 0
    is_container_stream = False
    last_container_process_ts = 0.0

    chunk_duration_s = max(settings.STREAM_CHUNK_DURATION_MS / 1000.0, 0.05)
    # PCM uses a byte-count threshold (raw size is predictable); container
    # streams use a wall-clock cadence (compressed bitrate is unknown).
    buffer_threshold = int(
        sample_rate * STREAM_SAMPLE_WIDTH * STREAM_CHANNELS * chunk_duration_s
    )
    CONTAINER_BUFFER_MAX_SECONDS = 60.0
    CONTAINER_BUFFER_MAX_BYTES = 8 * 1024 * 1024

    logger.info(
        f"[WS:{request_id}] Session started. "
        f"model={model}, buffer_threshold={buffer_threshold} bytes ({chunk_duration_s}s), "
        f"min_audio={MIN_AUDIO_BYTES} bytes, encoding={requested_encoding}, sample_rate={sample_rate}"
    )

    # 3. Send initial metadata (Deepgram SDK expects this on connect)
    try:
        open_message = {
            "type": "Metadata",
            "request_id": request_id,
            "model_info": {
                model: {
                    "name": f"whisper-{model}",
                    "version": "ggml-v1",
                    "arch": "whisper",
                }
            },
            "channels": 1,
            "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        }
        await websocket.send_json(open_message)
        logger.info(f"[WS:{request_id}] Sent initial Metadata message")
    except Exception as e:
        logger.error(f"[WS:{request_id}] Failed to send Metadata: {e}")
        return

    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive(), timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.debug(f"[WS:{request_id}] Timeout, no data received for 30s")
                continue

            if "text" in data:
                # Handle control messages
                text_data = data["text"]
                logger.info(f"[WS:{request_id}] Received text message: {text_data[:200]}")
                try:
                    msg = json.loads(text_data)
                    msg_type = msg.get("type", "")

                    if msg_type == "CloseStream":
                        pcm_left = len(audio_buffer)
                        ctnr_left = len(container_buffer)
                        logger.info(
                            f"[WS:{request_id}] CloseStream received. "
                            f"PCM buffer: {pcm_left} bytes, container buffer: {ctnr_left} bytes"
                        )
                        if is_container_stream and ctnr_left > 0:
                            window = await _process_container_window_safe(
                                bytes(container_buffer),
                                container_format or "webm",
                                request_id, model, language,
                                translate, diarize, detect_language,
                                committed_audio_seconds,
                                is_final=True, speech_final=True,
                            )
                            err = window.get("error")
                            if err:
                                for k in ("_full_duration", "_new_committed", "_final_msg", "_interim_msg"):
                                    window.pop(k, None)
                                await websocket.send_json(window)
                            else:
                                final_msg = window.pop("_final_msg", None)
                                # On close, the entire remaining tail is final.
                                if final_msg is not None:
                                    ftxt = (
                                        final_msg.get("channel", {})
                                                 .get("alternatives", [{}])[0]
                                                 .get("transcript", "")
                                    )
                                    logger.info(
                                        f"[WS:{request_id}] [FINAL-close] "
                                        f"{_fmt_range(final_msg.get('start', 0), final_msg.get('duration', 0))} "
                                        f"chars={len(ftxt)}"
                                    )
                                    final_msg["speech_final"] = True
                                    await websocket.send_json(final_msg)
                                    committed_audio_seconds = float(
                                        window.get("_new_committed", committed_audio_seconds)
                                    )
                            chunks_processed += 1
                        elif (not is_container_stream) and pcm_left > 0:
                            result = await _process_stream_chunk_safe(
                                bytes(audio_buffer), request_id, model, language,
                                translate, diarize, detect_language,
                                chunk_start_time, requested_encoding, sample_rate,
                                is_final=True, speech_final=True,
                            )
                            ptxt = (
                                result.get("channel", {})
                                      .get("alternatives", [{}])[0]
                                      .get("transcript", "")
                            )
                            logger.info(
                                f"[WS:{request_id}] [FINAL-close-PCM] "
                                f"{_fmt_range(result.get('start', 0), result.get('duration', 0))} "
                                f"chars={len(ptxt)}"
                            )
                            await websocket.send_json(result)
                            chunks_processed += 1
                        break

                    elif msg_type == "KeepAlive":
                        logger.debug(f"[WS:{request_id}] KeepAlive received")
                        continue
                    else:
                        logger.info(f"[WS:{request_id}] Unknown text message type: {msg_type}")

                except json.JSONDecodeError:
                    logger.warning(f"[WS:{request_id}] Non-JSON text received: {text_data[:100]}")

            elif "bytes" in data:
                audio_bytes = data["bytes"]

                # Decide PCM vs container path on the FIRST binary frame.
                if not is_container_stream and container_format is None:
                    detected = detect_stream_chunk_format(bytes(audio_bytes[:64]))
                    requested_norm = (requested_encoding or "linear16").strip().lower()
                    treat_as_container = (
                        requested_norm in STREAM_CONTAINER_ENCODINGS
                        or (requested_norm == "auto" and detected in STREAM_CONTAINER_ENCODINGS)
                        or (requested_norm in PCM_STREAM_ENCODINGS and detected in STREAM_CONTAINER_ENCODINGS)
                    )
                    if treat_as_container:
                        is_container_stream = True
                        container_format = (
                            detected if detected in STREAM_CONTAINER_ENCODINGS
                            else (requested_norm if requested_norm in STREAM_CONTAINER_ENCODINGS else "webm")
                        )
                        logger.info(
                            f"[WS:{request_id}] Container stream detected (format={container_format}, "
                            f"requested={requested_norm}). Using cumulative-decode strategy."
                        )

                if is_container_stream:
                    container_buffer.extend(audio_bytes)

                    # Drop oldest bytes if the cumulative buffer exceeds the cap.
                    # When this happens we lose the original header, so we also
                    # have to reset the stream baseline and accept transcript
                    # discontinuity. In practice this only kicks in for very
                    # long sessions (>~60s of compressed audio).
                    if len(container_buffer) > CONTAINER_BUFFER_MAX_BYTES:
                        logger.warning(
                            f"[WS:{request_id}] Container buffer exceeded "
                            f"{CONTAINER_BUFFER_MAX_BYTES} bytes; truncating from front. "
                            f"Long sessions should reconnect periodically."
                        )
                        container_buffer = bytearray(container_buffer[-CONTAINER_BUFFER_MAX_BYTES:])

                    now = asyncio.get_event_loop().time()
                    if (now - last_container_process_ts) >= chunk_duration_s:
                        last_container_process_ts = now

                        chunk_size = len(container_buffer)
                        logger.info(
                            f"[WS:{request_id}] Processing container window #{chunks_processed + 1} "
                            f"(cumulative={chunk_size} bytes, committed_until={_fmt_ts(committed_audio_seconds)}, "
                            f"format={container_format})"
                        )

                        window = await _process_container_window_safe(
                            bytes(container_buffer),
                            container_format or "webm",
                            request_id, model, language,
                            translate, diarize, detect_language,
                            committed_audio_seconds,
                            is_final=False, speech_final=False,
                        )

                        chunks_processed += 1
                        full_duration = float(window.get("_full_duration", 0.0))
                        new_committed = float(
                            window.get("_new_committed", committed_audio_seconds)
                        )
                        if full_duration > CONTAINER_BUFFER_MAX_SECONDS:
                            logger.warning(
                                f"[WS:{request_id}] Cumulative audio exceeded "
                                f"{CONTAINER_BUFFER_MAX_SECONDS}s; client should reconnect for best accuracy."
                            )
                        total_duration = full_duration

                        err = window.get("error")
                        if err:
                            logger.error(
                                f"[WS:{request_id}] Container window #{chunks_processed} error: {err}"
                            )
                            # Forward the error result and continue.
                            for k in ("_full_duration", "_new_committed", "_final_msg", "_interim_msg"):
                                window.pop(k, None)
                            await websocket.send_json(window)
                            continue

                        final_msg = window.pop("_final_msg", None)
                        interim_msg = window.pop("_interim_msg", None)
                        for k in ("_full_duration", "_new_committed"):
                            window.pop(k, None)

                        if final_msg is not None:
                            ftxt = (
                                final_msg.get("channel", {})
                                         .get("alternatives", [{}])[0]
                                         .get("transcript", "")
                            )
                            logger.info(
                                f"[WS:{request_id}] [FINAL] "
                                f"{_fmt_range(final_msg.get('start', 0), final_msg.get('duration', 0))} "
                                f"chars={len(ftxt)}"
                            )
                            await websocket.send_json(final_msg)
                            committed_audio_seconds = new_committed

                        if interim_msg is not None:
                            itxt = (
                                interim_msg.get("channel", {})
                                           .get("alternatives", [{}])[0]
                                           .get("transcript", "")
                            )
                            logger.info(
                                f"[WS:{request_id}] [INTERIM] "
                                f"{_fmt_range(interim_msg.get('start', 0), interim_msg.get('duration', 0))} "
                                f"chars={len(itxt)}"
                            )
                            await websocket.send_json(interim_msg)

                else:
                    # PCM (linear16) path — slice-and-process is safe because raw
                    # PCM has no container framing.
                    audio_buffer.extend(audio_bytes)

                    bytes_per_sec = max(sample_rate * STREAM_SAMPLE_WIDTH * STREAM_CHANNELS, 1)
                    if len(audio_buffer) % 32768 < len(audio_bytes):
                        logger.debug(
                            f"[WS:{request_id}] PCM buffer: {len(audio_buffer)}/{buffer_threshold} bytes "
                            f"({len(audio_buffer) / bytes_per_sec:.1f}s @ {sample_rate}Hz)"
                        )

                    if len(audio_buffer) >= buffer_threshold:
                        chunk_size = len(audio_buffer)
                        logger.info(
                            f"[WS:{request_id}] Processing PCM chunk #{chunks_processed + 1} "
                            f"({chunk_size} bytes)"
                        )

                        chunk_data = bytes(audio_buffer)
                        audio_buffer.clear()

                        result = await _process_stream_chunk_safe(
                            chunk_data, request_id, model, language,
                            translate, diarize, detect_language,
                            chunk_start_time, requested_encoding, sample_rate,
                            is_final=True, speech_final=False,
                        )

                        chunk_duration = float(result.get("duration", 0.0))
                        chunk_start_time += chunk_duration
                        total_duration += chunk_duration
                        chunks_processed += 1

                        ptxt = (
                            result.get("channel", {})
                                  .get("alternatives", [{}])[0]
                                  .get("transcript", "")
                        )
                        err = result.get("error")
                        if err:
                            logger.error(f"[WS:{request_id}] PCM chunk #{chunks_processed} error: {err}")
                        else:
                            logger.info(
                                f"[WS:{request_id}] [PCM-CHUNK #{chunks_processed}] "
                                f"{_fmt_range(result.get('start', 0), chunk_duration)} "
                                f"chars={len(ptxt)}"
                            )

                        await websocket.send_json(result)

            else:
                # Check for WebSocket disconnect frame
                frame_type = data.get("type", "")
                if frame_type == "websocket.disconnect":
                    logger.info(f"[WS:{request_id}] Received disconnect frame (code={data.get('code', '?')})")
                    break
                else:
                    logger.info(f"[WS:{request_id}] Received frame with keys: {list(data.keys())}")

    except WebSocketDisconnect:
        logger.info(f"[WS:{request_id}] Client disconnected")
    except RuntimeError as e:
        # Handle "Cannot call 'receive' once a disconnect message has been received"
        logger.info(f"[WS:{request_id}] Connection closed: {e}")
    except Exception as e:
        logger.error(f"[WS:{request_id}] Unhandled error: {type(e).__name__}: {e}", exc_info=True)
        try:
            error_msg = {
                "type": "Error",
                "message": str(e),
                "request_id": request_id,
            }
            await websocket.send_json(error_msg)
            await websocket.close(code=1011, reason=str(e)[:120])
        except Exception:
            pass
    finally:
        logger.info(
            f"[WS:{request_id}] Session ended. "
            f"chunks_processed={chunks_processed} total_audio={_fmt_ts(total_duration)}"
        )


async def _process_stream_chunk_safe(
    audio_data: bytes,
    request_id: str,
    model: str,
    language: str,
    translate: bool,
    diarize: bool,
    detect_language: bool,
    start_time: float,
    requested_encoding: str,
    sample_rate: int,
    is_final: bool = True,
    speech_final: bool = False,
) -> dict:
    """
    Process a chunk of streaming audio and return a Deepgram-compatible result.

    This is a 'safe' wrapper that never raises — errors are returned as part of
    the result dict so the WebSocket handler can forward them to the client.
    """
    duration = 0.0
    wav_path = None
    source_path = None

    try:
        detected_format = detect_stream_chunk_format(audio_data)
        resolved_encoding = resolve_stream_encoding(requested_encoding, detected_format)

        if resolved_encoding in PCM_STREAM_ENCODINGS:
            min_pcm_bytes = int(sample_rate * STREAM_SAMPLE_WIDTH * STREAM_CHANNELS * 0.5)
            duration = len(audio_data) / max(sample_rate * STREAM_SAMPLE_WIDTH * STREAM_CHANNELS, 1)

            if len(audio_data) < min_pcm_bytes:
                logger.warning(
                    f"[WS:{request_id}] PCM chunk too short ({len(audio_data)} bytes, "
                    f"need {min_pcm_bytes}). Returning empty result."
                )
                return _empty_streaming_result(request_id, model, start_time, duration, is_final, speech_final)

            wav_path = create_wav_from_pcm(audio_data, sample_rate=sample_rate)
            logger.debug(
                f"[WS:{request_id}] Created PCM WAV: {wav_path} "
                f"({os.path.getsize(wav_path)} bytes, sample_rate={sample_rate})"
            )
        else:
            extension = STREAM_CONTAINER_ENCODINGS.get(resolved_encoding)
            if not extension:
                raise ValueError(f"Unsupported resolved encoding: {resolved_encoding}")

            source_path = save_audio_bytes(audio_data, extension=extension)
            wav_path = await convert_audio_to_wav(source_path)
            duration = get_audio_duration(wav_path)
            logger.debug(
                f"[WS:{request_id}] Decoded {resolved_encoding} chunk via ffmpeg "
                f"to WAV: {wav_path} ({duration:.2f}s)"
            )

            if duration < 0.5:
                logger.warning(
                    f"[WS:{request_id}] Decoded chunk too short ({duration:.2f}s). Returning empty result."
                )
                return _empty_streaming_result(request_id, model, start_time, duration, is_final, speech_final)

        # Run whisper-cli
        async with _transcription_semaphore:
            whisper_json, _ = await transcribe_audio(
                audio_path=wav_path,
                model=model,
                language=language,
                translate=translate,
                diarize=diarize,
                detect_language=detect_language,
            )

        logger.debug(f"[WS:{request_id}] Whisper returned. Segments: {len(whisper_json.get('transcription', []))}")

        # Parse the whisper output
        deepgram_response = parse_whisper_json_to_deepgram(
            whisper_json=whisper_json,
            request_id=request_id,
            model=model,
            audio_duration=duration,
        )

        # Extract channel data for streaming format
        channel_data = {}
        if deepgram_response.get("results", {}).get("channels"):
            channel_data = deepgram_response["results"]["channels"][0]

        result = {
            "type": "Results",
            "channel_index": [0, 1],
            "duration": round(duration, 2),
            "start": round(start_time, 2),
            "is_final": is_final,
            "speech_final": speech_final,
            "channel": channel_data,
            "metadata": {
                "request_id": request_id,
                "model_info": deepgram_response.get("metadata", {}).get("model_info", {}),
            },
            "from_finalize": False,
        }

        return result

    except HTTPException as e:
        # whisper-cli failure (model not found, transcription failed, etc.)
        logger.error(f"[WS:{request_id}] Transcription HTTPException: {e.detail}")
        return _error_streaming_result(request_id, model, start_time, duration, str(e.detail), is_final, speech_final)

    except Exception as e:
        logger.error(f"[WS:{request_id}] Unexpected error in chunk processing: {type(e).__name__}: {e}", exc_info=True)
        return _error_streaming_result(request_id, model, start_time, duration, str(e), is_final, speech_final)

    finally:
        # Cleanup temp WAV file
        if wav_path and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except OSError:
                pass
        if source_path and os.path.exists(source_path):
            try:
                os.remove(source_path)
            except OSError:
                pass


def _empty_streaming_result(
    request_id: str, model: str, start_time: float, duration: float,
    is_final: bool, speech_final: bool,
) -> dict:
    """Return a valid but empty streaming result (no speech detected)."""
    return {
        "type": "Results",
        "channel_index": [0, 1],
        "duration": round(duration, 2),
        "start": round(start_time, 2),
        "is_final": is_final,
        "speech_final": speech_final,
        "channel": {
            "alternatives": [
                {
                    "transcript": "",
                    "confidence": 0.0,
                    "words": [],
                }
            ],
        },
        "metadata": {
            "request_id": request_id,
            "model_info": {model: {"name": f"whisper-{model}", "version": "ggml-v1", "arch": "whisper"}},
        },
        "from_finalize": False,
    }


def _error_streaming_result(
    request_id: str, model: str, start_time: float, duration: float,
    error_msg: str, is_final: bool, speech_final: bool,
) -> dict:
    """Return a streaming result that includes an error field."""
    result = _empty_streaming_result(request_id, model, start_time, duration, is_final, speech_final)
    result["error"] = error_msg
    return result


STABILITY_LAG_SECONDS = 3.0


async def _process_container_window_safe(
    cumulative_data: bytes,
    container_format: str,
    request_id: str,
    model: str,
    language: str,
    translate: bool,
    diarize: bool,
    detect_language: bool,
    committed_audio_seconds: float,
    is_final: bool = False,
    speech_final: bool = False,
) -> dict:
    """Decode the entire cumulative container stream and split the result
    into a finalized portion and an interim tail.

    Container formats (webm/ogg/opus/mp4) cannot be sliced mid-stream, so we
    re-decode from start each window. This is bullet-proof: ffmpeg always
    sees a valid stream.

    To avoid the UI clobbering older text, we split each window's output:

      * **Finalized** (is_final=True): segments that ended before
        ``full_duration - STABILITY_LAG_SECONDS``. These are stable; whisper
        is unlikely to revise them on later windows. Emitted with
        ``start=committed_audio_seconds`` and a positive duration so the
        client appends them to its committed transcript.
      * **Interim** (is_final=False): the unfinalized tail covering the most
        recent audio. The client should *replace* its current interim with
        this each window.

    On ``speech_final=True`` (CloseStream), the entire remaining transcript
    becomes finalized — no interim is returned.
    """
    full_duration = 0.0
    wav_path = None
    source_path = None

    try:
        extension = STREAM_CONTAINER_ENCODINGS.get(container_format, "webm")
        source_path = save_audio_bytes(cumulative_data, extension=extension)
        wav_path = await convert_audio_to_wav(source_path)
        full_duration = get_audio_duration(wav_path)

        delta_duration = max(full_duration - committed_audio_seconds, 0.0)
        min_full = 1.0
        min_delta = 1.0 if not speech_final else 0.1
        if full_duration < min_full or delta_duration < min_delta:
            logger.info(
                f"[WS:{request_id}] Skipping window: audio={_fmt_ts(full_duration)} "
                f"(min={min_full}s), new={_fmt_ts(delta_duration)} (min={min_delta}s)"
            )
            return {
                "_full_duration": full_duration,
                "_new_committed": committed_audio_seconds,
                "_final_msg": None,
                "_interim_msg": None,
            }

        async with _transcription_semaphore:
            whisper_json, _ = await transcribe_audio(
                audio_path=wav_path,
                model=model,
                language=language,
                translate=translate,
                diarize=diarize,
                detect_language=detect_language,
            )

        deepgram_response = parse_whisper_json_to_deepgram(
            whisper_json=whisper_json,
            request_id=request_id,
            model=model,
            audio_duration=full_duration,
        )

        channel_data = {}
        if deepgram_response.get("results", {}).get("channels"):
            channel_data = deepgram_response["results"]["channels"][0]

        alts = channel_data.get("alternatives") or [{}]
        first_alt = alts[0] if alts else {}
        confidence = first_alt.get("confidence", 0.0)
        all_words = first_alt.get("words") or []
        full_transcript = (first_alt.get("transcript") or "").strip()
        model_info_block = deepgram_response.get("metadata", {}).get("model_info", {})

        # Split segments into finalized vs interim using STABILITY_LAG_SECONDS.
        # On speech_final (close), everything becomes finalized.
        committed_ms = int(committed_audio_seconds * 1000)
        if speech_final:
            stable_cutoff_ms = int(full_duration * 1000) + 1
        else:
            stable_cutoff_ms = max(
                int((full_duration - STABILITY_LAG_SECONDS) * 1000),
                committed_ms,
            )

        segments = whisper_json.get("transcription", []) or []
        final_texts = []
        interim_texts = []
        final_end_ms = committed_ms
        for seg in segments:
            seg_offsets = seg.get("offsets", {}) or {}
            seg_start_ms = int(seg_offsets.get("from", 0))
            seg_end_ms = int(seg_offsets.get("to", 0))
            seg_text = (seg.get("text") or "").strip()
            if not seg_text:
                continue
            # Skip anything already committed (segment ends at/before commit).
            if seg_end_ms <= committed_ms:
                continue
            if seg_end_ms <= stable_cutoff_ms:
                final_texts.append(seg_text)
                if seg_end_ms > final_end_ms:
                    final_end_ms = seg_end_ms
            else:
                interim_texts.append(seg_text)

        new_committed_seconds = max(
            min(final_end_ms / 1000.0, full_duration),
            committed_audio_seconds,
        )

        # When segment offsets are missing (e.g. very short clips), fall back
        # to emitting everything as interim so the client still sees output.
        if not segments and full_transcript and not speech_final:
            interim_texts.append(full_transcript)

        final_text = " ".join(final_texts).strip()
        interim_text = " ".join(interim_texts).strip()

        final_msg = None
        if final_text:
            final_msg = {
                "type": "Results",
                "channel_index": [0, 1],
                "duration": round(new_committed_seconds - committed_audio_seconds, 2),
                "start": round(committed_audio_seconds, 2),
                "is_final": True,
                "speech_final": bool(speech_final),
                "channel": {
                    "alternatives": [{
                        "transcript": final_text,
                        "confidence": confidence,
                        "words": [
                            w for w in all_words
                            if committed_audio_seconds < float(w.get("end", 0.0)) <= new_committed_seconds
                        ],
                    }],
                },
                "metadata": {
                    "request_id": request_id,
                    "model_info": model_info_block,
                },
                "from_finalize": False,
            }

        interim_msg = None
        if interim_text and not speech_final:
            interim_msg = {
                "type": "Results",
                "channel_index": [0, 1],
                "duration": round(full_duration - new_committed_seconds, 2),
                "start": round(new_committed_seconds, 2),
                "is_final": False,
                "speech_final": False,
                "channel": {
                    "alternatives": [{
                        "transcript": interim_text,
                        "confidence": confidence,
                        "words": [
                            w for w in all_words
                            if float(w.get("end", 0.0)) > new_committed_seconds
                        ],
                    }],
                },
                "metadata": {
                    "request_id": request_id,
                    "model_info": model_info_block,
                },
                "from_finalize": False,
            }

        return {
            "_full_duration": full_duration,
            "_new_committed": new_committed_seconds,
            "_final_msg": final_msg,
            "_interim_msg": interim_msg,
        }

    except HTTPException as e:
        logger.error(f"[WS:{request_id}] Container window HTTPException: {e.detail}")
        err = _error_streaming_result(
            request_id, model, committed_audio_seconds,
            max(full_duration - committed_audio_seconds, 0.0),
            str(e.detail), is_final, speech_final,
        )
        err["_full_duration"] = full_duration
        err["_new_committed"] = committed_audio_seconds
        err["_final_msg"] = None
        err["_interim_msg"] = None
        return err
    except Exception as e:
        logger.error(
            f"[WS:{request_id}] Unexpected error in container window: {type(e).__name__}: {e}",
            exc_info=True,
        )
        err = _error_streaming_result(
            request_id, model, committed_audio_seconds,
            max(full_duration - committed_audio_seconds, 0.0),
            str(e), is_final, speech_final,
        )
        err["_full_duration"] = full_duration
        err["_new_committed"] = committed_audio_seconds
        err["_final_msg"] = None
        err["_interim_msg"] = None
        return err
    finally:
        if wav_path and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except OSError:
                pass
        if source_path and os.path.exists(source_path):
            try:
                os.remove(source_path)
            except OSError:
                pass
