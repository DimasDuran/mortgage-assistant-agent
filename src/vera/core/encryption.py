"""Symmetric field-level encryption for sensitive data (SSN, account numbers).

Uses Fernet (AES-128-CBC with HMAC-SHA256) so the ciphertext is
authenticated. The encryption key is loaded from settings. If no key is
configured, encryption is a silent no-op (pass-through) so the system works
in development without requiring a key.
"""

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from vera.core.config import get_settings


@lru_cache
def _cipher() -> Fernet | None:
    key = get_settings().encryption_key
    if not key:
        return None
    return Fernet(key.encode())


def encrypt(plaintext: str | None) -> str | None:
    """Encrypt a plaintext value. Returns None if input is None."""
    if plaintext is None:
        return None
    cipher = _cipher()
    if cipher is None:
        return plaintext
    return cipher.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str | None) -> str | None:
    """Decrypt a ciphertext value. Returns None if input is None.

    If no encryption key is configured, the value is returned as-is (no-op).
    If decryption fails, the value is returned as-is (fallback for
    previously unencrypted data during migration).
    """
    if ciphertext is None:
        return None
    cipher = _cipher()
    if cipher is None:
        return ciphertext
    try:
        return cipher.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        return ciphertext
