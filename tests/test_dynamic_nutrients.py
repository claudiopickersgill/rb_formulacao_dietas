from __future__ import annotations

import pandas as pd
import pytest

from src.nutrients import available_nutrient_codes, synchronize_constraints
from src.result_analysis import nutrient_result_display
from src.solver import solve_least_cost


def test_available_nutrients_include_selenium_when_declared() -> None:
    items = pd.DataFrame(
        [
            {"nome": "Milho", "MS": 86.9, "PB": 8.0, "Se": ""},
            {"nome": "Selenito", "MS": 100.0, "PB": 0.0, "Se": "450,0"},
        ]
    )
    codes = available_nutrient_codes(items)
    assert "MS" in codes
    assert "PB" in codes
    assert "Se" in codes
    assert "NDT" not in codes


def test_synchronize_constraints_adds_available_nutrients_and_preserves_values() -> None:
    items = pd.DataFrame(
        [
            {"MS": 90.0, "PB": 18.0, "Se": 0.2},
            {"MS": 88.0, "PB": 12.0, "Se": 0.1},
        ]
    )
    current = pd.DataFrame(
        [
            {"nutriente": "PB", "minimo": 14.0, "maximo": 20.0},
        ]
    )
    synced = synchronize_constraints(current, items).set_index("nutriente")
    assert set(synced.index) == {"MS", "PB", "Se"}
    assert synced.loc["PB", "minimo"] == pytest.approx(14.0)
    assert synced.loc["PB", "maximo"] == pytest.approx(20.0)
    assert pd.isna(synced.loc["Se", "minimo"])
    assert pd.isna(synced.loc["Se", "maximo"])


def test_solver_calculates_unrestricted_nutrient() -> None:
    items = pd.DataFrame(
        [
            {
                "ingredient_id": "a",
                "nome": "A",
                "tipo": "Alimento",
                "preco_kg": 1.0,
                "inclusao_min": 0,
                "inclusao_max": 100,
                "PB": 10.0,
                "Se": 0.10,
            },
            {
                "ingredient_id": "b",
                "nome": "B",
                "tipo": "Alimento",
                "preco_kg": 2.0,
                "inclusao_min": 0,
                "inclusao_max": 100,
                "PB": 20.0,
                "Se": 0.30,
            },
        ]
    )
    constraints = pd.DataFrame(
        [
            {"nutriente": "PB", "minimo": 15.0, "maximo": 20.0},
            {"nutriente": "Se", "minimo": None, "maximo": None},
        ]
    )
    result = solve_least_cost(items, constraints)
    assert result.success
    nutrient = result.constraints.set_index("nutriente")
    assert nutrient.loc["PB", "situacao"] == "Atendida"
    assert nutrient.loc["Se", "situacao"] == "Sem restrição"
    assert nutrient.loc["Se", "resultado"] == pytest.approx(0.20)


def test_unrestricted_incomplete_nutrient_does_not_block_solver() -> None:
    items = pd.DataFrame(
        [
            {
                "ingredient_id": "a",
                "nome": "A",
                "tipo": "Alimento",
                "preco_kg": 1.0,
                "inclusao_min": 0,
                "inclusao_max": 100,
                "PB": 10.0,
                "Se": "",
            },
            {
                "ingredient_id": "b",
                "nome": "B",
                "tipo": "Alimento",
                "preco_kg": 2.0,
                "inclusao_min": 0,
                "inclusao_max": 100,
                "PB": 20.0,
                "Se": 0.30,
            },
        ]
    )
    constraints = pd.DataFrame(
        [
            {"nutriente": "PB", "minimo": 10.0, "maximo": 20.0},
            {"nutriente": "Se", "minimo": None, "maximo": None},
        ]
    )
    result = solve_least_cost(items, constraints)
    assert result.success
    nutrient = result.constraints.set_index("nutriente")
    assert nutrient.loc["Se", "situacao"] == "Dados incompletos"
    assert pd.isna(nutrient.loc["Se", "resultado"])


def test_result_display_marks_unrestricted_nutrient() -> None:
    constraints = pd.DataFrame(
        [
            {
                "nutriente": "Se",
                "descricao": "Selênio",
                "unidade": "mg/kg",
                "minimo": None,
                "maximo": None,
                "resultado": 0.2,
                "situacao": "Sem restrição",
            }
        ]
    )
    display = nutrient_result_display(constraints)
    assert display.loc[0, "situacao_visual"] == "⚪ Sem restrição"
