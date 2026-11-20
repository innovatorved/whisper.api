---
title: Code Examples
description: Production-ready code snippets for cURL, Python, JavaScript, and the OpenAI SDK — file upload, translation, URL transcription, streaming, and diagnostics.
---


Complete, copy-paste-ready examples for integrating with the Whisper API. Replace `YOUR_API_KEY` with an actual token from `python -m app.cli create`.

---

## OpenAI-Compatible Audio API

Use the official OpenAI Python/JS SDKs or cURL directly against `/v1/audio/transcriptions` and `/v1/audio/translations` by pointing `base_url` to your Whisper API server:

<Tabs>
  <TabItem label="Python (OpenAI SDK)">
  ```python
  from openai import OpenAI

  client = OpenAI(
      api_key="YOUR_API_KEY",
      base_url="http://localhost:7860/v1",
  )

  # Transcribe with word-level & segment-level timestamps
  with open("audio/jfk.wav", "rb") as audio_file:
      transcript = client.audio.transcriptions.create(
          model="whisper-1",
          file=audio_file,
          response_format="verbose_json",
          timestamp_granularities=["word", "segment"],
      )

  print(transcript.text)
  for word in transcript.words:
      print(f"{word.start:.2f}s - {word.end:.2f}s: {word.word}")

  # Translate non-English speech to English
  with open("spanish_clip.mp3", "rb") as audio_file:
      translation = client.audio.translations.create(
          model="large-v3-turbo.q5",
          file=audio_file,
      )

  print(translation.text)
  ```
  </TabItem>
  <TabItem label="JavaScript (OpenAI SDK)">
  ```javascript
  import fs from 'fs';
  import OpenAI from 'openai';

  const client = new OpenAI({
    apiKey: 'YOUR_API_KEY',
    baseURL: 'http://localhost:7860/v1',
  });

  const transcript = await client.audio.transcriptions.create({
    model: 'whisper-1',
    file: fs.createReadStream('audio/jfk.wav'),
    response_format: 'verbose_json',
    timestamp_granularities: ['word', 'segment'],
  });

  console.log(transcript.text);
  console.log(transcript.words);
  ```
  </TabItem>
  <TabItem label="cURL">
  ```bash
  # Transcription with word timestamps
  curl -X POST 'http://localhost:7860/v1/audio/transcriptions' \
    -H "Authorization: Bearer YOUR_API_KEY" \
    -F "file=@audio/jfk.wav" \
    -F "model=whisper-1" \
    -F "response_format=verbose_json" \
    -F "timestamp_granularities[]=word"

  # Translation to English
  curl -X POST 'http://localhost:7860/v1/audio/translations' \
    -H "Authorization: Bearer YOUR_API_KEY" \
    -F "file=@spanish_clip.mp3" \
    -F "model=large-v3-turbo.q5"
  ```
  </TabItem>
</Tabs>

---

## File Upload (Deepgram Format)

Transcribe a local audio file by sending raw bytes:

<Tabs>
  <TabItem label="cURL">
  ```bash
  curl -X POST 'http://localhost:7860/v1/listen?model=tiny.en' \
    -H "Authorization: Token YOUR_API_KEY" \
    -H "Content-Type: audio/wav" \
    --data-binary @audio.wav
  ```
  </TabItem>
  <TabItem label="Python">
  ```python
  import httpx

  API_URL = "http://localhost:7860/v1/listen"
  API_KEY = "YOUR_API_KEY"

  with open("audio.wav", "rb") as f:
      response = httpx.post(
          API_URL,
          params={"model": "tiny.en"},
          headers={
              "Authorization": f"Token {API_KEY}",
              "Content-Type": "audio/wav",
          },
          content=f.read(),
          timeout=60.0,
      )

  data = response.json()
  transcript = data["results"]["channels"][0]["alternatives"][0]["transcript"]
  print(f"Transcript: {transcript}")
  ```
  </TabItem>
  <TabItem label="JavaScript">
  ```javascript
  const fs = require('fs');

  const API_URL = 'http://localhost:7860/v1/listen';
  const API_KEY = 'YOUR_API_KEY';

  const audioBuffer = fs.readFileSync('audio.wav');

  const response = await fetch(`${API_URL}?model=tiny.en`, {
    method: 'POST',
    headers: {
      'Authorization': `Token ${API_KEY}`,
      'Content-Type': 'audio/wav',
    },
    body: audioBuffer,
  });

  const data = await response.json();
  const transcript = data.results.channels[0].alternatives[0].transcript;
  console.log(`Transcript: ${transcript}`);
  ```
  </TabItem>
</Tabs>

---

## URL-Based Transcription

Transcribe an audio file hosted at a remote URL:

