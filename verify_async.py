import asyncio
import httpx
import time
import os

# Configuration
BASE_URL = "http://localhost:7860"
AUTH_TOKEN = "73c8be6aa64e47b2b2b79b2f8e64c201RCGHoLb7IDDRB7899cMn3Cgzq7NtuJSL"
TEST_FILE = "test.wav"


async def test_transcribe(client):
    print(f"[{time.time()}] Starting transcription request...")
    if not os.path.exists(TEST_FILE):
        print("Test file not found!")
        return

    with open(TEST_FILE, "rb") as f:
        files = {"file": (TEST_FILE, f, "audio/wav")}
        headers = {"Authentication": AUTH_TOKEN}
        response = await client.post(
            f"{BASE_URL}/api/v1/transcribe/", headers=headers, files=files, timeout=60.0
        )
        print(f"[{time.time()}] Transcription completed: {response.status_code}")
        return response.json()


async def test_ping(client):
    # Wait a tiny bit to ensure transcription request has hit the server
    await asyncio.sleep(0.1)
    print(f"[{time.time()}] Sending ping request...")
    start = time.time()
    response = await client.get(f"{BASE_URL}/ping")
    end = time.time()
    print(f"[{time.time()}] Ping completed in {end - start:.4f}s")
    return end - start


async def main():
    async with httpx.AsyncClient() as client:
        # Run both concurrent
        # We expect ping to finish FAST, even if transcribe takes time.

        # Start transcription task
        transcribe_task = asyncio.create_task(test_transcribe(client))

        # Start ping task
        ping_task = asyncio.create_task(test_ping(client))

        await ping_task
        ping_duration = ping_task.result()

        await transcribe_task
        transcription_result = transcribe_task.result()

        print(f"\nResults:")
        print(f"Ping duration: {ping_duration:.4f}s")
        print(f"Transcription result: {transcription_result}")

        if ping_duration < 1.0:
            print("SUCCESS: Ping was fast (Server is Async!)")
        else:
            print("FAILURE: Ping was slow (Server is Blocking!)")


if __name__ == "__main__":
    asyncio.run(main())
