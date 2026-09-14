from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_pasword
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
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
    user_model = User(username=user.username, password_hash=hash_pasword(user.password))

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


@router.post("/login", response_model=TokenResponse)
async def login_user(user: Annotated[LoginRequest, Body()]) -> TokenResponse:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="This method is not implemented yet",
    )
