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

## 📚 Documentation

Full documentation is available as a self-contained Astro Starlight site in the `docs/` directory. To run it locally:

```bash
cd docs && npm install && npm run dev
```

The docs site covers:

- **Getting Started** — Installation, prerequisites, environment variables, and server setup
- **Authentication** — API key generation, management, and usage patterns
- **REST API Reference** — Endpoint parameters, request/response schemas, and error codes
- **Live Streaming** — WebSocket protocol, audio formats, and control messages
- **Code Examples** — Production-ready snippets for cURL, Python, and JavaScript
- **Models** — GGML model sizes, quantization formats, and download links
- **Docker Deployment** — Dockerfile walkthrough and production checklist
- **Contributing** — Development setup, PR workflow, and project structure

---

## 🛠️ Quick Start

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

*Note: For testing purposes, you can enable a public token generation endpoint in the Swagger UI (`/docs`) by setting `ENABLE_TEST_TOKEN_ENDPOINT=true` in your `.env` file.*

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

### 6. Export Subtitles (cURL)
```bash
curl -X POST 'http://localhost:7860/v1/listen?response_format=srt' \
  -H "Authorization: Token <YOUR_KEY>" \
  -H "Content-Type: audio/wav" \
  --data-binary @audio.wav > output.srt
```


---

## 📄 License & References

[MIT License](https://choosealicense.com/licenses/mit/)

- [whisper.cpp](https://github.com/ggerganov/whisper.cpp)
- [OpenAI Whisper](https://github.com/openai/whisper)

**Author:** [Ved Gupta](https://www.github.com/innovatorved)
