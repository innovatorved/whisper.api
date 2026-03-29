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

For detailed guides, please refer to the documentation in the `docs/` folder:

- **[Getting Started](./docs/getting-started.md)**: Installation, prerequisites, and server setup.
- **[Authentication](./docs/authentication.md)**: Managing API keys via the `manage_keys.py` CLI.
- **[API Reference](./docs/api-reference.md)**: Detailed REST endpoint parameters and schemas.
- **[Code Examples](./docs/code-examples.md)**: Production-ready snippets for Python, JS, and cURL.
- **[Live Streaming](./docs/streaming.md)**: WebSocket protocol and data format specifications.
- **[Models](./docs/models.md)**: How to manage and add `ggml` models.

---

## 🛠️ Quick Start

### 1. Installation
```bash
pip install -r requirements.txt
cp .env.example .env
```

### 2. Setup Database & Keys
```bash
python -m app.cli init
python -m app.cli create --name "MyAdminKey"
```

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
