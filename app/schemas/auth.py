from pydantic import BaseModel


class RegisterRequest(BaseModel):
    usernamme: str
    password: str

class LoginRequest(BaseModel):
    usernamme: str
    password: str

class TokenResponse(BaseModel):
    token: str
    token_type: str = "bearer"

