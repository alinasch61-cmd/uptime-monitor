from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.user import User

_UNIQUE_VIOLATION_SQLSTATE = "23505"


class UserExistsError(Exception):
    pass


def create_user(username: str, password: str, db: Session) -> User:
    user_model = User(username=username, password_hash=get_password_hash(password))

    try:
        db.add(user_model)
        db.commit()
        db.refresh(user_model)
    except IntegrityError as exc:
        db.rollback()

        if getattr(exc.orig, "sqlstate", None) == _UNIQUE_VIOLATION_SQLSTATE:
            raise UserExistsError("A user with this username already exists")

        raise

    return user_model


def get_user(username: str, db: Session) -> User | None:
    stmt = select(User).where(User.username == username)
    return db.scalars(stmt).first()
