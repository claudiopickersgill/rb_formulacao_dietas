from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class Repository(ABC):
    @abstractmethod
    def initialize(self) -> None: ...

    @abstractmethod
    def list_ingredients(self, active_only: bool = True) -> pd.DataFrame: ...

    @abstractmethod
    def upsert_ingredient(self, payload: dict[str, Any], actor: str) -> dict[str, Any]: ...

    @abstractmethod
    def set_ingredient_active(self, ingredient_id: str, active: bool, actor: str) -> None: ...

    @abstractmethod
    def list_users(self) -> pd.DataFrame: ...

    @abstractmethod
    def get_user_by_email(self, email: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def upsert_user(self, payload: dict[str, Any], actor: str) -> dict[str, Any]: ...

    @abstractmethod
    def touch_login(self, email: str) -> None: ...

    @abstractmethod
    def list_diets(self, requester_email: str, requester_role: str) -> pd.DataFrame: ...

    @abstractmethod
    def get_diet(self, diet_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def save_diet(
        self,
        metadata: dict[str, Any],
        items: pd.DataFrame,
        constraints: pd.DataFrame,
        actor: str,
    ) -> str: ...

    @abstractmethod
    def delete_diet(self, diet_id: str, actor: str) -> None: ...

    @abstractmethod
    def list_audit(self, limit: int = 250) -> pd.DataFrame: ...
