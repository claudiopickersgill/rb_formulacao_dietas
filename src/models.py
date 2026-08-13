from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(slots=True)
class User:
    user_id: str
    email: str
    nome: str
    perfil: str
    ativo: bool = True

    @property
    def is_admin(self) -> bool:
        return self.perfil == "Administrador"

    @property
    def can_edit(self) -> bool:
        return self.perfil in {"Administrador", "Formulador"}


@dataclass(slots=True)
class SolverResult:
    success: bool
    status: str
    message: str
    cost_per_kg: float | None = None
    items: pd.DataFrame = field(default_factory=pd.DataFrame)
    constraints: pd.DataFrame = field(default_factory=pd.DataFrame)
    diagnostics: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
