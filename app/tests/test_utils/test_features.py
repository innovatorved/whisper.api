import os
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.cli import main as cli_main
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.models.ApiKey import ApiKey, generate_bearer_token
from app.utils.utils import (
    _is_special_whisper_token,
    _validate_audio_fetch_url,
    parse_whisper_json_to_deepgram,
    resolve_model_name,
    resolve_whisper_binary,
    transcribe_audio,
)

client = TestClient(app)


def get_auth_token() -> str:
    db = SessionLocal()
    try:
        token_string = generate_bearer_token()
        new_key = ApiKey(token=token_string, name="pytest_feature_key")
        db.add(new_key)
        db.commit()
        return token_string
    finally:
        db.close()


def test_resolve_whisper_binary_windows_and_unix(tmp_path, monkeypatch):
    win_exe = tmp_path / "whisper-cli.exe"
    win_exe.write_bytes(b"MZ")
    unix_bin = tmp_path / "whisper-cli"

    # Simulate Windows
    monkeypatch.setattr("os.name", "nt")
    monkeypatch.setattr("sys.platform", "win32")
    resolved_win = resolve_whisper_binary(str(unix_bin))
    assert resolved_win.endswith("whisper-cli.exe")

    # Simulate Unix with extensionless binary present
    unix_bin.write_bytes(b"\x7fELF")
    monkeypatch.setattr("os.name", "posix")
    monkeypatch.setattr("sys.platform", "darwin")
    resolved_unix = resolve_whisper_binary(str(win_exe))
    assert resolved_unix == str(unix_bin)


def test_resolve_model_name_aliases():
    assert resolve_model_name("whisper-1") in ("tiny.en", "base.en.q5", "tiny.en.q5")
    assert resolve_model_name("large-v3-turbo-q5_0") == "large-v3-turbo.q5"
    assert resolve_model_name("large-v3-turbo-q8_0") == "large-v3-turbo.q8"
    assert resolve_model_name("tiny.en") == "tiny.en"


def test_special_token_filtering_in_deepgram_parser():
    assert _is_special_whisper_token("[_BEG_]") is True
    assert _is_special_whisper_token("[_TT_398]") is True
    assert _is_special_whisper_token("<|endoftext|>") is True
    assert _is_special_whisper_token(" fellow") is False

    whisper_json = {
        "result": {"language": "en"},
        "transcription": [
            {
                "offsets": {"from": 0, "to": 2000},
                "text": " Ask not",
                "tokens": [
                    {"text": "[_BEG_]", "offsets": {"from": 0, "to": 0}, "p": 0.9},
                    {"text": " Ask", "offsets": {"from": 100, "to": 500}, "p": 0.95},
                    {"text": " not", "offsets": {"from": 500, "to": 1000}, "p": 0.97},
                    {"text": "[_TT_100]", "offsets": {"from": 1000, "to": 1000}, "p": 0.8},
                ],
            }
        ],
    }
    res = parse_whisper_json_to_deepgram(
        whisper_json=whisper_json,
        request_id="req-1",
        model="tiny.en",
        audio_duration=2.0,
        include_utterances=True,
    )
    alt = res["results"]["channels"][0]["alternatives"][0]
    assert alt["transcript"] == "Ask not"
    assert len(alt["words"]) == 2
    assert alt["words"][0]["word"] == "ask"
    assert alt["words"][1]["word"] == "not"
    assert alt["confidence"] == pytest.approx(0.96, rel=1e-3)
    assert len(res["results"]["utterances"]) == 1


