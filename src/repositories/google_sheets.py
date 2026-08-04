from __future__ import annotations

import re
import time
import unicodedata
from collections import Counter
from typing import Any, Callable, TypeVar

import pandas as pd

from ..config import INGREDIENT_COLUMNS, NUTRIENT_CODES, TABLE_SCHEMAS
from ..google_connection import open_spreadsheet
from ..utils import as_float, dataframe_for_storage, local_now_iso, new_id
from .tabular import TabularRepository

T = TypeVar("T")


class GoogleSheetsRepository(TabularRepository):
    """Repositório tabular que reutiliza a conexão Google do projeto original.

    As abas do aplicativo recebem um prefixo (por padrão ``rb_``), portanto a
    primeira aba já existente não é apagada nem reformatada. Quando habilitada,
    a migração legada copia os ingredientes dessa primeira aba para
    ``rb_ingredientes`` apenas se a tabela nova estiver vazia.
    """

    def __init__(
        self,
        credentials: dict[str, Any],
        spreadsheet_id: str = "",
        spreadsheet_url: str = "",
        cache_ttl_seconds: int = 60,
        table_prefix: str = "rb_",
        auto_migrate_legacy: bool = True,
        legacy_worksheet_title: str = "",
        legacy_worksheet_index: int = 0,
        max_retries: int = 5,
    ) -> None:
        self.spreadsheet = open_spreadsheet(
            credentials,
            spreadsheet_id=spreadsheet_id,
            spreadsheet_url=spreadsheet_url,
        )
        self.cache_ttl_seconds = max(int(cache_ttl_seconds), 0)
        self.table_prefix = str(table_prefix or "")
        self.auto_migrate_legacy = bool(auto_migrate_legacy)
        self.legacy_worksheet_title = str(legacy_worksheet_title or "").strip()
        self.legacy_worksheet_index = max(int(legacy_worksheet_index), 0)
        self.max_retries = max(int(max_retries), 1)
        self._cache: dict[str, tuple[float, pd.DataFrame]] = {}
        self.legacy_migration_summary: dict[str, Any] = {}

    def initialize(self) -> None:
        super().initialize()
        if self.auto_migrate_legacy:
            self._migrate_legacy_ingredients_if_needed()

    def _tab_name(self, logical_name: str) -> str:
        return f"{self.table_prefix}{logical_name}"

    def _worksheet(self, name: str):
        import gspread

        title = self._tab_name(name)
        try:
            return self._call(lambda: self.spreadsheet.worksheet(title))
        except gspread.WorksheetNotFound:
            columns = len(TABLE_SCHEMAS[name])
            return self._call(
                lambda: self.spreadsheet.add_worksheet(
                    title=title,
                    rows=1000,
                    cols=max(columns, 10),
                )
            )

    def _ensure_table(self, name: str, columns: list[str]) -> None:
        worksheet = self._worksheet(name)
        values = self._call(worksheet.get_all_values)
        if not values:
            self._call(lambda: worksheet.update(values=[columns], range_name="A1"))
            try:
                self._call(
                    lambda: worksheet.format(
                        f"A1:{_column_letter(len(columns))}1",
                        {
                            "textFormat": {"bold": True},
                            "backgroundColor": {"red": 0.85, "green": 0.92, "blue": 0.97},
                        },
                    )
                )
            except Exception:
                # Formatação é cosmética; não deve impedir a inicialização.
                pass
            return

        header = [str(value).strip() for value in values[0]]
        if header == columns:
            return

        # Evolução de schema sem perder colunas conhecidas.
        existing = (
            pd.DataFrame(values[1:], columns=header)
            if len(values) > 1 and header
            else pd.DataFrame()
        )
        for column in columns:
            if column not in existing.columns:
                existing[column] = ""
        self._write_table(name, existing[columns])

    def _read_table(self, name: str) -> pd.DataFrame:
        cached = self._cache.get(name)
        if cached and time.monotonic() - cached[0] <= self.cache_ttl_seconds:
            return cached[1].copy()

        worksheet = self._worksheet(name)
        values = self._call(worksheet.get_all_values)
        if not values:
            frame = pd.DataFrame(columns=TABLE_SCHEMAS[name])
        else:
            header = [str(value).strip() for value in values[0]]
            rows = values[1:]
            frame = pd.DataFrame(rows, columns=header)
        self._cache[name] = (time.monotonic(), frame.copy())
        return frame

    def _write_table(self, name: str, frame: pd.DataFrame) -> None:
        worksheet = self._worksheet(name)
        storage = dataframe_for_storage(frame)
        values = [storage.columns.tolist(), *storage.values.tolist()]
        rows_needed = max(len(values) + 20, 100)
        cols_needed = max(len(storage.columns), 10)
        self._call(lambda: worksheet.resize(rows=rows_needed, cols=cols_needed))
        self._call(worksheet.clear)
        self._call(lambda: worksheet.update(values=values, range_name="A1"))
        self._cache[name] = (time.monotonic(), frame.copy())

    def clear_cache(self) -> None:
        self._cache.clear()

    def _call(self, operation: Callable[[], T]) -> T:
        """Repete chamadas temporariamente limitadas pela API (429/5xx)."""
        import gspread

        delay = 1.0
        for attempt in range(self.max_retries):
            try:
                return operation()
            except gspread.exceptions.APIError as exc:
                response = getattr(exc, "response", None)
                status = getattr(response, "status_code", None)
                retryable = status == 429 or (isinstance(status, int) and status >= 500)
                if not retryable or attempt == self.max_retries - 1:
                    raise
                time.sleep(delay)
                delay = min(delay * 2, 16.0)
        raise RuntimeError("Falha inesperada ao acessar o Google Sheets.")

    def _migrate_legacy_ingredients_if_needed(self) -> None:
        target = self._read_table("ingredientes")
        if not target.empty:
            self.legacy_migration_summary = {
                "executed": False,
                "reason": "A tabela de ingredientes do aplicativo já possui dados.",
            }
            return

        legacy = self._legacy_worksheet()
        if legacy is None:
            self.legacy_migration_summary = {
                "executed": False,
                "reason": "Nenhuma aba legada compatível foi encontrada.",
            }
            return

        values = self._call(legacy.get_all_values)
        converted = _convert_legacy_ingredient_values(values)
        if converted.empty:
            self.legacy_migration_summary = {
                "executed": False,
                "reason": f"A aba '{legacy.title}' não contém ingredientes reconhecíveis.",
            }
            return

        self._write_table("ingredientes", converted[INGREDIENT_COLUMNS])
        warnings = int(converted["qualidade_dados"].astype(str).str.strip().ne("").sum())
        self.legacy_migration_summary = {
            "executed": True,
            "source": legacy.title,
            "rows": len(converted),
            "warnings": warnings,
        }
        self.audit(
            "migracao_google_sheets",
            "migrar",
            "ingredientes",
            "legacy_first_worksheet",
            f"{len(converted)} registros copiados de {legacy.title}; {warnings} alertas.",
        )

    def _legacy_worksheet(self):
        worksheets = self._call(self.spreadsheet.worksheets)
        app_titles = {self._tab_name(name) for name in TABLE_SCHEMAS}
        candidates = [worksheet for worksheet in worksheets if worksheet.title not in app_titles]
        if not candidates:
            return None

        if self.legacy_worksheet_title:
            for worksheet in candidates:
                if worksheet.title == self.legacy_worksheet_title:
                    return worksheet
            return None

        ordered = candidates[self.legacy_worksheet_index :] + candidates[: self.legacy_worksheet_index]
        for worksheet in ordered:
            values = self._call(worksheet.get_all_values)
            if values and _looks_like_legacy_ingredients(values[0]):
                return worksheet
        return None


