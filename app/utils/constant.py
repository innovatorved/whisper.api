"""
Constants for Whisper API — model registry, language map, and configuration.
"""

# ─── Model Registry ──────────────────────────────────────────────────
# Maps user-friendly model names to binary filenames

model_names = {
    "tiny.en": "ggml-tiny.en.bin",
    "tiny.en.q5": "ggml-model-whisper-tiny.en-q5_1.bin",
    "base.en.q5": "ggml-model-whisper-base.en-q5_1.bin",
}

# ─── Model Download URLs ─────────────────────────────────────────────

model_urls = {
    "tiny.en": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin",
    "tiny.en.q5": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en-q5_1.bin",
    "base.en.q5": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en-q5_1.bin",
}

# ─── Model Metadata (for GET /v1/models and response metadata) ───────

model_info = {
    "tiny.en": {
        "name": "whisper-tiny.en",
        "description": "Tiny English-only Whisper model (~75MB). Fastest inference, good for English.",
        "version": "ggml-v1",
        "arch": "whisper",
        "language": "en",
    },
    "tiny.en.q5": {
        "name": "whisper-tiny.en-q5_1",
        "description": "Quantized (Q5_1) tiny English-only model (~30MB). Very fast, low memory.",
        "version": "ggml-q5_1",
        "arch": "whisper",
        "language": "en",
    },
    "base.en.q5": {
        "name": "whisper-base.en-q5_1",
        "description": "Quantized (Q5_1) base English-only model (~57MB). Good balance of speed and accuracy.",
        "version": "ggml-q5_1",
        "arch": "whisper",
        "language": "en",
    },
}

# ─── Supported Languages (BCP-47 → whisper language code) ────────────
# whisper.cpp uses short language codes

supported_languages = {
    "en": "en",
    "zh": "zh",
    "de": "de",
    "es": "es",
    "ru": "ru",
    "ko": "ko",
    "fr": "fr",
    "ja": "ja",
    "pt": "pt",
    "tr": "tr",
    "pl": "pl",
    "ca": "ca",
    "nl": "nl",
    "ar": "ar",
    "sv": "sv",
    "it": "it",
    "id": "id",
    "hi": "hi",
    "fi": "fi",
    "vi": "vi",
    "he": "he",
    "uk": "uk",
    "el": "el",
    "ms": "ms",
    "cs": "cs",
    "ro": "ro",
    "da": "da",
    "hu": "hu",
    "ta": "ta",
    "no": "no",
    "th": "th",
    "ur": "ur",
    "hr": "hr",
    "bg": "bg",
    "lt": "lt",
    "la": "la",
    "mi": "mi",
    "ml": "ml",
    "cy": "cy",
    "sk": "sk",
    "te": "te",
    "fa": "fa",
    "lv": "lv",
    "bn": "bn",
    "sr": "sr",
    "az": "az",
    "sl": "sl",
    "kn": "kn",
    "et": "et",
    "mk": "mk",
    "br": "br",
    "eu": "eu",
    "is": "is",
    "hy": "hy",
    "ne": "ne",
    "mn": "mn",
    "bs": "bs",
    "kk": "kk",
    "sq": "sq",
    "sw": "sw",
    "gl": "gl",
    "mr": "mr",
    "pa": "pa",
    "si": "si",
    "km": "km",
    "sn": "sn",
    "yo": "yo",
    "so": "so",
    "af": "af",
    "oc": "oc",
    "ka": "ka",
    "be": "be",
    "tg": "tg",
    "sd": "sd",
    "gu": "gu",
    "am": "am",
    "yi": "yi",
    "lo": "lo",
    "uz": "uz",
    "fo": "fo",
    "ht": "ht",
    "ps": "ps",
    "tk": "tk",
    "nn": "nn",
    "mt": "mt",
    "sa": "sa",
    "lb": "lb",
    "my": "my",
    "bo": "bo",
    "tl": "tl",
    "mg": "mg",
    "as": "as",
    "tt": "tt",
    "haw": "haw",
    "ln": "ln",
    "ha": "ha",
    "ba": "ba",
    "jw": "jw",
    "su": "su",
    "auto": "auto",
}

# ─── Supported Audio Formats ─────────────────────────────────────────

SUPPORTED_AUDIO_CONTENT_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mp3",
    "audio/mpeg",
    "audio/ogg",
    "audio/flac",
    "audio/x-flac",
    "audio/webm",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "application/octet-stream",  # generic binary
}

# ─── Streaming Configuration Defaults ────────────────────────────────

DEFAULT_STREAM_CHUNK_DURATION_MS = 2000   # 2 seconds per chunk
DEFAULT_STREAM_BUFFER_SIZE = 16000 * 2 * 2  # 2 seconds at 16kHz, 16-bit mono
STREAM_SAMPLE_RATE = 16000
STREAM_CHANNELS = 1
STREAM_SAMPLE_WIDTH = 2  # 16-bit = 2 bytes
