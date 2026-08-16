from __future__ import annotations

from typing import Any

import pandas as pd

from .utils import as_float


def nutrient_result_display(constraints: pd.DataFrame) -> pd.DataFrame:
    """Cria uma visão amigável das restrições e da distância até os limites."""

    if constraints.empty:
        return pd.DataFrame(
            columns=[
                "nutriente",
                "descricao",
                "unidade",
                "minimo",
                "resultado",
                "maximo",
                "limite_proximo",
                "margem_limite",
                "situacao_visual",
            ]
        )

    rows: list[dict[str, Any]] = []
    for _, row in constraints.iterrows():
        data = row.to_dict()
        result_value = as_float(row.get("resultado"))
        minimum = as_float(row.get("minimo"))
        maximum = as_float(row.get("maximo"))
        original_status = str(row.get("situacao") or "")

        candidates: list[tuple[str, float]] = []
        if result_value is not None and minimum is not None:
            candidates.append(("Mínimo", result_value - minimum))
        if result_value is not None and maximum is not None:
            candidates.append(("Máximo", maximum - result_value))

        nearest_name = "—"
        nearest_margin: float | None = None
        if candidates:
            nearest_name, nearest_margin = min(candidates, key=lambda item: abs(item[1]))

        if original_status != "Atendida" or (nearest_margin is not None and nearest_margin < -1e-7):
            visual_status = "🔴 Fora do limite"
        elif result_value is None or nearest_margin is None:
            visual_status = "—"
        else:
            tolerance = max(1e-7, abs(result_value) * 1e-7)
            if abs(nearest_margin) <= tolerance:
                visual_status = "🟡 No limite"
            else:
                if minimum is not None and maximum is not None and maximum > minimum:
                    near_threshold = (maximum - minimum) * 0.10
                else:
                    reference = minimum if minimum is not None else maximum
                    near_threshold = max(abs(reference or result_value) * 0.05, 0.01)
                visual_status = (
                    "🟠 Próximo ao limite"
                    if nearest_margin <= near_threshold
                    else "🟢 Com folga"
                )

        rows.append(
            {
                "nutriente": data.get("nutriente", ""),
                "descricao": data.get("descricao", ""),
                "unidade": data.get("unidade", ""),
                "minimo": minimum,
                "resultado": result_value,
                "maximo": maximum,
                "limite_proximo": nearest_name,
                "margem_limite": nearest_margin,
                "situacao_visual": visual_status,
            }
        )

    return pd.DataFrame(rows)
