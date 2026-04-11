"""
Core transcription and audio utility functions for the Whisper Speech-to-Text API.

Uses whisper-cli with JSON output (-oj) to produce word-level timestamps,
then transforms the output into Deepgram-compatible response structures.
"""

import asyncio
import hashlib
import ipaddress
import json
import logging
import os
import re
import socket
import subprocess
import urllib
import shlex
import uuid
import wave
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
from urllib.parse import urlparse

import gdown
import httpx
from fastapi import HTTPException
from tqdm import tqdm

from app.core.config import settings

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

AUDIO_DIR = "audio"
TRANSCRIBE_DIR = "transcribe"

# Ensure directories exist
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(TRANSCRIBE_DIR, exist_ok=True)

_METADATA_IP = ipaddress.ip_address("169.254.169.254")


def _ip_is_public_facing(ip: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]) -> bool:
    if ip.is_private or ip.is_loopback or ip.is_link_local:
        return False
    if ip.is_reserved or ip.is_multicast or ip.is_unspecified:
        return False
    if ip == _METADATA_IP:
        return False
    if ip.version == 6 and ip in ipaddress.ip_network("fc00::/7"):
        return False
    return True


def _validate_hostname_is_public(hostname: str) -> None:
    """Reject hosts that resolve to non-public addresses (SSRF mitigation)."""
    if not hostname:
        raise HTTPException(status_code=400, detail="Invalid URL hostname")

    host_lower = hostname.strip().lower()
    blocked_exact = {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
    }
    if host_lower in blocked_exact or host_lower.endswith(".localhost"):
        raise HTTPException(
            status_code=400,
            detail="URL host is not allowed for security reasons",
        )

    try:
        parsed_ip = ipaddress.ip_address(hostname)
        if not _ip_is_public_facing(parsed_ip):
            raise HTTPException(
                status_code=400,
                detail="URL host is not allowed for security reasons",
            )
        return
    except ValueError:
        pass

    try:
        addrinfos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(
            status_code=400,
            detail="Could not resolve audio URL hostname",
        ) from None

    if not addrinfos:
        raise HTTPException(
            status_code=400,
            detail="Could not resolve audio URL hostname",
        )

    for _fam, _skt, _proto, _canon, sockaddr in addrinfos:
        ip_str = sockaddr[0]
        try:
            resolved = ipaddress.ip_address(ip_str)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="Invalid IP in DNS resolution for URL host",
            ) from exc
        if not _ip_is_public_facing(resolved):
            raise HTTPException(
                status_code=400,
                detail="URL host is not allowed for security reasons",
            )


