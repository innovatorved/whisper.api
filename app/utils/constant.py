"""
Constants for Whisper API — model registry, language map, and configuration.
"""

# ─── Default Startup Models ──────────────────────────────────────────
# Lightweight models checked/downloaded automatically on server startup.
DEFAULT_STARTUP_MODELS = (
    "tiny.en",
    "tiny.en.q5",
    "base.en.q5",
)

# ─── Model Registry ──────────────────────────────────────────────────
# Maps user-friendly model names to binary filenames in MODELS_DIR.

model_names = {
    "tiny.en": "ggml-tiny.en.bin",
    "tiny.en.q5": "ggml-model-whisper-tiny.en-q5_1.bin",
    "base.en": "ggml-base.en.bin",
    "base.en.q5": "ggml-model-whisper-base.en-q5_1.bin",
    "small.en": "ggml-small.en.bin",
    "small.en.q5": "ggml-small.en-q5_1.bin",
    "medium.en": "ggml-medium.en.bin",
    "large-v3": "ggml-large-v3.bin",
    "large-v3-turbo": "ggml-large-v3-turbo.bin",
    "large-v3-turbo.q5": "ggml-large-v3-turbo-q5_0.bin",
    "large-v3-turbo.q8": "ggml-large-v3-turbo-q8_0.bin",
    "silero-v6.2.0": "ggml-silero-v6.2.0.bin",
}

# ─── Model Aliases (OpenAI / Deepgram / HuggingFace compatibility) ───

MODEL_ALIASES = {
    "whisper-1": "tiny.en",
    "large-v3-turbo-q5_0": "large-v3-turbo.q5",
    "large-v3-turbo-q8_0": "large-v3-turbo.q8",
    "tiny.en-q5_1": "tiny.en.q5",
    "base.en-q5_1": "base.en.q5",
    "small.en-q5_1": "small.en.q5",
}

# ─── Model Download URLs ─────────────────────────────────────────────

model_urls = {
    "tiny.en": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin",
    "tiny.en.q5": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en-q5_1.bin",
    "base.en": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin",
    "base.en.q5": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en-q5_1.bin",
    "small.en": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin",
    "small.en.q5": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en-q5_1.bin",
    "medium.en": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.en.bin",
    "large-v3": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin",
    "large-v3-turbo": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin",
    "large-v3-turbo.q5": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin",
    "large-v3-turbo.q8": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q8_0.bin",
    "silero-v6.2.0": "https://huggingface.co/ggml-org/whisper-vad/resolve/main/ggml-silero-v6.2.0.bin",
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
    "base.en": {
        "name": "whisper-base.en",
        "description": "Base English-only Whisper model (~142MB). Higher accuracy than tiny with fast inference.",
        "version": "ggml-v1",
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
    "small.en": {
        "name": "whisper-small.en",
        "description": "Small English-only Whisper model (~466MB). Strong accuracy for production English workloads.",
        "version": "ggml-v1",
        "arch": "whisper",
        "language": "en",
    },
    "small.en.q5": {
        "name": "whisper-small.en-q5_1",
        "description": "Quantized (Q5_1) small English-only model (~181MB). Great accuracy-to-memory ratio.",
        "version": "ggml-q5_1",
        "arch": "whisper",
        "language": "en",
    },
    "medium.en": {
        "name": "whisper-medium.en",
        "description": "Medium English-only Whisper model (~1.5GB). High accuracy for complex English audio.",
        "version": "ggml-v1",
        "arch": "whisper",
        "language": "en",
    },
    "large-v3": {
        "name": "whisper-large-v3",
        "description": "Full Large-v3 multilingual Whisper model (~2.9GB). Highest accuracy across 99 languages.",
        "version": "ggml-v3",
        "arch": "whisper",
        "language": "multilingual",
    },
    "large-v3-turbo": {
        "name": "whisper-large-v3-turbo",
        "description": "Large-v3 Turbo multilingual model (~1.5GB). Near Large-v3 accuracy with significantly faster decoding.",
        "version": "ggml-v3-turbo",
        "arch": "whisper",
        "language": "multilingual",
    },
    "large-v3-turbo.q5": {
        "name": "whisper-large-v3-turbo-q5_0",
        "description": "Quantized (Q5_0) Large-v3 Turbo multilingual model (~547MB). Best overall speed/accuracy/memory tradeoff.",
        "version": "ggml-q5_0",
        "arch": "whisper",
        "language": "multilingual",
    },
    "large-v3-turbo.q8": {
        "name": "whisper-large-v3-turbo-q8_0",
        "description": "Quantized (Q8_0) Large-v3 Turbo multilingual model (~834MB). Near-lossless quantization of Large-v3 Turbo.",
        "version": "ggml-q8_0",
        "arch": "whisper",
        "language": "multilingual",
    },
    "silero-v6.2.0": {
        "name": "silero-vad-v6.2.0",
        "description": "Silero Voice Activity Detection (VAD) GGML model (~885KB) for filtering non-speech intervals.",
        "version": "v6.2.0",
        "arch": "silero-vad",
        "language": "agnostic",
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

# ─── Supported Audio & Video Formats ─────────────────────────────────

SUPPORTED_VIDEO_CONTENT_TYPES = {
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "video/x-matroska",
    "video/mpeg",
    "video/x-msvideo",
}

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
    *SUPPORTED_VIDEO_CONTENT_TYPES,
}

# ─── Streaming Configuration Defaults ────────────────────────────────

DEFAULT_STREAM_CHUNK_DURATION_MS = 2000   # 2 seconds per chunk
DEFAULT_STREAM_BUFFER_SIZE = 16000 * 2 * 2  # 2 seconds at 16kHz, 16-bit mono
STREAM_SAMPLE_RATE = 16000
STREAM_CHANNELS = 1
STREAM_SAMPLE_WIDTH = 2  # 16-bit = 2 bytes
