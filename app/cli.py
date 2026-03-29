import argparse
import sys
from app.core.database import SessionLocal, Base, engine
from app.core.models.ApiKey import ApiKey, generate_bearer_token

def create_key(name):
    db = SessionLocal()
    try:
        token_string = generate_bearer_token()
        new_key = ApiKey(token=token_string, name=name)
        db.add(new_key)
        db.commit()
        db.refresh(new_key)
        print("✅ API Key Created Successfully!")
        print("-" * 40)
        print(f"Name:  {name if name else 'Unnamed'}")
        print(f"Token: {token_string}")
        print("-" * 40)
        print("Keep this token safe! Pass it in the Authorization header as: Token <token>")
    finally:
        db.close()

def list_keys():
    db = SessionLocal()
    try:
        keys = db.query(ApiKey).all()
        if not keys:
            print("No API keys found.")
            return
        
        print("🔑 Active API Keys")
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
        print(f"✅ Successfully revoked key '{key_to_delete.name or 'Unnamed'}' starting with {key_to_delete.token[:8]}")
    finally:
        db.close()

def init_db():
    print("Initializing Database structure...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Whisper API Offline Key Manager")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Command: create
    parser_create = subparsers.add_parser("create", help="Create a new API key")
    parser_create.add_argument("--name", "-n", type=str, help="Optional short name/description for the key", default=None)

    # Command: list
    parser_list = subparsers.add_parser("list", help="List active API keys")

    # Command: revoke
    parser_revoke = subparsers.add_parser("revoke", help="Revoke an API key")
    parser_revoke.add_argument("token", type=str, help="The token string (or prefix) to revoke")

    # Command: init
    parser_init = subparsers.add_parser("init", help="Initialize database tables")

    args = parser.parse_args()

    if args.command == "create":
        create_key(args.name)
    elif args.command == "list":
        list_keys()
    elif args.command == "revoke":
        revoke_key(args.token)
    elif args.command == "init":
        init_db()
    else:
        parser.print_help()
        sys.exit(1)
