from __future__ import annotations

from src.security import hash_password, has_password, validate_password_strength, verify_password


def test_password_hash_round_trip() -> None:
    encoded = hash_password("SenhaForte123")
    assert encoded != "SenhaForte123"
    assert has_password(encoded)
    assert verify_password("SenhaForte123", encoded)
    assert not verify_password("senha-incorreta", encoded)


def test_password_hash_uses_random_salt() -> None:
    first = hash_password("SenhaForte123")
    second = hash_password("SenhaForte123")
    assert first != second
    assert verify_password("SenhaForte123", first)
    assert verify_password("SenhaForte123", second)


def test_password_strength() -> None:
    assert validate_password_strength("1234567")
    assert validate_password_strength(" senha-segura")
    assert validate_password_strength("senha-segura ")
    assert validate_password_strength("senha-segura") == []
