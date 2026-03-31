#!/usr/bin/env python3
"""
Standalone WebSocket streaming test for Whisper API.

Streams a known audio file in chunks (simulating real-time microphone input)
to the /v1/listen WebSocket endpoint and prints Deepgram-compatible JSON results.

Usage:
    # Convert a WAV to raw PCM first (if not 16kHz mono):
    ffmpeg -y -i audio/jfk.wav -f s16le -acodec pcm_s16le -ar 16000 -ac 1 /tmp/test_pcm.raw

    # Run the test:
    python examples/test_streaming.py --token YOUR_TOKEN --audio audio/jfk.wav

Requirements:
    pip install websockets
"""

import argparse
import asyncio
import json
import os
import struct
import sys
import time
import wave

try:
    import websockets
except ImportError:
    print("ERROR: 'websockets' library not found. Install it:")
    print("  pip install websockets")
    sys.exit(1)


# Audio parameters (must match server expectations)
SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2  # 16-bit = 2 bytes
CHANNELS = 1
CHUNK_SIZE = 4096  # bytes per chunk (~0.128s per chunk)
INTER_CHUNK_DELAY = CHUNK_SIZE / (SAMPLE_RATE * SAMPLE_WIDTH)  # real-time pacing


def wav_to_raw_pcm(wav_path: str) -> bytes:
    """Read a WAV file and return raw PCM bytes."""
    with wave.open(wav_path, "rb") as wf:
        assert wf.getnchannels() == CHANNELS, f"Expected {CHANNELS} channel, got {wf.getnchannels()}"
        assert wf.getsampwidth() == SAMPLE_WIDTH, f"Expected {SAMPLE_WIDTH}-byte samples, got {wf.getsampwidth()}"
        assert wf.getframerate() == SAMPLE_RATE, f"Expected {SAMPLE_RATE}Hz, got {wf.getframerate()}"
        return wf.readframes(wf.getnframes())


