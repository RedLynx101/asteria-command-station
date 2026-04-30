from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from pathlib import Path

from .types import MobileAuthConfig


def generate_device_token() -> str:
    return secrets.token_urlsafe(32)


def constant_time_match(expected: str, provided: str) -> bool:
    return hmac.compare_digest(expected.encode("utf-8"), provided.encode("utf-8"))


def redact_token(token: str, visible: int = 6) -> str:
    if len(token) <= visible:
        return "*" * len(token)
    return token[:visible] + "..." + ("*" * 6)


def token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]


def config_path(base_dir: Path) -> Path:
    return base_dir / "mobile-auth.json"


def make_auth_config(device_name: str = "Asteria DS") -> MobileAuthConfig:
    return MobileAuthConfig(device_token=generate_device_token(), device_name=device_name)


def load_auth_config(base_dir: Path) -> MobileAuthConfig:
    target = config_path(base_dir)
    payload = json.loads(target.read_text(encoding="utf-8"))
    return MobileAuthConfig(**payload)
