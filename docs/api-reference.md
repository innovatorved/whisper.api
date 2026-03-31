# API Reference

The Whisper API mimics the Deepgram API structure to facilitate seamless migration.

## Pre-Recorded Audio

`POST /v1/listen` (Upload File or URL)

### Request Parameters (Query String)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | `string` | `tiny.en` | Model to use. Check `/v1/models` for options. |
| `language` | `string` | `en` | BCP-47 language code for transcription. |
| `prompt` | `string` | `null` | Context/Prompt to guide the model (e.g. "TURNIPS, MUTTON"). |
| `start` | `integer` | `0` | Offset in milliseconds for the start of audio processing. |
| `duration` | `integer` | `null` | Maximum duration in milliseconds to process. |
| `response_format` | `string` | `json` | Format of the response (`json`, `srt`, `vtt`). |
| `diarize` | `boolean` | `false` | Enable speaker separation (requires stereo audio). |
| `utterances` | `boolean` | `false` | Return speech intervals in metadata. |

### Request Headings
- `Authorization`: `Token <your_api_key>`
- `Content-Type`: `audio/wav`, `audio/mpeg`, etc. (for file upload) or `application/json` (for URL)

### Request Body (JSON for URL)
```json
{
  "url": "https://example.com/audio.mp3"
}
```

### JSON Response Example
```json
{
  "metadata": {
    "request_id": "...",
    "created": "2026-03-29T...",
    "duration": 10.43,
    "sha256": "..."
  },
  "results": {
    "channels": [
      {
        "alternatives": [
          {
            "transcript": "Hello world",
            "confidence": 0.98,
            "words": [...]
          }
        ]
      }
    ]
  }
}
```

## Available Models

`GET /v1/models`

Returns a list of all `.bin` models currently loaded in the `models/` directory.

---

For production-ready integration snippets, check the **[Code Examples](./code-examples.md)** guide.

