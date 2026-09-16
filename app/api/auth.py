from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
)
from app.db.session import get_db
from app.schemas.auth import (
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from app.services.auth import authenticate_user
from app.services.user import UserExistsError, create_user

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
    try:
        user_model = create_user(user.username, user.password, db)
    except UserExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this username already exists",
        )

    return RegisterResponse(id=user_model.id, username=user_model.username)


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
    user = authenticate_user(form_data.username, form_data.password, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(access_token=create_access_token(form_data.username))
