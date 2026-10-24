import hashlib
import os
import secrets

from fastapi import Header, HTTPException, status

import config


def verify_api_key(authorization: str | None = Header(None)) -> str:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected 'Bearer <key>'.",
        )

    provided_key = authorization.removeprefix("Bearer ")
    expected_key = os.getenv(config.API_KEY)

    # Fail closed: an unset key must reject every request with 401, never 500.
    # Bytes comparison: compare_digest raises TypeError on non-ASCII str.
    if not expected_key or not secrets.compare_digest(
        provided_key.encode(), expected_key.encode()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )

    return hashlib.sha256(provided_key.encode()).hexdigest()
