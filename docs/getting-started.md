# Getting Started

The Whisper API is a high-performance, self-hosted transcription engine built on top of `whisper.cpp`. It provides a Deepgram-compatible REST and WebSocket interface.

## Prerequisites

- **Python 3.10+**: Recommended environment manager (Conda/venv).
- **FFmpeg**: Required for audio transcoding to 16kHz WAV.
- **whisper.cpp Binary**: The `whisper-cli` executable must be present in the `binary/` directory.

## Installation

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/innovatorved/whisper.api.git
    cd whisper.api
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Configuration**:
    Copy `.env.example` to `.env` and configure your paths.
    ```bash
    cp .env.example .env
    ```

4.  **Database and Keys**:
    Initialize the database and create your first API token.
    ```bash
    python -m app.cli init
    python -m app.cli create --name "AdminToken"
    ```

## Running the Server

Start the API with Uvicorn:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 7860 --reload
```

The API will be available at `http://localhost:7860`. You can access the interactive Swagger documentation at `http://localhost:7860/docs`.
