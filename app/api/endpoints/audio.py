"""
OpenAI-Compatible Audio Endpoints.

POST /v1/audio/transcriptions → Transcribe audio into the input language
POST /v1/audio/translations   → Translate audio into English

Compatible with the official OpenAI Python/JS SDKs (`client.audio.transcriptions.create`
and `client.audio.translations.create`).
"""

import asyncio
import os
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.endpoints.listen import _transcription_semaphore
from app.core.config import settings
from app.core.database import get_db
from app.core.models.ApiKey import ApiKey
from app.utils.constant import MODEL_ALIASES, model_names
from app.utils.utils import (
    convert_audio_to_wav,
    get_audio_duration,
    parse_whisper_json_to_openai,
    resolve_model_name,
    save_audio_bytes,
    transcribe_audio,
)

router = APIRouter()

VALID_OPENAI_RESPONSE_FORMATS = {"json", "text", "srt", "verbose_json", "vtt"}


def extract_openai_api_key(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> str:
    """
    Extract and validate API key from the Authorization header.
    Supports both OpenAI-standard `Authorization: Bearer <key>` and
    Deepgram-style `Authorization: Token <key>`.
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header. Use: Authorization: Bearer <your_api_key>",
        )
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() not in ("bearer", "token"):
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization format. Use: Authorization: Bearer <your_api_key>",
        )
    token = parts[1].strip()
    record = db.query(ApiKey).filter(ApiKey.token == token).first()
    if not record:
        raise HTTPException(
            status_code=401,
            detail="Invalid or revoked API key",
        )
    return token


async def _handle_openai_audio_request(
    request: Request,
    file: UploadFile,
    model: str,
    language: Optional[str],
    prompt: Optional[str],
    response_format: str,
    temperature: Optional[float],
    timestamp_granularities: Optional[List[str]],
    vad: bool,
    translate: bool,
):
    fmt = (response_format or "json").strip().lower()
    if fmt not in VALID_OPENAI_RESPONSE_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported response_format '{response_format}'. Supported: {', '.join(sorted(VALID_OPENAI_RESPONSE_FORMATS))}",
        )

    canonical_model = resolve_model_name(model or "whisper-1")
    if canonical_model not in model_names:
        available = ", ".join(list(model_names.keys()) + list(MODEL_ALIASES.keys()))
        raise HTTPException(
            status_code=400,
            detail=f"Unknown model '{model}'. Available: {available}",
        )

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty")
    if len(audio_bytes) > settings.MAX_AUDIO_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Audio exceeds maximum upload size",
        )

    # Also support OpenAI SDK form field `timestamp_granularities[]`
    granularities: List[str] = list(timestamp_granularities or [])
    try:
        form = await request.form()
        if "timestamp_granularities[]" in form:
            granularities.extend(
                [str(v) for v in form.getlist("timestamp_granularities[]")]
            )
    except Exception:
        pass

    filename = getattr(file, "filename", "upload.wav") or "upload.wav"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "wav"
    audio_path = save_audio_bytes(audio_bytes, ext)
    needs_conversion = ext != "wav"

    try:
        if needs_conversion:
            converted_path = await convert_audio_to_wav(audio_path)
            if converted_path != audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
            audio_path = converted_path

        duration = get_audio_duration(audio_path)
        whisper_fmt = fmt if fmt in ("srt", "vtt") else "json"
        detect_lang = language is None or language.strip() == "" or language == "auto"

        async with _transcription_semaphore:
            whisper_output, _ = await transcribe_audio(
                audio_path=audio_path,
                model=canonical_model,
                language=language or "en",
                translate=translate,
                detect_language=detect_lang,
                prompt=prompt,
                response_format=whisper_fmt,
                temperature=temperature,
                vad=vad,
            )

        if fmt in ("srt", "vtt"):
            media_type = "text/vtt" if fmt == "vtt" else "text/plain"
            return PlainTextResponse(content=str(whisper_output), media_type=media_type)

        openai_result = parse_whisper_json_to_openai(
            whisper_json=whisper_output,
            response_format=fmt,
            audio_duration=duration,
            translate=translate,
            timestamp_granularities=granularities or ["segment"],
        )

        if fmt == "text":
            return PlainTextResponse(content=str(openai_result), media_type="text/plain")

        return openai_result
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except OSError:
                pass


@router.post(
    "/transcriptions",
    summary="Create Transcription (OpenAI-Compatible)",
    description="Transcribes audio into the input language. Drop-in compatible with OpenAI's POST /v1/audio/transcriptions.",
    tags=["openai-audio"],
)
async def create_transcription(
    request: Request,
    file: UploadFile = File(..., description="The audio file object to transcribe"),
    model: str = Form("whisper-1", description="ID of the model to use (e.g. 'whisper-1', 'tiny.en', 'large-v3-turbo.q5')"),
    language: Optional[str] = Form(None, description="The language of the input audio in ISO-639-1 format"),
    prompt: Optional[str] = Form(None, description="Optional text to guide the model's style"),
    response_format: str = Form("json", description="Format of the transcript output: json, text, srt, verbose_json, or vtt"),
    temperature: Optional[float] = Form(None, ge=0.0, le=1.0, description="Sampling temperature between 0 and 1"),
    timestamp_granularities: Optional[List[str]] = Form(None, description="Timestamp granularities (word, segment) for verbose_json"),
    vad: bool = Form(False, description="Enable Voice Activity Detection (Silero VAD)"),
    api_key: str = Depends(extract_openai_api_key),
):
    return await _handle_openai_audio_request(
        request=request,
        file=file,
        model=model,
        language=language,
        prompt=prompt,
        response_format=response_format,
        temperature=temperature,
        timestamp_granularities=timestamp_granularities,
        vad=vad,
        translate=False,
    )


@router.post(
    "/translations",
    summary="Create Translation (OpenAI-Compatible)",
    description="Translates audio into English. Drop-in compatible with OpenAI's POST /v1/audio/translations.",
    tags=["openai-audio"],
)
async def create_translation(
    request: Request,
    file: UploadFile = File(..., description="The audio file object to translate into English"),
    model: str = Form("whisper-1", description="ID of the model to use (e.g. 'whisper-1', 'tiny.en', 'large-v3-turbo.q5')"),
    prompt: Optional[str] = Form(None, description="Optional text to guide the model's style in English"),
    response_format: str = Form("json", description="Format of the transcript output: json, text, srt, verbose_json, or vtt"),
    temperature: Optional[float] = Form(None, ge=0.0, le=1.0, description="Sampling temperature between 0 and 1"),
    vad: bool = Form(False, description="Enable Voice Activity Detection (Silero VAD)"),
    api_key: str = Depends(extract_openai_api_key),
):
    return await _handle_openai_audio_request(
        request=request,
        file=file,
        model=model,
        language="auto",
        prompt=prompt,
        response_format=response_format,
        temperature=temperature,
        timestamp_granularities=["segment"],
        vad=vad,
        translate=True,
    )
