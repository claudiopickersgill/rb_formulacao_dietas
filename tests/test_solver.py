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


def test_solver_treats_blank_mineral_nutrients_as_zero() -> None:
    items = pd.DataFrame(
        [
            {
                "ingredient_id": "food",
                "nome": "Milho",
                "tipo": "Alimento",
                "preco_kg": 1.0,
                "inclusao_min": 0,
                "inclusao_max": 100,
                "PB": 10.0,
            },
            {
                "ingredient_id": "min",
                "nome": "Calcário",
                "tipo": "Mineral",
                "preco_kg": 2.0,
                "inclusao_min": 0,
                "inclusao_max": 5,
                "PB": "",
            },
        ]
    )
    constraints = pd.DataFrame([{"nutriente": "PB", "minimo": 9.5, "maximo": 10.0}])
    result = solve_least_cost(items, constraints)
    assert result.success
    assert result.items["inclusao_calculada"].sum() == pytest.approx(100.0)


def test_solver_rejects_blank_food_nutrient_without_crashing() -> None:
    items = pd.DataFrame(
        [
            {
                "ingredient_id": "food",
                "nome": "Alimento incompleto",
                "tipo": "Alimento",
                "preco_kg": 1.0,
                "inclusao_min": 0,
                "inclusao_max": 100,
                "PB": "",
            }
        ]
    )
    constraints = pd.DataFrame([{"nutriente": "PB", "minimo": 10.0, "maximo": 20.0}])
    result = solve_least_cost(items, constraints)
    assert not result.success
    assert result.status == "dados_invalidos"
    assert any("ausente, vazio ou não numérico" in message for message in result.diagnostics)


def test_solver_diagnoses_conflicting_fdn_fda_constraints() -> None:
    items = pd.DataFrame(
        [
            {"ingredient_id": "soja", "nome": "Farelo de soja", "tipo": "Alimento", "preco_kg": 2.5, "inclusao_min": 0, "inclusao_max": 100, "NDT": 85, "PB": 45, "FDN": 11.9, "FDA": 7.2, "CA": 0.30, "P": 0.70},
            {"ingredient_id": "milho", "nome": "Milho", "tipo": "Alimento", "preco_kg": 1.7, "inclusao_min": 0, "inclusao_max": 100, "NDT": 80, "PB": 8, "FDN": 9.8, "FDA": 3.6, "CA": 0.04, "P": 0.31},
            {"ingredient_id": "arroz_i", "nome": "Farelo de arroz integral", "tipo": "Alimento", "preco_kg": 0.9, "inclusao_min": 0, "inclusao_max": 15, "NDT": 75, "PB": 14.8, "FDN": 23.1, "FDA": 13.8, "CA": 0.78, "P": 0.12},
            {"ingredient_id": "arroz_d", "nome": "Farelo de arroz desengordurado", "tipo": "Alimento", "preco_kg": 1.2, "inclusao_min": 0, "inclusao_max": 15, "NDT": 70, "PB": 18.5, "FDN": 25.9, "FDA": 12.7, "CA": 0.83, "P": 2.48},
            {"ingredient_id": "casq", "nome": "Casquinha de soja", "tipo": "Alimento", "preco_kg": 0.0, "inclusao_min": 0, "inclusao_max": 100, "NDT": 48.76, "PB": 11.9, "FDN": 66.7, "FDA": 47.9, "CA": 0.64, "P": 0.13},
            {"ingredient_id": "calc", "nome": "Calcário calcítico", "tipo": "Mineral", "preco_kg": 2.5, "inclusao_min": 0, "inclusao_max": 1, "NDT": "", "PB": "", "FDN": "", "FDA": "", "CA": 38.5, "P": ""},
            {"ingredient_id": "fosf", "nome": "Fosfato de cálcio (dibásico)", "tipo": "Mineral", "preco_kg": 0.6, "inclusao_min": 0, "inclusao_max": 1, "NDT": "", "PB": "", "FDN": "", "FDA": "", "CA": 22.0, "P": 19.3},
        ]
    )
    constraints = pd.DataFrame(
        [
            {"nutriente": "NDT", "minimo": 70, "maximo": 80},
            {"nutriente": "PB", "minimo": 18, "maximo": 20},
            {"nutriente": "FDN", "minimo": 10, "maximo": 20},
            {"nutriente": "FDA", "minimo": 15, "maximo": 20},
            {"nutriente": "CA", "minimo": 0, "maximo": 1},
            {"nutriente": "P", "minimo": 0, "maximo": 0.7},
        ]
    )
    result = solve_least_cost(items, constraints)
    assert not result.success
    assert result.status == "inviavel"
    assert any(message.startswith("FDN:") for message in result.diagnostics)
    assert any(message.startswith("FDA:") for message in result.diagnostics)
