# Live Transcription Studio

Realtime frontend speech-to-text demo built with Vite, React, Tailwind CSS, and `@deepgram/sdk` targeting `whisper.api`.

## Getting Started

```bash
bun install
bun run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

Update `DEEPGRAM_API_KEY` and `DEEPGRAM_BASE_URL` in `src/App.tsx` to point to your Whisper API server.

## Production Build

```bash
bun run build
bun run preview
```
