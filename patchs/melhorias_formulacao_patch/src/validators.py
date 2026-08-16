from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config import NUTRIENT_CODES
from .utils import as_bool, as_float, normalize_text, numeric_series


@dataclass(slots=True)
class ValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str]


def validate_formulation(items: pd.DataFrame, constraints: pd.DataFrame) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if items.empty:
        return ValidationResult(False, ["Selecione pelo menos um ingrediente."], [])

    work = items.copy()
    required = {"ingredient_id", "nome", "preco_kg", "inclusao_min", "inclusao_max"}
    missing_columns = required - set(work.columns)
    if missing_columns:
        errors.append(f"Faltam colunas na tabela de ingredientes: {', '.join(sorted(missing_columns))}.")
        return ValidationResult(False, errors, warnings)

    ids = work["ingredient_id"].astype(str)
    if ids.duplicated().any():
        names = work.loc[ids.duplicated(keep=False), "nome"].astype(str).unique().tolist()
        errors.append("O mesmo ingrediente aparece mais de uma vez: " + ", ".join(names) + ".")

    for idx, row in work.iterrows():
        label = str(row.get("nome") or f"Linha {idx + 1}")
        price = as_float(row.get("preco_kg"))
        free_of_cost = as_bool(row.get("sem_custo"), False)
        minimum = as_float(row.get("inclusao_min"), 0.0)
        maximum = as_float(row.get("inclusao_max"), 100.0)

        if free_of_cost:
            if price is not None and price < 0:
                errors.append(f"Informe um preço válido para {label}.")
            elif price is not None and price > 0:
                warnings.append(
                    f"{label} está marcado como sem custo; o preço informado será desconsiderado no cálculo."
                )
        elif price is None or price <= 0:
            errors.append(
                f"O preço de {label} está vazio ou igual a zero. Informe um preço maior que zero "
                "ou marque 'Sem custo' se o ingrediente realmente não tiver custo."
            )
        if minimum is None or maximum is None:
            errors.append(f"Informe os limites de inclusão de {label}.")
            continue
        if minimum < 0 or maximum > 100:
            errors.append(f"Os limites de {label} devem ficar entre 0 e 100%.")
        if minimum > maximum:
            errors.append(f"O mínimo de {label} não pode ser maior que o máximo.")

    min_sum = numeric_series(work["inclusao_min"]).fillna(0).sum()
    max_sum = numeric_series(work["inclusao_max"]).fillna(100).sum()
    if min_sum > 100 + 1e-8:
        errors.append(f"A soma das inclusões mínimas é {min_sum:.2f}%, acima de 100%.")
    if max_sum < 100 - 1e-8:
        errors.append(f"A soma das inclusões máximas é {max_sum:.2f}%, abaixo de 100%.")

    active = constraints.copy()
    if not active.empty:
        active = active[active["nutriente"].astype(str).str.strip().ne("")]
        active = active[
            active["minimo"].notna() | active["maximo"].notna()
        ]

    if active.empty:
        warnings.append("Nenhuma restrição nutricional foi informada; o cálculo minimizará apenas o custo.")
    else:
        invalid_codes = sorted(set(active["nutriente"].astype(str)) - set(NUTRIENT_CODES))
        if invalid_codes:
            errors.append("Nutrientes inválidos: " + ", ".join(invalid_codes) + ".")
        duplicated = active["nutriente"].astype(str).duplicated(keep=False)
        if duplicated.any():
            errors.append(
                "Cada nutriente deve aparecer apenas uma vez nas restrições: "
                + ", ".join(sorted(active.loc[duplicated, "nutriente"].astype(str).unique()))
                + "."
            )
        for _, row in active.iterrows():
            code = str(row["nutriente"])
            minimum = as_float(row.get("minimo"))
            maximum = as_float(row.get("maximo"))
            if minimum is not None and maximum is not None and minimum > maximum:
                errors.append(f"No nutriente {code}, o mínimo não pode ser maior que o máximo.")
            if code not in work.columns:
                errors.append(f"O nutriente {code} não existe na tabela de ingredientes.")
                continue

            numeric = numeric_series(work[code])
            if "tipo" in work.columns:
                mineral_mask = work["tipo"].map(normalize_text).eq("mineral")
                numeric = numeric.mask(mineral_mask & numeric.isna(), 0.0)

            missing_mask = numeric.isna()
            if missing_mask.any():
                missing_names = work.loc[missing_mask, "nome"].astype(str).tolist()
                errors.append(
                    f"O nutriente {code} está ausente, vazio ou não numérico para: {', '.join(missing_names)}. "
                    "Preencha o cadastro ou remova essa restrição."
                )

    return ValidationResult(not errors, errors, warnings)
