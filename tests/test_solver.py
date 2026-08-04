from __future__ import annotations

import pandas as pd
import pytest

from src.solver import solve_least_cost


def test_solver_finds_least_cost_mix() -> None:
    items = pd.DataFrame(
        [
            {"ingredient_id": "a", "nome": "A", "preco_kg": 1.0, "inclusao_min": 0, "inclusao_max": 100, "PB": 8.0},
            {"ingredient_id": "b", "nome": "B", "preco_kg": 2.0, "inclusao_min": 0, "inclusao_max": 100, "PB": 20.0},
        ]
    )
    constraints = pd.DataFrame([{"nutriente": "PB", "minimo": 12.0, "maximo": 15.0}])
    result = solve_least_cost(items, constraints)
    assert result.success
    assert result.cost_per_kg == pytest.approx(4 / 3, rel=1e-6)
    inclusion_b = result.items.set_index("ingredient_id").loc["b", "inclusao_calculada"]
    assert inclusion_b == pytest.approx(100 / 3, rel=1e-6)
    assert result.items["inclusao_calculada"].sum() == pytest.approx(100.0)


def test_solver_reports_infeasible_constraint() -> None:
    items = pd.DataFrame(
        [
            {"ingredient_id": "a", "nome": "A", "preco_kg": 1.0, "inclusao_min": 0, "inclusao_max": 100, "PB": 8.0},
            {"ingredient_id": "b", "nome": "B", "preco_kg": 2.0, "inclusao_min": 0, "inclusao_max": 100, "PB": 20.0},
        ]
    )
    constraints = pd.DataFrame([{"nutriente": "PB", "minimo": 25.0, "maximo": None}])
    result = solve_least_cost(items, constraints)
    assert not result.success
    assert result.status == "inviavel"
    assert any("máximo" in message for message in result.diagnostics)


def test_solver_rejects_missing_nutrient_data() -> None:
    items = pd.DataFrame(
        [
            {"ingredient_id": "a", "nome": "A", "preco_kg": 1.0, "inclusao_min": 0, "inclusao_max": 100, "PB": None},
        ]
    )
    constraints = pd.DataFrame([{"nutriente": "PB", "minimo": 10.0, "maximo": None}])
    result = solve_least_cost(items, constraints)
    assert not result.success
    assert result.status == "dados_invalidos"
    assert any("ausente" in message for message in result.diagnostics)
