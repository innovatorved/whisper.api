from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api import api_router
from app.api.models.ping import PingResponse
from app.core.config import settings
from app.core.errors import error_handler
from app.utils import print_routes
from app.utils.checks import run_checks

if not run_checks():
    raise Exception("Failed to pass all checks")


app = FastAPI(
    title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    return RedirectResponse(url="/docs")


@app.get("/ping", tags=["ping"], response_model=PingResponse)
async def ping():
    return {"ping": "pong"}


# Include routers
app.include_router(api_router, prefix=settings.API_V1_STR)

# # Error handlers
app.add_exception_handler(500, error_handler)

# Print all routes
print_routes(app)
