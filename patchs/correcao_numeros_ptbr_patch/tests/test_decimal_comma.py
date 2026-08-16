from __future__ import annotations

import pandas as pd

from src.solver import solve_least_cost
from src.validators import validate_formulation


def _items_ptbr() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ingredient_id": "a",
                "nome": "Ingrediente A",
                "tipo": "Alimento",
                "preco_kg": "1,50",
                "inclusao_min": "0,0",
                "inclusao_max": "100,0",
                "NDT": "70,5",
                "PB": "10,0",
            },
            {
                "ingredient_id": "b",
                "nome": "Ingrediente B",
                "tipo": "Alimento",
                "preco_kg": "2,00",
                "inclusao_min": "0,0",
                "inclusao_max": "100,0",
                "NDT": "80,5",
                "PB": "20,0",
            },
        ]
    )


def _constraints_ptbr() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"nutriente": "NDT", "minimo": "75,5", "maximo": "80,5"},
            {"nutriente": "PB", "minimo": "15,0", "maximo": "20,0"},
        ]
    )


def test_validation_accepts_brazilian_decimal_comma() -> None:
    validation = validate_formulation(_items_ptbr(), _constraints_ptbr())
    assert validation.valid, validation.errors


def test_solver_accepts_brazilian_decimal_comma() -> None:
    result = solve_least_cost(_items_ptbr(), _constraints_ptbr())
    assert result.success, result.diagnostics
    assert abs(result.items["inclusao_calculada"].sum() - 100.0) < 1e-7
    assert result.constraints["situacao"].eq("Atendida").all()


def test_values_matching_real_google_sheet_pattern_are_numeric() -> None:
    # Regressão para o padrão que aparecia como ausente no app: vírgula decimal.
    items = pd.DataFrame(
        [
            {
                "ingredient_id": "casquinha",
                "nome": "Casquinha de soja",
                "tipo": "Alimento",
                "preco_kg": "0,90",
                "inclusao_min": "0",
                "inclusao_max": "100",
                "NDT": "48,76",
                "PB": "11,9",
                "FDN": "66,7",
                "FDA": "47,9",
                "CA": "0,64",
                "P": "0,13",
            }
        ]
    )
    constraints = pd.DataFrame(
        [
            {"nutriente": "NDT", "minimo": "0", "maximo": "100"},
            {"nutriente": "PB", "minimo": "0", "maximo": "100"},
            {"nutriente": "FDN", "minimo": "0", "maximo": "100"},
            {"nutriente": "FDA", "minimo": "0", "maximo": "100"},
            {"nutriente": "CA", "minimo": "0", "maximo": "100"},
            {"nutriente": "P", "minimo": "0", "maximo": "100"},
        ]
    )
    validation = validate_formulation(items, constraints)
    assert validation.valid, validation.errors
