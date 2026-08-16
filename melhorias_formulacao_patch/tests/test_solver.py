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
            {"ingredient_id": "casq", "nome": "Casquinha de soja", "tipo": "Alimento", "preco_kg": 0.0, "sem_custo": True, "inclusao_min": 0, "inclusao_max": 100, "NDT": 48.76, "PB": 11.9, "FDN": 66.7, "FDA": 47.9, "CA": 0.64, "P": 0.13},
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


def test_solver_rejects_zero_price_without_free_flag() -> None:
    items = pd.DataFrame(
        [
            {
                "ingredient_id": "a",
                "nome": "Ingrediente sem preço",
                "tipo": "Alimento",
                "preco_kg": 0.0,
                "sem_custo": False,
                "inclusao_min": 0,
                "inclusao_max": 100,
                "PB": 10.0,
            }
        ]
    )
    constraints = pd.DataFrame([{"nutriente": "PB", "minimo": 8.0, "maximo": 12.0}])
    result = solve_least_cost(items, constraints)
    assert not result.success
    assert result.status == "dados_invalidos"
    assert any("marque 'Sem custo'" in message for message in result.diagnostics)


def test_solver_accepts_explicit_free_ingredient() -> None:
    items = pd.DataFrame(
        [
            {
                "ingredient_id": "free",
                "nome": "Ingrediente gratuito",
                "tipo": "Alimento",
                "preco_kg": 0.0,
                "sem_custo": True,
                "inclusao_min": 0,
                "inclusao_max": 100,
                "PB": 10.0,
            },
            {
                "ingredient_id": "paid",
                "nome": "Ingrediente pago",
                "tipo": "Alimento",
                "preco_kg": 2.0,
                "sem_custo": False,
                "inclusao_min": 0,
                "inclusao_max": 100,
                "PB": 20.0,
            },
        ]
    )
    constraints = pd.DataFrame([{"nutriente": "PB", "minimo": 10.0, "maximo": 20.0}])
    result = solve_least_cost(items, constraints)
    assert result.success
    assert result.cost_per_kg == pytest.approx(0.0)
    free_row = result.items.set_index("ingredient_id").loc["free"]
    assert free_row["inclusao_calculada"] == pytest.approx(100.0)
    assert free_row["preco_kg"] == pytest.approx(0.0)


def test_solver_ignores_entered_price_when_marked_free() -> None:
    items = pd.DataFrame(
        [
            {
                "ingredient_id": "free",
                "nome": "Ingrediente gratuito",
                "tipo": "Alimento",
                "preco_kg": 9.99,
                "sem_custo": True,
                "inclusao_min": 0,
                "inclusao_max": 100,
                "PB": 10.0,
            }
        ]
    )
    constraints = pd.DataFrame([{"nutriente": "PB", "minimo": 10.0, "maximo": 10.0}])
    result = solve_least_cost(items, constraints)
    assert result.success
    assert result.cost_per_kg == pytest.approx(0.0)
    assert any("desconsiderado" in message for message in result.diagnostics)


def test_solver_matches_excel_reference_diet() -> None:
    items = pd.DataFrame(
        [
            {"ingredient_id": "milho", "nome": "Milho", "tipo": "Alimento", "preco_kg": 1.70, "sem_custo": False, "inclusao_min": 0, "inclusao_max": 100, "MS": 86.90, "NDT": 80.0, "PB": 8.0, "FDN": 9.8, "FDA": 3.6, "AMIDO": 70.4, "CA": 0.04, "P": 0.31},
            {"ingredient_id": "soja", "nome": "Farelo de soja", "tipo": "Alimento", "preco_kg": 2.50, "sem_custo": False, "inclusao_min": 0, "inclusao_max": 100, "MS": 90.0, "NDT": 85.0, "PB": 45.0, "FDN": 11.9, "FDA": 7.2, "AMIDO": 1.9, "CA": 0.30, "P": 0.70},
            {"ingredient_id": "arroz_i", "nome": "Farelo de arroz integral", "tipo": "Alimento", "preco_kg": 0.90, "sem_custo": False, "inclusao_min": 0, "inclusao_max": 15, "MS": 80.67, "NDT": 75.0, "PB": 14.8, "FDN": 23.1, "FDA": 13.8, "AMIDO": 22.2, "CA": 0.78, "P": 0.12},
            {"ingredient_id": "arroz_d", "nome": "Farelo de arroz desengordurado", "tipo": "Alimento", "preco_kg": 1.20, "sem_custo": False, "inclusao_min": 0, "inclusao_max": 15, "MS": 83.61, "NDT": 70.0, "PB": 18.5, "FDN": 25.9, "FDA": 12.7, "AMIDO": 21.5, "CA": 0.83, "P": 2.48},
            {"ingredient_id": "casq", "nome": "Casquinha de soja", "tipo": "Alimento", "preco_kg": 0.0, "sem_custo": True, "inclusao_min": 0, "inclusao_max": 100, "MS": 90.40, "NDT": 48.76, "PB": 11.9, "FDN": 66.7, "FDA": 47.9, "AMIDO": 1.0, "CA": 0.64, "P": 0.13},
            {"ingredient_id": "fosf", "nome": "Fosfato de cálcio (dibásico)", "tipo": "Mineral", "preco_kg": 2.50, "sem_custo": False, "inclusao_min": 0, "inclusao_max": 1, "MS": 100.0, "NDT": 0.0, "PB": 0.0, "FDN": 0.0, "FDA": 0.0, "AMIDO": 0.0, "CA": 22.0, "P": 19.3},
            {"ingredient_id": "calc", "nome": "Calcário calcítico", "tipo": "Mineral", "preco_kg": 0.60, "sem_custo": False, "inclusao_min": 0, "inclusao_max": 1, "MS": 100.0, "NDT": 0.0, "PB": 0.0, "FDN": 0.0, "FDA": 0.0, "AMIDO": 0.0, "CA": 38.5, "P": 0.0},
        ]
    )
    constraints = pd.DataFrame(
        [
            {"nutriente": "MS", "minimo": 89, "maximo": 99},
            {"nutriente": "NDT", "minimo": 70, "maximo": 80},
            {"nutriente": "PB", "minimo": 18, "maximo": 25},
            {"nutriente": "FDN", "minimo": 10, "maximo": 25},
            {"nutriente": "FDA", "minimo": 10, "maximo": 20},
            {"nutriente": "AMIDO", "minimo": 20, "maximo": 100},
            {"nutriente": "CA", "minimo": 0.5, "maximo": 1},
            {"nutriente": "P", "minimo": 0.3, "maximo": 0.7},
        ]
    )
    result = solve_least_cost(items, constraints)
    assert result.success
    assert result.cost_per_kg == pytest.approx(1.4958, abs=5e-5)
    mix = result.items.set_index("ingredient_id")["inclusao_calculada"]
    assert mix["milho"] == pytest.approx(42.0582, abs=5e-4)
    assert mix["soja"] == pytest.approx(29.9907, abs=5e-4)
    assert mix["casq"] == pytest.approx(25.9511, abs=5e-4)
    assert mix["fosf"] == pytest.approx(1.0, abs=1e-6)
    assert mix["calc"] == pytest.approx(1.0, abs=1e-6)
