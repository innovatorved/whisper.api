from fastapi import Request, Response
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse


async def error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Error handler function for FastAPI.

    Args:
        request: The HTTP request that caused the error.
        exc: The exception that was raised.

    Returns:
        The error response.
    """

    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )
