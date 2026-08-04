from __future__ import annotations

import pandas as pd
import streamlit as st

from ..models import User
from ..repositories.base import Repository
from ..ui_helpers import go_to, page_header
from ..utils import as_bool, format_brl


def render(repository: Repository, user: User) -> None:
    page_header("Visão geral", "Resumo da base de ingredientes e das formulações salvas.")
    ingredients = repository.list_ingredients(active_only=False)
    diets = repository.list_diets(user.email, user.perfil)

    active_count = 0 if ingredients.empty else int(ingredients["ativo"].map(lambda v: as_bool(v, True)).sum())
    warning_count = 0 if ingredients.empty else int(ingredients["qualidade_dados"].fillna("").astype(str).str.strip().ne("").sum())
    avg_cost = pd.to_numeric(diets.get("custo_kg", pd.Series(dtype=float)), errors="coerce").mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ingredientes ativos", active_count)
    c2.metric("Alertas na base", warning_count)
    c3.metric("Dietas salvas", len(diets))
    c4.metric("Custo médio/kg", format_brl(avg_cost, 4))

    st.subheader("Ações rápidas")
    a1, a2, a3 = st.columns(3)
    if a1.button("Nova formulação", type="primary", width="stretch"):
        go_to("Nova formulação")
    if a2.button("Cadastrar ingrediente", width="stretch"):
        go_to("Ingredientes")
    if a3.button("Abrir dietas salvas", width="stretch"):
        go_to("Dietas salvas")

    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Dietas recentes")
        if diets.empty:
            st.info("Nenhuma dieta foi salva ainda.")
        else:
            display = diets[["nome", "status", "custo_kg", "proprietario", "updated_at"]].head(8).copy()
            display["custo_kg"] = pd.to_numeric(display["custo_kg"], errors="coerce")
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
            st.success("Nenhum alerta cadastral foi identificado.")
        else:
            warnings = ingredients[
                ingredients["qualidade_dados"].fillna("").astype(str).str.strip().ne("")
            ][["nome", "qualidade_dados"]].head(10)
            st.warning(f"Há {warning_count} ingredientes com observações de qualidade.")
            st.dataframe(warnings, hide_index=True, width="stretch")
            st.caption("Revise esses registros antes de usá-los em restrições nutricionais críticas.")
