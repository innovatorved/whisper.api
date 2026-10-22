import argparse
import os
import sys
from app.core.config import settings
from app.core.database import SessionLocal, Base, engine
from app.core.models.ApiKey import ApiKey, generate_bearer_token
from app.utils.checks import download_model
from app.utils.constant import model_info, model_names
from app.utils.utils import resolve_model_name


def create_key(name):
    db = SessionLocal()
    try:
        token_string = generate_bearer_token()
        new_key = ApiKey(token=token_string, name=name)
        db.add(new_key)
        db.commit()
        db.refresh(new_key)
        print("API Key Created Successfully!")
        print("-" * 40)
        print(f"Name:  {name if name else 'Unnamed'}")
        print(f"Token: {token_string}")
        print("-" * 40)
        print("Keep this token safe! Pass it in the Authorization header as: Token <token> or Bearer <token>")
    finally:
        db.close()


def list_keys():
    db = SessionLocal()
    try:
        keys = db.query(ApiKey).all()
        if not keys:
            print("No API keys found.")
            return

        print("Active API Keys")
        print("-" * 60)
        for k in keys:
            print(f"Token: {k.token[:8]}*** | Name: {k.name} | Created: {k.created_at}")
        print("-" * 60)
    finally:
        db.close()


def revoke_key(token_prefix):
    db = SessionLocal()
    try:
        keys = db.query(ApiKey).filter(ApiKey.token.like(f"{token_prefix}%")).all()
        if not keys:
            print(f"No key found matching prefix '{token_prefix}'")
            return

        if len(keys) > 1:
            print(f"Multiple keys match prefix '{token_prefix}'. Please be more specific.")
            return

        key_to_delete = keys[0]
        db.delete(key_to_delete)
        db.commit()
        print(f"Successfully revoked key '{key_to_delete.name or 'Unnamed'}' starting with {key_to_delete.token[:8]}")
    finally:
        db.close()


def init_db():
    print("Initializing Database structure...")
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully.")


def cli_list_models():
    print("Registered Whisper & VAD Models")
    print("-" * 85)
    for key, filename in model_names.items():
        path = os.path.join(settings.MODELS_DIR, filename)
        status = "INSTALLED" if os.path.exists(path) else "NOT INSTALLED"
        desc = model_info.get(key, {}).get("description", "")
        print(f"{key:<22} | {status:<13} | {filename:<36} | {desc}")
    print("-" * 85)


def cli_download_model(model_key: str) -> bool:
    canonical = resolve_model_name(model_key)
    if canonical not in model_names:
        print(f"Unknown model '{model_key}'. Available models: {', '.join(model_names.keys())}")
        return False
    return download_model(canonical)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Whisper API Offline Key & Model Manager")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Command: create
    parser_create = subparsers.add_parser("create", help="Create a new API key")
    parser_create.add_argument("--name", "-n", type=str, help="Optional short name/description for the key", default=None)

    # Command: list
    subparsers.add_parser("list", help="List active API keys")

    # Command: revoke
    parser_revoke = subparsers.add_parser("revoke", help="Revoke an API key")
    parser_revoke.add_argument("token", type=str, help="The token string (or prefix) to revoke")

    # Command: init
    subparsers.add_parser("init", help="Initialize database tables")

    # Command: models
    subparsers.add_parser("models", help="List all registered Whisper/VAD models and installation status")

    # Command: download
    parser_download = subparsers.add_parser("download", help="Download a Whisper or VAD model from Hugging Face")
    parser_download.add_argument("model", type=str, help="Model ID to download (e.g. large-v3-turbo.q5, base.en, silero-v6.2.0)")

    args = parser.parse_args(argv)

    if args.command == "create":
        create_key(args.name)
    elif args.command == "list":
        list_keys()
    elif args.command == "revoke":
        revoke_key(args.token)
    elif args.command == "init":
        init_db()
    elif args.command == "models":
        cli_list_models()
    elif args.command == "download":
        if not cli_download_model(args.model):
            return 1
    else:
        parser.print_help()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
