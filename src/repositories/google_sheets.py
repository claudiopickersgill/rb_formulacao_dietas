from __future__ import annotations

import re
import time
import threading
import warnings
import json
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Callable, TypeVar

import pandas as pd

from ..config import INGREDIENT_COLUMNS, NUTRIENT_CODES, TABLE_SCHEMAS
from ..google_connection import open_spreadsheet
from ..utils import as_bool, as_float, dataframe_for_storage, local_now_iso, new_id
from .tabular import TabularRepository

T = TypeVar("T")


class GoogleSheetsRepository(TabularRepository):
    """Repositório tabular que reutiliza a conexão Google do projeto original.

    As abas do aplicativo recebem um prefixo (por padrão ``rb_``), portanto a
    primeira aba já existente não é apagada nem reformatada. Quando habilitada,
    a migração legada copia os ingredientes dessa primeira aba para
    ``rb_ingredientes`` apenas se a tabela nova estiver vazia.
    """

    _ingredient_lock = threading.RLock()

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
        self.ingredient_backfill_summary: dict[str, Any] = {}

    def initialize(self) -> None:
        super().initialize()
        if self.auto_migrate_legacy:
            self._migrate_legacy_ingredients_if_needed()
        # Valores vazios podem ser desconhecidos por decisão do formulador.
        # Complementação deve ser explícita, nunca executada ao iniciar o app.
        self.ingredient_backfill_summary = {
            "executed": False, "reason": "Complementação automática desabilitada."
        }

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

        # Acrescenta colunas ao final sem limpar ou reordenar dados existentes.
        missing = [column for column in columns if column not in header]
        if missing:
            expanded = header + missing
            if worksheet.col_count < len(expanded):
                self._call(lambda: worksheet.add_cols(len(expanded) - worksheet.col_count))
            self._call(lambda: worksheet.update(values=[expanded], range_name="A1", value_input_option="RAW"))
            self._cache.pop(name, None)

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
            frame = pd.DataFrame([row + [""] * (len(header) - len(row)) for row in rows], columns=header)
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

    def _fresh_ingredients(self):
        self._cache.pop("ingredientes", None)
        return self._normalized("ingredientes").astype(object)

    def upsert_ingredient(self, payload: dict[str, Any], actor: str) -> dict[str, Any]:
        # Serializa operações no mesmo processo; append do Sheets não apaga outras linhas.
        with self._ingredient_lock:
            current = self._fresh_ingredients()
            ingredient_id = str(payload.get("ingredient_id") or new_id("ing"))
            matches = current[current["ingredient_id"].astype(str).eq(ingredient_id)]
            if len(matches) > 1:
                raise ValueError("ID de ingrediente duplicado; revise a base antes de salvar.")
            old = matches.iloc[0].to_dict() if len(matches) else {}
            data = {col: payload.get(col, old.get(col, "")) for col in INGREDIENT_COLUMNS}
            data.update(ingredient_id=ingredient_id, ativo=as_bool(data.get("ativo"), True),
                        created_by=old.get("created_by") or payload.get("created_by") or actor,
                        created_at=old.get("created_at") or payload.get("created_at") or local_now_iso(),
                        updated_at=local_now_iso())
            if data["ativo"]:
                self._check_active_duplicate(current, data)
            worksheet = self._worksheet("ingredientes")
            raw = self._call(worksheet.get_all_values)
            header = raw[0]
            if any(c not in header for c in INGREDIENT_COLUMNS):
                raise RuntimeError("Schema desatualizado. Reinicie o aplicativo antes de importar.")
            positions = [i for i, row in enumerate(raw[1:], 2) if row and str(row[0]) == ingredient_id]
            if len(positions) > 1:
                raise ValueError("ID duplicado na planilha.")
            old_raw = dict(zip(header, raw[positions[0]-1])) if positions else {}
            complete = {col: data[col] if col in data else old_raw.get(col, "") for col in header}
            stored = dataframe_for_storage(pd.DataFrame([complete], columns=header)).values.tolist()[0]
            if positions:
                row_number = positions[0]
                self._call(lambda: worksheet.update(values=[stored], range_name=f"A{row_number}:{_column_letter(len(header))}{row_number}", value_input_option="RAW"))
            else:
                # Não repete append cegamente após erro de rede: confirma pelo ID.
                try:
                    worksheet.append_row(stored, value_input_option="RAW", table_range="A1")
                except Exception:
                    check = self._call(worksheet.get_all_values)
                    if not any(row and str(row[0]) == ingredient_id for row in check[1:]):
                        raise
            verified = self._fresh_ingredients()
            found = verified[verified["ingredient_id"].astype(str).eq(ingredient_id)]
            if len(found) != 1:
                raise RuntimeError("Gravação sem confirmação única no Google Sheets.")
            expected = dataframe_for_storage(pd.DataFrame([data], columns=INGREDIENT_COLUMNS)).iloc[0]
            actual = dataframe_for_storage(found[INGREDIENT_COLUMNS]).iloc[0]
            if expected.astype(str).tolist() != actual.astype(str).tolist():
                # Sheets formata números conforme locale. Compara números por valor.
                for col in INGREDIENT_COLUMNS:
                    if col == "ativo" and as_bool(expected[col]) == as_bool(actual[col]):
                        continue
                    if str(expected[col]) == str(actual[col]):
                        continue
                    left, right = as_float(expected[col]), as_float(actual[col])
                    if left is None or right is None or abs(left - right) > 1e-10:
                        raise RuntimeError("Valor divergente após gravação: " + col)
            try:
                self.audit(actor, "atualizar" if old else "criar", "ingrediente", ingredient_id, data.get("nome", ""))
            except Exception as exc:
                warnings.warn("Ingrediente gravado, mas a auditoria falhou: " + str(exc), RuntimeWarning)
            return data

    def set_ingredient_active(self, ingredient_id: str, active: bool, actor: str) -> None:
        current = self._fresh_ingredients()
        matches = current[current["ingredient_id"].astype(str).eq(str(ingredient_id))]
        if len(matches) != 1:
            raise KeyError("Ingrediente não encontrado ou ID duplicado.")
        payload = matches.iloc[0].to_dict()
        payload["ativo"] = bool(active)
        self.upsert_ingredient(payload, actor)

    def audit(self, actor: str, action: str, entity: str, entity_id: str, details: Any) -> None:
        self._cache.pop("auditoria", None)
        worksheet = self._worksheet("auditoria")
        from ..config import AUDIT_COLUMNS
        record = dict(audit_id=new_id("aud"), timestamp=local_now_iso(), usuario=actor,
                      acao=action, entidade=entity, entity_id=entity_id,
                      detalhes=details if isinstance(details, str) else json.dumps(details, ensure_ascii=False))
        worksheet.append_row([record[c] for c in AUDIT_COLUMNS], value_input_option="RAW", table_range="A1")
        self._cache.pop("auditoria", None)

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

    def _backfill_missing_ingredient_nutrients(self) -> None:
        """Preenche somente nutrientes ausentes em ``rb_ingredientes``.

        A rotina existe para reparar tabelas já migradas por versões antigas do
        WebApp que podiam ter mantido parte da composição em branco. O
        procedimento é deliberadamente conservador: casa registros por
        ``tipo + nome`` normalizados e só escreve em células vazias. Valores
        numéricos existentes, inclusive 0, são preservados.
        """

        current = self._read_table("ingredientes")
        if current.empty:
            self.ingredient_backfill_summary = {
                "executed": False,
                "reason": "A tabela de ingredientes está vazia.",
                "cells_filled": 0,
                "rows_changed": 0,
            }
            return

        references: list[tuple[str, pd.DataFrame]] = []

        # 1) Prioriza a aba legada da própria planilha Google.
        try:
            legacy = self._legacy_worksheet()
            if legacy is not None:
                legacy_values = self._call(legacy.get_all_values)
                legacy_frame = _convert_legacy_ingredient_values(legacy_values)
                if not legacy_frame.empty:
                    references.append((f"Google:{legacy.title}", legacy_frame))
        except Exception:
            # O reparo é auxiliar e não deve impedir o aplicativo de iniciar.
            pass

        # 2) Fallback para a base original v1.2 que acompanha o projeto.
        seed_path = Path(__file__).resolve().parents[2] / "data" / "seed_ingredientes.csv"
        if seed_path.exists():
            try:
                seed = pd.read_csv(seed_path)
                if not seed.empty and {"tipo", "nome"}.issubset(seed.columns):
                    references.append(("seed_ingredientes.csv", seed))
            except Exception:
                pass

        if not references:
            self.ingredient_backfill_summary = {
                "executed": False,
                "reason": "Nenhuma base de referência foi encontrada.",
                "cells_filled": 0,
                "rows_changed": 0,
            }
            return

        repaired = current.copy().astype(object)
        cells_filled = 0
        rows_changed: set[int] = set()
        source_hits: Counter[str] = Counter()

        # Índices por tipo+nome. A ordem da lista de referências define
        # prioridade: Google legado primeiro; seed local depois.
        reference_maps: list[tuple[str, dict[tuple[str, str], dict[str, Any]]]] = []
        for source_name, frame in references:
            mapping: dict[tuple[str, str], dict[str, Any]] = {}
            for _, ref_row in frame.iterrows():
                key = (_clean_text(ref_row.get("tipo")), _clean_text(ref_row.get("nome")))
                if key == ("", "") or not all(key):
                    continue
                # Em duplicidades da base original, a primeira ocorrência é
                # suficiente porque os nutrientes duplicados são equivalentes.
                mapping.setdefault(key, ref_row.to_dict())
            reference_maps.append((source_name, mapping))

        for idx, row in repaired.iterrows():
            key = (_clean_text(row.get("tipo")), _clean_text(row.get("nome")))
            if not all(key):
                continue

            for code in NUTRIENT_CODES:
                if code not in repaired.columns or not _is_blank_cell(row.get(code)):
                    continue

                replacement = None
                replacement_source = ""
                for source_name, mapping in reference_maps:
                    ref = mapping.get(key)
                    if not ref:
                        continue
                    candidate = as_float(ref.get(code))
                    if candidate is not None:
                        replacement = candidate
                        replacement_source = source_name
                        break

                if replacement is None:
                    continue

                repaired.at[idx, code] = replacement
                row[code] = replacement
                cells_filled += 1
                rows_changed.add(int(idx))
                source_hits[replacement_source] += 1

        if not cells_filled:
            self.ingredient_backfill_summary = {
                "executed": False,
                "reason": "Nenhuma célula nutricional vazia pôde ser complementada.",
                "cells_filled": 0,
                "rows_changed": 0,
            }
            return

        now = local_now_iso()
        for idx in rows_changed:
            if "updated_at" in repaired.columns:
                repaired.at[idx, "updated_at"] = now
            if "observacoes" in repaired.columns:
                note = str(repaired.at[idx, "observacoes"] or "").strip()
                repair_note = "Composição nutricional complementada automaticamente a partir da base original."
                if repair_note not in note:
                    repaired.at[idx, "observacoes"] = (note + "; " + repair_note).strip("; ")

        self._write_table("ingredientes", repaired[INGREDIENT_COLUMNS])
        self.ingredient_backfill_summary = {
            "executed": True,
            "cells_filled": cells_filled,
            "rows_changed": len(rows_changed),
            "sources": dict(source_hits),
        }
        self.audit(
            "sistema",
            "reparar_composicao",
            "ingredientes",
            "backfill_nutrientes",
            f"{cells_filled} célula(s) preenchida(s) em {len(rows_changed)} ingrediente(s).",
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
    frame = frame.reindex(columns=list(dict.fromkeys([*frame.columns, *NUTRIENT_CODES])))

    for column in ["preco_padrao", *NUTRIENT_CODES]:
        frame[column] = frame[column].map(lambda value: as_float(value))
    frame = frame.copy()

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


def _is_blank_cell(value: Any) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return isinstance(value, str) and not value.strip()


def _column_letter(number: int) -> str:
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result or "A"
