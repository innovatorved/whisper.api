"""
Deepgram-compatible response models for speech-to-text API.

These Pydantic models mirror the Deepgram API response structure,
providing a familiar interface for users migrating from Deepgram
while being powered by whisper.cpp under the hood.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


# ─── Word-Level Detail ───────────────────────────────────────────────

class WordInfo(BaseModel):
    """A single word with timing and confidence information."""
    word: str
    start: float = Field(..., description="Start time in seconds from beginning of audio")
    end: float = Field(..., description="End time in seconds from beginning of audio")
    confidence: float = Field(..., ge=0.0, le=1.0)
    punctuated_word: Optional[str] = Field(
        None, description="Word with punctuation/capitalization applied"
    )
    speaker: Optional[int] = Field(None, description="Speaker index (when diarize=true)")
    speaker_confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Confidence of speaker assignment"
    )


# ─── Alternatives & Channels ─────────────────────────────────────────

class Paragraph(BaseModel):
    """A paragraph within the transcript."""
    sentences: List[Dict[str, Any]] = Field(default_factory=list)
    speaker: Optional[int] = None
    num_words: int = 0
    start: float = 0.0
    end: float = 0.0


class ParagraphsInfo(BaseModel):
    """Paragraphs container."""
    transcript: str = ""
    paragraphs: List[Paragraph] = Field(default_factory=list)


class Alternative(BaseModel):
    """One possible transcription of an audio segment."""
    transcript: str = ""
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    words: List[WordInfo] = Field(default_factory=list)
    paragraphs: Optional[ParagraphsInfo] = None


class Channel(BaseModel):
    """Transcription results for a single audio channel."""
    alternatives: List[Alternative] = Field(default_factory=list)
    detected_language: Optional[str] = Field(
        None, description="Detected language code (when detect_language=true)"
    )


# ─── Utterances ───────────────────────────────────────────────────────

class Utterance(BaseModel):
    """A continuous speech segment (when utterances=true)."""
    start: float
    end: float
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    channel: int = 0
    transcript: str = ""
    words: List[WordInfo] = Field(default_factory=list)
    speaker: Optional[int] = None
    id: str = Field(default_factory=lambda: f"utt-{uuid.uuid4().hex[:8]}")


# ─── Model Info ───────────────────────────────────────────────────────

class ModelDetail(BaseModel):
    """Details about a specific model used for transcription."""
    name: str
    version: str
    arch: str = "whisper"


class ModelListItem(BaseModel):
    """Model entry for the GET /v1/models endpoint."""
    name: str
    model_id: str
    description: str
    language: str
    version: str


# ─── Metadata ─────────────────────────────────────────────────────────

class ListenMetadata(BaseModel):
    """Metadata about the transcription request."""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created: str = Field(
        default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    )
    duration: float = Field(0.0, description="Duration of audio in seconds")
    channels: int = Field(1, description="Number of audio channels")
    models: List[str] = Field(default_factory=list)
    model_info: Dict[str, ModelDetail] = Field(default_factory=dict)
    sha256: Optional[str] = None


# ─── Pre-Recorded Response ────────────────────────────────────────────

class ListenResults(BaseModel):
    """Container for transcription results."""
    channels: List[Channel] = Field(default_factory=list)
    utterances: Optional[List[Utterance]] = None


class ListenResponse(BaseModel):
    """
    Full response for pre-recorded audio transcription.
    Mirrors Deepgram's POST /v1/listen response format.
    """
    metadata: ListenMetadata
    results: ListenResults


# ─── Streaming Response ───────────────────────────────────────────────

class StreamingMetadata(BaseModel):
    """Metadata included in each streaming result."""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model_info: Dict[str, ModelDetail] = Field(default_factory=dict)
    model_uuid: Optional[str] = None


class StreamingResult(BaseModel):
    """
    A single streaming transcription result.
    Mirrors Deepgram's WebSocket response message format.
    """
    type: str = "Results"
    channel_index: List[int] = Field(default_factory=lambda: [0, 1])
    duration: float = 0.0
    start: float = 0.0
    is_final: bool = True
    speech_final: bool = False
    channel: Channel = Field(default_factory=Channel)
    metadata: StreamingMetadata = Field(default_factory=StreamingMetadata)
    from_finalize: bool = False


# ─── Request Models ──────────────────────────────────────────────────

class URLRequest(BaseModel):
    """Request body for URL-based transcription."""
    url: str = Field(..., description="URL of the audio file to transcribe")


# ─── Query Parameters Model ─────────────────────────────────────────

class ListenQueryParams(BaseModel):
    """
    Query parameters for the listen endpoint.
    Maps Deepgram-style params to whisper-cli flags.
    """
    model: str = Field("tiny.en", description="Model to use for transcription")
    language: str = Field("en", description="BCP-47 language code")
    translate: bool = Field(False, description="Translate to English")
    diarize: bool = Field(False, description="Enable speaker diarization (stereo audio)")
    punctuate: bool = Field(True, description="Add punctuation")
    utterances: bool = Field(False, description="Split output into utterances")
    smart_format: bool = Field(False, description="Apply smart formatting")
    detect_language: bool = Field(False, description="Auto-detect language")
    keywords: Optional[List[str]] = Field(None, description="Keywords to boost")
    channels: int = Field(1, description="Number of audio channels")
