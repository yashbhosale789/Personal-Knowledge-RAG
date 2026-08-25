import os
import secrets
from fastapi import Header, HTTPException, status

import config


def verify_api_key(authorization: str | None = Header(None)) -> None:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected 'Bearer <key>'.",
        )

    provided_key = authorization.removeprefix("Bearer ")

    if not secrets.compare_digest(provided_key, os.getenv(config.API_KEY)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )
