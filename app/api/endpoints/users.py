from fastapi import APIRouter, HTTPException
from uuid import UUID

from app.api.models.user import User, UpdateUser, UserResponse, PasswordUpdate
from app.core.database import SessionLocal
from app.core.security import get_password_hash, verify_password
from app.core.models import UserInDB
from app.core.models.User import UserController

database = SessionLocal()
users_router = router = APIRouter()


@router.post("/", status_code=201, response_model=UserResponse)
async def create_user(user: User):
    try:
        USER = UserController(database)
        USER.create(
            username=user.username,
            email=user.email,
            password=user.password,
        )

        return UserResponse.from_orm(USER.details())
    except Exception as e:
        raise HTTPException(status_code=400, detail=e.__str__())


@router.get("/{user_id}/", response_model=UserResponse)
async def read_user(user_id: UUID):
    try:
        USER = UserController(database)
        USER.read(user_id)
        return UserResponse.from_orm(USER.details())
    except Exception as e:
        raise HTTPException(status_code=400, detail=e.__str__())


@router.put("/{user_id}/update_password/", response_model=UserResponse)
async def update_password(user_id: UUID, password: PasswordUpdate):
    try:
        USER = UserController(database)
        USER.update_password(user_id, password.current_password, password.new_password)
        return UserResponse.from_orm(USER.details())

    except Exception as e:
        raise HTTPException(status_code=400, detail=e.__str__())


@router.delete("/{user_id}/")
async def delete_user(user_id: UUID):
    db_user = database.query(UserInDB).filter(UserInDB.id == user_id).first()
    database.delete(db_user)
    database.commit()
    return user_id
