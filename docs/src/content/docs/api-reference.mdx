---
title: REST API Reference
description: Complete reference for the Whisper API REST endpoints — parameters, request formats, response schemas, and error codes.
---


The Whisper API provides both a **Deepgram-compatible** REST & WebSocket interface (`/v1/listen`) and an **OpenAI-compatible** Audio API (`/v1/audio/transcriptions` and `/v1/audio/translations`) for pre-recorded audio transcription, translation, and model management.

---

## Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| <span class="badge badge-post">POST</span> | `/v1/listen` | Transcribe audio — Deepgram-compatible (file upload or URL) |
| <span class="badge badge-post">POST</span> | `/v1/audio/transcriptions` | Transcribe audio — OpenAI-compatible (`multipart/form-data`) |
| <span class="badge badge-post">POST</span> | `/v1/audio/translations` | Translate speech to English — OpenAI-compatible (`multipart/form-data`) |
| <span class="badge badge-get">GET</span> | `/v1/models` | List available & registered models (no auth) |
| <span class="badge badge-get">GET</span> | `/ping` | Health check |
| <span class="badge badge-post">POST</span> | `/v1/auth/test-token` | Generate test token (dev only) |
| <span class="badge badge-ws">WS</span> | `/v1/listen` | Live streaming (see [Streaming docs](/docs/streaming)) |

---

## POST `/v1/listen` — Transcribe Audio (Deepgram-compatible)

The primary Deepgram-compatible transcription endpoint. Accepts audio either as a binary file upload or as a URL in a JSON body. Upload size is capped by `MAX_AUDIO_UPLOAD_BYTES` (default 50 MiB).

### Request Parameters (Query String)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | `string` | `tiny.en` | Model to use (`tiny.en`, `base.en.q5`, `large-v3-turbo.q5`, `whisper-1`, etc.). See `GET /v1/models`. |
| `language` | `string` | `en` | BCP-47 language code for transcription (`en`, `es`, `fr`, `auto`, etc.). |
| `prompt` | `string` | `null` | Context/vocabulary prompt to guide the model (e.g., `"TURNIPS, MUTTON"`). |
| `start` | `integer` | `0` | Offset in **milliseconds** — skip audio before this point. |
| `duration` | `integer` | `null` | Maximum duration in **milliseconds** to process. |
| `response_format` | `string` | `json` | Response format: `json`, `srt`, `vtt`, or `text`. |
| `diarize` | `boolean` | `false` | Enable speaker separation (best with stereo audio). |
| `utterances` | `boolean` | `false` | Return speech interval metadata. |
| `translate` | `boolean` | `false` | Translate source speech into English (`whisper-cli -tr`). |
| `temperature` | `float` | `null` | Sampling temperature (`0.0` to `1.0`). |
| `beam_size` | `integer` | `null` | Beam size for beam search decoding (`1` to `10`). |
| `split_on_word` | `boolean` | `false` | Split segments on word boundaries rather than token boundaries (`-sow`). |
| `vad` | `boolean` | `false` | Enable Silero Voice Activity Detection (`--vad`) to filter non-speech intervals. |

### Request Headers

| Header | Value | Required |
|--------|-------|----------|
| `Authorization` | `Token <your_api_key>` | Yes |
| `Content-Type` | `audio/*` (`wav`, `mpeg`, `mp4`, `ogg`, `flac`, `webm`) or `video/*` (`mp4`, `webm`, `quicktime`, `x-matroska`) | For file upload |
| `Content-Type` | `application/json` | For URL-based transcription |

---

### File Upload

Send raw audio bytes as the request body:

```bash
curl -X POST 'http://localhost:7860/v1/listen?model=tiny.en&language=en' \
  -H "Authorization: Token YOUR_API_KEY" \
  -H "Content-Type: audio/wav" \
  --data-binary @audio.wav
```

### URL-Based Transcription

