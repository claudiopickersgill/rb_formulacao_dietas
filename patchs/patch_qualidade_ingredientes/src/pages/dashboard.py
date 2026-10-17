from __future__ import annotations

import pandas as pd
import streamlit as st

from ..models import User
from ..ingredient_quality import active_quality_warnings
from ..repositories.base import Repository
from ..ui_helpers import go_to, page_header
from ..utils import as_bool, format_brl, numeric_series


def render(repository: Repository, user: User) -> None:
    page_header("Visão geral", "Resumo da base de ingredientes e das formulações salvas.")
    ingredients = repository.list_ingredients(active_only=False)
    diets = repository.list_diets(user.email, user.perfil)

    active_count = 0 if ingredients.empty else int(ingredients["ativo"].map(lambda v: as_bool(v, True)).sum())
    warnings = active_quality_warnings(ingredients)
    warning_count = len(warnings)
    avg_cost = numeric_series(diets.get("custo_kg", pd.Series(dtype=float))).mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ingredientes ativos", active_count)
    c2.metric("Ativos com pendências", warning_count)
    c3.metric("Dietas salvas", len(diets))
    c4.metric("Custo médio/kg", format_brl(avg_cost, 4))

    st.subheader("Ações rápidas")
    a1, a2, a3 = st.columns(3)
    a1.button(
        "Nova formulação",
        type="primary",
        width="stretch",
        on_click=go_to,
        args=("Nova formulação",),
    )
    a2.button(
        "Cadastrar ingrediente",
        width="stretch",
        on_click=go_to,
        args=("Ingredientes",),
    )
    a3.button(
        "Abrir dietas salvas",
        width="stretch",
        on_click=go_to,
        args=("Dietas salvas",),
    )

    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Dietas recentes")
        if diets.empty:
            st.info("Nenhuma dieta foi salva ainda.")
        else:
            display = diets[["nome", "status", "custo_kg", "proprietario", "updated_at"]].head(8).copy()
            display["custo_kg"] = numeric_series(display["custo_kg"])
            st.dataframe(
                display,
                hide_index=True,
                width="stretch",
                column_config={
                    "nome": "Dieta",
                    "status": "Status",
                    "custo_kg": st.column_config.NumberColumn("Custo/kg", format="R$ %.4f"),
                    "proprietario": "Autor",
                    "updated_at": "Atualizada em",
                },
            )

    with right:
        st.subheader("Qualidade dos cadastros")
        if warning_count == 0:
            st.success("Nenhum ingrediente ativo com pendência cadastrada.")
        else:
            warnings = warnings[["nome", "qualidade_dados"]]
            st.warning(f"Há {warning_count} ingredientes ativos com pendências de qualidade.")
            st.dataframe(warnings, hide_index=True, width="stretch")
            st.caption("Revise esses registros antes de usá-los em restrições nutricionais críticas.")
