#!/usr/bin/env python3
"""
Live microphone transcription client for Whisper API.

Streams microphone audio via WebSocket to the Whisper API server
and prints real-time transcription results in Deepgram-compatible JSON.

Usage:
    python examples/mic_transcription.py --token YOUR_TOKEN

    # With custom server:
    python examples/mic_transcription.py --token YOUR_TOKEN --host 192.168.1.100 --port 7860

    # List available audio devices:
    python examples/mic_transcription.py --list-devices

    # Use a specific audio device:
    python examples/mic_transcription.py --token YOUR_TOKEN --device 3

Requirements:
    pip install pyaudio websockets
"""

import argparse
import asyncio
import json
import os
import signal
import sys
import time

try:
    import pyaudio
except ImportError:
    print("ERROR: pyaudio not installed. Install it:")
    print("  pip install pyaudio")
    sys.exit(1)

try:
    import websockets
except ImportError:
    print("ERROR: websockets not installed. Install it:")
    print("  pip install websockets")
    sys.exit(1)


# Audio capture parameters (must match server expectations: 16kHz, 16-bit, mono)
SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2  # 16-bit = 2 bytes
CHANNELS = 1
FRAMES_PER_BUFFER = 4096  # ~0.256s per read at 16kHz


async def transcribe_microphone(host: str, port: str, token: str, model: str, device_index: int = None):
    """Stream microphone audio to the Whisper API and print results."""

    # Build WebSocket URL
    ws_url = f"ws://{host}:{port}/v1/listen?token={token}&model={model}"
    print(f"[CONNECT] {ws_url}")

    stop_event = asyncio.Event()
    ctrl_c_count = 0

    # Handle Ctrl+C — first press stops gracefully, second press force-exits
    def signal_handler(sig, frame):
        nonlocal ctrl_c_count
        ctrl_c_count += 1
        if ctrl_c_count == 1:
            print("\n\n[STOP] Stopping gracefully... (press Ctrl+C again to force quit)")
            stop_event.set()
        else:
            print("\n[STOP] Force quitting!")
            os._exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        async with websockets.connect(ws_url) as ws:
            print("[OK] WebSocket connected")

            # -- Receive task: print incoming transcription results --
            async def receive_messages():
                try:
                    async for message in ws:
                        data = json.loads(message)
                        msg_type = data.get("type", "unknown")

                        if msg_type == "Metadata":
                            print(f"\n[METADATA]")
                            print(json.dumps(data, indent=2))

                        elif msg_type == "Results":
                            print(f"\n[RESULT]")
                            print(json.dumps(data, indent=2))

                        elif msg_type == "Error":
                            print(f"\n[ERROR]")
                            print(json.dumps(data, indent=2))

                except websockets.ConnectionClosed:
                    pass

            receiver = asyncio.create_task(receive_messages())

            # -- Microphone capture setup --
            audio = pyaudio.PyAudio()

            # Pick device
            if device_index is not None:
                dev_info = audio.get_device_info_by_index(device_index)
                dev_name = dev_info['name']
            else:
                dev_info = audio.get_default_input_device_info()
                device_index = int(dev_info['index'])
                dev_name = dev_info['name']

            print(f"[DEVICE] Using input device [{device_index}]: {dev_name}")

            stream = audio.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=FRAMES_PER_BUFFER,
            )

            print(f"\n[LISTEN] Listening... (model: {model})")
            print("         Speak now. Press Ctrl+C to stop.\n")
            print("-" * 60)

            loop = asyncio.get_event_loop()
            chunks_sent = 0

            try:
                while not stop_event.is_set():
                    # Read from microphone (blocking call in executor)
                    try:
                        pcm_data = await asyncio.wait_for(
                            loop.run_in_executor(
                                None, lambda: stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
                            ),
                            timeout=1.0,
                        )
                    except asyncio.TimeoutError:
                        continue

                    # Send PCM audio bytes via WebSocket
                    await ws.send(pcm_data)
                    chunks_sent += 1

                    # Visual indicator every ~0.5s
                    if chunks_sent % 2 == 0:
                        print(".", end="", flush=True)

            except Exception as e:
                print(f"\n[WARN] Microphone error: {e}")

            # -- Cleanup --
            print("\n\nShutting down...")
            stream.stop_stream()
            stream.close()
            audio.terminate()

            # Send CloseStream to flush remaining audio
            try:
                await ws.send(json.dumps({"type": "CloseStream"}))
                print("[SEND] CloseStream sent, waiting for final results...")
                await asyncio.sleep(3)
            except websockets.ConnectionClosed:
                pass

            receiver.cancel()
            try:
                await receiver
            except asyncio.CancelledError:
                pass

            print(f"\n[DONE] Sent {chunks_sent} audio chunks "
                  f"({chunks_sent * FRAMES_PER_BUFFER / SAMPLE_RATE:.1f}s of audio).")

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"\n[ERROR] Connection rejected (HTTP {e.status_code})")
    except ConnectionRefusedError:
        print(f"\n[ERROR] Cannot connect to {host}:{port}. Is the server running?")
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Live microphone transcription using Whisper API (WebSocket)"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Server host")
    parser.add_argument("--port", default="7860", help="Server port")
    parser.add_argument("--token", default=None, help="API token")
    parser.add_argument("--device", type=int, default=None, help="Audio input device index (run with --list-devices to see available)")
    parser.add_argument("--list-devices", action="store_true", help="List audio input devices and exit")
    parser.add_argument("--model", default="tiny.en", help="Whisper model to use")
    args = parser.parse_args()

    # List devices mode
    if args.list_devices:
        a = pyaudio.PyAudio()
        print("Available input devices:")
        for i in range(a.get_device_count()):
            d = a.get_device_info_by_index(i)
            if d['maxInputChannels'] > 0:
                dflt = " (DEFAULT)" if i == a.get_default_input_device_info()['index'] else ""
                print(f"  [{i}] {d['name']} - ch={d['maxInputChannels']}, rate={d['defaultSampleRate']}{dflt}")
        a.terminate()
        return

    # Auto-detect token from token.txt
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
            print("ERROR: No token provided. Use --token YOUR_TOKEN")
            sys.exit(1)

    print("Whisper API - Live Microphone Transcription")
    print(f"  Server: ws://{args.host}:{args.port}/v1/listen")
    print(f"  Model:  {args.model}")
    print(f"  Token:  {token[:8]}...{token[-4:]}")
    print()

    asyncio.run(transcribe_microphone(args.host, args.port, token, args.model, args.device))


if __name__ == "__main__":
    main()
