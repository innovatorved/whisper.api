"""
Core transcription and audio utility functions for the Whisper Speech-to-Text API.

Uses whisper-cli with JSON output (-oj) to produce word-level timestamps,
then transforms the output into Deepgram-compatible response structures.
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import struct
import subprocess
import tempfile
import urllib
import uuid
import wave
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import gdown
import httpx
from fastapi import HTTPException
from tqdm import tqdm

from .constant import (
    STREAM_CHANNELS,
    STREAM_SAMPLE_RATE,
    STREAM_SAMPLE_WIDTH,
    model_info,
    model_names,
    supported_languages,
)

logger = logging.getLogger(__name__)

# ─── Paths ────────────────────────────────────────────────────────────

WHISPER_BINARY = os.environ.get("WHISPER_BINARY_PATH", "./binary/whisper-cli")
MODELS_DIR = os.environ.get("MODELS_DIR", "./models")
AUDIO_DIR = "audio"
TRANSCRIBE_DIR = "transcribe"

# Ensure directories exist
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(TRANSCRIBE_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════
# TRANSCRIPTION ENGINE
# ═══════════════════════════════════════════════════════════════════════


async def transcribe_audio(
    audio_path: str,
    model: str = "tiny.en",
    language: str = "en",
    translate: bool = False,
    diarize: bool = False,
    detect_language: bool = False,
    threads: int = 4,
    prompt: Optional[str] = None,
    start_ms: Optional[int] = None,
    duration_ms: Optional[int] = None,
    response_format: str = "json"
) -> Tuple[Union[Dict[str, Any], str], str]:
    """
    Transcribe an audio file using whisper-cli.

    Returns the parsed JSON dictionary OR raw subtitle text (SRT/VTT).
    """
    model_file = get_model_filename(model)
    model_path = os.path.join(MODELS_DIR, model_file)

    if not os.path.exists(model_path):
        raise HTTPException(
            status_code=400,
            detail=f"Model '{model}' not found at {model_path}",
        )

    # Generate unique output base path
    request_id = str(uuid.uuid4())
    output_base = os.path.join(TRANSCRIBE_DIR, request_id)

    # Build whisper-cli command
    cmd_parts = [
        WHISPER_BINARY,
        "-m", model_path,
        "-f", audio_path,
        "-t", str(threads),
        "-of", output_base,             # output file base
    ]

    # Output format
    if response_format == "srt":
        cmd_parts.append("-osrt")
        output_ext = ".srt"
    elif response_format == "vtt":
        cmd_parts.append("-ovtt")
        output_ext = ".vtt"
    else:
        cmd_parts.append("-oj")
        output_ext = ".json"
        
    # Language
    if detect_language:
        cmd_parts.extend(["-dl"])       # detect language
    else:
        whisper_lang = supported_languages.get(language, "en")
        cmd_parts.extend(["-l", whisper_lang])

    # Translate to English
    if translate:
        cmd_parts.append("-tr")

    # Diarize (stereo audio)
    if diarize:
        cmd_parts.append("-di")
        
    # Advanced features
    if prompt:
        cmd_parts.extend(["--prompt", f"\"{prompt}\""])
    if start_ms is not None:
        cmd_parts.extend(["-ot", str(start_ms)])
    if duration_ms is not None:
        cmd_parts.extend(["-d", str(duration_ms)])

    command = " ".join(cmd_parts)
    print(f"\n[AI EXECUTE] {command}")
    logger.info(f"[{request_id}] Executing whisper-cli: {command}")
    
    start_time_exec = asyncio.get_event_loop().time()
    stdout, stderr, code = await execute_command(command)
    end_time_exec = asyncio.get_event_loop().time()
    
    duration = end_time_exec - start_time_exec
    print(f"[AI FINISHED] Task {request_id} in {duration:.2f}s with code {code}.")
    logger.info(f"[{request_id}] Command finished in {duration:.2f}s with code {code}.")

    # Read output
    out_path = f"{output_base}{output_ext}"
    if not os.path.exists(out_path):
        print(f"[AI ERROR] Output file missing for task {request_id}!")
        logger.error(f"[{request_id}] Output file {out_path} missing. stdout: '{stdout}', stderr: '{stderr}'")
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: output missing. Error: {stderr}",
        )

    if response_format in ("srt", "vtt"):
        with open(out_path, "r", encoding="utf-8") as f:
            whisper_output = f.read()
    else:
        with open(out_path, "r", encoding="utf-8") as f:
            whisper_output = json.load(f)
            logger.info(f"[{request_id}] Parsed Whisper JSON output successfully.")

    # Cleanup output files
    _cleanup_files(output_base)

    return whisper_output, request_id


def parse_whisper_json_to_deepgram(
    whisper_json: Dict[str, Any],
    request_id: str,
    model: str = "tiny.en",
    audio_duration: float = 0.0,
    include_utterances: bool = False,
    sha256: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Transform whisper-cli JSON output into Deepgram-compatible response format.

    Whisper JSON structure:
    {
      "systeminfo": "...",
      "model": { "type": "...", "multilingual": false, ... },
      "params": { ... },
      "result": { "language": "en" },
      "transcription": [
        {
          "timestamps": { "from": "00:00:00,000", "to": "00:00:05,000" },
          "offsets": { "from": 0, "to": 5000 },
          "text": " Hello world",
          "tokens": [
            { "text": " Hello", "timestamps": {"from": "...", "to": "..."}, "offsets": {...}, "id": 15947, "p": 0.95 },
            ...
          ]
        },
        ...
      ]
    }
    """
    transcription_segments = whisper_json.get("transcription", [])
    detected_lang = whisper_json.get("result", {}).get("language", "en")

    # Build word list and full transcript from segments
    words = []
    full_transcript_parts = []
    utterances = []

    for seg_idx, segment in enumerate(transcription_segments):
        seg_text = segment.get("text", "").strip()
        full_transcript_parts.append(seg_text)

        # Segment-level timing
        seg_offsets = segment.get("offsets", {})
        seg_start_ms = seg_offsets.get("from", 0)
        seg_end_ms = seg_offsets.get("to", 0)
        seg_start = seg_start_ms / 1000.0
        seg_end = seg_end_ms / 1000.0

        # Token-level words
        tokens = segment.get("tokens", [])
        segment_words = []

        for token in tokens:
            token_text = token.get("text", "").strip()
            if not token_text:
                continue

            # Token timing
            t_offsets = token.get("offsets", {})
            t_start = t_offsets.get("from", seg_start_ms) / 1000.0
            t_end = t_offsets.get("to", seg_end_ms) / 1000.0
            t_confidence = token.get("p", 0.0)

            word_info = {
                "word": token_text.lower().strip(" .,!?;:"),
                "start": round(t_start, 2),
                "end": round(t_end, 2),
                "confidence": round(t_confidence, 6),
                "punctuated_word": token_text.strip(),
            }
            words.append(word_info)
            segment_words.append(word_info)

        # Build utterance from segment
        if include_utterances and seg_text:
            utterance = {
                "start": round(seg_start, 2),
                "end": round(seg_end, 2),
                "confidence": _avg_confidence(segment_words),
                "channel": 0,
                "transcript": seg_text,
                "words": segment_words,
                "speaker": 0,
                "id": f"utt-{uuid.uuid4().hex[:8]}",
            }
            utterances.append(utterance)

    full_transcript = " ".join(full_transcript_parts).strip()
    overall_confidence = _avg_confidence(words) if words else 0.0

    # Build model info
    m_info = model_info.get(model, {
        "name": f"whisper-{model}",
        "version": "ggml-v1",
        "arch": "whisper",
    })

    # Construct Deepgram-style response
    response = {
        "metadata": {
            "request_id": request_id,
            "created": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "duration": round(audio_duration, 6),
            "channels": 1,
            "models": [model],
            "model_info": {
                model: {
                    "name": m_info.get("name", f"whisper-{model}"),
                    "version": m_info.get("version", "unknown"),
                    "arch": m_info.get("arch", "whisper"),
                }
            },
        },
        "results": {
            "channels": [
                {
                    "alternatives": [
                        {
                            "transcript": full_transcript,
                            "confidence": round(overall_confidence, 6),
                            "words": words,
                        }
                    ],
                    "detected_language": detected_lang,
                }
            ],
        },
    }

    if sha256:
        response["metadata"]["sha256"] = sha256

    if include_utterances:
        response["results"]["utterances"] = utterances

    return response