Send a JSON body with the audio file URL:

```bash
curl -X POST 'http://localhost:7860/v1/listen?model=tiny.en' \
  -H "Authorization: Token YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/audio.mp3"}'
```

### URL fetch rules (SSRF protection)

When you pass `{"url": "..."}`, the server downloads the file for you. To reduce **SSRF** risk (callers tricking your server into hitting internal addresses), the implementation:

- Allows only **`http`** and **`https`** URLs.
- Resolves the hostname and **rejects** addresses that are not **publicly routable** (for example loopback, private RFC1918 ranges, link-local, and IPv6 ULA).
- Enforces a maximum download size (`MAX_AUDIO_DOWNLOAD_BYTES`, default 50 MiB).
- By default **does not follow redirects** (`AUDIO_URL_FOLLOW_REDIRECTS=false`). If you enable redirects for CDN short links, the server re-checks the **final** URL host after redirects.

---

### JSON Response Schema

When `response_format=json` (default), the response follows the Deepgram format:

```json
{
  "metadata": {
    "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "created": "2026-03-29T10:30:00.000000Z",
    "duration": 10.43,
    "channels": 1,
    "sha256": "abc123def456..."
  },
  "results": {
    "channels": [
      {
        "alternatives": [
          {
            "transcript": "And so my fellow Americans ask not what your country can do for you ask what you can do for your country",
            "confidence": 0.98,
            "words": [
              {
                "word": "and",
                "start": 0.0,
                "end": 0.32,
                "confidence": 0.97
              },
              {
                "word": "so",
                "start": 0.32,
                "end": 0.56,
                "confidence": 0.99
              }
            ]
          }
        ]
      }
    ]
  }
}
```

### SRT Response

When `response_format=srt`, raw subtitle text is returned:

```txt
1
00:00:00,000 --> 00:00:03,200
And so my fellow Americans

2
00:00:03,200 --> 00:00:06,800
ask not what your country can do for you

3
00:00:06,800 --> 00:00:10,430
ask what you can do for your country
```

### VTT Response

When `response_format=vtt`:

```txt
WEBVTT

00:00:00.000 --> 00:00:03.200
And so my fellow Americans

00:00:03.200 --> 00:00:06.800
ask not what your country can do for you

00:00:06.800 --> 00:00:10.430
ask what you can do for your country
```

### Plain Text Response

When `response_format=text`, the server returns the plain transcript string with `Content-Type: text/plain`.

---

## POST `/v1/audio/transcriptions` & `/v1/audio/translations` — OpenAI Audio API

Drop-in compatible with the OpenAI Audio API (`client.audio.transcriptions.create` and `client.audio.translations.create`). Accepts `Bearer <key>` or `Token <key>` in the `Authorization` header.

### Form Fields (`multipart/form-data`)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `file` | `file` | *(required)* | Audio or video file to transcribe/translate (`wav`, `mp3`, `m4a`, `mp4`, `webm`, etc.). |
| `model` | `string` | `whisper-1` | Model ID or alias (`whisper-1`, `tiny.en`, `large-v3-turbo.q5`, etc.). |
| `language` | `string` | `auto` | ISO-639-1 language code (`en`, `fr`, `de`, etc.). *Transcriptions only.* |
| `prompt` | `string` | `null` | Optional text prompt to guide style or vocabulary. |
| `response_format` | `string` | `json` | One of `json`, `verbose_json`, `text`, `srt`, or `vtt`. |
| `temperature` | `float` | `null` | Sampling temperature between `0.0` and `1.0`. |
| `timestamp_granularities[]` | `string[]` | `["segment"]` | Include `"word"` and/or `"segment"` timestamps when `response_format=verbose_json`. *Transcriptions only.* |
| `vad` | `boolean` | `false` | Enable Silero VAD (`silero-v6.2.0`) when installed. |

### Example Requests

