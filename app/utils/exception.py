import logging

logger = logging.getLogger(__name__)
from fastapi import HTTPException, status


def handle_exceptions(func):
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException as exc:
            logger.error(exc)
            raise exc
        except Exception as exc:
            logger.error(exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc

    return wrapper
