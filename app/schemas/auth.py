from pydantic import BaseModel


class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    token: str
    token_type: str = "bearer"

class RegisterResponse(BaseModel):
    username: str
    id: int

