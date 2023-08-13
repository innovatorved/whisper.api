from fastapi import APIRouter, HTTPException
from uuid import UUID

from app.api.models.user import User, UpdateUser, UserResponse
from app.core.database import SessionLocal
from app.core.security import get_password_hash, verify_password
from app.core.models import UserInDB

database = SessionLocal()
users_router = router = APIRouter()


@router.post("/", status_code=201)
async def create_user(user: User):
    db_user = UserInDB(
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password),
    )
    database.add(db_user)
    database.commit()
    database.refresh(db_user)
    print(db_user)
    return {**db_user.data()}


@router.get("/{user_id}/", response_model=UserResponse)
async def read_user(user_id: UUID):
    db_user = database.query(UserInDB).filter(UserInDB.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.from_orm(db_user)


@router.put("/{user_id}/", response_model=User)
async def update_user(user_id: UUID, user: UpdateUser):
    db_user = database.query(UserInDB).filter(UserInDB.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(user.current_password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    if user.email != db_user.email:
        raise HTTPException(status_code=400, detail="Email cannot be changed")
    if user.username is None:
        user.username = db_user.username
    else:
        db_user.username = user.username
    db_user.hashed_password = get_password_hash(user.password)
    database.commit()
    database.refresh(db_user)
    return {**user.dict(), "id": db_user.id, "hashed_password": None}


@router.delete("/{user_id}/")
async def delete_user(user_id: UUID):
    db_user = database.query(UserInDB).filter(UserInDB.id == user_id).first()
    database.delete(db_user)
    database.commit()
    return user_id