def _convert_legacy_ingredient_values(values: list[list[str]]) -> pd.DataFrame:
    if not values:
        return pd.DataFrame(columns=INGREDIENT_COLUMNS)
    raw_headers = [str(value).strip() for value in values[0]]
    if not _looks_like_legacy_ingredients(raw_headers):
        return pd.DataFrame(columns=INGREDIENT_COLUMNS)

    width = len(raw_headers)
    rows = [(row + [""] * width)[:width] for row in values[1:]]
    frame = pd.DataFrame(rows, columns=raw_headers)
    renamed: dict[str, str] = {}
    nutrient_lookup = {_normalize_header(code): code for code in NUTRIENT_CODES}
    for column in frame.columns:
        normalized = _normalize_header(column)
        target = _LEGACY_HEADER_MAP.get(normalized) or nutrient_lookup.get(normalized)
        if target:
            renamed[column] = target
    frame = frame.rename(columns=renamed)

    for required in ["tipo", "nome"]:
        if required not in frame.columns:
            return pd.DataFrame(columns=INGREDIENT_COLUMNS)
    frame = frame[
        frame["tipo"].fillna("").astype(str).str.strip().ne("")
        & frame["nome"].fillna("").astype(str).str.strip().ne("")
    ].copy()
    if frame.empty:
        return pd.DataFrame(columns=INGREDIENT_COLUMNS)

    for column in ["classificacao", "formula_quimica", "fonte"]:
        if column not in frame.columns:
            frame[column] = ""
    if "preco_padrao" not in frame.columns:
        frame["preco_padrao"] = None
    for code in NUTRIENT_CODES:
        if code not in frame.columns:
            frame[code] = None

    for column in ["preco_padrao", *NUTRIENT_CODES]:
        frame[column] = frame[column].map(lambda value: as_float(value))

    duplicate_counts = Counter(
        (_clean_text(row.tipo), _clean_text(row.nome)) for row in frame.itertuples()
    )
    quality: list[str] = []
    for row in frame.itertuples():
        issues: list[str] = []
        key = (_clean_text(row.tipo), _clean_text(row.nome))
        if duplicate_counts[key] > 1:
            issues.append("Nome duplicado na planilha legada")
        classification = str(getattr(row, "classificacao", "") or "").strip()
        if len(classification) == 1 and classification.isalpha():
            issues.append("Classificação parece ser nota de rodapé")
        if _clean_text(row.tipo) == "mineral" and _clean_text(classification) == "energetico":
            issues.append("Classificação incompatível com tipo mineral")
        if _clean_text(row.tipo) == "alimento":
            major = [getattr(row, code, None) for code in ["NDT", "PB", "FDN", "FDA", "AMIDO"]]
            numeric = [float(value or 0) for value in major]
            if all(value == 0 for value in numeric):
                issues.append("Composição principal possivelmente incompleta")
            elif float(getattr(row, "NDT", None) or 0) == 0 and any(value > 0 for value in numeric[2:]):
                issues.append("NDT igual a zero; revisar se é dado ausente")
        quality.append("; ".join(issues))

    now = local_now_iso()
    frame["ingredient_id"] = [new_id("ing") for _ in range(len(frame))]
    frame["ativo"] = True
    frame["qualidade_dados"] = quality
    frame["created_by"] = "migracao_google_sheets"
    frame["created_at"] = now
    frame["updated_at"] = now

    for column in INGREDIENT_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    return frame[INGREDIENT_COLUMNS].reset_index(drop=True)


def _looks_like_legacy_ingredients(headers: list[str]) -> bool:
    normalized = {_normalize_header(header) for header in headers}
    has_type = "tipo" in normalized
    has_name = bool(normalized & {"ingredientes", "ingrediente", "nome"})
    has_nutrient = bool(normalized & {_normalize_header(code) for code in NUTRIENT_CODES})
    return has_type and has_name and has_nutrient


def _normalize_header(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _clean_text(value: Any) -> str:
    return _normalize_header(value)


_LEGACY_HEADER_MAP = {
    "tipo": "tipo",
    "ingredientes": "nome",
    "ingrediente": "nome",
    "nome": "nome",
    "classificacao": "classificacao",
    "formula": "formula_quimica",
    "formulaquimica": "formula_quimica",
    "fonte": "fonte",
    "r": "preco_padrao",
    "preco": "preco_padrao",
    "precopadrao": "preco_padrao",
    "rkg": "preco_padrao",
}


def _column_letter(number: int) -> str:
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result or "A"
