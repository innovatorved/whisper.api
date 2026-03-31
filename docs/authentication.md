# Authentication

The API is secured using permanent API keys that are managed offline via a Python CLI.

## Key Generation and Management

Use the `app.cli` module to generate, list, and revoke tokens.

### Initialize the Database
Before generating your first key, ensure the database is initialized:
```bash
python -m app.cli init
```

### Create a New API Key
Generate a new token with an optional descriptive name:
```bash
python -m app.cli create --name "AdminToken"
```
**Output:**
```text
✅ API Key Created Successfully!
----------------------------------------
Name:  AdminToken
Token: 90e4b3189f324cc881e708c27d81d1d0...
----------------------------------------
Keep this token safe! Pass it in the Authorization header as: Token <token>
```

### List Active Keys
View all generated keys and their creation timestamps:
```bash
python -m app.cli list
```

### Revoke a Key
To permanently revoke access, pass the token prefix:
```bash
python -m app.cli revoke <token_prefix>
```

### Swagger UI Testing Tokens
If you are running the system in a testing or sandbox environment where you want users to quickly generate a token from the Swagger UI (`/docs`), you can enable the public `/v1/auth/test-token` endpoint by setting `ENABLE_TEST_TOKEN_ENDPOINT=true` as an environment variable or in your `.env` file. Do not enable this in production environments!

## Using the API Key

For all REST API and WebSocket requests, the token must be passed in the `Authorization` header.

### REST API Header
```bash
Authorization: Token <your_api_key_here>
```

### WebSocket Query Parameter
For WebSocket connections (`WS /v1/listen`), the token must be passed as a query string parameter:
```bash
ws://localhost:7860/v1/listen?token=<your_api_key_here>
```
