from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .base import Repository
from .google_sheets import GoogleSheetsRepository
from .local import LocalRepository


def build_repository(
    mode: str,
    project_root: str | Path,
    settings: Mapping[str, Any] | None = None,
    service_account: Mapping[str, Any] | None = None,
) -> Repository:
    settings = settings or {}
    root = Path(project_root)
    normalized = str(mode or "local").strip().lower()
    if normalized == "google_sheets":
        return GoogleSheetsRepository(
            credentials=dict(service_account or {}),
            spreadsheet_id=str(settings.get("spreadsheet_id", "")),
            spreadsheet_url=str(settings.get("spreadsheet_url", "")),
            cache_ttl_seconds=int(settings.get("cache_ttl_seconds", 60)),
            table_prefix=str(settings.get("table_prefix", "rb_")),
            auto_migrate_legacy=bool(settings.get("auto_migrate_legacy", True)),
            legacy_worksheet_title=str(settings.get("legacy_worksheet_title", "")),
            legacy_worksheet_index=int(settings.get("legacy_worksheet_index", 0)),
            max_retries=int(settings.get("max_retries", 5)),
        )
    return LocalRepository(root=root / ".local_db", seed_dir=root / "data")