# ═══════════════════════════════════════════════════════════════════════
# AUDIO UTILITIES
# ═══════════════════════════════════════════════════════════════════════


def save_audio_file(file=None) -> str:
    """Save an uploaded audio file to disk. Returns the file path."""
    if file is None:
        return ""
    path = os.path.join(AUDIO_DIR, f"{uuid.uuid4()}.wav")
    with open(path, "wb") as f:
        f.write(file.file.read())
    return path


def save_audio_bytes(audio_bytes: bytes, extension: str = "wav") -> str:
    """Save raw audio bytes to disk. Returns the file path."""
    path = os.path.join(AUDIO_DIR, f"{uuid.uuid4()}.{extension}")
    with open(path, "wb") as f:
        f.write(audio_bytes)
    return path


async def download_audio_from_url(url: str) -> str:
    """
    Download an audio file from a URL.
    Returns the local file path.
    """
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()

            # Determine extension from content type or URL
            content_type = response.headers.get("content-type", "")
            ext = _content_type_to_ext(content_type, url)

            path = os.path.join(AUDIO_DIR, f"{uuid.uuid4()}.{ext}")
            with open(path, "wb") as f:
                f.write(response.content)

            return path
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to download audio from URL: {str(e)}",
        )


async def convert_audio_to_wav(input_path: str) -> str:
    """
    Convert any audio file to 16kHz mono WAV using ffmpeg.
    Returns the path to the converted WAV file.
    """
    output_path = os.path.join(AUDIO_DIR, f"{uuid.uuid4()}.wav")
    command = (
        f"ffmpeg -y -i {input_path} -ar 16000 -ac 1 -c:a pcm_s16le {output_path}"
    )

    try:
        stdout, stderr, code = await execute_command(command)
        if code != 0:
            logger.error(f"ffmpeg conversion failed with code {code}: {stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Audio conversion failed: {stderr}",
            )
        return output_path
    except Exception as e:
        # Don't fall back to original file because whisper-cli (this build) requires WAV
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Error during audio conversion: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error executing audio conversion: {str(e)}",
        )


