# File: my-fastapi-project/app/api/__init__.py

from fastapi import FastAPI
from .endpoints import items, users
from .models import item, user

app = FastAPI()

app.include_router(items.router)
app.include_router(users.router)