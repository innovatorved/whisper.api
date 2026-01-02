from fastapi import HTTPException
import asyncio
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


async def transcribe_file(
    path: str = None, model="ggml-model-whisper-tiny.en-q5_1.bin"
):
    """./binary/whisper -m models/ggml-tiny.en.bin -f Rev.mp3 out.wav -nt --output-text out1.txt"""
    try:
        if path is None:
            raise HTTPException(status_code=400, detail="No path provided")
        rand = uuid.uuid4()
        outputFilePath: str = f"transcribe/{rand}.txt"
        output_audio_path: str = f"audio/{rand}.wav"
        output_base: str = f"transcribe/{rand}"
        command: str = (
            f"./binary/whisper-cli -m models/{model} -f {path} -nt -of {output_base} -otxt"
        )
        await execute_command(command)
        f = open(outputFilePath, "r")
        data = f.read()
        f.close()
        return [data, output_audio_path]
    except Exception as exc:
        logging.error(exc)
        raise HTTPException(status_code=400, detail=exc.__str__())


async def execute_command(command: str) -> str:
    try:
        process = await asyncio.create_subprocess_shell(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logging.error(stderr.decode("utf-8").strip())
            raise HTTPException(status_code=400, detail="Error while transcribing")

        return stdout.decode("utf-8").strip()
    except Exception as exc:
        logging.error(exc)
        raise HTTPException(status_code=400, detail="Error while transcribing")


def save_audio_file(file=None):
    if file is None:
        return ""
    path = f"audio/{uuid.uuid4()}.wav"
    with open(path, "wb") as f:
        f.write(file.file.read())
    return path


def get_audio_duration(audio_file):
    """Gets the duration of the audio file in seconds using ffprobe."""
    try:
        command = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {audio_file}"
        duration = subprocess.check_output(command, shell=True).decode("utf-8").strip()
        return int(round(float(duration), 0))
    except Exception as e:
        logging.error(f"Error getting duration: {e}")
        return 0


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
