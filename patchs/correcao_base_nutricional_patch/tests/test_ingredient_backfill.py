from __future__ import annotations

import sys
import types

from src.config import INGREDIENT_COLUMNS
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


def _row(**values):
    record = {column: "" for column in INGREDIENT_COLUMNS}
    record.update(values)
    return [record[column] for column in INGREDIENT_COLUMNS]


def test_existing_google_ingredient_blanks_are_backfilled_without_overwriting(monkeypatch):
    fake_gspread = types.SimpleNamespace(
        WorksheetNotFound=FakeWorksheetNotFound,
        exceptions=types.SimpleNamespace(APIError=FakeAPIError),
    )
    monkeypatch.setitem(sys.modules, "gspread", fake_gspread)

    legacy = FakeWorksheet(
        "TabelaIngredientes",
        [
            ["Tipo", "Ingredientes", "Classificação", "MS", "NDT", "PB", "FDN", "FDA", "CA", "P"],
            ["Alimento", "Milho", "Energético", "86,9", "80", "8", "9,8", "3,6", "0,04", "0,31"],
        ],
    )
    existing = FakeWorksheet(
        "rb_ingredientes",
        [
            INGREDIENT_COLUMNS,
            _row(
                ingredient_id="ing_1",
                tipo="Alimento",
                nome="Milho",
                classificacao="Energético",
                NDT="79",  # valor existente deve ser preservado
                PB="8",
                FDN="",
                FDA="",
                CA="0",  # zero explícito também deve ser preservado
                P="",
                ativo="True",
            ),
        ],
    )
    spreadsheet = FakeSpreadsheet([legacy, existing])
    monkeypatch.setattr(module, "open_spreadsheet", lambda *args, **kwargs: spreadsheet)

    repository = module.GoogleSheetsRepository(
        credentials={"type": "service_account"},
        spreadsheet_url="https://example.invalid/sheet",
        table_prefix="rb_",
        cache_ttl_seconds=0,
    )
    repository.initialize()

    ingredients = repository.list_ingredients(active_only=False)
    milho = ingredients.loc[ingredients["nome"].eq("Milho")].iloc[0]
    assert float(milho["NDT"]) == 79.0
    assert float(milho["FDN"]) == 9.8
    assert float(milho["FDA"]) == 3.6
    assert float(milho["CA"]) == 0.0
    assert float(milho["P"]) == 0.31
    assert repository.ingredient_backfill_summary["executed"] is True
    assert repository.ingredient_backfill_summary["cells_filled"] >= 3
