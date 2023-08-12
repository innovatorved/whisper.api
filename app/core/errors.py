from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException, RequestValidationError


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Exception handler for HTTP errors
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )


async def http_error_handler(request: Request, exc: Exception):
    """
    Exception handler for HTTP errors
    """
    if isinstance(exc, HTTPException):
        detail = exc.detail
        status_code = exc.status_code
    else:
        detail = "Internal server error"
        status_code = 500
    return JSONResponse(
        status_code=status_code,
        content={"message": detail},
    )


def http422_error_handler(request: Request, exc: RequestValidationError):
    """
    Exception handler for HTTP 422 errors
    """
    return JSONResponse(
        status_code=422,
        content={"message": "Validation error", "details": exc.errors()},
    )
