import os
from typing import Iterable, Optional

from app.core.config import settings
from app.utils.constant import DEFAULT_STARTUP_MODELS, model_names, model_urls
from app.utils.utils import download_file


def run_checks() -> bool:
    try:
        if not check_models_exist():
            return False
        return True
    except Exception as exc:
        print("Error in run_checks: {}".format(str(exc)))
        return False


def check_models_exist(required_models: Optional[Iterable[str]] = None) -> bool:
    """
    Ensure default startup models exist in settings.MODELS_DIR, downloading any missing ones.
    Only checks lightweight DEFAULT_STARTUP_MODELS by default so optional large models
    (e.g. large-v3-turbo) are not forcefully downloaded at boot time.
    """
    try:
        os.makedirs(settings.MODELS_DIR, exist_ok=True)
        models_to_check = (
            list(required_models)
            if required_models is not None
            else [k for k in DEFAULT_STARTUP_MODELS if k in model_names]
        )
        for key in models_to_check:
            value = model_names[key]
            if os.path.exists(os.path.join(settings.MODELS_DIR, value)):
                print("Model {} exists".format(key))
            else:
                print("Model {} does not exist".format(key))
                download_model(key)
        return True
    except Exception as exc:
        print("Error in check_models_exist: {}".format(str(exc)))
        return False


def download_model(model_key: str) -> bool:
    try:
        if model_key not in model_urls or model_key not in model_names:
            raise ValueError(f"Unknown model key: {model_key}")
        os.makedirs(settings.MODELS_DIR, exist_ok=True)
        print("Downloading model {} from {}".format(model_key, model_urls[model_key]))
        download_file(
            model_urls[model_key],
            os.path.join(settings.MODELS_DIR, model_names[model_key]),
        )
        print("Downloaded model {} from {}".format(model_key, model_urls[model_key]))
        return True
    except Exception as exc:
        print("Error in download_models: {}".format(str(exc)))
        return False
