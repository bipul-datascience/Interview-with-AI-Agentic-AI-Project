"""Encryption for sensitive persisted application records."""

from __future__ import annotations

import json
import os

from cryptography.fernet import Fernet, InvalidToken


class EncryptionConfigurationError(RuntimeError):
    pass


def _fernet() -> Fernet:
    key = os.getenv("DATA_ENCRYPTION_KEY")
    if not key:
        raise EncryptionConfigurationError("DATA_ENCRYPTION_KEY is required before persisting resume or interview data.")
    return Fernet(key.encode())


def encrypt_text(value: str | dict) -> str:
    content = json.dumps(value) if isinstance(value, dict) else value
    return _fernet().encrypt(content.encode()).decode()


def decrypt_text(value: str) -> str | dict:
    try:
        content = _fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise EncryptionConfigurationError("Unable to decrypt saved data. Check DATA_ENCRYPTION_KEY.") from exc
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return content
