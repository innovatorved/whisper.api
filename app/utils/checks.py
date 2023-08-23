import os

from app.utils.constant import model_names, model_urls
from app.utils.utils import download_file


def run_checks():
    try:
        if not check_models_exist():
            return False
        return True
    except Exception as exc:
        print(f"Error in run_checks: {str(exc)}")
        return False


def check_models_exist():
    try:
        for key, value in model_names.items():
            if os.path.exists(os.path.join(os.getcwd(), "models", value)):
                print(f"Model {key} exists")
            else:
                print(f"Model {key} does not exist")
                download_model(key)
        return True
    except Exception as exc:
        print(f"Error in check_models_exist: {str(exc)}")
        return False


def download_model(model_key: str):
    try:
        print(f"Downloading model {model_key} from {model_urls[model_key]}")
        download_file(
            model_urls[model_key],
            os.path.join(os.getcwd(), "models", model_names[model_key]),
        )
        print(f"Downloaded model {model_key} from {model_urls[model_key]}")
    except Exception as exc:
        print(f"Error in download_models: {str(exc)}")
