from datetime import UTC, datetime, timedelta

import jwt
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash

from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

_password_hasher = PasswordHash.recommended()


def get_password_hash(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password_hash(plain_password: str, hashed_password: str) -> bool:
    return _password_hasher.verify(plain_password, hashed_password)


DUMMY_HASH = get_password_hash("fakepassword")
_JWT_ALGORITHM = "HS256"


def create_access_token(username: str) -> str:
    token_data = {
        "sub": username,
        "exp": datetime.now(tz=UTC) + timedelta(settings.access_token_expires_minutes),
    }

    return jwt.encode(token_data, settings.secret_key, algorithm=_JWT_ALGORITHM)
