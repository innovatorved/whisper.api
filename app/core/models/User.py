import uuid

from fastapi import HTTPException, status
from sqlalchemy import Boolean, Column, DateTime, String, or_
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.config import settings
from app.core.database import Base
from app.core.models import AuthTokenController
from app.core.security import get_password_hash, verify_password
from app.utils.utils import is_valid_email, is_valid_password


class UserInDB(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    transcribes = relationship("TranscibeInDB", back_populates="user")
    auth_tokens = relationship("AuthToken", back_populates="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __init__(self, username: str, email: str, hashed_password: str):
        self.username = username
        self.email = email
        self.hashed_password = hashed_password

    def data(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at,
        }


class UserController:
    UserInDB = UserInDB

    def __init__(self, database):
        self.db = database

    def create(self, username: str, email: str, password: str, init_token: bool = True):
        if not is_valid_email(email):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid Email"
            )
        if not is_valid_password(password):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid Password",
            )

        is_user_exists: Boolean = self.CheckUserIsExistsByEmailAndUsername(
            email, username
        )
        if is_user_exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email or Username Already Registered",
            )

        self.username = username
        self.email = email
        self.hashed_password = get_password_hash(password)

        self.db_user = UserInDB(
            username=self.username,
            email=self.email,
            hashed_password=self.hashed_password,
        )
        self.db.add(self.db_user)
        self.db.commit()
        self.db.refresh(self.db_user)
        self.user = self.db_user.data()

        if init_token == False:
            return
        AuthTokenController(self.db).create(self.db_user.id)

    def read_token(self, email: str, password: str):
        self.read_by_email(email)
        if not verify_password(password, self.db_user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect password")
        TOKEN = AuthTokenController(self.db)
        TOKEN.get_token_from_user_id(self.db_user.id)
        return TOKEN.get_token()

    def CheckUserIsExistsByEmailAndUsername(self, email: str, username: str):
        db_user = (
            self.db.query(UserInDB)
            .filter(or_(UserInDB.email == email, UserInDB.username == username))
            .first()
        )
        if db_user:
            return True
        return False

    def read_by_email(self, email: str):
        self.db_user = self.db.query(UserInDB).filter(UserInDB.email == email).first()
        if not self.db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        self.user = self.db_user.data()

    def read(self, user_id: uuid.UUID):
        self.db_user = self.db.query(UserInDB).filter(UserInDB.id == user_id).first()
        if not self.db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        self.user = self.db_user.data()

    def update_password(
        self, user_id: uuid.UUID, current_password: str, new_password: str
    ):
        self.read(user_id)
        if verify_password(current_password, self.db_user.hashed_password):
            self.db_user.hashed_password = get_password_hash(new_password)
            self.db.commit()
            self.db.refresh(self.db_user)
            self.user = self.db_user.data()
        else:
            raise HTTPException(status_code=400, detail="Incorrect password")

    def delete(self, user_id: uuid.UUID):
        self.read(user_id)
        self.db.delete(self.db_user)
        self.db.commit()
        return user_id

    def details(self):
        return self.db_user

    def detailsInJSON(self):
        return self.user
