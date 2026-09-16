from sqlalchemy.orm import Session

from app.core.security import (
    DUMMY_HASH,
    InvalidTokenError,
    decode_access_token,
    verify_password_hash,
)
from app.models.user import User
from app.services.user import get_user


def authenticate_user(username: str, user_password: str, db: Session) -> User | None:
    user_in_db: User | None = get_user(username, db)

    if user_in_db is None:
        verify_password_hash(user_password, DUMMY_HASH)
        return None

    if not verify_password_hash(user_password, user_in_db.password_hash):
        return None

    return user_in_db


def get_current_user(token: str, db: Session) -> User | None:
    try:
        payload = decode_access_token(token)
    except InvalidTokenError:
        return None

    username = payload.get("sub")
    if username is None:
        return None

    return get_user(username, db)
