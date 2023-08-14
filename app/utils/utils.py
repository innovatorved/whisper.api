import json
import subprocess
import uuid
import logging


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


def transcribeFile(path: str = None, model="ggml-model-whisper-tiny.en-q5_1.bin"):
    """./binary/whisper -m models/ggml-tiny.en.bin -f Rev.mp3 -nt --output-text out1.txt"""
    try:
        if path is None:
            raise Exception("No path provided")
        outputFilePath: str = f"transcribe/{uuid.uuid4()}.txt"
        command: str = f"./binary/whisper -m models/{model} -f {path} -nt --output-text {outputFilePath}"
        execute_command(command)
        f = open(outputFilePath, "r")
        data = f.read()
        f.close()
        return data
    except Exception as e:
        logging.error(e)
        raise Exception(e.__str__())


def execute_command(command: str) -> str:
    try:
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        return result.decode("utf-8").strip()
    except subprocess.CalledProcessError as e:
        logging.error(e.output.decode("utf-8").strip())
        raise Exception("Error while transcribing")


def save_audio_file(file=None):
    if file is None:
        return ""
    path = f"audio/{uuid.uuid4()}.mp3"
    with open(path, "wb") as f:
        f.write(file.file.read())
    return path
