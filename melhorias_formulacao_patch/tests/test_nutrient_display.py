from __future__ import annotations

import pandas as pd

from src.result_analysis import nutrient_result_display


def test_nutrient_display_marks_active_and_near_limits() -> None:
    constraints = pd.DataFrame(
        [
            {
                "nutriente": "MS",
                "descricao": "Matéria seca",
                "unidade": "%",
                "minimo": 89.0,
                "maximo": 99.0,
                "resultado": 89.0,
                "situacao": "Atendida",
            },
            {
                "nutriente": "NDT",
                "descricao": "Nutrientes digestíveis totais",
                "unidade": "%",
                "minimo": 70.0,
                "maximo": 80.0,
                "resultado": 70.5,
                "situacao": "Atendida",
            },
            {
                "nutriente": "PB",
                "descricao": "Proteína bruta",
                "unidade": "%",
                "minimo": 18.0,
                "maximo": 25.0,
                "resultado": 21.0,
                "situacao": "Atendida",
            },
        ]
    )

    display = nutrient_result_display(constraints).set_index("nutriente")
    assert display.loc["MS", "situacao_visual"] == "🟡 No limite"
    assert display.loc["NDT", "situacao_visual"] == "🟠 Próximo ao limite"
    assert display.loc["PB", "situacao_visual"] == "🟢 Com folga"
    assert display.loc["NDT", "limite_proximo"] == "Mínimo"
    assert display.loc["NDT", "margem_limite"] == 0.5
