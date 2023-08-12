from fastapi import APIRouter

from app.api.models.user import UserInDB
from app.core.database import SessionLocal

database = SessionLocal()

users_router = router = APIRouter()


@router.post("/", response_model=UserInDB, status_code=201)
async def create_user(user: UserInDB):
    query = UserInDB.insert().values(
        username=user.username,
        email=user.email,
        hashed_password=user.hashed_password
    )
    user_id = await database.execute(query)
    return {**user.dict(), "id": user_id}


@router.get("/{id}/", response_model=UserInDB)
async def read_user(id: int):
    query = UserInDB.select().where(UserInDB.c.id == id)
    user = await database.fetch_one(query)
    return user


@router.put("/{id}/", response_model=UserInDB)
async def update_user(id: int, user: UserInDB):
    query = (
        UserInDB
        .update()
        .where(UserInDB.c.id == id)
        .values(
            username=user.username,
            email=user.email,
            hashed_password=user.hashed_password
        )
        .returning(UserInDB.c.id)
    )
    user_id = await database.execute(query)
    return {**user.dict(), "id": user_id}


@router.delete("/{id}/", response_model=int)
async def delete_user(id: int):
    query = UserInDB.delete().where(UserInDB.c.id == id)
    user_id = await database.execute(query)
    return user_id