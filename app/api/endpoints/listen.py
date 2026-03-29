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

from app.api.models.listen import (
    ListenResponse,
    StreamingResult,
    URLRequest,
)
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
            if not url:
                raise HTTPException(
                    status_code=400,
                    detail="Request body must contain 'url' field",
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
            # Map content type to extension
            ext_map = {
                "audio/wav": "wav", "audio/x-wav": "wav", "audio/wave": "wav",
                "audio/mp3": "mp3", "audio/mpeg": "mp3",
                "audio/ogg": "ogg", "audio/flac": "flac",
                "audio/webm": "webm", "audio/mp4": "mp4",
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


@router.websocket("")
async def listen_streaming(
    websocket: WebSocket,
    model: str = Query("tiny.en"),
    language: str = Query("en"),
    translate: bool = Query(False),
    diarize: bool = Query(False),
    detect_language: bool = Query(False),
    utterances: bool = Query(False),
    # Auth via query param for WebSocket
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Live streaming audio transcription via WebSocket.

    **Client sends:** Raw audio bytes (16kHz, 16-bit, mono PCM)
    **Server sends:** JSON StreamingResult messages

    **Control messages (JSON from client):**
    - `{"type": "KeepAlive"}` — Keep connection alive without sending audio
    - `{"type": "CloseStream"}` — Gracefully close the connection
    """
    # Validate auth
    if not token:
        await websocket.close(code=4001, reason="Missing token query parameter. Send ?token=...")
        return
        
    record = db.query(ApiKey).filter(ApiKey.token == token).first()
    if not record:
        await websocket.close(code=4001, reason="Invalid API key")
        return

    await websocket.accept()

    request_id = str(uuid.uuid4())
    audio_buffer = bytearray()
    chunk_start_time = 0.0
    total_duration = 0.0

    # Calculate buffer threshold (bytes for N seconds of 16kHz 16-bit mono)
    chunk_duration_s = settings.STREAM_CHUNK_DURATION_MS / 1000.0
    buffer_threshold = int(STREAM_SAMPLE_RATE * STREAM_SAMPLE_WIDTH * STREAM_CHANNELS * chunk_duration_s)

    logger.info(f"Streaming session {request_id} started. Buffer threshold: {buffer_threshold} bytes")

    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive(), timeout=30.0
                )
            except asyncio.TimeoutError:
                # Send keepalive response
                continue

            if "text" in data:
                # Handle control messages
                try:
                    msg = json.loads(data["text"])
                    msg_type = msg.get("type", "")

                    if msg_type == "CloseStream":
                        # Process any remaining buffer before closing
                        if len(audio_buffer) > STREAM_SAMPLE_RATE:  # >0.5s of audio
                            result = await _process_stream_chunk(
                                audio_buffer, request_id, model, language,
                                translate, diarize, detect_language,
                                chunk_start_time, is_final=True, speech_final=True,
                            )
                            await websocket.send_json(result)
                        break

                    elif msg_type == "KeepAlive":
                        continue

                except json.JSONDecodeError:
                    pass  # Not JSON, ignore

            elif "bytes" in data:
                # Audio data
                audio_buffer.extend(data["bytes"])

                # Process when buffer reaches threshold
                if len(audio_buffer) >= buffer_threshold:
                    chunk_data = bytes(audio_buffer)
                    audio_buffer.clear()

                    result = await _process_stream_chunk(
                        chunk_data, request_id, model, language,
                        translate, diarize, detect_language,
                        chunk_start_time, is_final=True, speech_final=False,
                    )

                    chunk_duration = len(chunk_data) / (STREAM_SAMPLE_RATE * STREAM_SAMPLE_WIDTH)
                    chunk_start_time += chunk_duration
                    total_duration += chunk_duration

                    await websocket.send_json(result)

    except WebSocketDisconnect:
        logger.info(f"Streaming session {request_id} disconnected")
    except Exception as e:
        logger.error(f"Streaming error in session {request_id}: {e}")
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception:
            pass
    finally:
        logger.info(f"Streaming session {request_id} ended. Total duration: {total_duration:.2f}s")


async def _process_stream_chunk(
    audio_data: bytes,
    request_id: str,
    model: str,
    language: str,
    translate: bool,
    diarize: bool,
    detect_language: bool,
    start_time: float,
    is_final: bool = True,
    speech_final: bool = False,
) -> dict:
    """Process a chunk of streaming audio and return a StreamingResult."""

    # Save PCM data as WAV
    wav_path = create_wav_from_pcm(audio_data)

    try:
        duration = len(audio_data) / (STREAM_SAMPLE_RATE * STREAM_SAMPLE_WIDTH)

        async with _transcription_semaphore:
            whisper_json, _ = await transcribe_audio(
                audio_path=wav_path,
                model=model,
                language=language,
                translate=translate,
                diarize=diarize,
                detect_language=detect_language,
            )

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

    finally:
        # Cleanup temp WAV file
        if os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except OSError:
                pass
