import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import Request


AUTH_SECRET = os.getenv("AUTH_SECRET", "")

if len(AUTH_SECRET) < 32:
    if os.getenv("PRODUCTION", "false").lower() in {"1", "true", "yes"}:
        raise RuntimeError("secret too short")
    AUTH_SECRET = "local-development-secret-do-not-use-in-production-9f2e"


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def create_access_token(payload: dict[str, Any], expires_minutes: int = 60 * 24 * 7) -> str:
    issued_at = datetime.now(timezone.utc)
    token_payload = dict(payload)
    token_payload["iat"] = int(issued_at.timestamp())
    token_payload["exp"] = int((issued_at.timestamp()) + expires_minutes * 60)

    encoded_payload = _b64url_encode(json.dumps(token_payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    signature = hmac.new(AUTH_SECRET.encode("utf-8"), encoded_payload.encode("utf-8"), hashlib.sha256).digest()
    return f"{encoded_payload}.{_b64url_encode(signature)}"


def verify_access_token(token: str) -> Optional[dict[str, Any]]:
    if not token or "." not in token:
        return None

    try:
        encoded_payload, encoded_signature = token.rsplit(".", 1)
        expected_signature = hmac.new(
            AUTH_SECRET.encode("utf-8"),
            encoded_payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(_b64url_encode(expected_signature), encoded_signature):
            return None

        payload = json.loads(_b64url_decode(encoded_payload).decode("utf-8"))
        exp = int(payload.get("exp", 0))
        if exp < int(datetime.now(timezone.utc).timestamp()):
            return None
        return payload
    except Exception:
        return None


def extract_access_token(request: Request) -> Optional[str]:
    token = request.cookies.get("access_token")
    if token:
        return token

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]

    return None