def get_audio_duration(audio_file: str) -> float:
    """Gets the duration of the audio file in seconds using ffprobe."""
    try:
        command = (
            f"ffprobe -v error -show_entries format=duration "
            f"-of default=noprint_wrappers=1:nokey=1 {audio_file}"
        )
        duration = subprocess.check_output(command, shell=True).decode("utf-8").strip()
        return float(duration)
    except Exception as e:
        logger.error(f"Error getting duration: {e}")
        return 0.0


def compute_sha256(file_path: str) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def create_wav_from_pcm(pcm_data: bytes, sample_rate: int = STREAM_SAMPLE_RATE) -> str:
    """
    Create a WAV file from raw PCM data (16-bit mono).
    Used for streaming: buffer PCM chunks → write WAV → transcribe.
    """
    path = os.path.join(AUDIO_DIR, f"stream_{uuid.uuid4()}.wav")
    with wave.open(path, "wb") as wf:
        wf.setnchannels(STREAM_CHANNELS)
        wf.setsampwidth(STREAM_SAMPLE_WIDTH)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return path


# ═══════════════════════════════════════════════════════════════════════
# MODEL UTILITIES
# ═══════════════════════════════════════════════════════════════════════


def get_model_filename(model: str) -> str:
    """Get the model binary filename from user-friendly model name."""
    if model in model_names:
        return model_names[model]
    # Default to tiny.en.q5
    return model_names.get("tiny.en.q5", "ggml-model-whisper-tiny.en-q5_1.bin")


def get_model_name(model: str = None) -> str:
    """Legacy compat — get model filename."""
    return get_model_filename(model or "tiny.en.q5")


def list_available_models() -> list:
    """List all available models with metadata."""
    available = []
    for key, filename in model_names.items():
        model_path = os.path.join(MODELS_DIR, filename)
        if os.path.exists(model_path):
            info = model_info.get(key, {})
            available.append({
                "name": info.get("name", key),
                "model_id": key,
                "description": info.get("description", ""),
                "language": info.get("language", "en"),
                "version": info.get("version", "unknown"),
                "file": filename,
                "size_bytes": os.path.getsize(model_path),
            })
    return available


