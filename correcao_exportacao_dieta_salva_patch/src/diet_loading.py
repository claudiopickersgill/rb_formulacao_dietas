from __future__ import annotations

import pandas as pd

from .config import NUTRIENT_CODES
from .utils import as_bool, as_float, dataframe_fingerprint


def normalize_loaded_metadata(metadata: dict) -> dict:
    """Restaura tipos numéricos relevantes do cabeçalho da dieta salva.

    Planilhas do Google devolvem valores formatados como texto. Em especial,
    custos podem chegar como ``"1,4958"`` e precisam ser convertidos antes de
    métricas, comparações e exportações.
    """
    normalized = dict(metadata or {})
    for key in ("custo_kg", "custo_per_kg"):
        if key in normalized:
            normalized[key] = as_float(normalized.get(key))
    return normalized


def normalize_loaded_items(items: pd.DataFrame) -> pd.DataFrame:
    """Restaura tipos de uma dieta lida de armazenamento tabular.

    O Google Sheets devolve ``get_all_values()`` como texto, inclusive para
    percentuais e custos. O resultado salvo precisa voltar ao app com os mesmos
    tipos numéricos/booleanos de uma dieta recém-calculada.
    """
    normalized = items.copy()
    if "sem_custo" not in normalized.columns:
        normalized["sem_custo"] = False
    else:
        normalized["sem_custo"] = normalized["sem_custo"].map(
            lambda value: as_bool(value, False)
        )

    numeric_columns = [
        "preco_kg",
        "inclusao_min",
        "inclusao_max",
        "inclusao_calculada",
        "custo_parcial",
        *NUTRIENT_CODES,
    ]
    for column in numeric_columns:
        if column in normalized.columns:
            normalized[column] = normalized[column].map(lambda value: as_float(value))
    return normalized


def normalize_loaded_constraints(constraints: pd.DataFrame) -> pd.DataFrame:
    """Restaura limites e resultados nutricionais salvos como texto."""
    normalized = constraints.copy()
    for column in ("minimo", "maximo", "resultado"):
        if column in normalized.columns:
            normalized[column] = normalized[column].map(lambda value: as_float(value))
    return normalized


def calculation_fingerprint(items: pd.DataFrame, constraints: pd.DataFrame) -> str:
    """Fingerprint somente dos dados que influenciam a otimização.

    Colunas de saída como ``inclusao_calculada`` e ``custo_parcial`` não fazem
    parte da comparação. Isso evita que uma dieta recém-aberta seja marcada
    como alterada só porque o Google Sheets devolveu strings ou porque o catálogo
    contém metadados que não são persistidos em ``dieta_ingredientes``.
    """
    normalized_items = normalize_loaded_items(items)
    item_columns = [
        column
        for column in [
            "ingredient_id",
            "sem_custo",
            "preco_kg",
            "inclusao_min",
            "inclusao_max",
            *NUTRIENT_CODES,
        ]
        if column in normalized_items.columns
    ]
    item_input = normalized_items[item_columns].copy()
    if "ingredient_id" in item_input.columns:
        item_input["ingredient_id"] = item_input["ingredient_id"].astype(str)
        item_input = item_input.sort_values("ingredient_id", kind="stable").reset_index(drop=True)

    normalized_constraints = normalize_loaded_constraints(constraints)
    constraint_columns = [
        column
        for column in ["nutriente", "minimo", "maximo"]
        if column in normalized_constraints.columns
    ]
    constraint_input = normalized_constraints[constraint_columns].copy()
    if "nutriente" in constraint_input.columns:
        constraint_input["nutriente"] = constraint_input["nutriente"].astype(str)
        constraint_input = constraint_input.sort_values("nutriente", kind="stable").reset_index(drop=True)

    return dataframe_fingerprint(item_input, constraint_input)
