from __future__ import annotations

import math
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.optimize import linprog

from .config import NUTRIENT_BY_CODE
from .models import SolverResult
from .utils import as_bool, as_float, normalize_text, numeric_series
from .validators import validate_formulation


def _nutrient_vector(items: pd.DataFrame, code: str) -> np.ndarray:
    """Return a finite nutrient vector for the solver.

    Google Sheets returns empty cells as empty strings. For mineral ingredients,
    an empty nutrient cell means no declared contribution and is treated as 0.
    For foods, an empty/non-numeric value remains NaN so validation can stop the
    calculation and identify the ingredient that needs its composition completed.
    """
    if code not in items.columns:
        return np.full(len(items), np.nan, dtype=float)

    values = numeric_series(items[code])
    if "tipo" in items.columns:
        mineral_mask = items["tipo"].map(normalize_text).eq("mineral")
        values = values.mask(mineral_mask & values.isna(), 0.0)
    return values.to_numpy(dtype=float)


def _constraint_matrices(
    work: pd.DataFrame,
    active: pd.DataFrame,
    *,
    skip_code: str | None = None,
) -> tuple[list[np.ndarray], list[float]]:
    a_ub: list[np.ndarray] = []
    b_ub: list[float] = []
    for _, row in active.iterrows():
        code = str(row["nutriente"])
        if skip_code is not None and code == skip_code:
            continue
        vector = _nutrient_vector(work, code) / 100.0
        minimum = as_float(row.get("minimo"))
        maximum = as_float(row.get("maximo"))
        if maximum is not None:
            a_ub.append(vector)
            b_ub.append(maximum)
        if minimum is not None:
            a_ub.append(-vector)
            b_ub.append(-minimum)
    return a_ub, b_ub


def estimate_conditional_ranges(
    items: pd.DataFrame,
    constraints: pd.DataFrame,
) -> dict[str, tuple[float | None, float | None]]:
    """Estimate each nutrient range while enforcing all the *other* constraints.

    This is more useful for diagnosing an infeasible formulation than looking at
    inclusion bounds alone because it exposes conflicts between nutrient targets.
    """
    work = items.copy().reset_index(drop=True)
    active = _active_constraints(constraints)
    n = len(work)
    a_eq = np.ones((1, n), dtype=float)
    b_eq = np.array([100.0])
    bounds = _bounds(work)
    ranges: dict[str, tuple[float | None, float | None]] = {}

    for code in active["nutriente"].astype(str).unique():
        objective = _nutrient_vector(work, code) / 100.0
        if not np.isfinite(objective).all():
            ranges[code] = (None, None)
            continue
        a_ub, b_ub = _constraint_matrices(work, active, skip_code=code)
        if a_ub and not np.isfinite(np.vstack(a_ub)).all():
            ranges[code] = (None, None)
            continue
        common = dict(
            A_ub=np.vstack(a_ub) if a_ub else None,
            b_ub=np.asarray(b_ub, dtype=float) if b_ub else None,
            A_eq=a_eq,
            b_eq=b_eq,
            bounds=bounds,
            method="highs",
        )
        low = linprog(objective, **common)
        high = linprog(-objective, **common)
        ranges[code] = (
            float(low.fun) if low.success else None,
            float(-high.fun) if high.success else None,
        )
    return ranges


def _active_constraints(constraints: pd.DataFrame) -> pd.DataFrame:
    if constraints.empty:
        return pd.DataFrame(columns=["nutriente", "minimo", "maximo"])
    work = constraints.copy()
    work["nutriente"] = work["nutriente"].astype(str).str.strip()
    work = work[work["nutriente"].ne("")]
    work = work[work["minimo"].notna() | work["maximo"].notna()]
    return work.reset_index(drop=True)


def _bounds(items: pd.DataFrame) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    for _, row in items.iterrows():
        minimum = as_float(row.get("inclusao_min"), 0.0) or 0.0
        maximum = as_float(row.get("inclusao_max"), 100.0)
        result.append((minimum, 100.0 if maximum is None else maximum))
    return result


def estimate_achievable_ranges(
    items: pd.DataFrame,
    nutrient_codes: Iterable[str],
) -> dict[str, tuple[float | None, float | None]]:
    """Estimate each nutrient range using only inclusion bounds and the 100% sum."""
    n = len(items)
    a_eq = np.ones((1, n), dtype=float)
    b_eq = np.array([100.0])
    bounds = _bounds(items)
    ranges: dict[str, tuple[float | None, float | None]] = {}

    for code in nutrient_codes:
        values = _nutrient_vector(items, code)
        if not np.isfinite(values).all():
            ranges[code] = (None, None)
            continue
        objective = values / 100.0
        low = linprog(objective, A_eq=a_eq, b_eq=b_eq, bounds=bounds, method="highs")
        high = linprog(-objective, A_eq=a_eq, b_eq=b_eq, bounds=bounds, method="highs")
        ranges[code] = (
            float(low.fun) if low.success else None,
            float(-high.fun) if high.success else None,
        )
    return ranges


