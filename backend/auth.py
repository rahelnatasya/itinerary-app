from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
import os

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback_rahasia_lokal")
ALGORITHM = "HS256"

security = HTTPBearer()


def create_access_token(data: dict) -> str:
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user_from_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    user_name = payload.get("sub")
    if not user_name:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    return user_name


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    return get_current_user_from_token(credentials.credentials)
