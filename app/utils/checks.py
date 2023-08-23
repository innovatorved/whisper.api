import os

from app.utils.constant import model_names, model_urls
from app.utils.utils import download_file


def run_checks():
    try:
        if not check_models_exist():
            return False
        return True
    except Exception as exc:
        print("Error in run_checks: {}".format(str(exc)))
        return False


def check_models_exist():
    try:
        for key, value in model_names.items():
            if os.path.exists(os.path.join(os.getcwd(), "models", value)):
                print("Model {} exists".format(key))
            else:
                print("Model {} does not exist".format(key))
                download_model(key)
        return True
    except Exception as exc:
        print("Error in check_models_exist: {}".format(str(exc)))
        return False


def download_model(model_key: str):
    try:
        print("Downloading model {} from {}".format(model_key, model_urls[model_key]))
        download_file(
            model_urls[model_key],
            os.path.join(os.getcwd(), "models", model_names[model_key]),
        )
        print("Downloaded model {} from {}".format(model_key, model_urls[model_key]))
    except Exception as exc:
        print("Error in download_models: {}".format(str(exc)))
