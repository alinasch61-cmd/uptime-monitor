from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    DUMMY_HASH,
    create_access_token,
    get_password_hash,
    verify_password_hash,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)

_UNIQUE_VIOLATION_SQLSTATE = "23505"

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={500: {"description": "Internal Server Error"}},
)


@router.post(
    "/register",
    status_code=201,
    response_model=RegisterResponse,
    responses={status.HTTP_409_CONFLICT: {"description": "User already exists"}},
)
def register_user(
    user: Annotated[RegisterRequest, Body()],
    db: Annotated[Session, Depends(get_db)],
) -> RegisterResponse:
    user_model = User(
        username=user.username, password_hash=get_password_hash(user.password)
    )

    try:
        db.add(user_model)
        db.commit()
        db.refresh(user_model)
    except IntegrityError as exc:
        db.rollback()

        if getattr(exc.orig, "sqlstate", None) == _UNIQUE_VIOLATION_SQLSTATE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this username is already exists",
            )

        raise

    return RegisterResponse(id=user_model.id, username=user_model.username)


def authenticate_user(username: str, user_password: str, db: Session) -> bool:
    stmt = select(User.password_hash).where(User.username == username)
    passw_in_db: str | None = db.scalars(stmt).first()

    if passw_in_db is None:
        verify_password_hash(user_password, DUMMY_HASH)
        return False

    return verify_password_hash(user_password, passw_in_db)


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Invalid username or password"}
    },
)
def login_user(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    if not authenticate_user(form_data.username, form_data.password, db):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(access_token=create_access_token(form_data.username))