<Tabs>
  <TabItem label="Transcription (verbose_json)">
  ```bash
  curl -X POST 'http://localhost:7860/v1/audio/transcriptions' \
    -H "Authorization: Bearer YOUR_API_KEY" \
    -F "file=@audio/jfk.wav" \
    -F "model=whisper-1" \
    -F "response_format=verbose_json" \
    -F "timestamp_granularities[]=word" \
    -F "timestamp_granularities[]=segment"
  ```
  </TabItem>
  <TabItem label="Translation to English">
  ```bash
  curl -X POST 'http://localhost:7860/v1/audio/translations' \
    -H "Authorization: Bearer YOUR_API_KEY" \
    -F "file=@spanish_clip.mp3" \
    -F "model=large-v3-turbo.q5" \
    -F "response_format=json"
  ```
  </TabItem>
</Tabs>

### OpenAI Response Schemas

When `response_format=json` (default):

```json
{
  "text": "And so my fellow Americans ask not what your country can do for you ask what you can do for your country"
}
```

When `response_format=verbose_json` with `timestamp_granularities[]=word` and `timestamp_granularities[]=segment`:

```json
{
  "task": "transcribe",
  "language": "en",
  "duration": 10.43,
  "text": "And so my fellow Americans ask not what your country can do for you ask what you can do for your country",
  "segments": [
    {
      "id": 0,
      "seek": 0,
      "start": 0.0,
      "end": 10.43,
      "text": "And so my fellow Americans ask not what your country can do for you ask what you can do for your country",
      "avg_logprob": -0.04,
      "no_speech_prob": 0.01
    }
  ],
  "words": [
    { "word": "And", "start": 0.0, "end": 0.32 },
    { "word": "so", "start": 0.32, "end": 0.56 }
  ]
}
```

---

## GET `/v1/models` — List Models

Returns metadata for each `.bin` model file present under `MODELS_DIR`. Pass `?include_uninstalled=true` to also list registered models (and `silero-v6.2.0`) that have not been downloaded yet. **No authentication required.**

```bash
# Installed transcription models only
curl -X GET 'http://localhost:7860/v1/models'

# All registered models (including not yet downloaded)
curl -X GET 'http://localhost:7860/v1/models?include_uninstalled=true'
```

**Response:**

```json
{
  "models": [
    {
      "name": "whisper-tiny.en",
      "model_id": "tiny.en",
      "description": "Tiny English-only Whisper model (~75MB). Fastest inference, good for English.",
      "language": "en",
      "version": "ggml-v1",
      "file": "ggml-tiny.en.bin",
      "installed": true,
      "size_bytes": 78643200
    }
  ],
  "count": 1
}
```

---

## GET `/ping` — Health Check

A simple health check endpoint (no authentication required):

```bash
curl http://localhost:7860/ping
```

```json
{
  "ping": "pong",
  "status": "healthy"
}
```

---

## Error Responses

| Status Code | Description |
|-------------|-------------|
| `400` | Bad request — invalid parameters, unsupported format, URL policy violation, or download failure |
| `401` | Unauthorized — missing or invalid API key |
| `413` | Payload too large — upload body exceeds `MAX_AUDIO_UPLOAD_BYTES` |
| `415` | Unsupported media type — unrecognized content type |
| `422` | Validation error — malformed request body |
| `500` | Internal server error — transcription or conversion failed |
| `504` | Gateway timeout — `whisper-cli` or ffmpeg exceeded configured timeout |

Concurrent transcriptions wait on an internal limiter (`MAX_CONCURRENT_TRANSCRIPTIONS`); requests are **queued**, not rejected with `503`, unless the client or proxy times out first.

### Error Response Format

```json
{
  "detail": "Invalid or missing API key"
}
```

<Aside type="tip">
  The interactive Swagger UI at `http://localhost:7860/docs` lets you test all endpoints directly in your browser with auto-generated forms and response viewers.
</Aside>
