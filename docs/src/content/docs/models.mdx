---
title: Models
description: Managing whisper.cpp GGML models — available sizes, quantization formats, downloading, and performance comparison.
---


The Whisper API uses **GGML-format** model files (`.bin`) compatible with [whisper.cpp](https://github.com/ggml-org/whisper.cpp). Files live under `MODELS_DIR` (default `models/`). The server exposes a **registered catalog** in `app/utils/constant.py` (`model_names` & `MODEL_ALIASES`):

- `GET /v1/models` lists installed transcription models (pass `?include_uninstalled=true` to see all registered models including Silero VAD).
- On startup, only lightweight `DEFAULT_STARTUP_MODELS` (`tiny.en`, `tiny.en.q5`, `base.en.q5`) are checked/downloaded automatically so boot stays fast. Larger models are downloaded on demand via `python -m app.cli download <model>`.

---

## Registered Models

| Model ID | Disk Size | Language | Quantization | Best For |
|----------|-----------|----------|--------------|----------|
| `tiny.en` | ~75 MB | English | Full | Fastest inference, low-resource devices *(startup default)* |
| `tiny.en.q5` | ~30 MB | English | `q5_1` | Ultra-lightweight, lowest memory *(startup default)* |
| `base.en` | ~142 MB | English | Full | Fast English transcription with better accuracy |
| `base.en.q5` | ~57 MB | English | `q5_1` | Balanced speed and accuracy *(startup default)* |
| `small.en` | ~466 MB | English | Full | Strong accuracy for production English workloads |
| `small.en.q5` | ~181 MB | English | `q5_1` | Great English accuracy-to-memory ratio |
| `medium.en` | ~1.5 GB | English | Full | High accuracy for complex English audio |
| `large-v3` | ~2.9 GB | Multilingual (99) | Full | Maximum accuracy across all supported languages |
| `large-v3-turbo` | ~1.5 GB | Multilingual (99) | Full | Near `large-v3` quality at ~4× faster decoding |
| `large-v3-turbo.q5` | ~547 MB | Multilingual (99) | `q5_0` | **Recommended** multilingual speed/accuracy/memory tradeoff |
| `large-v3-turbo.q8` | ~834 MB | Multilingual (99) | `q8_0` | Near-lossless quantized `large-v3-turbo` |
| `silero-v6.2.0` | ~885 KB | Agnostic | VAD | Silero Voice Activity Detection (`vad=true`) |

<Aside type="tip">
  For most production workloads, **`large-v3-turbo.q5`** (multilingual) or **`small.en.q5`** (English-only) offers the best balance of speed, memory footprint, and transcription accuracy. You can also pass `model=whisper-1` for OpenAI SDK compatibility.
</Aside>

### Model Aliases

The API automatically resolves common OpenAI and Hugging Face model aliases to their canonical registered IDs:

| Alias | Resolves To |
|-------|-------------|
| `whisper-1` | `tiny.en` |
| `large-v3-turbo-q5_0` | `large-v3-turbo.q5` |
| `large-v3-turbo-q8_0` | `large-v3-turbo.q8` |
| `tiny.en-q5_1` | `tiny.en.q5` |
| `base.en-q5_1` | `base.en.q5` |
| `small.en-q5_1` | `small.en.q5` |

---

## Quantization Formats

GGML models support multiple quantization levels to trade accuracy for speed and memory:

| Format | Bits | Size Reduction | Quality | Recommended |
|--------|------|---------------|---------|-------------|
| `f32` | 32-bit | 1x (baseline) | Highest | No (too large) |
| `f16` | 16-bit | ~0.5x | Very High | Research only |
| `q8_0` | 8-bit | ~0.25x | High | Yes, if memory allows |
| `q5_1` | 5-bit | ~0.16x | Good | **Best overall** |
| `q5_0` | 5-bit | ~0.16x | Good | Alternative to q5_1 |
| `q4_1` | 4-bit | ~0.125x | Fair | Max speed priority |
| `q4_0` | 4-bit | ~0.125x | Fair | Smallest size |

---

## Downloading Models

### Using the Built-in CLI (`app.cli`)

You can list all registered models and download any model directly via the CLI without manual `curl` commands:

```bash
# List all registered models, aliases, and installation status
python -m app.cli models

# Download large-v3-turbo (q5_0) or Silero VAD
python -m app.cli download large-v3-turbo.q5
python -m app.cli download silero-v6.2.0
```

### From Hugging Face

Official GGML models are available on the [whisper.cpp Hugging Face repository](https://huggingface.co/ggerganov/whisper.cpp/tree/main):

```bash
# Download tiny.en (q5_1 quantized)
curl -L -o models/ggml-tiny.en-q5_1.bin \
  "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en-q5_1.bin"

# Download small.en (q5_1 quantized)
curl -L -o models/ggml-small.en-q5_1.bin \
  "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en-q5_1.bin"

# Download base.en (full precision)
curl -L -o models/ggml-base.en.bin \
  "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin"
```

### From the Setup Scripts

The `setup_whisper.sh` (macOS/Linux) and `setup_whisper.ps1` (Windows) scripts automatically download the `tiny.en` model if none exists:

```bash
# macOS & Linux
./setup_whisper.sh
```

```powershell
# Windows (PowerShell)
.\setup_whisper.ps1
```

---

## Adding a New Model

<Steps>

1. **Download** the `.bin` file from Hugging Face or another source

2. **Move** it to the `models/` directory:
   ```bash
   mv ggml-small.en-q5_1.bin models/
   ```

3. **Register** the model in `app/utils/constant.py` (`model_names`, and optionally `model_info` / `model_urls`) so the API knows the `model` query id and filename.

4. **Restart** the API server:
   ```bash
   # Stop the running server (Ctrl+C)
   uvicorn app.main:app --host 0.0.0.0 --port 7860
   ```

5. **Verify** the model appears (no auth required):
   ```bash
   curl -X GET 'http://localhost:7860/v1/models'
   ```

</Steps>

---

## Model File Mapping

Each registered model ID in `app/utils/constant.py` maps to a specific `.bin` filename under `MODELS_DIR`:

| API `model` Parameter | File Name in `MODELS_DIR` |
|-----------------------|---------------------------|
| `tiny.en` *(or `whisper-1`)* | `ggml-tiny.en.bin` |
| `tiny.en.q5` | `ggml-model-whisper-tiny.en-q5_1.bin` |
| `base.en.q5` | `ggml-model-whisper-base.en-q5_1.bin` |
| `small.en.q5` | `ggml-small.en-q5_1.bin` |
| `large-v3-turbo.q5` | `ggml-large-v3-turbo-q5_0.bin` |
| `silero-v6.2.0` | `ggml-silero-v6.2.0.bin` |

---

## Model Directory Configuration

The model and VAD paths are configured via environment variables:

```ini
# .env
MODELS_DIR=./models
VAD_MODEL_PATH=./models/ggml-silero-v6.2.0.bin
```

Only **registered** models (see `model_names` and `MODEL_ALIASES`) with a present file under `MODELS_DIR` are listed by `GET /v1/models` and accepted by `/v1/listen` and `/v1/audio/*`. Pass `GET /v1/models?include_uninstalled=true` to inspect all registered models regardless of download status.

<Aside type="note">
  The `models/` directory is included in `.gitignore` by default — model files are too large for version control. Download them during deployment or include them in your Docker image.
</Aside>
