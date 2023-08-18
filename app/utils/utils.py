from fastapi import HTTPException
import os
import re
import urllib
import subprocess
import uuid
import logging
import wave
import gdown
from tqdm import tqdm


from .constant import model_names


def get_all_routes(app):
    routes = []
    for route in app.routes:
        routes.append(
            {
                "path": route.path,
                "name": route.name,
                "methods": list(route.methods),
            }
        )
    return routes


def print_routes(app):
    routes = get_all_routes(app)
    print("\n\n")
    print("Path" + " " * 45 + "Name" + " " * 45 + "Methods")
    print("-" * 105)
    for route in routes:
        print(
            f"{route['path']}"
            + " " * (48 - len(route["path"]))
            + f"{route['name']}"
            + " " * (48 - len(route["name"]))
            + f"{', '.join(route['methods'])}"
        )
    print("\n")


def transcribe_file(path: str = None, model="ggml-model-whisper-tiny.en-q5_1.bin"):
    """./binary/whisper -m models/ggml-tiny.en.bin -f Rev.mp3 out.wav -nt --output-text out1.txt"""
    try:
        if path is None:
            raise HTTPException(status_code=400, detail="No path provided")
        rand = uuid.uuid4()
        outputFilePath: str = f"transcribe/{rand}.txt"
        output_audio_path: str = f"audio/{rand}.wav"
        command: str = f"./binary/whisper -m models/{model} -f {path} {output_audio_path} -nt --output-text {outputFilePath}"
        execute_command(command)
        f = open(outputFilePath, "r")
        data = f.read()
        f.close()
        return [data, output_audio_path]
    except Exception as exc:
        logging.error(exc)
        raise HTTPException(status_code=400, detail=exc.__str__())


def execute_command(command: str) -> str:
    try:
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        return result.decode("utf-8").strip()
    except subprocess.CalledProcessError as exc:
        logging.error(exc.output.decode("utf-8").strip())
        raise HTTPException(status_code=400, detail="Error while transcribing")


def save_audio_file(file=None):
    if file is None:
        return ""
    path = f"audio/{uuid.uuid4()}.mp3"
    with open(path, "wb") as f:
        f.write(file.file.read())
    return path


def get_audio_duration(audio_file):
    """Gets the duration of the audio file in seconds.

    Args:
      audio_file: The path to the audio file.

    Returns:
      The duration of the audio file in seconds.
    """

    with wave.open(audio_file, "rb") as f:
        frames = f.getnframes()
        sample_rate = f.getframerate()
        duration = frames / sample_rate
        rounded_duration = int(round(duration, 0))

    return rounded_duration


def get_model_name(model: str = None):
    if model is None:
        model = "tiny.en.q5"

    if model in model_names.keys():
        return model_names[model]

    return model_names["tiny.en.q5"]


def download_from_drive(url, output):
    try:
        gdown.download(url, output, quiet=False)
        return True
    except:
        raise HTTPException(
            status_code=400, detail="Error Occured in Downloading model from Gdrive"
        )


def download_file(url, filepath):
    try:
        filename = os.path.basename(url)

        with tqdm(
            unit="B", unit_scale=True, unit_divisor=1024, miniters=1, desc=filename
        ) as progress_bar:
            urllib.request.urlretrieve(
                url,
                filepath,
                reporthook=lambda block_num, block_size, total_size: progress_bar.update(
                    block_size
                ),
            )

        print("File downloaded successfully!")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"An error occurred: {exc}")


def is_valid_email(email: str) -> bool:
    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(email_regex, email))


def is_valid_password(password: str) -> bool:
    if len(password) < 6:
        return False
    return True


def is_field_valid(**kwargs) -> bool:
    for key, value in kwargs.items():
        if key == "email":
            if not is_valid_email(value):
                return False
        elif key == "password":
            if not is_valid_password(value):
                return False
        elif key == "username":
            if len(value) < 3:
                return False
        else:
            return False
    return True
