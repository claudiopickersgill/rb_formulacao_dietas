from __future__ import annotations

import base64
import hashlib
import hmac
import os

_ALGORITHM = "pbkdf2_sha256"
_DEFAULT_ITERATIONS = 310_000
_SALT_BYTES = 16


def hash_password(password: str, *, iterations: int = _DEFAULT_ITERATIONS) -> str:
    """Gera um hash PBKDF2-SHA256 com salt aleatório.

    O valor retornado pode ser armazenado na planilha; a senha original não é
    recuperável a partir dele.
    """
    if not isinstance(password, str) or not password:
        raise ValueError("A senha não pode estar vazia.")
    if iterations < 100_000:
        raise ValueError("O número de iterações é insuficiente.")

    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    salt_b64 = base64.urlsafe_b64encode(salt).decode("ascii").rstrip("=")
    digest_b64 = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"{_ALGORITHM}${iterations}${salt_b64}${digest_b64}"


def verify_password(password: str, encoded_hash: str) -> bool:
    """Valida uma senha contra um hash criado por :func:`hash_password`."""
    if not isinstance(password, str) or not isinstance(encoded_hash, str):
        return False
    encoded_hash = encoded_hash.strip()
    if not password or not encoded_hash:
        return False

    try:
        algorithm, iterations_raw, salt_b64, digest_b64 = encoded_hash.split("$", 3)
        if algorithm != _ALGORITHM:
            return False
        iterations = int(iterations_raw)
        salt = _b64decode(salt_b64)
        expected = _b64decode(digest_b64)
    except (ValueError, TypeError):
        return False

    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(candidate, expected)


def has_password(encoded_hash: object) -> bool:
    return isinstance(encoded_hash, str) and encoded_hash.strip().startswith(f"{_ALGORITHM}$")


def validate_password_strength(password: str) -> list[str]:
    errors: list[str] = []
    if len(password) < 8:
        errors.append("A senha deve ter pelo menos 8 caracteres.")
    if password and password.strip() != password:
        errors.append("A senha não pode começar ou terminar com espaços.")
    return errors


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
