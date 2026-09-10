from typing import Annotated

from fastapi import APIRouter, Body
from schemas.auth import LoginRequest, RegisterRequest, RegisterResponse, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201)
async def register_user(user: Annotated[RegisterRequest, Body()]) -> RegisterResponse:
    pass


@router.post("/login")
async def login_user(user: Annotated[LoginRequest, Body()]) -> TokenResponse:
    pass
