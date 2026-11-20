---
title: Whisper API
description: Open-source, high-performance, self-hosted speech-to-text API powered by whisper.cpp with Deepgram and OpenAI compatibility.
template: splash
hero:
  tagline: A self-hosted, Deepgram- and OpenAI-compatible speech-to-text API powered by whisper.cpp. Full data ownership, cross-platform acceleration, and production-ready from day one.
  actions:
    - text: Get Started
      link: /docs/getting-started
      icon: right-arrow
      variant: primary
    - text: API Reference
      link: /docs/api-reference
      icon: external
      variant: minimal
---


## What is Whisper API?

Whisper API wraps the blazing-fast [whisper.cpp](https://github.com/ggml-org/whisper.cpp) engine ([custom fork with native video input](https://github.com/innovatorved/whisper.cpp)) with both a **Deepgram-compatible** (`/v1/listen` REST & WebSocket) and an **OpenAI-compatible** (`/v1/audio/transcriptions` & `/v1/audio/translations`) interface. Deploy it on your own infrastructure — your audio never leaves your servers.

It handles everything from pre-recorded audio/video uploads and URL ingestion to real-time microphone streaming, with word-level timestamps (`-ojf`), Silero VAD filtering, translation to English, speaker diarization, and subtitle export (SRT/VTT).

---

## Core Capabilities

<CardGrid>
  <Card title="Dual Industry-Standard APIs" icon="puzzle">
    Drop-in replacement for Deepgram (`/v1/listen`) and OpenAI Audio (`/v1/audio/transcriptions`, `/v1/audio/translations`) with `whisper-1` aliasing and official SDK support.
  </Card>
  <Card title="Real-Time Streaming" icon="rocket">
    WebSocket endpoint for live transcription. Supports PCM, WebM, OGG, FLAC, auto-detection, and cumulative container decoding.
  </Card>
  <Card title="Cross-Platform Acceleration" icon="laptop">
    Native setup scripts for macOS (Metal/Accelerate/CoreML), Linux (x86_64/ARM64/CUDA), and Windows (MSVC/MinGW/CUDA) with zero cloud dependency.
  </Card>
  <Card title="Offline Key & Model CLI" icon="approve-check-circle">
    Create/revoke API keys and download GGML models (`large-v3-turbo`, quantized models, Silero VAD) directly via `python -m app.cli`.
  </Card>
</CardGrid>

---

## Architecture

The server sits between your clients and the `whisper-cli` binary, handling audio/video conversion, authentication, concurrency limiting, and response formatting.

```
Client (cURL / Python / JS / OpenAI SDK / Deepgram SDK)
  │
  ▼  HTTP POST or WebSocket
FastAPI Server (:7860)
  ├── /v1/listen               POST → Transcribe audio/video file or URL (Deepgram format)
  ├── /v1/listen               WS   → Real-time streaming transcription
  ├── /v1/audio/transcriptions POST → Transcribe audio/video (OpenAI format)
  ├── /v1/audio/translations   POST → Translate speech to English (OpenAI format)
  ├── /v1/models               GET  → List installed & registered GGML models (no auth)
  └── /v1/auth/test-token      POST → Mint API key (dev only; disabled by default)
  │
  ▼  subprocess (-ojf full JSON + optional Silero VAD)
whisper-cli (compiled from innovatorved/whisper.cpp)
  │
  ▼  reads
models/ggml-*.bin (GGML quantized Whisper & Silero VAD models)
```

---

## Quick Links

<CardGrid>
  <LinkCard title="Installation" href="/docs/getting-started" description="Clone, install dependencies, build the binary on macOS/Linux/Windows, and start the server." />
  <LinkCard title="REST Reference" href="/docs/api-reference" description="Parameters, headers, response schemas, and error codes for Deepgram and OpenAI endpoints." />
  <LinkCard title="WebSocket Streaming" href="/docs/streaming" description="Connection protocol, audio formats, control messages, and example scripts." />
  <LinkCard title="Docker" href="/docs/docker" description="Production deployment with Docker, Docker Compose, and NVIDIA CUDA." />
</CardGrid>

---

## Stack

| Layer | Technology |
|-------|-----------|
| Runtime | Python 3.11+ / FastAPI |
| Transcription | whisper.cpp (C++ binary via subprocess with `-ojf` word timestamps) |
| Models | GGML Whisper models (`large-v3-turbo`, `small.en`, `tiny.en`, etc.) + Silero VAD v6.2.0 |
| Database | SQLite (or PostgreSQL) via SQLAlchemy 2.x |
| Streaming | Native FastAPI WebSocket |
| Container | Docker (`python:3.12-slim-bookworm`) |
| License | MIT |
