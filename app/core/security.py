from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash


def hash_pasword(password: str) -> str:
    password_hasher = PasswordHash.recommended()
    return password_hasher.hash(password)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
