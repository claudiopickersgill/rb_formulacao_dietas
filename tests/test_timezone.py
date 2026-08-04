from __future__ import annotations

import pandas as pd

from src.repositories.local import LocalRepository
from src.utils import APP_TIMEZONE_NAME, local_now_iso, timestamp_to_local_iso


def test_current_timestamp_uses_brazil_timezone() -> None:
    value = local_now_iso()
    parsed = pd.Timestamp(value)
    assert APP_TIMEZONE_NAME == "America/Sao_Paulo"
    assert parsed.utcoffset().total_seconds() == -3 * 60 * 60


def test_utc_timestamp_is_converted_to_sao_paulo() -> None:
    converted = timestamp_to_local_iso("2026-08-04T14:23:28+00:00")
    assert converted == "2026-08-04T11:23:28-03:00"


def test_naive_timestamp_is_treated_as_existing_local_time() -> None:
    converted = timestamp_to_local_iso("2026-08-04T11:23:28")
    assert converted == "2026-08-04T11:23:28-03:00"


def test_repository_initialization_migrates_existing_utc_fields(tmp_path) -> None:
    repository = LocalRepository(tmp_path)
    repository.initialize()

    users = pd.DataFrame(
        [
            {
                "user_id": "usr_1",
                "email": "junior@rb.com.br",
                "nome": "Junior",
                "perfil": "Formulador",
                "ativo": True,
                "password_hash": "",
                "created_at": "2026-08-04T13:07:18+00:00",
                "updated_at": "2026-08-04T13:07:18+00:00",
                "last_login": "2026-08-04T14:23:28+00:00",
            }
        ]
    )
    repository._write_table("usuarios", users)

    repository.initialize()
    stored = repository.get_user_by_email("junior@rb.com.br")

    assert stored is not None
    assert stored["created_at"] == "2026-08-04T10:07:18-03:00"
    assert stored["updated_at"] == "2026-08-04T10:07:18-03:00"
    assert stored["last_login"] == "2026-08-04T11:23:28-03:00"
