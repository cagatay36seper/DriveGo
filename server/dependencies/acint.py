import json
from typing import Any, Optional

from fastapi import HTTPException, Request, status

from server.routes.acint_validator import ACIntError, validate_acint


def extract_acint_from_request(request: Request) -> Optional[list[Any]]:
    raw_value = request.headers.get("X-ACINT") or request.headers.get("X-Acint")
    if not raw_value:
        return None

    if isinstance(raw_value, str):
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Request could not be verified.",
            ) from exc
        return parsed

    return raw_value


def require_valid_acint(value: Optional[list[Any]], label: str = "request") -> dict:
    if not value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Request could not be verified for {label}.",
        )

    try:
        return validate_acint(value)
    except ACIntError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Request could not be verified for {label}.",
        ) from exc
