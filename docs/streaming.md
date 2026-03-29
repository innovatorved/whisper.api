# Live Streaming (WebSocket)

The Whisper API supports real-time, low-latency transcription via WebSockets.

## Connection Protocol

### Endpoint
`WS /v1/listen`

### Query Parameters
- `token`: **Required** API Key.
- `model`: Model to use (`tiny.en`, `base.en`, etc.).
- `language`: Transcription language (`en`, `es`, `fr`, etc.).

### Example Connection (using `wscat`)
```bash
wscat -c "ws://localhost:7860/v1/listen?token=90e4b31...&model=tiny.en&language=en"
```

## Sending Data

Clients should send **raw PCM binary bytes** to the server.

### Format Specifications:
- **Sample Rate**: 16,000 Hz
- **Bit Depth**: 16-bit
- **Channels**: 1 (Mono)
- **Endianness**: Little-Endian (Native)

## Server Responses

The server will stream JSON results as speech is processed:
```json
{
  "channel": {
    "alternatives": [
      {
        "transcript": "Hello world",
        "confidence": 0.98,
        "words": [
          { "word": "hello", "start": 0.0, "end": 0.5, "confidence": 0.97 },
          { "word": "world", "start": 0.5, "end": 1.0, "confidence": 0.99 }
        ]
      }
    ]
  },
  "metadata": {
    "request_id": "...",
    "created": "..."
  }
}
```

## Control Messages (Optional)

Clients can also send JSON-formatted control messages:

### Keep Alive
```json
{ "type": "KeepAlive" }
```

### Close Stream
```json
{ "type": "CloseStream" }
```