# ═══════════════════════════════════════════════════════════════════════
# COMMAND EXECUTION
# ═══════════════════════════════════════════════════════════════════════


async def execute_command(command: str) -> Tuple[str, str, int]:
    """
    Execute a shell command asynchronously.
    Returns (stdout, stderr, returncode).
    """
    try:
        process = await asyncio.create_subprocess_shell(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        return stdout.decode("utf-8").strip(), stderr.decode("utf-8").strip(), process.returncode
    except Exception as exc:
        logger.error(f"Command execution error: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Error executing command: {str(exc)}",
        )


# ═══════════════════════════════════════════════════════════════════════
# DOWNLOAD UTILITIES
# ═══════════════════════════════════════════════════════════════════════


def download_from_drive(url, output):
    """Download a file from Google Drive."""
    try:
        gdown.download(url, output, quiet=False)
        return True
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Error Occurred in Downloading model from Gdrive",
        )


def download_file(url, filepath):
    """Download a file from a URL with progress."""
    try:
        filename = os.path.basename(url)
        with tqdm(
            unit="B", unit_scale=True, unit_divisor=1024, miniters=1, desc=filename
        ) as progress_bar:
            urllib.request.urlretrieve(
                url,
                filepath,
                reporthook=lambda block_num, block_size, total_size: progress_bar.update(
                    block_size
                ),
            )
        logger.info("File downloaded successfully!")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Download error: {exc}")


# ═══════════════════════════════════════════════════════════════════════
# ROUTE PRINTING (kept for dev convenience)
# ═══════════════════════════════════════════════════════════════════════


def get_all_routes(app):
    routes = []
    for route in app.routes:
        methods = getattr(route, "methods", set())
        routes.append(
            {
                "path": route.path,
                "name": route.name,
                "methods": list(methods) if methods else [],
            }
        )
    return routes


def print_routes(app):
    routes = get_all_routes(app)
    print("\n")
    print(f"{'Path':<50}{'Name':<50}{'Methods'}")
    print("-" * 110)
    for route in routes:
        print(
            f"{route['path']:<50}{route['name']:<50}{', '.join(route['methods'])}"
        )
    print("\n")


# ═══════════════════════════════════════════════════════════════════════
# VALIDATION UTILITIES (kept for auth)
# ═══════════════════════════════════════════════════════════════════════


def is_valid_email(email: str) -> bool:
    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(email_regex, email))


def is_valid_password(password: str) -> bool:
    return len(password) >= 6


def is_field_valid(**kwargs) -> bool:
    for key, value in kwargs.items():
        if key == "email":
            if not is_valid_email(value):
                return False
        elif key == "password":
            if not is_valid_password(value):
                return False
        elif key == "username":
            if len(value) < 3:
                return False
        else:
            return False
    return True


# ═══════════════════════════════════════════════════════════════════════
# PRIVATE HELPERS
# ═══════════════════════════════════════════════════════════════════════


def _avg_confidence(words: list) -> float:
    """Calculate average confidence from a list of word dicts."""
    if not words:
        return 0.0
    confs = [w.get("confidence", 0.0) for w in words]
    return round(sum(confs) / len(confs), 6)


def _content_type_to_ext(content_type: str, url: str = "") -> str:
    """Map content type to file extension."""
    ct_map = {
        "audio/wav": "wav",
        "audio/x-wav": "wav",
        "audio/wave": "wav",
        "audio/mp3": "mp3",
        "audio/mpeg": "mp3",
        "audio/ogg": "ogg",
        "audio/flac": "flac",
        "audio/webm": "webm",
        "audio/mp4": "mp4",
        "audio/m4a": "m4a",
    }
    ext = ct_map.get(content_type.split(";")[0].strip(), "")
    if not ext and url:
        # Try to extract from URL
        path = url.split("?")[0]
        if "." in path:
            ext = path.rsplit(".", 1)[-1].lower()
    return ext or "wav"


def _cleanup_files(output_base: str):
    """Remove transcription output files."""
    for ext in [".json", ".txt", ".srt", ".vtt"]:
        path = f"{output_base}{ext}"
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
