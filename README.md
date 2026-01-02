---
title: whisper.api
emoji: 😶‍🌫️
colorFrom: purple
colorTo: gray
sdk: docker
app_file: Dockerfile
app_port: 7860
---

## Whisper API - Speech to Text Transcription

This open source project provides a self-hostable API for speech to text transcription using a finetuned Whisper ASR model. The API allows you to easily convert audio files to text through HTTP requests. Ideal for adding speech recognition capabilities to your applications.

Key features:

- Uses a finetuned Whisper model for accurate speech recognition
- Simple HTTP API for audio file transcription
- User level access with API keys for managing usage
- Self-hostable code for your own speech transcription service
- Quantized model optimization for fast and efficient inference
- **Asynchronous Processing**: Non-blocking transcription for high availability
- **Concurrency Control**: Built-in request queuing to prevent server overload
- Open source implementation for customization and transparency

This repository contains code to deploy the API server along with finetuning and quantizing models. Check out the documentation for getting started!

## Installation

To install the necessary dependencies and setup the Whisper binary, follow these steps:

### 1. System Dependencies
Install `ffmpeg` for audio processing and build tools (`make`, `cmake`, `g++`) for compiling Whisper.

```bash
# Ubuntu/Debian
sudo apt install ffmpeg git make cmake g++

# macOS
brew install ffmpeg cmake
```

### 2. Python Dependencies
Install the required Python packages.

```bash
pip install -r requirements.txt
```

### 3. Setup Environment
Copy the example environment file and configure it:

```bash
cp .env.example .env
# Edit .env with your database credentials and settings
# Optional: Set MAX_CONCURRENT_TRANSCRIPTIONS (default: 2) in .env to control parallel jobs
```

### 4. Setup Whisper
Run the setup script to clone, build, and configure the Whisper binary.

```bash
chmod +x setup_whisper.sh
./setup_whisper.sh
```

## Running the Project

### Run Locally (without Docker)
To run the project locally (e.g., inside a Conda environment or virtualenv):

```bash
# Ensure your environment is active (e.g., conda activate whisper-api)
uvicorn app.main:app --host 0.0.0.0 --port 7860 --reload
```

### Docker (Production)
To run the project using Docker:

```bash
# Build the image
docker build -t whisper-api .

# Run the container (ensure env vars are passed or secrets used)
# For local testing with .env file:
docker run --env-file .env -p 7860:7860 whisper-api
```

## Get Your token
To get your token, use the following command:

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/users/get_token' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "email": "example@domain.com",
  "password": "password"
}'
```

## Example to Transcribe a File
To upload a file and transcribe it, use the following command:
Note: The token is a dummy token and will not work. Please use the token provided by the admin.

Here are the available models:
- tiny.en
- tiny.en.q5
- base.en.q5

```bash

# Modify the token and audioFilePath
curl -X 'POST' \
  'http://localhost:8000/api/v1/transcribe/?model=tiny.en.q5' \
  -H 'accept: application/json' \
  -H 'Authentication: e9b7658aa93342c492fa64153849c68b8md9uBmaqCwKq4VcgkuBD0G54FmsE8JT' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@audioFilePath.wav;type=audio/wav'
```

## License

[MIT](https://choosealicense.com/licenses/mit/)


## Reference & Credits

- [https://github.com/openai/whisper](https://github.com/openai/whisper)
- [https://openai.com/blog/whisper/](https://openai.com/blog/whisper/)
- [https://github.com/ggerganov/whisper.cpp](https://github.com/ggerganov/whisper.cpp)

  
## Authors

- [Ved Gupta](https://www.github.com/innovatorved)

  
## 🚀 About Me
Just try to be a developer!
  
## Support

For support, email vedgupta@protonmail.com
