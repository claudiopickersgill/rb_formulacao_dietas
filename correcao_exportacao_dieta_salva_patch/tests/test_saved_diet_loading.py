import pandas as pd

from src.diet_loading import (
    calculation_fingerprint,
    normalize_loaded_constraints,
    normalize_loaded_items,
)


def test_saved_diet_numeric_fields_are_restored_from_google_text():
    items = pd.DataFrame(
        [
            {
                "ingredient_id": "ing_1",
                "nome": "Milho",
                "sem_custo": "FALSE",
                "preco_kg": "1,70",
                "inclusao_min": "0",
                "inclusao_max": "100",
                "inclusao_calculada": "42,0582",
                "custo_parcial": "0,7150",
                "MS": "86,90",
                "NDT": "80,00",
            },
            {
                "ingredient_id": "ing_2",
                "nome": "Casquinha",
                "sem_custo": "TRUE",
                "preco_kg": "0",
                "inclusao_min": "0",
                "inclusao_max": "100",
                "inclusao_calculada": "25,9511",
                "custo_parcial": "0",
                "MS": "90,40",
                "NDT": "48,76",
            },
        ]
    )
    normalized = normalize_loaded_items(items)

    assert normalized["inclusao_calculada"].sum() == 68.0093
    assert normalized.loc[0, "preco_kg"] == 1.70
    assert normalized.loc[1, "NDT"] == 48.76
    assert normalized["sem_custo"].tolist() == [False, True]


def test_saved_constraints_are_restored_as_numbers():
    constraints = pd.DataFrame(
        [{"nutriente": "MS", "minimo": "89,0", "maximo": "99,0", "resultado": "89,0", "situacao": "Atendida"}]
    )
    normalized = normalize_loaded_constraints(constraints)
    assert normalized.loc[0, "minimo"] == 89.0
    assert normalized.loc[0, "maximo"] == 99.0
    assert normalized.loc[0, "resultado"] == 89.0


def test_fingerprint_ignores_saved_outputs_and_catalog_metadata():
    saved_items = pd.DataFrame(
        [{
            "ingredient_id": "ing_1",
            "sem_custo": "FALSE",
            "preco_kg": "1,70",
            "inclusao_min": "0",
            "inclusao_max": "100",
            "inclusao_calculada": "42,0582",
            "custo_parcial": "0,7150",
            "MS": "86,90",
            "NDT": "80",
        }]
    )
    current_items = pd.DataFrame(
        [{
            "ingredient_id": "ing_1",
            "nome": "Milho",
            "tipo": "Alimento",
            "fonte": "catálogo",
            "sem_custo": False,
            "preco_kg": 1.70,
            "inclusao_min": 0.0,
            "inclusao_max": 100.0,
            "inclusao_calculada": None,
            "custo_parcial": None,
            "MS": 86.90,
            "NDT": 80.0,
        }]
    )
    constraints_saved = pd.DataFrame([{"nutriente": "MS", "minimo": "89", "maximo": "99", "resultado": "89"}])
    constraints_current = pd.DataFrame([{"nutriente": "MS", "minimo": 89.0, "maximo": 99.0}])

    assert calculation_fingerprint(saved_items, constraints_saved) == calculation_fingerprint(
        current_items, constraints_current
    )


def test_normalize_loaded_metadata_accepts_ptbr_cost() -> None:
    from src.diet_loading import normalize_loaded_metadata

    normalized = normalize_loaded_metadata({"nome": "Dieta 1", "custo_kg": "1,4958"})
    assert normalized["custo_kg"] == 1.4958