def _validate_audio_fetch_url(url: str) -> None:
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400,
            detail="Audio URL must use http or https",
        )
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="Invalid audio URL")
    _validate_hostname_is_public(hostname)


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
    model_path = os.path.join(settings.MODELS_DIR, model_file)

    if not os.path.exists(model_path):
        raise HTTPException(
            status_code=400,
            detail=f"Model '{model}' not found at {model_path}",
        )

    # Generate unique output base path
    request_id = str(uuid.uuid4())
    output_base = os.path.join(TRANSCRIBE_DIR, request_id)

    # Build whisper-cli argv (no shell — avoids injection via paths or prompt)
    cmd_parts: List[str] = [
        settings.WHISPER_BINARY_PATH,
        "-m",
        model_path,
        "-f",
        audio_path,
        "-t",
        str(threads),
        "-of",
        output_base,
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
        cmd_parts.append("-dl")
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
    if prompt is not None and prompt != "":
        cmd_parts.extend(["--prompt", prompt])
    if start_ms is not None:
        cmd_parts.extend(["-ot", str(start_ms)])
    if duration_ms is not None:
        cmd_parts.extend(["-d", str(duration_ms)])

    logger.info(
        f"[{request_id}] Starting transcription "
        f"(model={model}, format={response_format}, translate={translate}, detect_language={detect_language})"
    )
    logger.debug(f"[{request_id}] whisper-cli argv: {shlex.join(cmd_parts)}")

    start_time_exec = asyncio.get_event_loop().time()
    stdout, stderr, code = await execute_command(
        cmd_parts, timeout=settings.WHISPER_CLI_TIMEOUT_SEC
    )
    end_time_exec = asyncio.get_event_loop().time()

    exec_wall = end_time_exec - start_time_exec
    logger.info(
        f"[{request_id}] Transcription finished in {exec_wall:.2f}s (exit_code={code})."
    )

    # Read output
    out_path = f"{output_base}{output_ext}"
    if code != 0:
        logger.error(
            f"[{request_id}] whisper-cli failed (exit_code={code}). stderr: {stderr[:2000]}"
        )
        _cleanup_files(output_base)
        raise HTTPException(
            status_code=500,
            detail="Transcription failed",
        )

    if not os.path.exists(out_path):
        logger.error(f"[{request_id}] Output file {out_path} missing after whisper-cli execution.")
        logger.debug(f"[{request_id}] whisper-cli stdout: {stdout}")
        logger.debug(f"[{request_id}] whisper-cli stderr: {stderr}")
        raise HTTPException(
            status_code=500,
            detail="Transcription failed: output missing",
        )

    if response_format in ("srt", "vtt"):
        with open(out_path, "r", encoding="utf-8") as f:
            whisper_output = f.read()
    else:
        with open(out_path, "r", encoding="utf-8") as f:
            whisper_output = json.load(f)
            logger.debug(f"[{request_id}] Parsed Whisper JSON output successfully.")

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
    if not isinstance(url, str) or not url.strip():
        raise HTTPException(status_code=400, detail="Invalid URL")

    _validate_audio_fetch_url(url)
    max_bytes = settings.MAX_AUDIO_DOWNLOAD_BYTES

    timeout = httpx.Timeout(60.0, connect=10.0)
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=settings.AUDIO_URL_FOLLOW_REDIRECTS,
        ) as client:
            async with client.stream("GET", url) as response:
                if settings.AUDIO_URL_FOLLOW_REDIRECTS and response.url.host:
                    _validate_hostname_is_public(response.url.host)
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")
                ext = _content_type_to_ext(content_type, url)
                path = os.path.join(AUDIO_DIR, f"{uuid.uuid4()}.{ext}")

                total = 0
                with open(path, "wb") as outfile:
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        total += len(chunk)
                        if total > max_bytes:
                            try:
                                os.remove(path)
                            except OSError:
                                pass
                            raise HTTPException(
                                status_code=400,
                                detail="Downloaded audio exceeds maximum allowed size",
                            )
                        outfile.write(chunk)

                return path
    except HTTPException:
        raise
    except httpx.HTTPError:
        raise HTTPException(
            status_code=400,
            detail="Failed to download audio from URL",
        ) from None


async def convert_audio_to_wav(input_path: str) -> str:
    """
    Convert any audio file to 16kHz mono WAV using ffmpeg.
    Returns the path to the converted WAV file.
    """
    output_path = os.path.join(AUDIO_DIR, f"{uuid.uuid4()}.wav")
    argv = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-ar",
        "16000",
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        output_path,
    ]

    try:
        stdout, stderr, code = await execute_command(
            argv, timeout=settings.FFMPEG_TIMEOUT_SEC
        )
        if code != 0:
            logger.error("ffmpeg conversion failed with code %s: %s", code, stderr[:2000])
            raise HTTPException(
                status_code=500,
                detail="Audio conversion failed",
            )
        return output_path
    except Exception as e:
        # Don't fall back to original file because whisper-cli (this build) requires WAV
        if isinstance(e, HTTPException):
            raise
        logger.error("Error during audio conversion: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Audio conversion failed",
        ) from e


def get_audio_duration(audio_file: str) -> float:
    """Gets the duration of the audio file in seconds using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                audio_file,
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        if result.returncode != 0:
            logger.error("ffprobe failed: %s", result.stderr.strip()[:500])
            return 0.0
        duration = result.stdout.strip()
        return float(duration)
    except (ValueError, subprocess.TimeoutExpired, OSError) as e:
        logger.error("Error getting duration: %s", e)
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
    raise HTTPException(
        status_code=400,
        detail=f"Unknown model '{model}'",
    )


def get_model_name(model: str = None) -> str:
    """Legacy compat — get model filename."""
    return get_model_filename(model or "tiny.en.q5")


def list_available_models() -> list:
    """List all available models with metadata."""
    available = []
    for key, filename in model_names.items():
        model_path = os.path.join(settings.MODELS_DIR, filename)
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


async def execute_command(
    argv: Sequence[str],
    timeout: Optional[float] = None,
) -> Tuple[str, str, int]:
    """
    Execute a subprocess asynchronously without a shell.
    Returns (stdout, stderr, returncode).
    """
    try:
        process = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise HTTPException(
                status_code=504,
                detail="Audio processing timed out",
            ) from None

        stdout = stdout_b.decode("utf-8", errors="replace").strip()
        stderr = stderr_b.decode("utf-8", errors="replace").strip()
        code = process.returncode if process.returncode is not None else -1
        return stdout, stderr, code
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Command execution error: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Error executing audio processor",
        ) from exc


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
