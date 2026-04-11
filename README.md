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

An open-source, high-performance, self-hosted API for speech-to-text transcription powered by [whisper.cpp](https://github.com/ggerganov/whisper.cpp).

This project provides a **Deepgram-compatible** interface (REST & WebSocket), making it easy to integrate into existing workflows while maintaining full data ownership.

---

## Key Features

- **Standardized API**: Drop-in compatible with `/v1/listen` endpoints.
- **Advanced Transcription**: Custom vocabulary (prompting), audio cropping (`start`/`duration`), and speaker diarization.
- **Flexible Formats**: Native support for **JSON**, **SRT**, and **VTT** exports.
- **Live Streaming**: Real-time 16kHz PCM transcription via WebSockets.
- **Offline Management**: Simple CLI for secure API key generation and model management.

---

## Documentation

Documentation lives in the `docs/` folder (Astro Starlight). Run it locally with Bun:

```bash
cd docs && bun install && bun run dev
```

What you will find in the docs:

- Getting started and local setup
- Authentication and API keys
- REST and WebSocket API reference
- Code examples
- Models and deployment guides
- Contributing workflow

---

## Quick Start

### 1. Installation
```bash
pip install -r requirements.txt
cp .env.example .env
chmod +x setup_whisper.sh
./setup_whisper.sh
```

### 2. Setup Database & Keys
```bash
python -m app.cli init
python -m app.cli create --name "MyAdminKey"
```

*Note: For **local testing only**, you can enable `POST /v1/auth/test-token` in Swagger by setting `ENABLE_TEST_TOKEN_ENDPOINT=true`. It defaults to **off**; never enable it in production.*

### 3. Start the Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 7860
```

### 4. Transcribe a File (cURL)
```bash
curl -X POST 'http://localhost:7860/v1/listen' \
  -H "Authorization: Token <YOUR_KEY>" \
  -H "Content-Type: audio/wav" \
  --data-binary @audio.wav
```

### 5. Transcribe from URL (cURL)
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

- [whisper.cpp](https://github.com/ggerganov/whisper.cpp)
- [OpenAI Whisper](https://github.com/openai/whisper)

**Author:** [Ved Gupta](https://www.github.com/innovatorved)
