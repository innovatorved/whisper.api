# Live Streaming (WebSocket)

The Whisper API supports real-time, low-latency transcription via WebSockets.

## Connection Protocol

### Endpoint
`WS /v1/listen`

### Query Parameters
- `token`: **Required** API Key.
- `model`: Model to use (`tiny.en`, `base.en`, etc.).
- `language`: Transcription language (`en`, `es`, `fr`, etc.).
- `encoding`: Optional stream encoding. Default `linear16`.
- `sample_rate`: Optional PCM sample rate. Default `16000`.

`encoding` supports: `linear16`, `pcm16`, `wav`, `webm`, `ogg`, `opus`, `mp3`, `flac`, `mp4`, `m4a`, `auto`.

For browser clients using MediaRecorder/Deepgram SDK, use `encoding=auto` (or explicit `webm`/`ogg`) so the server decodes compressed chunks before transcription.

### Example Connection (using `wscat`)
```bash
wscat -c "ws://localhost:7860/v1/listen?token=YOUR_API_KEY&model=tiny.en&language=en"
```

## Sending Data

Clients can send either:
- **Raw PCM binary bytes** (`encoding=linear16` or `pcm16`)
- **Compressed/container bytes** (`encoding=auto`, `webm`, `ogg`, etc.)

### PCM Format Specifications (`encoding=linear16`)
- **Sample Rate**: 16,000 Hz
- **Bit Depth**: 16-bit
- **Channels**: 1 (Mono)
- **Endianness**: Little-Endian (Native)

## Server Responses

### Initial Metadata

On connection, the server sends a metadata message:
```json
{
  "type": "Metadata",
  "request_id": "c4937a39-3482-414b-be42-2750043044f2",
  "model_info": {
    "tiny.en": {
      "name": "whisper-tiny.en",
      "version": "ggml-v1",
      "arch": "whisper"
    }
  },
  "channels": 1,
  "created": "2026-03-30T00:03:18.621907Z"
}
```

### Transcription Results

As audio is buffered and processed (every ~2 seconds), the server streams JSON results:
```json
{
  "type": "Results",
  "channel_index": [0, 1],
  "duration": 2.05,
  "start": 0.0,
  "is_final": true,
  "speech_final": false,
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
    ],
    "detected_language": "en"
  },
  "metadata": {
    "request_id": "c4937a39-3482-414b-be42-2750043044f2",
    "model_info": {
      "tiny.en": {
        "name": "whisper-tiny.en",
        "version": "ggml-v1",
        "arch": "whisper"
      }
    }
  },
  "from_finalize": false
}
```

## Control Messages

Clients can send JSON-formatted control messages:

### Keep Alive
```json
{ "type": "KeepAlive" }
```

### Close Stream
Signals the server to process any remaining buffered audio and close the session:
```json
{ "type": "CloseStream" }
```

## Examples

### File-based streaming test
```bash
python examples/test_streaming.py --token YOUR_API_KEY --audio audio/jfk.wav --model tiny.en
```

### Live microphone transcription
```bash
python examples/mic_transcription.py --token YOUR_API_KEY --model tiny.en --device 3
```

### List available audio devices
```bash
python examples/mic_transcription.py --list-devices
```