async def test_streaming(host: str, port: str, token: str, model: str, audio_file: str):
    """Connect to the WebSocket endpoint and stream audio."""

    # Determine if audio_file is WAV or raw PCM
    if audio_file.endswith(".wav"):
        print(f"[READ] WAV file: {audio_file}")
        try:
            pcm_data = wav_to_raw_pcm(audio_file)
        except (AssertionError, wave.Error) as e:
            print(f"[WARN] WAV format mismatch ({e}). Converting with ffmpeg...")
            raw_path = "/tmp/whisper_test_pcm.raw"
            os.system(
                f"ffmpeg -y -i {audio_file} -f s16le -acodec pcm_s16le "
                f"-ar {SAMPLE_RATE} -ac {CHANNELS} {raw_path} 2>/dev/null"
            )
            with open(raw_path, "rb") as f:
                pcm_data = f.read()
    else:
        print(f"[READ] Raw PCM file: {audio_file}")
        with open(audio_file, "rb") as f:
            pcm_data = f.read()

    total_duration = len(pcm_data) / (SAMPLE_RATE * SAMPLE_WIDTH)
    total_chunks = (len(pcm_data) + CHUNK_SIZE - 1) // CHUNK_SIZE
    print(f"[INFO] Audio: {len(pcm_data)} bytes = {total_duration:.2f}s, {total_chunks} chunks")

    # Build WebSocket URL
    ws_url = f"ws://{host}:{port}/v1/listen?token={token}&model={model}"
    print(f"[CONNECT] {ws_url}")

    results_received = []
    errors_received = []

    try:
        async with websockets.connect(ws_url) as ws:
            print("[OK] WebSocket connected")

            # Start a task to receive messages
            async def receive_messages():
                try:
                    async for message in ws:
                        data = json.loads(message)
                        msg_type = data.get("type", "unknown")

                        if msg_type == "Metadata":
                            print(f"\n[METADATA] request_id={data.get('request_id')}")
                            print(json.dumps(data, indent=2))

                        elif msg_type == "Results":
                            transcript = (
                                data.get("channel", {})
                                .get("alternatives", [{}])[0]
                                .get("transcript", "")
                            )
                            error = data.get("error")
                            start = data.get("start", 0)
                            duration = data.get("duration", 0)

                            if error:
                                print(f"\n[ERROR] at {start:.1f}s: {error}")
                                errors_received.append(error)
                            elif transcript.strip():
                                print(f"\n[TRANSCRIPT] [{start:.1f}s-{start+duration:.1f}s]: \"{transcript.strip()}\"")
                                print(json.dumps(data, indent=2))
                                results_received.append(transcript.strip())
                            else:
                                print(f"\n[SILENCE] [{start:.1f}s-{start+duration:.1f}s]")

                        elif msg_type == "Error":
                            print(f"\n[ERROR] {data.get('message')}")
                            print(json.dumps(data, indent=2))
                            errors_received.append(data.get("message", ""))

                        else:
                            print(f"\n[UNKNOWN] type='{msg_type}': {json.dumps(data, indent=2)[:200]}")

                except websockets.ConnectionClosed:
                    print("\n[CLOSED] Connection closed by server")

            receiver_task = asyncio.create_task(receive_messages())

            # Send audio data
            print(f"\n[STREAM] Sending {total_chunks} chunks (pacing: {INTER_CHUNK_DELAY*1000:.0f}ms/chunk)...\n")
            chunks_sent = 0
            start_time = time.time()

            offset = 0
            while offset < len(pcm_data):
                chunk = pcm_data[offset:offset + CHUNK_SIZE]
                await ws.send(chunk)
                offset += CHUNK_SIZE
                chunks_sent += 1

                # Visual progress
                if chunks_sent % 8 == 0:
                    elapsed = time.time() - start_time
                    audio_time = chunks_sent * INTER_CHUNK_DELAY
                    print(f"  [SEND] {chunks_sent}/{total_chunks} chunks "
                          f"({audio_time:.1f}s audio in {elapsed:.1f}s wall)", end="\r")

                # Pace to simulate real-time
                await asyncio.sleep(INTER_CHUNK_DELAY)

            elapsed = time.time() - start_time
            print(f"\n\n[DONE] Finished sending {chunks_sent} chunks in {elapsed:.1f}s")

            # Wait for server to process remaining data
            print("[WAIT] Waiting 3s for final results...")
            await asyncio.sleep(3)

            # Send CloseStream command
            print("[SEND] CloseStream")
            await ws.send(json.dumps({"type": "CloseStream"}))

            # Wait for close response
            await asyncio.sleep(2)

            # Cancel receiver
            receiver_task.cancel()
            try:
                await receiver_task
            except asyncio.CancelledError:
                pass

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"\n[ERROR] Connection rejected with status {e.status_code}")
        return
    except ConnectionRefusedError:
        print(f"\n[ERROR] Connection refused. Is the server running on {host}:{port}?")
        return
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        return

    # Summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    print(f"  Transcripts received: {len(results_received)}")
    print(f"  Errors received:      {len(errors_received)}")
    if results_received:
        full = " ".join(results_received)
        print(f"  Full transcript:      \"{full}\"")
    if errors_received:
        for err in errors_received:
            print(f"  Error: {err}")

    if results_received:
        print("\n[PASS] Streaming test passed - received transcription output")
    else:
        print("\n[FAIL] Streaming test failed - no transcription received")


def main():
    parser = argparse.ArgumentParser(description="Test WebSocket streaming transcription")
    parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("--port", default="7860", help="Server port (default: 7860)")
    parser.add_argument("--token", default=None, help="API token (reads from token.txt if not provided)")
    parser.add_argument("--model", default="tiny.en", help="Whisper model (default: tiny.en)")
    parser.add_argument("--audio", default="audio/jfk.wav", help="Audio file path (WAV or raw PCM)")
    args = parser.parse_args()

    # Auto-detect token
    token = args.token
    if not token:
        token_file = os.path.join(os.path.dirname(__file__), "..", "token.txt")
        if os.path.exists(token_file):
            with open(token_file) as f:
                content = f.read().strip()
                for line in content.splitlines():
                    line = line.strip()
                    if len(line) > 20 and not line.startswith("#"):
                        token = line
                        break
        if not token:
            print("ERROR: No token provided and token.txt not found.")
            print("Usage: python examples/test_streaming.py --token YOUR_TOKEN")
            sys.exit(1)

    print("Whisper API - WebSocket Streaming Test")
    print(f"  Server: {args.host}:{args.port}")
    print(f"  Model:  {args.model}")
    print(f"  Audio:  {args.audio}")
    print(f"  Token:  {token[:8]}...{token[-4:]}")
    print()

    asyncio.run(test_streaming(args.host, args.port, token, args.model, args.audio))


if __name__ == "__main__":
    main()
