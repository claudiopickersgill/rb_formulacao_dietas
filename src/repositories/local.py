from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import pandas as pd

from ..config import TABLE_SCHEMAS
from .tabular import TabularRepository


class LocalRepository(TabularRepository):
    def __init__(self, root: str | Path, seed_dir: str | Path | None = None) -> None:
        self.root = Path(root)
        self.seed_dir = Path(seed_dir) if seed_dir else None
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, name: str) -> Path:
        return self.root / f"{name}.csv"

    def _ensure_table(self, name: str, columns: list[str]) -> None:
        path = self._path(name)
        if path.exists():
            return
        seed = self.seed_dir / f"seed_{name}.csv" if self.seed_dir else None
        if seed and seed.exists():
            shutil.copy2(seed, path)
            return
        pd.DataFrame(columns=columns).to_csv(path, index=False, encoding="utf-8-sig")

    def _read_table(self, name: str) -> pd.DataFrame:
        path = self._path(name)
        if not path.exists():
            self._ensure_table(name, TABLE_SCHEMAS[name])
        try:
            return pd.read_csv(path, encoding="utf-8-sig")
        except pd.errors.EmptyDataError:
            return pd.DataFrame(columns=TABLE_SCHEMAS[name])

    def _write_table(self, name: str, frame: pd.DataFrame) -> None:
        path = self._path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        frame = frame.copy()
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".csv",
            prefix=f"{name}_",
            dir=path.parent,
            delete=False,
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            temporary = Path(handle.name)
            frame.to_csv(handle, index=False)
        os.replace(temporary, path)
