# Whisper API (`whisper.api`) — Comprehensive Architecture Audit, Upstream Synchronization & v2.1.0 Upgrade Report

**Date:** October 22, 2026  
**Repository:** `innovatorved/whisper.api`  
**Fork Synchronized:** [`innovatorved/whisper.cpp`](https://github.com/innovatorved/whisper.cpp) (`develop` @ `efa0df3c`, merged with [`ggml-org/whisper.cpp`](https://github.com/ggml-org/whisper.cpp) `master` @ `231638a0`)  
**Target Release Version:** `v2.1.0`

---

## 1. Executive Summary

This report documents the end-to-end architectural audit, upstream C++ engine synchronization, dependency modernization, cross-platform build system overhaul (**Apple macOS**, **Linux**, and **Windows**), bug remediation, and feature expansion of `whisper.api`.

### Key Outcomes
1. **Upstream `whisper.cpp` Fork Merged & Pushed (`efa0df3c`)**: Merged 628 upstream commits from `ggml-org/whisper.cpp` (`master` @ `231638a0`, `v1.9.5-dev` / `ggml 0.27.0`) into `innovatorved/whisper.cpp` (`develop`), cleanly resolving conflicts in `examples/cli/cli.cpp` and `examples/cli/README.md` while preserving custom `-vi` / `--video-input` FFmpeg video transcription support.
2. **Critical Word-Timestamp & Confidence Bug Fixed (`-oj` $\rightarrow$ `-ojf`)**: `transcribe_audio()` in `app/utils/utils.py` previously invoked `whisper-cli` with `-oj` (basic JSON without token arrays), causing `parse_whisper_json_to_deepgram()` to always return empty `words: []` and `confidence: 0.0`. Upgrading to `-ojf` (`--output-json-full`) and filtering out internal Whisper special tokens (`[_BEG_]`, `[_TT_...]`, `<|...|>`), restored accurate per-word timestamps and token probabilities across both Deepgram and OpenAI responses.
3. **OpenAI Audio API Compatibility (`/v1/audio/transcriptions` & `/v1/audio/translations`)**: Added drop-in OpenAI-compatible endpoints supporting `Bearer` and `Token` authentication, `whisper-1` model aliasing, `json` / `verbose_json` / `text` / `srt` / `vtt` formats, and `timestamp_granularities[]` (`word` and `segment`).
4. **Expanded Model Catalog & On-Demand CLI Manager**: Added `large-v3-turbo` (`q5_0`, `q8_0`, full), `large-v3`, `medium.en`, `small.en.q5`, `small.en`, `base.en`, and `silero-v6.2.0` (Silero VAD) to `app/utils/constant.py`, decoupled startup downloads via `DEFAULT_STARTUP_MODELS`, and added `python -m app.cli models` and `python -m app.cli download <model>`.
5. **Full Cross-Platform Support (macOS, Linux, Windows)**: Refactored `setup_whisper.sh`, created native PowerShell `setup_whisper.ps1` for Windows, added cross-platform `resolve_whisper_binary()` (`.exe` vs extensionless resolution), and expanded GitHub Actions CI (`.github/workflows/testing.yaml`) across `ubuntu-latest`, `macos-latest`, and `windows-latest`.
6. **Dependency Modernization**: Upgraded all Python (`requirements.txt`) and Astro documentation (`docs/package.json`) packages to their latest stable releases and resolved FastAPI `0.159.1` / Starlette `1.9.0` route inspection changes.

---

## 2. Codebase Audit & Bugs Fixed

| # | Location | Issue Identified | Resolution Implemented |
|---|----------|------------------|------------------------|
| 1 | `app/utils/utils.py` (`transcribe_audio`) | `whisper-cli` was invoked with `-oj` (`--output-json`) instead of `-ojf` (`--output-json-full`). Because `-oj` omits the `tokens` array inside each segment, `parse_whisper_json_to_deepgram()` always produced `words: []` and `confidence: 0.0`. | Switched `whisper-cli` invocation to `-ojf` so full token metadata (`t_dtw`, `offsets`, `p`) is emitted on every JSON transcription. |
| 2 | `app/utils/utils.py` (`_is_special_whisper_token`) | With `-ojf` enabled, `whisper.cpp` emits internal control tokens such as `[_BEG_]`, `[_TT_175]`, `[_EOT_]`, and `<|endoftext|>` inside segment token lists, polluting word-level timestamps. | Added `_is_special_whisper_token()` to filter out all `[_...]` and `<|...|>` control tokens before constructing word arrays and computing segment confidence averages. |
| 3 | `app/utils/utils.py` (`get_all_routes`) | FastAPI `0.159.1` wraps included `APIRouter` objects in `_IncludedRouter` instances that do not expose a top-level `.path` attribute, raising `AttributeError` at startup. | Updated `get_all_routes()` to recursively traverse nested `route.routes` collections and inspect `getattr(route, "path", None)`. |
| 4 | `setup_whisper.sh` | Hardcoded `git checkout v1.7.0` (discarding the custom `develop` branch with `-vi`), ran destructive `sed` commands on `examples/cli/cli.cpp`, and failed on `--help` verification due to `set -o pipefail` + `head -n 5` (`SIGPIPE`). | Removed the `v1.7.0` checkout and `sed` hacks, cloned `innovatorved/whisper.cpp` (`-b develop --depth 1`), added OS/GPU auto-detection, and fixed binary verification without `SIGPIPE`. |
| 5 | `app/utils/checks.py` (`check_models`) | Downloading every model in `model_names` at startup would block boot for gigabytes of downloads once `large-v3` and `large-v3-turbo` were added. | Introduced `DEFAULT_STARTUP_MODELS` (`tiny.en`, `tiny.en.q5`, `base.en.q5`) so startup remains fast while larger models are downloaded on-demand via `python -m app.cli download <model>` or `ensure_model_available()`. |
| 6 | `app/core/config.py`, `app/core/models/ApiKey.py` | Used deprecated `datetime.utcnow()` and PostgreSQL-only `sqlalchemy.dialects.postgresql.UUID`. | Migrated to timezone-aware `datetime.now(timezone.utc)`, SQLAlchemy 2.x generic `sqlalchemy.Uuid`, and Pydantic v2 `@field_validator`. |

---

## 3. Upstream `whisper.cpp` Fork Synchronization (`R2`)

### Remotes & Branches
- **Custom Fork (`origin`)**: `https://github.com/innovatorved/whisper.cpp.git` (default branch: `develop`, previously at `f5dd0bd5` based on `v1.7.4`).
- **Official Upstream (`upstream`)**: `https://github.com/ggml-org/whisper.cpp.git` (`master` at `231638a0`, `v1.9.5-dev` / `ggml 0.27.0`).

### Custom Fork Feature Preserved (`-vi` / `--video-input`)
The `innovatorved/whisper.cpp` fork adds native video input support to `whisper-cli`:
- CLI flag `-vi` / `--video-input` (`bool is_video = false` in `whisper_params`).
- Automatic FFmpeg audio extraction (`ffmpeg -i <video> -vn -acodec pcm_s16le -ar 16000 -ac 2 <temp.wav> -y`) prior to inference and automatic temporary `.wav` cleanup after inference.

### Merge & Conflict Resolution Summary
- Merged `upstream/master` (`231638a0`) into `develop` (`efa0df3c`).
- Resolved conflicts in:
  - `examples/cli/cli.cpp`: Integrated `-vi` / `--video-input` argument parsing, help documentation, FFmpeg extraction, and temp-file cleanup alongside upstream's new Voice Activity Detection (`--vad`, `-vm`), grammar, and audio buffer loop.
  - `examples/cli/README.md`: Preserved `-vi` documentation alongside upstream CLI options.
- Compiled `whisper-cli` with Apple Metal, Accelerate, and BLAS support and verified `./binary/whisper-cli --help` exposes both `-vi, --video-input` and `--vad`.
- Pushed `develop` (`efa0df3c`) to `origin` (`https://github.com/innovatorved/whisper.cpp.git`).

---

## 4. Dependency Modernization Log (`R3`)

### Python Dependencies (`requirements.txt`)

| Package | Previous Version | Upgraded Version | Notes |
|---------|------------------|------------------|-------|
| `fastapi` | `0.111.0` | `0.159.1` | Recursive router inspection updated in `app/utils/utils.py` |
| `starlette` | `0.37.2` | `1.9.0` | Latest ASGI toolkit |
| `uvicorn` | `0.30.1` | `0.54.0` | High-performance ASGI server |
| `pydantic` | `2.8.2` | `2.14.1` | Pydantic v2 validation |
| `pydantic-settings` | `2.3.4` | `2.16.1` | Settings management |
| `sqlalchemy` | `2.0.31` | `2.1.6` | Generic `Uuid` type support |
| `python-multipart` | `0.0.9` | `0.0.32` | Multipart form parsing for `/v1/audio/*` |
| `websockets` | `12.0` | `17.3` | Live streaming WebSocket support |
| `aiofiles` | `24.1.0` | `25.1.0` | Async file I/O |
| `gdown` | `5.2.0` | `6.4.2` | Model download fallback |
| `tqdm` | `4.66.4` | `4.70.1` | Progress bars for model downloads |
| `pytest` | `8.2.2` | `9.1.1` | Test runner |
| `pytest-cov` | `5.0.0` | `7.1.0` | Coverage plugin |

### Documentation Dependencies (`docs/package.json`)

| Package | Previous Version | Upgraded Version |
|---------|------------------|------------------|
| `astro` | `^5.18.1` | `^6.4.8` |
| `@astrojs/mdx` | `^4.3.13` | `^5.0.6` |
| `@astrojs/sitemap` | `^3.7.0` | `^3.7.4` |
| `tailwindcss` | `^4.1.11` | `^4.3.3` |
| `@tailwindcss/vite` | `^4.1.11` | `^4.3.3` |
| `@tailwindcss/typography` | `^0.5.16` | `^0.5.20` |

Verified with `cd docs && bun run build` (9 static documentation pages built cleanly with 0 errors).

---

## 5. Cross-Platform Support Matrix (`R4`)

| Platform | Architecture | Setup Script | Hardware Acceleration Flags | Binary Resolution |
|----------|--------------|--------------|-----------------------------|-------------------|
| **Apple macOS** | Apple Silicon (`arm64`) & Intel (`x86_64`) | `./setup_whisper.sh` | `-DGGML_METAL=ON -DGGML_ACCELERATE=ON` (+ optional `WHISPER_COREML=1`) | `./binary/whisper-cli` |
| **Linux** | `x86_64`, `aarch64` / `arm64` | `./setup_whisper.sh` | Auto-detects `nvcc` for `-DGGML_CUDA=ON`; CPU fallback with OpenMP | `./binary/whisper-cli` |
| **Windows** | `x64` / `ARM64` | `.\setup_whisper.ps1` (PowerShell) or `./setup_whisper.sh` (MSYS2/Git Bash) | MSVC / MinGW CMake Release build + optional `-DGGML_CUDA=ON` | `./binary/whisper-cli.exe` (resolved automatically via `resolve_whisper_binary()`) |
| **Docker** | Multi-arch (`python:3.12-slim-bookworm`) | `Dockerfile` | Builds `whisper-cli` in container & runs on port `7860` | `/app/binary/whisper-cli` |

---

## 6. New Features & API Expansion (`R5`)

### 6.1 OpenAI-Compatible Audio Endpoints (`app/api/endpoints/audio.py`)
- **`POST /v1/audio/transcriptions`**: Multipart form upload compatible with OpenAI Python/JS SDKs (`file`, `model`, `language`, `prompt`, `response_format`, `temperature`, `timestamp_granularities[]`, `vad`).
- **`POST /v1/audio/translations`**: Multipart form upload that translates speech into English (`translate=True`).
- **Supported Response Formats**:
  - `json`: `{"text": "..."}`
  - `verbose_json`: Includes `task`, `language`, `duration`, `text`, `segments`, and (when `"word"` is in `timestamp_granularities[]`) word-level `words` (`word`, `start`, `end`).
  - `text`, `srt`, `vtt`: Plain-text and subtitle responses.
- **Dual Auth Header Support**: Accepts both `Authorization: Bearer <token>` (OpenAI standard) and `Authorization: Token <token>` (Deepgram standard).

### 6.2 Enhanced Deepgram `/v1/listen` Endpoint
- Added query parameters:
  - `translate` (`bool`): Translate speech to English (`-tr`).
  - `temperature` (`float`, `0.0–1.0`): Sampling temperature (`-tp`).
  - `beam_size` (`int`, `1–10`): Beam search size (`-bs`).
  - `split_on_word` (`bool`): Split segments on word boundaries (`-sow`).
  - `vad` (`bool`): Enable Silero Voice Activity Detection (`--vad -vm models/ggml-silero-v6.2.0.bin`).
  - `response_format=text`: Plain-text transcript output in addition to `json`, `srt`, and `vtt`.

### 6.3 Expanded Model Registry & CLI Commands
- **New Models in `app/utils/constant.py`**:
  - `large-v3-turbo`, `large-v3-turbo.q5`, `large-v3-turbo.q8`
  - `large-v3`, `medium.en`, `small.en`, `small.en.q5`, `base.en`
  - `silero-v6.2.0` (Voice Activity Detection model)
  - Model aliases (`whisper-1`, `large-v3-turbo-q5_0`, `large-v3-turbo-q8_0`, `silero-vad`, etc.)
- **New CLI Subcommands (`app/cli.py`)**:
  - `python -m app.cli models`: Displays a formatted table of all registered models, disk sizes, installation status, and aliases.
  - `python -m app.cli download <model>`: Downloads a specific model (or `--all-startup`) from Hugging Face with progress reporting.

---

## 7. Verification & Test Suite Summary

All **31 automated tests** pass (`pytest -v`), including real end-to-end binary execution with `audio/jfk.wav`:
- `app/tests/test_api/test_audio_openai.py`: Tests OpenAI `/v1/audio/transcriptions` and `/v1/audio/translations` authentication (`Bearer` & `Token`), `verbose_json` word & segment timestamps, `text`/`srt`/`vtt` outputs, and invalid model/format error handling.
- `app/tests/test_api/test_listen.py`: Tests Deepgram REST `/v1/listen`, URL ingestion, `/v1/models`, and WebSocket live streaming (query token, subprotocols, WebM/WAV container detection, cumulative decoding).
- `app/tests/test_utils/test_features.py`: Tests cross-platform `resolve_whisper_binary()` (Windows `.exe` vs Unix), `resolve_model_name()` aliases (`whisper-1`), `_is_special_whisper_token()` filtering, `-ojf` and advanced decoding CLI flags, SSRF protection against private/loopback/cloud-metadata IPs, CLI `models` subcommand, and real end-to-end `jfk.wav` transcription verifying non-empty word timestamps and confidence scores.

---

## 8. Release Instructions (`v2.1.0`)

To publish the new release of `whisper.api`:

```bash
# 1. Stage and commit all changes
git add -A
git commit -m "feat: sync whisper.cpp v1.9.5-dev, add OpenAI audio API, cross-platform builds, and word timestamps (-ojf)"

# 2. Tag the release
git tag -a v2.1.0 -m "Release v2.1.0: OpenAI Audio API, whisper.cpp v1.9.5-dev sync, large-v3-turbo & cross-platform support"

# 3. Push branch and tag to GitHub
git push origin main --tags
```
