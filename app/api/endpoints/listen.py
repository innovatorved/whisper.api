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


@router.websocket("")
async def listen_streaming(
    websocket: WebSocket,
    model: str = Query("tiny.en"),
    language: str = Query("en"),
    translate: bool = Query(False),
    diarize: bool = Query(False),
    detect_language: bool = Query(False),
    utterances: bool = Query(False),
    # Optional token query param
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Live streaming audio transcription via WebSocket.

    Buffers incoming PCM audio data (16kHz, 16-bit, mono) and transcribes
    in chunks using whisper-cli. Returns Deepgram-compatible streaming results.
    """
    # 1. Extract token from Query or Headers
    auth_token = token
    if not auth_token:
        # Check Authorization header (Deepgram SDK style)
        auth_header = websocket.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("token "):
            auth_token = auth_header.split(" ", 1)[1].strip()
        elif auth_header and auth_header.lower().startswith("bearer "):
            # Supporting Bearer for compatibility
            auth_token = auth_header.split(" ", 1)[1].strip()

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

    await websocket.accept()

    request_id = str(uuid.uuid4())
    audio_buffer = bytearray()
    chunk_start_time = 0.0
    total_duration = 0.0
    chunks_processed = 0

    # Calculate buffer threshold (bytes for N seconds of 16kHz 16-bit mono)
    chunk_duration_s = settings.STREAM_CHUNK_DURATION_MS / 1000.0
    buffer_threshold = int(STREAM_SAMPLE_RATE * STREAM_SAMPLE_WIDTH * STREAM_CHANNELS * chunk_duration_s)

    logger.info(
        f"[WS:{request_id}] Session started. "
        f"model={model}, buffer_threshold={buffer_threshold} bytes ({chunk_duration_s}s), "
        f"min_audio={MIN_AUDIO_BYTES} bytes"
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
            "created": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
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
                        logger.info(f"[WS:{request_id}] CloseStream received. Buffer: {len(audio_buffer)} bytes")
                        # Process any remaining buffer before closing
                        if len(audio_buffer) >= MIN_AUDIO_BYTES:
                            result = await _process_stream_chunk_safe(
                                audio_buffer, request_id, model, language,
                                translate, diarize, detect_language,
                                chunk_start_time, is_final=True, speech_final=True,
                            )
                            await websocket.send_json(result)
                            chunks_processed += 1
                        else:
                            logger.info(
                                f"[WS:{request_id}] Remaining buffer too small "
                                f"({len(audio_buffer)} < {MIN_AUDIO_BYTES} bytes), skipping"
                            )
                        break

                    elif msg_type == "KeepAlive":
                        logger.debug(f"[WS:{request_id}] KeepAlive received")
                        continue
                    else:
                        logger.info(f"[WS:{request_id}] Unknown text message type: {msg_type}")

                except json.JSONDecodeError:
                    logger.warning(f"[WS:{request_id}] Non-JSON text received: {text_data[:100]}")

            elif "bytes" in data:
                # Audio data received
                audio_bytes = data["bytes"]
                audio_buffer.extend(audio_bytes)

                # Visual feedback
                print(".", end="", flush=True)

                # Log every ~1 second of incoming audio
                if len(audio_buffer) % 32768 < len(audio_bytes):
                    logger.info(
                        f"[WS:{request_id}] Audio buffer: {len(audio_buffer)}/{buffer_threshold} bytes "
                        f"({len(audio_buffer) / (STREAM_SAMPLE_RATE * STREAM_SAMPLE_WIDTH):.1f}s)"
                    )

                # Process when buffer reaches threshold
                if len(audio_buffer) >= buffer_threshold:
                    chunk_size = len(audio_buffer)
                    print(f"\n[WS:{request_id}] Buffer full ({chunk_size} bytes). Transcribing chunk #{chunks_processed + 1}...")
                    logger.info(f"[WS:{request_id}] Processing chunk #{chunks_processed + 1} ({chunk_size} bytes)")

                    chunk_data = bytes(audio_buffer)
                    audio_buffer.clear()

                    result = await _process_stream_chunk_safe(
                        chunk_data, request_id, model, language,
                        translate, diarize, detect_language,
                        chunk_start_time, is_final=True, speech_final=False,
                    )

                    chunk_duration = len(chunk_data) / (STREAM_SAMPLE_RATE * STREAM_SAMPLE_WIDTH)
                    chunk_start_time += chunk_duration
                    total_duration += chunk_duration
                    chunks_processed += 1

                    # Log the result
                    transcript = result.get("channel", {}).get("alternatives", [{}])[0].get("transcript", "")
                    err = result.get("error")
                    if err:
                        print(f"[WS:{request_id}] [WARN] Chunk error: {err}")
                        logger.error(f"[WS:{request_id}] Chunk #{chunks_processed} error: {err}")
                    else:
                        print(f"[WS:{request_id}] [OK] Result: '{transcript}'")
                        logger.info(f"[WS:{request_id}] Chunk #{chunks_processed} transcript: '{transcript}'")

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
            f"Chunks processed: {chunks_processed}, Total duration: {total_duration:.2f}s"
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
    is_final: bool = True,
    speech_final: bool = False,
) -> dict:
    """
    Process a chunk of streaming audio and return a Deepgram-compatible result.

    This is a 'safe' wrapper that never raises — errors are returned as part of
    the result dict so the WebSocket handler can forward them to the client.
    """
    duration = len(audio_data) / (STREAM_SAMPLE_RATE * STREAM_SAMPLE_WIDTH)
    wav_path = None

    try:
        # Validate minimum audio size
        if len(audio_data) < MIN_AUDIO_BYTES:
            logger.warning(
                f"[WS:{request_id}] Audio chunk too short ({len(audio_data)} bytes, "
                f"need {MIN_AUDIO_BYTES}). Returning empty result."
            )
            return _empty_streaming_result(request_id, model, start_time, duration, is_final, speech_final)

        # Save PCM data as WAV
        wav_path = create_wav_from_pcm(audio_data)
        logger.info(f"[WS:{request_id}] Created temp WAV: {wav_path} ({os.path.getsize(wav_path)} bytes)")

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

        logger.info(f"[WS:{request_id}] Whisper returned. Segments: {len(whisper_json.get('transcription', []))}")

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
