# whisper.api

This is a production level project structure for a Python FastAPI project.

## Project Structure

```
whisper.api
├── app
│   ├── __init__.py
│   ├── api
│   │   ├── __init__.py
│   │   ├── endpoints
│   │   │   ├── __init__.py
│   │   │   ├── items.py
│   │   │   └── users.py
│   │   └── models
│   │       ├── __init__.py
│   │       ├── item.py
│   │       └── user.py
│   ├── core
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── security.py
│   │   └── database.py
│   ├── tests
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_api
│   │   │   ├── __init__.py
│   │   │   ├── test_items.py
│   │   │   └── test_users.py
│   │   └── test_core
│   │       ├── __init__.py
│   │       ├── test_config.py
│   │       ├── test_security.py
│   │       └── test_database.py
│   └── main.py
├── .env
├── .gitignore
├── Dockerfile
├── requirements.txt
├── README.md
└── .vscode
    ├── settings.json
    └── launch.json
```

## Description


## Install Dependecy
```bash
# Install ffmpeg for Audio Processing
sudo apt install ffmpeg

# Install Python Package
pip install -r requirements.txt

```

## Run this Project

```bash
uvicorn app.main:app --reload
```

# Upload File
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/transcribe/' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'audio_file=@ElevenLabs_2023-08-10T13 53 05.000Z_VedVoice_bFrkzQsyKvReo52Q6712.mp3;type=audio/mpeg'
```