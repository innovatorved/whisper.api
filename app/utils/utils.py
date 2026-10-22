"""
Core transcription and audio utility functions for the Whisper Speech-to-Text API.

Uses whisper-cli with full JSON output (-ojf) to produce word-level timestamps and
token probabilities, transforming the output into Deepgram-compatible and
OpenAI-compatible response structures.
"""

import asyncio
import hashlib
import ipaddress
import json
import logging
import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
import urllib
import uuid
import wave
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
from urllib.parse import urlparse

import gdown
import httpx
from fastapi import HTTPException
from tqdm import tqdm

from app.core.config import settings

from .constant import (
    MODEL_ALIASES,
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


def resolve_whisper_binary(configured_path: Optional[str] = None) -> str:
    """
    Resolve the whisper-cli binary path across platforms (macOS, Linux, Windows).

    Automatically handles `.exe` extension differences on Windows vs Unix-like OSes
    and falls back to PATH lookup if the configured relative path is not present.
    """
    raw_path = (configured_path or settings.WHISPER_BINARY_PATH or "./binary/whisper-cli").strip()
    norm_path = os.path.normpath(raw_path)
    is_windows = os.name == "nt" or sys.platform == "win32"

    candidates: List[str] = []
    if is_windows:
        if not norm_path.lower().endswith(".exe"):
            candidates.append(f"{norm_path}.exe")
        candidates.append(norm_path)
    else:
        if norm_path.lower().endswith(".exe"):
            candidates.append(norm_path[:-4])
        candidates.append(norm_path)

    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate

    # Fallback: check system PATH for whisper-cli / whisper-cli.exe
    which_cmd = "whisper-cli.exe" if is_windows else "whisper-cli"
    found_in_path = shutil.which(which_cmd) or shutil.which("whisper-cli")
    if found_in_path:
        return found_in_path

    # Return primary platform-appropriate candidate even if not yet built
    return candidates[0]


def resolve_model_name(model: str) -> str:
    """
    Resolve a user-supplied model name or alias (e.g. 'whisper-1') to a canonical
    key in `model_names`.
    """
    cleaned = (model or "tiny.en").strip()
    if cleaned in model_names:
        return cleaned
    if cleaned in MODEL_ALIASES:
        target = MODEL_ALIASES[cleaned]
        # For whisper-1 alias, prefer tiny.en if present, otherwise first available startup model
        if cleaned == "whisper-1":
            for candidate in ("tiny.en", "base.en.q5", "tiny.en.q5"):
                candidate_file = model_names.get(candidate)
                if candidate_file and os.path.exists(
                    os.path.join(settings.MODELS_DIR, candidate_file)
                ):
                    return candidate
        return target
    return cleaned


def _is_special_whisper_token(token_text: str) -> bool:
    """
    Return True if a whisper-cli token string is an internal special token
    such as `[_BEG_]`, `[_TT_398]`, `[_EOT_]`, `[_SOT_]`, etc.
    """
    stripped = token_text.strip()
    if not stripped:
        return True
    if stripped.startswith("[_") and stripped.endswith("]"):
        return True
    if stripped.startswith("<|") and stripped.endswith("|>"):
        return True
    return False


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
    response_format: str = "json",
    temperature: Optional[float] = None,
    beam_size: Optional[int] = None,
    vad: bool = False,
    vad_threshold: Optional[float] = None,
    split_on_word: bool = False,
    no_fallback: bool = False,
    suppress_nst: bool = False,
    no_context: bool = False,
    max_len: Optional[int] = None,
    video_input: bool = False,
) -> Tuple[Union[Dict[str, Any], str], str]:
    """
    Transcribe an audio (or video) file using whisper-cli.

    Returns the parsed JSON dictionary OR raw subtitle text (SRT/VTT).
    """
    canonical_model = resolve_model_name(model)
    model_file = get_model_filename(canonical_model)
    model_path = os.path.join(settings.MODELS_DIR, model_file)

    if not os.path.exists(model_path):
        raise HTTPException(
            status_code=400,
            detail=f"Model '{model}' not found at {model_path}",
        )

    # Generate unique output base path
    request_id = str(uuid.uuid4())
    output_base = os.path.join(TRANSCRIBE_DIR, request_id)
    binary_path = resolve_whisper_binary(settings.WHISPER_BINARY_PATH)

    input_flag = "-vi" if video_input else "-f"

    # Build whisper-cli argv (no shell — avoids injection via paths or prompt)
    cmd_parts: List[str] = [
        binary_path,
        "-m",
        model_path,
        input_flag,
        audio_path,
        "-t",
        str(threads),
        "-of",
        output_base,
    ]

    # Output format — use -ojf (--output-json-full) so token-level timestamps
    # and confidence scores are populated in the JSON output!
    if response_format == "srt":
        cmd_parts.append("-osrt")
        output_ext = ".srt"
    elif response_format == "vtt":
        cmd_parts.append("-ovtt")
        output_ext = ".vtt"
    else:
        cmd_parts.append("-ojf")
        output_ext = ".json"

    # Language
    if detect_language or language == "auto":
        cmd_parts.extend(["-l", "auto"])
    else:
        whisper_lang = supported_languages.get(language, "en")
        cmd_parts.extend(["-l", whisper_lang])

    # Translate to English
    if translate:
        cmd_parts.append("-tr")

    # Diarize (stereo audio)
    if diarize:
        cmd_parts.append("-di")

    # Advanced features & decoding controls
    if prompt is not None and prompt != "":
        cmd_parts.extend(["--prompt", prompt])
    if start_ms is not None:
        cmd_parts.extend(["-ot", str(start_ms)])
    if duration_ms is not None:
        cmd_parts.extend(["-d", str(duration_ms)])
    if temperature is not None:
        cmd_parts.extend(["-tp", str(temperature)])
    if beam_size is not None:
        cmd_parts.extend(["-bs", str(beam_size)])
    if split_on_word:
        cmd_parts.append("-sow")
    if no_fallback:
        cmd_parts.append("-nf")
    if suppress_nst:
        cmd_parts.append("--suppress-nst")
    if no_context:
        cmd_parts.append("-nc")
    if max_len is not None and max_len > 0:
        cmd_parts.extend(["-ml", str(max_len)])
    if vad:
        vad_model_path = settings.VAD_MODEL_PATH
        if not vad_model_path or not os.path.exists(vad_model_path):
            try:
                from app.utils.checks import ensure_model_available
                vad_model_path = ensure_model_available("silero-v6.2.0")
            except Exception as e:
                logger.warning("Could not auto-download Silero VAD model: %s", e)
        cmd_parts.append("--vad")
        if vad_model_path and os.path.exists(vad_model_path):
            cmd_parts.extend(["-vm", vad_model_path])
        if vad_threshold is not None:
            cmd_parts.extend(["-vt", str(vad_threshold)])

    logger.info(
        f"[{request_id}] Starting transcription "
        f"(model={canonical_model}, format={response_format}, translate={translate}, detect_language={detect_language})"
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
    Transform whisper-cli JSON output (-ojf) into Deepgram-compatible response format.
    """
    canonical_model = resolve_model_name(model)
    transcription_segments = whisper_json.get("transcription", [])
    detected_lang = whisper_json.get("result", {}).get("language", "en")

    # Build word list and full transcript from segments
    words = []
    full_transcript_parts = []
    utterances = []

    for segment in transcription_segments:
        seg_text = segment.get("text", "").strip()
        if seg_text:
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
            if _is_special_whisper_token(token_text):
                continue

            cleaned_word = token_text.lower().strip(" .,!?;:\"'()-[]")
            if not cleaned_word:
                continue

            # Token timing
            t_offsets = token.get("offsets", {})
            t_start = t_offsets.get("from", seg_start_ms) / 1000.0
            t_end = t_offsets.get("to", seg_end_ms) / 1000.0
            t_confidence = float(token.get("p", 0.0))

            word_info = {
                "word": cleaned_word,
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
    m_info = model_info.get(
        canonical_model,
        {
            "name": f"whisper-{canonical_model}",
            "version": "ggml-v1",
            "arch": "whisper",
        },
    )

    # Construct Deepgram-style response
    response = {
        "metadata": {
            "request_id": request_id,
            "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "duration": round(audio_duration, 6),
            "channels": 1,
            "models": [model],
            "model_info": {
                model: {
                    "name": m_info.get("name", f"whisper-{canonical_model}"),
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


def parse_whisper_json_to_openai(
    whisper_json: Dict[str, Any],
    response_format: str = "json",
    audio_duration: float = 0.0,
    translate: bool = False,
    timestamp_granularities: Optional[Sequence[str]] = None,
) -> Union[Dict[str, Any], str]:
    """
    Transform whisper-cli JSON output (-ojf) into OpenAI Audio API format
    (`json`, `text`, or `verbose_json`).
    """
    transcription_segments = whisper_json.get("transcription", [])
    detected_lang = whisper_json.get("result", {}).get("language", "en")

    full_transcript_parts: List[str] = []
    openai_segments: List[Dict[str, Any]] = []
    openai_words: List[Dict[str, Any]] = []

    for seg_idx, segment in enumerate(transcription_segments):
        seg_text = segment.get("text", "").strip()
        if seg_text:
            full_transcript_parts.append(seg_text)

        seg_offsets = segment.get("offsets", {})
        seg_start_ms = seg_offsets.get("from", 0)
        seg_end_ms = seg_offsets.get("to", 0)
        seg_start = round(seg_start_ms / 1000.0, 2)
        seg_end = round(seg_end_ms / 1000.0, 2)

        tokens = segment.get("tokens", [])
        token_ids: List[int] = []
        token_probs: List[float] = []

        for token in tokens:
            token_text = token.get("text", "").strip()
            if _is_special_whisper_token(token_text):
                continue

            if "id" in token:
                token_ids.append(int(token["id"]))
            prob = float(token.get("p", 0.0))
            token_probs.append(prob)

            cleaned_word = token_text.strip(" .,!?;:\"'()-[]")
            if cleaned_word:
                t_offsets = token.get("offsets", {})
                w_start = round(t_offsets.get("from", seg_start_ms) / 1000.0, 2)
                w_end = round(t_offsets.get("to", seg_end_ms) / 1000.0, 2)
                openai_words.append(
                    {
                        "word": cleaned_word,
                        "start": w_start,
                        "end": w_end,
                    }
                )

        avg_prob = sum(token_probs) / len(token_probs) if token_probs else 0.0
        openai_segments.append(
            {
                "id": seg_idx,
                "seek": 0,
                "start": seg_start,
                "end": seg_end,
                "text": segment.get("text", ""),
                "tokens": token_ids,
                "temperature": 0.0,
                "avg_logprob": round(avg_prob - 1.0, 4) if avg_prob > 0 else -0.5,
                "compression_ratio": 1.0,
                "no_speech_prob": round(max(0.0, 1.0 - avg_prob), 4) if avg_prob > 0 else 0.0,
            }
        )

    full_transcript = " ".join(full_transcript_parts).strip()

    if response_format == "text":
        return full_transcript

    if response_format == "verbose_json":
        granularities = set(timestamp_granularities or ["segment"])
        result: Dict[str, Any] = {
            "task": "translate" if translate else "transcribe",
            "language": detected_lang,
            "duration": round(audio_duration, 2),
            "text": full_transcript,
        }
        if "word" in granularities:
            result["words"] = openai_words
        if "segment" in granularities or not granularities:
            result["segments"] = openai_segments
        return result

    return {"text": full_transcript}


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
    clean_ext = (extension or "wav").lstrip(".").lower()
    path = os.path.join(AUDIO_DIR, f"{uuid.uuid4()}.{clean_ext}")
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
    Convert any audio or video file to 16kHz mono WAV using ffmpeg.
    Returns the path to the converted WAV file.
    """
    output_path = os.path.join(AUDIO_DIR, f"{uuid.uuid4()}.wav")
    argv = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-vn",
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
        if isinstance(e, HTTPException):
            raise
        logger.error("Error during audio conversion: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Audio conversion failed",
        ) from e


def get_audio_duration(audio_file: str) -> float:
    """Gets the duration of the audio file in seconds using ffprobe (with wave module fallback)."""
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
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
        logger.debug("ffprobe non-zero or empty output: %s", result.stderr.strip()[:500])
    except (ValueError, subprocess.TimeoutExpired, OSError) as e:
        logger.debug("ffprobe unavailable or failed (%s); trying wave fallback", e)

    # Fallback for WAV files if ffprobe is not installed
    try:
        if audio_file.lower().endswith(".wav") and os.path.exists(audio_file):
            with wave.open(audio_file, "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0:
                    return float(frames) / float(rate)
    except Exception:
        pass
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
    """Get the model binary filename from user-friendly model name or alias."""
    canonical = resolve_model_name(model)
    if canonical in model_names:
        return model_names[canonical]
    raise HTTPException(
        status_code=400,
        detail=f"Unknown model '{model}'",
    )


def get_model_name(model: str = None) -> str:
    """Legacy compat — get model filename."""
    return get_model_filename(model or "tiny.en.q5")


def list_available_models(include_uninstalled: bool = False) -> list:
    """List available models with metadata."""
    available = []
    for key, filename in model_names.items():
        if key == "silero-v6.2.0" and not include_uninstalled:
            continue
        model_path = os.path.join(settings.MODELS_DIR, filename)
        exists = os.path.exists(model_path)
        if exists or include_uninstalled:
            info = model_info.get(key, {})
            available.append(
                {
                    "name": info.get("name", key),
                    "model_id": key,
                    "description": info.get("description", ""),
                    "language": info.get("language", "en"),
                    "version": info.get("version", "unknown"),
                    "file": filename,
                    "installed": exists,
                    "size_bytes": os.path.getsize(model_path) if exists else 0,
                }
            )
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

    def _collect(route_list, prefix=""):
        for route in route_list:
            if hasattr(route, "path"):
                methods = getattr(route, "methods", set())
                full_path = f"{prefix}{route.path}" if prefix else route.path
                routes.append(
                    {
                        "path": full_path,
                        "name": getattr(route, "name", "") or "",
                        "methods": list(methods) if methods else [],
                    }
                )
            elif hasattr(route, "routes"):
                sub_prefix = f"{prefix}{getattr(route, 'prefix', '')}"
                _collect(route.routes, sub_prefix)

    _collect(getattr(app, "routes", []))
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
        "video/mp4": "mp4",
        "video/webm": "webm",
        "video/quicktime": "mov",
        "video/x-matroska": "mkv",
    }
    ext = ct_map.get(content_type.split(";")[0].strip().lower(), "")
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
