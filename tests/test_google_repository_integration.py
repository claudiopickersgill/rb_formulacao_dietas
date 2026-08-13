from __future__ import annotations

import sys
import types

from src.repositories import google_sheets as module


class FakeWorksheetNotFound(Exception):
    pass


class FakeAPIError(Exception):
    def __init__(self, status_code: int = 500):
        self.response = types.SimpleNamespace(status_code=status_code)


class FakeWorksheet:
    def __init__(self, title: str, values: list[list[str]] | None = None):
        self.title = title
        self._values = [row[:] for row in (values or [])]

    def get_all_values(self):
        return [row[:] for row in self._values]

    def update(self, values=None, range_name=None, *args, **kwargs):
        if values is None and args:
            values = args[0]
        self._values = [list(row) for row in (values or [])]

    def format(self, *args, **kwargs):
        return None

    def resize(self, rows=None, cols=None):
        return None

    def clear(self):
        self._values = []


class FakeSpreadsheet:
    def __init__(self, worksheets: list[FakeWorksheet]):
        self._worksheets = {worksheet.title: worksheet for worksheet in worksheets}

    def worksheet(self, title: str):
        try:
            return self._worksheets[title]
        except KeyError as exc:
            raise FakeWorksheetNotFound(title) from exc

    def add_worksheet(self, title: str, rows: int, cols: int):
        worksheet = FakeWorksheet(title)
        self._worksheets[title] = worksheet
        return worksheet

    def worksheets(self):
        return list(self._worksheets.values())


def test_google_repository_creates_prefixed_tabs_and_migrates(monkeypatch):
    fake_gspread = types.SimpleNamespace(
        WorksheetNotFound=FakeWorksheetNotFound,
        exceptions=types.SimpleNamespace(APIError=FakeAPIError),
    )
    monkeypatch.setitem(sys.modules, "gspread", fake_gspread)

    legacy = FakeWorksheet(
        "TabelaIngredientes",
        [
            ["Tipo", "Ingredientes", "Classificação", "R$", "MS", "NDT", "PB"],
            ["Alimento", "Milho", "Energético", "1,50", "88", "80", "9"],
        ],
    )
    spreadsheet = FakeSpreadsheet([legacy])
    monkeypatch.setattr(module, "open_spreadsheet", lambda *args, **kwargs: spreadsheet)

    repository = module.GoogleSheetsRepository(
        credentials={"type": "service_account"},
        spreadsheet_url="https://example.invalid/sheet",
        table_prefix="rb_",
        cache_ttl_seconds=0,
    )
    repository.initialize()

    assert "rb_ingredientes" in spreadsheet._worksheets
    assert "rb_dietas" in spreadsheet._worksheets
    assert legacy.get_all_values()[1][1] == "Milho"  # aba original preservada

    ingredients = repository.list_ingredients(active_only=False)
    assert len(ingredients) == 1
    assert ingredients.loc[0, "nome"] == "Milho"
    assert float(ingredients.loc[0, "preco_padrao"]) == 1.5
    assert repository.legacy_migration_summary["executed"] is True

    repository.upsert_ingredient(
        {"tipo": "Alimento", "nome": "Sorgo", "NDT": 77, "ativo": True},
        actor="admin@example.com",
    )
    names = set(repository.list_ingredients(active_only=False)["nome"].astype(str))
    assert names == {"Milho", "Sorgo"}
