---
title: whisper.api
emoji: 😶‍🌫️
colorFrom: purple
colorTo: gray
sdk: docker
app_file: Dockerfile
app_port: 7860
---

# Whisper API 🎙️

An open-source, high-performance, self-hosted API for speech-to-text transcription and translation powered by [whisper.cpp](https://github.com/ggml-org/whisper.cpp) ([fork with native video input](https://github.com/innovatorved/whisper.cpp)).

This project provides both **Deepgram-compatible** (`/v1/listen` REST & WebSocket) and **OpenAI-compatible** (`/v1/audio/transcriptions` & `/v1/audio/translations`) interfaces, making it a drop-in replacement for cloud speech APIs with full data ownership and cross-platform hardware acceleration (**Apple macOS Metal/Accelerate/CoreML**, **Linux x86_64/ARM64/CUDA**, and **Windows**).

---

## Key Features

- **Dual Industry-Standard APIs**:
  - **Deepgram-compatible**: `POST /v1/listen` and `WS /v1/listen` with full word-level timestamps & confidence scores (`-ojf`).
  - **OpenAI-compatible**: `POST /v1/audio/transcriptions` and `POST /v1/audio/translations` (works out of the box with the official `openai` Python/JS SDKs and `model="whisper-1"`).
- **Modern Whisper Models & VAD**: Supports `large-v3-turbo` (`q5_0`, `q8_0`, full), `large-v3`, `medium.en`, `small.en.q5`, `base.en.q5`, `tiny.en`, and **Silero VAD v6.2.0** (`vad=true`) for non-speech filtering.
- **Advanced Decoding Controls**: Custom vocabulary (`prompt`), audio cropping (`start`/`duration`), speaker diarization (`diarize`), `temperature`, `beam_size`, `split_on_word`, and translation to English (`translate=true`).
- **Flexible Formats**: Native support for **JSON**, **Verbose JSON**, **Text**, **SRT**, and **VTT** exports.
- **Cross-Platform Native Builds**: Automated setup scripts for **macOS & Linux** (`./setup_whisper.sh`) and **Windows PowerShell** (`.\setup_whisper.ps1`).
- **Offline CLI Management**: Manage API keys (`init`, `create`, `list`, `revoke`) and download/inspect GGML models (`models`, `download`) directly from `python -m app.cli`.

---

## Documentation

Documentation is live at **[whisper.vedgupta.in](https://whisper.vedgupta.in)** and lives in the `docs/` folder (Astro 7 + Tailwind CSS v4). Run it locally with Bun:

```bash
cd docs && bun install && bun run dev
```

What you will find in the docs:

- Getting started and local setup (macOS, Linux, Windows)
- Authentication and API keys
- Deepgram & OpenAI REST and WebSocket API reference
- Code examples
- Models (`large-v3-turbo`, Silero VAD, quantized GGML) and deployment guides
- Contributing workflow

---

## Quick Start

### 1. Installation

**macOS & Linux:**
```bash
pip install -r requirements.txt
cp .env.example .env
chmod +x setup_whisper.sh
./setup_whisper.sh
```

**Windows (PowerShell):**
```powershell
pip install -r requirements.txt
Copy-Item .env.example .env
.\setup_whisper.ps1
```

### 2. Setup Database, API Keys & Models
```bash
# Initialize database and create an API key
python -m app.cli init
python -m app.cli create --name "MyAdminKey"

# List registered models and download additional models on demand
python -m app.cli models
python -m app.cli download large-v3-turbo.q5
```

*Note: For **local testing only**, you can enable `POST /v1/auth/test-token` in Swagger by setting `ENABLE_TEST_TOKEN_ENDPOINT=true`. It defaults to **off**; never enable it in production.*

### 3. Start the Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 7860
```

### 4. Transcribe a File — Deepgram Format (`/v1/listen`)
```bash
curl -X POST 'http://localhost:7860/v1/listen?model=tiny.en&vad=false' \
  -H "Authorization: Token <YOUR_KEY>" \
  -H "Content-Type: audio/wav" \
  --data-binary @audio/jfk.wav
```

### 5. Transcribe or Translate — OpenAI Format (`/v1/audio/transcriptions`)
```bash
curl -X POST 'http://localhost:7860/v1/audio/transcriptions' \
  -H "Authorization: Bearer <YOUR_KEY>" \
  -F "file=@audio/jfk.wav" \
  -F "model=whisper-1" \
  -F "response_format=verbose_json" \
  -F "timestamp_granularities[]=word"
```

### 6. Transcribe from URL (`/v1/listen`)
```bash
curl -X POST 'http://localhost:7860/v1/listen' \
  -H "Authorization: Token <YOUR_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/audio.mp3"}'
```

The server fetches the URL for you with **SSRF protections** (public hosts only, size limits; redirects off by default). See `docs/` or `.env.example` for `MAX_AUDIO_DOWNLOAD_BYTES`, `AUDIO_URL_FOLLOW_REDIRECTS`, and related settings.

---

## License & References

[MIT License](https://choosealicense.com/licenses/mit/)

- [whisper.cpp (Upstream)](https://github.com/ggml-org/whisper.cpp)
- [whisper.cpp (Custom Fork with Video Input)](https://github.com/innovatorved/whisper.cpp)
- [OpenAI Whisper](https://github.com/openai/whisper)

**Author:** [Ved Gupta](https://www.github.com/innovatorved)