<Tabs>
  <TabItem label="cURL">
  ```bash
  curl -X POST 'http://localhost:7860/v1/listen?model=tiny.en' \
    -H "Authorization: Token YOUR_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"url": "https://example.com/audio.mp3"}'
  ```
  </TabItem>
  <TabItem label="Python">
  ```python
  import httpx

  response = httpx.post(
      "http://localhost:7860/v1/listen",
      params={"model": "tiny.en"},
      headers={"Authorization": "Token YOUR_API_KEY"},
      json={"url": "https://example.com/audio.mp3"},
      timeout=60.0,
  )

  print(response.json())
  ```
  </TabItem>
  <TabItem label="JavaScript">
  ```javascript
  const response = await fetch(
    'http://localhost:7860/v1/listen?model=tiny.en',
    {
      method: 'POST',
      headers: {
        'Authorization': 'Token YOUR_API_KEY',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        url: 'https://example.com/audio.mp3',
      }),
    }
  );

  console.log(await response.json());
  ```
  </TabItem>
</Tabs>

---

## Advanced Controls

### Audio Cropping

Process only a specific segment of the audio — skip to 2 seconds and process 5 seconds:

```bash
curl -X POST 'http://localhost:7860/v1/listen?start=2000&duration=5000' \
  -H "Authorization: Token YOUR_API_KEY" \
  -H "Content-Type: audio/wav" \
  --data-binary @audio.wav
```

### Custom Vocabulary Prompting

Guide the model to correctly recognize domain-specific terms:

```bash
curl -X POST 'http://localhost:7860/v1/listen?prompt=MUTTON,TURNIPS,KUBERNETES' \
  -H "Authorization: Token YOUR_API_KEY" \
  -H "Content-Type: audio/wav" \
  --data-binary @audio.wav
```

<Aside type="tip">
  Prompting is especially useful for proper nouns, technical terms, and acronyms that the model might otherwise misrecognize.
</Aside>

### Silero VAD, Translation & Decoding Parameters

Enable Silero Voice Activity Detection (`vad=true`), translate to English (`translate=true`), and tune decoding options (`temperature`, `beam_size`, `split_on_word`):

```bash
curl -X POST 'http://localhost:7860/v1/listen?model=large-v3-turbo.q5&translate=true&vad=true&beam_size=5&temperature=0.0&split_on_word=true' \
  -H "Authorization: Token YOUR_API_KEY" \
  -H "Content-Type: audio/mpeg" \
  --data-binary @interview.mp3
```

---

## Subtitle & Plain-Text Export

### Plain Text Format

```bash
curl -X POST 'http://localhost:7860/v1/listen?response_format=text' \
  -H "Authorization: Token YOUR_API_KEY" \
  -H "Content-Type: audio/wav" \
  --data-binary @audio.wav
```

### SRT Format

```bash
curl -X POST 'http://localhost:7860/v1/listen?response_format=srt' \
  -H "Authorization: Token YOUR_API_KEY" \
  -H "Content-Type: audio/wav" \
  --data-binary @audio.wav > subtitles.srt
```

### VTT Format

```bash
curl -X POST 'http://localhost:7860/v1/listen?response_format=vtt' \
  -H "Authorization: Token YOUR_API_KEY" \
  -H "Content-Type: audio/wav" \
  --data-binary @audio.wav > subtitles.vtt
```

---

## Live Streaming

### WebSocket with Python

```python
import asyncio
import websockets
import json

async def stream_file(file_path, token, model="tiny.en"):
    uri = f"ws://localhost:7860/v1/listen?token={token}&model={model}"

    async with websockets.connect(uri) as ws:
        # Read initial metadata
        metadata = json.loads(await ws.recv())
        print(f"Connected: {metadata['request_id']}")

        # Stream audio in chunks
        with open(file_path, "rb") as f:
            while chunk := f.read(8000):
                await ws.send(chunk)
                await asyncio.sleep(0.25)  # Simulate real-time

        # Signal end
        await ws.send(json.dumps({"type": "CloseStream"}))

        # Collect remaining results
        async for msg in ws:
            result = json.loads(msg)
            if result.get("type") == "Results":
                text = result["channel"]["alternatives"][0]["transcript"]
                if text.strip():
                    print(f"[{result['start']:.1f}s] {text}")

asyncio.run(stream_file("audio.wav", "YOUR_API_KEY"))
```

### Using the Included Example Scripts

```bash
# File-based streaming
python examples/test_streaming.py \
  --token YOUR_API_KEY \
  --audio audio/jfk.wav \
  --model tiny.en

# Live microphone
python examples/mic_transcription.py \
  --token YOUR_API_KEY \
  --model tiny.en

# List audio devices
python examples/mic_transcription.py --list-devices
```

### WebSocket with `wscat`

```bash
# Install wscat
npm install -g wscat

# Connect
wscat -c "ws://localhost:7860/v1/listen?token=YOUR_API_KEY&model=tiny.en"
```

---

## Diagnostics

### Check Available Models

```bash
# Installed transcription models
curl -X GET 'http://localhost:7860/v1/models'

# All registered models (including uninstalled & Silero VAD)
curl -X GET 'http://localhost:7860/v1/models?include_uninstalled=true'
```

### Health Check

```bash
curl http://localhost:7860/ping
```

### API Documentation

Open in your browser:

```
http://localhost:7860/docs    # Swagger UI
http://localhost:7860/redoc   # ReDoc
```
