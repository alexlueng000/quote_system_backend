from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any


TOKEN_TTL_SECONDS = 60 * 60 * 8
PASSWORD_HASH_ITERATIONS = 200000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_HASH_ITERATIONS)
    return (
        f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}$"
        f"{base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"
    )


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        algorithm, iterations_text, salt_text, digest_text = password_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    iterations = int(iterations_text)
    salt = base64.b64decode(salt_text.encode())
    expected = base64.b64decode(digest_text.encode())
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return hmac.compare_digest(actual, expected)


def create_token(payload: dict[str, Any]) -> str:
    data = {**payload, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    body = _base64_url_encode(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode())
    signature = _sign(body)
    return f"{body}.{signature}"


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        body, signature = token.split(".", 1)
    except ValueError:
        return None
    if not hmac.compare_digest(_sign(body), signature):
        return None
    try:
        payload = json.loads(_base64_url_decode(body).decode())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload


def _sign(body: str) -> str:
    secret = os.getenv("AUTH_SECRET", "dev-quote-system-secret")
    digest = hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()
    return _base64_url_encode(digest)


def _base64_url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _base64_url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode())