def test_transcribe_audio_uses_ojf_and_advanced_flags(tmp_path, monkeypatch):
    import asyncio
    from app.utils import utils as utils_module

    captured_cmd = []

    async def fake_execute_command(argv, timeout=None):
        captured_cmd.extend(argv)
        # Find -of argument to write dummy .json output
        of_idx = argv.index("-of")
        out_base = argv[of_idx + 1]
        with open(f"{out_base}.json", "w", encoding="utf-8") as f:
            f.write('{"result":{"language":"en"},"transcription":[]}')
        return "", "", 0

    monkeypatch.setattr(utils_module, "execute_command", fake_execute_command)
    vad_model = tmp_path / "ggml-silero-v6.2.0.bin"
    vad_model.write_bytes(b"vad")
    monkeypatch.setattr(settings, "VAD_MODEL_PATH", str(vad_model))

    out, _ = asyncio.run(
        transcribe_audio(
            audio_path="audio/jfk.wav",
            model="tiny.en",
            temperature=0.3,
            beam_size=5,
            vad=True,
            vad_threshold=0.6,
            split_on_word=True,
            no_fallback=True,
            suppress_nst=True,
            no_context=True,
            max_len=42,
            video_input=True,
        )
    )
    assert "-ojf" in captured_cmd
    assert "-oj" not in captured_cmd
    assert "-vi" in captured_cmd
    assert "-tp" in captured_cmd and "0.3" in captured_cmd
    assert "-bs" in captured_cmd and "5" in captured_cmd
    assert "--vad" in captured_cmd
    assert "-vm" in captured_cmd and str(vad_model) in captured_cmd
    assert "-vt" in captured_cmd and "0.6" in captured_cmd
    assert "-sow" in captured_cmd
    assert "-nf" in captured_cmd
    assert "--suppress-nst" in captured_cmd
    assert "-nc" in captured_cmd
    assert "-ml" in captured_cmd and "42" in captured_cmd


def test_ssrf_protection_blocks_private_and_metadata_urls():
    for bad_url in [
        "http://127.0.0.1:8000/audio.wav",
        "http://localhost/audio.wav",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/audio.wav",
        "file:///etc/passwd",
    ]:
        with pytest.raises(HTTPException) as exc:
            _validate_audio_fetch_url(bad_url)
        assert exc.value.status_code == 400


def test_cli_commands(capsys):
    assert cli_main(["init"]) == 0
    assert cli_main(["create", "--name", "cli_test_key"]) == 0
    assert cli_main(["list"]) == 0
    assert cli_main(["models"]) == 0
    out = capsys.readouterr().out
    assert "API Key Created Successfully" in out
    assert "large-v3-turbo.q5" in out


@pytest.mark.skipif(
    not (os.path.exists("./binary/whisper-cli") and os.path.exists("audio/jfk.wav")),
    reason="Requires compiled ./binary/whisper-cli and audio/jfk.wav",
)
def test_e2e_real_jfk_transcription_word_timestamps():
    """Real end-to-end transcription test using compiled whisper-cli on audio/jfk.wav."""
    token = get_auth_token()
    with open("audio/jfk.wav", "rb") as f:
        wav_bytes = f.read()

    # 1. Deepgram-compatible /v1/listen
    res_dg = client.post(
        "/v1/listen?model=tiny.en&utterances=true",
        headers={"Authorization": f"Token {token}", "Content-Type": "audio/wav"},
        content=wav_bytes,
    )
    assert res_dg.status_code == 200
    dg_data = res_dg.json()
    alt = dg_data["results"]["channels"][0]["alternatives"][0]
    assert "fellow americans" in alt["transcript"].lower()
    assert len(alt["words"]) > 10
    assert alt["confidence"] > 0.5
    assert all(not w["word"].startswith("[_") for w in alt["words"])

    # 2. OpenAI-compatible /v1/audio/transcriptions
    res_oai = client.post(
        "/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("jfk.wav", wav_bytes, "audio/wav")},
        data={
            "model": "whisper-1",
            "response_format": "verbose_json",
            "timestamp_granularities": ["word", "segment"],
        },
    )
    assert res_oai.status_code == 200
    oai_data = res_oai.json()
    assert "fellow americans" in oai_data["text"].lower()
    assert len(oai_data["words"]) > 10
    assert len(oai_data["segments"]) >= 1

    # 3. Deepgram-compatible /v1/listen with response_format=text
    res_txt = client.post(
        "/v1/listen?model=whisper-1&response_format=text",
        headers={"Authorization": f"Token {token}", "Content-Type": "audio/wav"},
        content=wav_bytes,
    )
    assert res_txt.status_code == 200
    assert "fellow americans" in res_txt.text.lower()
