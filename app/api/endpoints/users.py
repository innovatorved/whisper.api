from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.models.user import (PasswordUpdate, Response_Token, User,
                                 User_GET_TOKEN, UserDeletedResponse,
                                 UserResponse)
from app.core.database import get_db
from app.core.models.User import UserController
from app.utils import logger

router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def create_user(user: User, db: Session = Depends(get_db)):
    try:
        USER = UserController(db)
        USER.create(
            username=user.username,
            email=user.email,
            password=user.password,
        )

        return UserResponse.model_validate(USER.details())
    except HTTPException as exc:
        logger.error(exc)
        raise exc
    except Exception as exc:
        logger.error(exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.post(
    "/get_token", status_code=status.HTTP_200_OK, response_model=Response_Token
)
async def get_user_token(user: User_GET_TOKEN, db: Session = Depends(get_db)):
    try:
        USER = UserController(db)
        token = USER.read_token(user.email, user.password)
        return {"token": token}
    except HTTPException as exc:
        logger.error(exc)
        raise exc
    except Exception as exc:
        logger.error(exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.get("/{user_id}/", status_code=status.HTTP_200_OK, response_model=UserResponse)
async def read_user(user_id: UUID, db: Session = Depends(get_db)):
    try:
        USER = UserController(db)
        USER.read(user_id)
        return UserResponse.model_validate(USER.details())
    except HTTPException as exc:
        logger.error(exc)
        raise exc
    except Exception as exc:
        logger.error(exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.put(
    "/{user_id}/update_password/",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
)
async def update_password(
    user_id: UUID, password: PasswordUpdate, db: Session = Depends(get_db)
):
    try:
        USER = UserController(db)
        USER.update_password(user_id, password.current_password, password.new_password)
        return UserResponse.model_validate(USER.details())
    except HTTPException as exc:
        logger.error(exc)
        raise exc
    except Exception as exc:
        logger.error(exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.delete(
    "/{user_id}/delete",
    status_code=status.HTTP_200_OK,
    response_model=UserDeletedResponse,
)
async def delete_user(user_id: UUID, db: Session = Depends(get_db)):
    try:
        USER = UserController(db)
        USER.delete(user_id)
        return {"detail": "User Deleted"}
    except HTTPException as exc:
        logger.error(exc)
        raise exc
    except Exception as exc:
        logger.error(exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
