from __future__ import annotations

import math
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.optimize import linprog

from .config import NUTRIENT_BY_CODE
from .models import SolverResult
from .utils import as_float
from .validators import validate_formulation


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
        values = pd.to_numeric(items[code], errors="coerce").to_numpy(dtype=float)
        if np.isnan(values).any():
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

    prices = pd.to_numeric(work["preco_kg"], errors="coerce").to_numpy(dtype=float)
    c = prices / 100.0
    a_eq = np.ones((1, n), dtype=float)
    b_eq = np.array([100.0])
    a_ub: list[np.ndarray] = []
    b_ub: list[float] = []

    for _, row in active.iterrows():
        code = str(row["nutriente"])
        vector = pd.to_numeric(work[code], errors="coerce").to_numpy(dtype=float) / 100.0
        minimum = as_float(row.get("minimo"))
        maximum = as_float(row.get("maximo"))
        if maximum is not None:
            a_ub.append(vector)
            b_ub.append(maximum)
        if minimum is not None:
            a_ub.append(-vector)
            b_ub.append(-minimum)

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
        values = pd.to_numeric(work[code], errors="coerce").to_numpy(dtype=float)
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