def solve_least_cost(items: pd.DataFrame, constraints: pd.DataFrame) -> SolverResult:
    validation = validate_formulation(items, constraints)
    if not validation.valid:
        return SolverResult(
            success=False,
            status="dados_invalidos",
            message="A formulação contém dados inválidos.",
            diagnostics=validation.errors + validation.warnings,
        )

    work = items.copy().reset_index(drop=True)
    active = _active_constraints(constraints)
    n = len(work)

    prices_series = numeric_series(work["preco_kg"])
    if "sem_custo" in work.columns:
        free_mask = work["sem_custo"].map(lambda value: as_bool(value, False))
        prices_series = prices_series.mask(free_mask, 0.0)
    prices = prices_series.to_numpy(dtype=float)
    # O resultado e as exportações devem refletir o preço efetivamente usado
    # pela função objetivo. Ingredientes marcados como sem custo ficam em zero.
    work["preco_kg"] = prices
    c = prices / 100.0
    a_eq = np.ones((1, n), dtype=float)
    b_eq = np.array([100.0])
    a_ub, b_ub = _constraint_matrices(work, active)

    # Defensive guard: validation should catch these values first, but the
    # solver must never crash the entire Streamlit app because of one bad cell.
    if not np.isfinite(c).all() or (a_ub and not np.isfinite(np.vstack(a_ub)).all()):
        return SolverResult(
            success=False,
            status="dados_invalidos",
            message="Há valores ausentes ou não numéricos nos dados usados no cálculo.",
            diagnostics=validation.warnings + [
                "Revise os preços e a composição dos nutrientes que possuem restrições ativas."
            ],
        )

    try:
        result = linprog(
        c,
        A_ub=np.vstack(a_ub) if a_ub else None,
        b_ub=np.asarray(b_ub, dtype=float) if b_ub else None,
        A_eq=a_eq,
        b_eq=b_eq,
        bounds=_bounds(work),
        method="highs",
        options={"presolve": True},
        )
    except ValueError as exc:
        return SolverResult(
            success=False,
            status="dados_invalidos",
            message="Não foi possível montar o problema de otimização com os dados informados.",
            diagnostics=[str(exc)] + validation.warnings,
        )

    if not result.success:
        diagnostics = [f"Solver: {result.message}"]
        codes = active["nutriente"].astype(str).tolist()
        achievable = estimate_achievable_ranges(work, codes)
        for _, row in active.iterrows():
            code = str(row["nutriente"])
            low, high = achievable.get(code, (None, None))
            minimum = as_float(row.get("minimo"))
            maximum = as_float(row.get("maximo"))
            unit = NUTRIENT_BY_CODE[code].unit
            if low is None or high is None:
                continue
            if minimum is not None and minimum > high + 1e-7:
                diagnostics.append(
                    f"{code}: o mínimo solicitado ({minimum:g} {unit}) é maior que o máximo "
                    f"aproximadamente alcançável ({high:.4g} {unit})."
                )
            if maximum is not None and maximum < low - 1e-7:
                diagnostics.append(
                    f"{code}: o máximo solicitado ({maximum:g} {unit}) é menor que o mínimo "
                    f"aproximadamente alcançável ({low:.4g} {unit})."
                )
        conditional = estimate_conditional_ranges(work, active)
        for _, row in active.iterrows():
            code = str(row["nutriente"])
            low, high = conditional.get(code, (None, None))
            minimum = as_float(row.get("minimo"))
            maximum = as_float(row.get("maximo"))
            unit = NUTRIENT_BY_CODE[code].unit
            if low is None or high is None:
                continue
            if minimum is not None and minimum > high + 1e-7:
                diagnostics.append(
                    f"{code}: mantendo as demais restrições, o maior valor alcançável é "
                    f"{high:.4g} {unit}, abaixo do mínimo solicitado de {minimum:g} {unit}."
                )
            if maximum is not None and maximum < low - 1e-7:
                diagnostics.append(
                    f"{code}: mantendo as demais restrições, o menor valor alcançável é "
                    f"{low:.4g} {unit}, acima do máximo solicitado de {maximum:g} {unit}."
                )

        if len(diagnostics) == 1:
            diagnostics.append(
                "As restrições podem ser individualmente possíveis, mas incompatíveis quando aplicadas em conjunto."
            )
        return SolverResult(
            success=False,
            status="inviavel" if result.status == 2 else "falha_solver",
            message="Não foi encontrada uma solução que atenda simultaneamente às restrições.",
            diagnostics=diagnostics + validation.warnings,
            raw={"status": int(result.status), "message": str(result.message)},
        )

    inclusion = np.asarray(result.x, dtype=float)
    work["inclusao_calculada"] = inclusion
    work["custo_parcial"] = prices * inclusion / 100.0

    evaluations: list[dict[str, object]] = []
    for _, row in active.iterrows():
        code = str(row["nutriente"])
        values = _nutrient_vector(work, code)
        achieved = float(np.dot(values, inclusion) / 100.0)
        minimum = as_float(row.get("minimo"))
        maximum = as_float(row.get("maximo"))
        tolerance = max(1e-7, abs(achieved) * 1e-7)
        ok_min = minimum is None or achieved >= minimum - tolerance
        ok_max = maximum is None or achieved <= maximum + tolerance
        situation = "Atendida" if ok_min and ok_max else "Fora do limite"
        evaluations.append(
            {
                "nutriente": code,
                "descricao": NUTRIENT_BY_CODE[code].label,
                "unidade": NUTRIENT_BY_CODE[code].unit,
                "minimo": minimum,
                "maximo": maximum,
                "resultado": achieved,
                "situacao": situation,
            }
        )

    cost = float(np.dot(prices, inclusion) / 100.0)
    sum_inclusion = float(inclusion.sum())
    if not math.isclose(sum_inclusion, 100.0, abs_tol=1e-5):
        return SolverResult(
            success=False,
            status="erro_numerico",
            message="O solver retornou uma solução com soma diferente de 100%.",
            diagnostics=[f"Soma retornada: {sum_inclusion:.8f}%"],
        )

    return SolverResult(
        success=True,
        status="otima",
        message="Solução ótima encontrada.",
        cost_per_kg=cost,
        items=work,
        constraints=pd.DataFrame(evaluations),
        diagnostics=validation.warnings,
        raw={
            "status": int(result.status),
            "message": str(result.message),
            "iterations": int(getattr(result, "nit", 0) or 0),
            "objective": float(result.fun),
        },
    )
