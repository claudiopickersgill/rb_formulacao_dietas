from __future__ import annotations

import pandas as pd

from src.repositories.local import LocalRepository


def test_local_repository_crud(tmp_path) -> None:
    repository = LocalRepository(tmp_path)
    repository.initialize()
    ingredient = repository.upsert_ingredient(
        {"tipo": "Alimento", "nome": "Milho teste", "preco_padrao": 2.5, "ativo": True},
        actor="teste@example.com",
    )
    assert len(repository.list_ingredients()) == 1

    repository.upsert_user(
        {"email": "teste@example.com", "nome": "Teste", "perfil": "Formulador", "ativo": True},
        actor="teste@example.com",
    )
    assert repository.get_user_by_email("TESTE@example.com") is not None

    items = pd.DataFrame(
        [
            {
                "ingredient_id": ingredient["ingredient_id"],
                "nome": "Milho teste",
                "tipo": "Alimento",
                "classificacao": "Energético",
                "preco_kg": 2.5,
                "inclusao_min": 0,
                "inclusao_max": 100,
                "inclusao_calculada": 100,
                "custo_parcial": 2.5,
                "PB": 8,
            }
        ]
    )
    constraints = pd.DataFrame(
        [{"nutriente": "PB", "unidade": "%", "minimo": 8, "maximo": 10, "resultado": 8, "situacao": "Atendida"}]
    )
    diet_id = repository.save_diet(
        {"nome": "Teste", "proprietario": "teste@example.com", "status": "Ótima", "custo_kg": 2.5},
        items,
        constraints,
        actor="teste@example.com",
    )
    loaded = repository.get_diet(diet_id)
    assert loaded is not None
    assert loaded["metadata"]["nome"] == "Teste"
    assert len(loaded["items"]) == 1
    repository.delete_diet(diet_id, actor="teste@example.com")
    assert repository.get_diet(diet_id) is None
