from fastapi import HTTPException
from app.core.security import verify_password, get_password_hash


def test_password_hashing():
    password = "testpassword"
    hashed_password = get_password_hash(password)
    assert hashed_password != password


def test_password_verification():
    password = "testpassword"
    hashed_password = get_password_hash(password)
    assert verify_password(password, hashed_password)
    assert not verify_password("wrongpassword", hashed_password)


def test_password_verification_exception():
    password = "testpassword"
    hashed_password = get_password_hash(password)
    try:
        verify_password("wrongpassword", hashed_password)
    except HTTPException as exc:
        assert exc.status_code == 401
        assert exc.detail == "Incorrect email or password"
