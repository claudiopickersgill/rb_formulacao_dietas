from __future__ import annotations

import pandas as pd

from src.exports import make_csv_bytes, make_excel_bytes, make_pdf_bytes


def test_exports_create_valid_headers() -> None:
    metadata = {"nome": "Dieta teste", "proprietario": "teste@example.com", "status": "Ótima", "custo_kg": 1.25}
    items = pd.DataFrame(
        [{"nome": "Milho", "tipo": "Alimento", "classificacao": "Energético", "preco_kg": 1.25, "inclusao_min": 0, "inclusao_max": 100, "inclusao_calculada": 100, "custo_parcial": 1.25, "PB": 8}]
    )
    constraints = pd.DataFrame(
        [{"nutriente": "PB", "unidade": "%", "minimo": 8, "maximo": 10, "resultado": 8, "situacao": "Atendida"}]
    )
    assert make_excel_bytes(metadata, items, constraints).startswith(b"PK")
    assert make_pdf_bytes(metadata, items, constraints).startswith(b"%PDF")
    assert b"Milho" in make_csv_bytes(items)


def test_exports_accept_google_sheets_ptbr_strings() -> None:
    metadata = {
        "nome": "Dieta salva",
        "proprietario": "admin@local",
        "status": "Ótima",
        "custo_kg": "1,4958",
    }
    items = pd.DataFrame(
        [
            {
                "nome": "Milho",
                "tipo": "Alimento",
                "classificacao": "Energético",
                "preco_kg": "1,7000",
                "inclusao_min": "0",
                "inclusao_max": "100",
                "inclusao_calculada": "42,0582",
                "custo_parcial": "0,7150",
                "MS": "86,90",
                "NDT": "80,00",
            }
        ]
    )
    constraints = pd.DataFrame(
        [
            {
                "nutriente": "MS",
                "unidade": "%",
                "minimo": "89,0000",
                "maximo": "99,0000",
                "resultado": "89,0000",
                "situacao": "Atendida",
            }
        ]
    )

    assert make_excel_bytes(metadata, items, constraints).startswith(b"PK")
    assert make_pdf_bytes(metadata, items, constraints).startswith(b"%PDF")
    csv_bytes = make_csv_bytes(items)
    assert b"Milho" in csv_bytes
    assert b"42,0582" in csv_bytes
