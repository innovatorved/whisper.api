# Examples

### 1. Basic File Upload
Transcribe a local audio file using binary data.
```bash
curl -X POST 'http://localhost:7860/v1/listen?model=tiny.en' \
  -H "Authorization: Token YOUR_API_KEY" \
  -H "Content-Type: audio/wav" \
  --data-binary @audio.wav
```

### 2. Transcribe from Remote URL
Transcribe an audio file hosted on a remote server.
```bash
curl -X POST 'http://localhost:7860/v1/listen?model=tiny.en' \
  -H "Authorization: Token YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/audio.mp3"}'
```

### 3. Advanced Controls (Cropping & Prompting)
Isolate a specific segment (2s to 7s) and guide the model with a custom vocabulary prompt.
```bash
curl -X POST 'http://localhost:7860/v1/listen?start=2000&duration=5000&prompt=MUTTON,TURNIPS' \
  -H "Authorization: Token YOUR_API_KEY" \
  -H "Content-Type: audio/wav" \
  --data-binary @audio.wav
```

### 4. Exporting SRT/VTT Subtitles
Request raw subtitle text directly and save to a file.
```bash
curl -X POST 'http://localhost:7860/v1/listen?response_format=srt' \
  -H "Authorization: Token YOUR_API_KEY" \
  -H "Content-Type: audio/wav" \
  --data-binary @audio.wav > subtitles.srt
```

---

## Live Streaming

### File-based streaming test (Python)
Stream a pre-recorded audio file to the WebSocket endpoint, simulating real-time input.
```bash
python examples/test_streaming.py --token YOUR_API_KEY --audio audio/jfk.wav --model tiny.en
```

### Live microphone transcription (Python)
Stream audio from your microphone for real-time transcription.
```bash
python examples/mic_transcription.py --token YOUR_API_KEY --model tiny.en
```

### WebSocket Connection (using `wscat`)
Connect to the real-time stream and monitor transcription results.
```bash
wscat -c "ws://localhost:7860/v1/listen?token=YOUR_API_KEY&model=tiny.en"
```

---

## Diagnostics

### Check Available Models
```bash
curl -X GET 'http://localhost:7860/v1/models' \
  -H "Authorization: Token YOUR_API_KEY"
```

### Health Check
```bash
curl -X GET 'http://localhost:7860/ping'
```