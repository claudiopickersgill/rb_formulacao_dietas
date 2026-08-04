from __future__ import annotations

import json
from abc import abstractmethod
from typing import Any

import pandas as pd

from ..config import (
    AUDIT_COLUMNS,
    DIET_COLUMNS,
    DIET_CONSTRAINT_COLUMNS,
    DIET_ITEM_COLUMNS,
    INGREDIENT_COLUMNS,
    TABLE_SCHEMAS,
    USER_COLUMNS,
)
from ..utils import as_bool, new_id, normalize_text, utc_now_iso
from .base import Repository


class TabularRepository(Repository):
    """CRUD shared by local CSV and Google Sheets backends."""

    @abstractmethod
    def _ensure_table(self, name: str, columns: list[str]) -> None: ...

    @abstractmethod
    def _read_table(self, name: str) -> pd.DataFrame: ...

    @abstractmethod
    def _write_table(self, name: str, frame: pd.DataFrame) -> None: ...

    def initialize(self) -> None:
        for name, columns in TABLE_SCHEMAS.items():
            self._ensure_table(name, columns)

    def _normalized(self, name: str) -> pd.DataFrame:
        frame = self._read_table(name).copy()
        schema = TABLE_SCHEMAS[name]
        for col in schema:
            if col not in frame.columns:
                frame[col] = None
        return frame[schema]

    def list_ingredients(self, active_only: bool = True) -> pd.DataFrame:
        frame = self._normalized("ingredientes")
        if active_only and not frame.empty:
            frame = frame[frame["ativo"].map(lambda value: as_bool(value, True))]
        return frame.sort_values(["tipo", "nome"], na_position="last").reset_index(drop=True)

    def upsert_ingredient(self, payload: dict[str, Any], actor: str) -> dict[str, Any]:
        now = utc_now_iso()
        data = {col: payload.get(col, "") for col in INGREDIENT_COLUMNS}
        data["ingredient_id"] = str(payload.get("ingredient_id") or new_id("ing"))
        data["ativo"] = as_bool(payload.get("ativo"), True)
        data["created_by"] = str(payload.get("created_by") or actor)
        data["created_at"] = str(payload.get("created_at") or now)
        data["updated_at"] = now

        current = self._normalized("ingredientes")
        mask = current["ingredient_id"].astype(str).eq(data["ingredient_id"])
        action = "atualizar"
        if mask.any():
            idx = current.index[mask][0]
            for col in INGREDIENT_COLUMNS:
                current.at[idx, col] = data[col]
        else:
            action = "criar"
            new_row = pd.DataFrame([data], columns=INGREDIENT_COLUMNS)
            current = new_row if current.empty else pd.concat([current, new_row], ignore_index=True)
        self._write_table("ingredientes", current[INGREDIENT_COLUMNS])
        self.audit(actor, action, "ingrediente", data["ingredient_id"], data.get("nome", ""))
        return data

    def set_ingredient_active(self, ingredient_id: str, active: bool, actor: str) -> None:
        current = self._normalized("ingredientes")
        mask = current["ingredient_id"].astype(str).eq(str(ingredient_id))
        if not mask.any():
            raise KeyError(f"Ingrediente não encontrado: {ingredient_id}")
        current.loc[mask, "ativo"] = bool(active)
        current.loc[mask, "updated_at"] = utc_now_iso()
        self._write_table("ingredientes", current)
        self.audit(actor, "ativar" if active else "inativar", "ingrediente", ingredient_id, "")

    def list_users(self) -> pd.DataFrame:
        frame = self._normalized("usuarios")
        return frame.sort_values("nome", na_position="last").reset_index(drop=True)

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        frame = self._normalized("usuarios")
        if frame.empty:
            return None
        target = normalize_text(email)
        mask = frame["email"].map(normalize_text).eq(target)
        if not mask.any():
            return None
        return frame.loc[mask].iloc[0].to_dict()

    def upsert_user(self, payload: dict[str, Any], actor: str) -> dict[str, Any]:
        now = utc_now_iso()
        data = {col: payload.get(col, "") for col in USER_COLUMNS}
        data["user_id"] = str(payload.get("user_id") or new_id("usr"))
        data["email"] = str(payload.get("email") or "").strip().lower()
        data["ativo"] = as_bool(payload.get("ativo"), True)
        data["created_at"] = str(payload.get("created_at") or now)
        data["updated_at"] = now

        if not data["email"]:
            raise ValueError("O email do usuário é obrigatório.")

        current = self._normalized("usuarios")
        id_mask = current["user_id"].astype(str).eq(data["user_id"])
        email_mask = current["email"].map(normalize_text).eq(normalize_text(data["email"]))
        mask = id_mask | email_mask
        action = "atualizar"
        if mask.any():
            idx = current.index[mask][0]
            data["user_id"] = str(current.at[idx, "user_id"] or data["user_id"])
            data["created_at"] = str(current.at[idx, "created_at"] or data["created_at"])
            for col in USER_COLUMNS:
                current.at[idx, col] = data[col]
        else:
            action = "criar"
            new_row = pd.DataFrame([data], columns=USER_COLUMNS)
            current = new_row if current.empty else pd.concat([current, new_row], ignore_index=True)
        self._write_table("usuarios", current[USER_COLUMNS])
        self.audit(actor, action, "usuario", data["user_id"], data["email"])
        return data

    def touch_login(self, email: str) -> None:
        current = self._normalized("usuarios")
        if current.empty:
            return
        mask = current["email"].map(normalize_text).eq(normalize_text(email))
        if mask.any():
            current.loc[mask, "last_login"] = utc_now_iso()
            self._write_table("usuarios", current)

    def list_diets(self, requester_email: str, requester_role: str) -> pd.DataFrame:
        frame = self._normalized("dietas")
        if requester_role != "Administrador" and not frame.empty:
            frame = frame[frame["proprietario"].map(normalize_text).eq(normalize_text(requester_email))]
        if "updated_at" in frame.columns:
            frame = frame.sort_values("updated_at", ascending=False, na_position="last")
        return frame.reset_index(drop=True)

    def get_diet(self, diet_id: str) -> dict[str, Any] | None:
        diets = self._normalized("dietas")
        mask = diets["diet_id"].astype(str).eq(str(diet_id))
        if not mask.any():
            return None
        metadata = diets.loc[mask].iloc[0].to_dict()
        items = self._normalized("dieta_ingredientes")
        items = items[items["diet_id"].astype(str).eq(str(diet_id))].copy()
        if not items.empty:
            items["ordem"] = pd.to_numeric(items["ordem"], errors="coerce")
            items = items.sort_values("ordem", na_position="last").reset_index(drop=True)
        constraints = self._normalized("dieta_restricoes")
        constraints = constraints[constraints["diet_id"].astype(str).eq(str(diet_id))].reset_index(drop=True)
        return {"metadata": metadata, "items": items, "constraints": constraints}

    def save_diet(
        self,
        metadata: dict[str, Any],
        items: pd.DataFrame,
        constraints: pd.DataFrame,
        actor: str,
    ) -> str:
        now = utc_now_iso()
        diet_id = str(metadata.get("diet_id") or new_id("diet"))
        current_diets = self._normalized("dietas")
        existing = current_diets["diet_id"].astype(str).eq(diet_id)
        previous_created = ""
        if existing.any():
            previous_created = str(current_diets.loc[existing, "created_at"].iloc[0] or "")

        diet_data = {col: metadata.get(col, "") for col in DIET_COLUMNS}
        diet_data["diet_id"] = diet_id
        diet_data["proprietario"] = str(metadata.get("proprietario") or actor)
        diet_data["created_at"] = str(metadata.get("created_at") or previous_created or now)
        diet_data["updated_at"] = now

        if existing.any():
            idx = current_diets.index[existing][0]
            for col in DIET_COLUMNS:
                current_diets.at[idx, col] = diet_data[col]
            action = "atualizar"
        else:
            new_row = pd.DataFrame([diet_data], columns=DIET_COLUMNS)
            current_diets = new_row if current_diets.empty else pd.concat([current_diets, new_row], ignore_index=True)
            action = "criar"
        self._write_table("dietas", current_diets[DIET_COLUMNS])

        current_items = self._normalized("dieta_ingredientes")
        current_items = current_items[~current_items["diet_id"].astype(str).eq(diet_id)]
        item_frame = items.copy().reset_index(drop=True)
        item_frame["diet_id"] = diet_id
        item_frame["ordem"] = range(1, len(item_frame) + 1)
        for col in DIET_ITEM_COLUMNS:
            if col not in item_frame.columns:
                item_frame[col] = ""
        item_rows = item_frame[DIET_ITEM_COLUMNS]
        current_items = item_rows if current_items.empty else pd.concat([current_items, item_rows], ignore_index=True)
        self._write_table("dieta_ingredientes", current_items[DIET_ITEM_COLUMNS])

        current_constraints = self._normalized("dieta_restricoes")
        current_constraints = current_constraints[
            ~current_constraints["diet_id"].astype(str).eq(diet_id)
        ]
        constraint_frame = constraints.copy().reset_index(drop=True)
        constraint_frame["diet_id"] = diet_id
        for col in DIET_CONSTRAINT_COLUMNS:
            if col not in constraint_frame.columns:
                constraint_frame[col] = ""
        constraint_rows = constraint_frame[DIET_CONSTRAINT_COLUMNS]
        current_constraints = constraint_rows if current_constraints.empty else pd.concat(
            [current_constraints, constraint_rows], ignore_index=True
        )
        self._write_table("dieta_restricoes", current_constraints[DIET_CONSTRAINT_COLUMNS])

        self.audit(actor, action, "dieta", diet_id, str(metadata.get("nome") or ""))
        return diet_id

    def delete_diet(self, diet_id: str, actor: str) -> None:
        diets = self._normalized("dietas")
        mask = diets["diet_id"].astype(str).eq(str(diet_id))
        if not mask.any():
            raise KeyError(f"Dieta não encontrada: {diet_id}")
        name = str(diets.loc[mask, "nome"].iloc[0] or "")
        self._write_table("dietas", diets.loc[~mask, DIET_COLUMNS])

        items = self._normalized("dieta_ingredientes")
        self._write_table(
            "dieta_ingredientes",
            items.loc[~items["diet_id"].astype(str).eq(str(diet_id)), DIET_ITEM_COLUMNS],
        )
        restrictions = self._normalized("dieta_restricoes")
        self._write_table(
            "dieta_restricoes",
            restrictions.loc[
                ~restrictions["diet_id"].astype(str).eq(str(diet_id)),
                DIET_CONSTRAINT_COLUMNS,
            ],
        )
        self.audit(actor, "excluir", "dieta", diet_id, name)

    def audit(self, actor: str, action: str, entity: str, entity_id: str, details: Any) -> None:
        audit = self._normalized("auditoria")
        row = {
            "audit_id": new_id("aud"),
            "timestamp": utc_now_iso(),
            "usuario": actor,
            "acao": action,
            "entidade": entity,
            "entity_id": entity_id,
            "detalhes": details if isinstance(details, str) else json.dumps(details, ensure_ascii=False),
        }
        new_row = pd.DataFrame([row], columns=AUDIT_COLUMNS)
        audit = new_row if audit.empty else pd.concat([audit, new_row], ignore_index=True)
        self._write_table("auditoria", audit[AUDIT_COLUMNS])

    def list_audit(self, limit: int = 250) -> pd.DataFrame:
        frame = self._normalized("auditoria")
        if frame.empty:
            return frame
        frame = frame.sort_values("timestamp", ascending=False, na_position="last")
        return frame.head(limit).reset_index(drop=True)
