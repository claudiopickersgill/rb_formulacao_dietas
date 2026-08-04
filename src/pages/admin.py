from __future__ import annotations

import pandas as pd
import streamlit as st

from ..config import ROLES
from ..models import User
from ..repositories.base import Repository
from ..ui_helpers import page_header
from ..utils import as_bool


def render(repository: Repository, user: User) -> None:
    page_header("Administração", "Controle de acesso e trilha de auditoria.")
    if not user.is_admin:
        st.error("Apenas administradores podem acessar esta página.")
        return

    users_tab, audit_tab, system_tab = st.tabs(["Usuários", "Auditoria", "Sistema"])
    with users_tab:
        users = repository.list_users()
        st.dataframe(users, hide_index=True, width="stretch")
        st.subheader("Adicionar ou atualizar usuário")
        ids = [""] + users["user_id"].astype(str).tolist() if not users.empty else [""]
        selected_id = st.selectbox(
            "Registro existente",
            ids,
            format_func=lambda value: "Novo usuário" if not value else _user_label(users, value),
        )
        existing = {}
        if selected_id:
            existing = users[users["user_id"].astype(str).eq(selected_id)].iloc[0].to_dict()
        with st.form("admin_user_form"):
            c1, c2 = st.columns(2)
            email = c1.text_input("Email *", value=str(existing.get("email") or ""))
            name = c2.text_input("Nome *", value=str(existing.get("nome") or ""))
            c3, c4 = st.columns(2)
            role_value = str(existing.get("perfil") or "Consulta")
            role = c3.selectbox("Perfil", list(ROLES), index=list(ROLES).index(role_value) if role_value in ROLES else 2)
            active = c4.checkbox("Ativo", value=as_bool(existing.get("ativo"), True))
            submit = st.form_submit_button("Salvar usuário", type="primary")
        if submit:
            if not email.strip() or "@" not in email:
                st.error("Informe um email válido.")
            elif not name.strip():
                st.error("Informe o nome.")
            else:
                repository.upsert_user(
                    {
                        "user_id": existing.get("user_id", ""),
                        "email": email.strip().lower(),
                        "nome": name.strip(),
                        "perfil": role,
                        "ativo": active,
                        "created_at": existing.get("created_at", ""),
                        "last_login": existing.get("last_login", ""),
                    },
                    actor=user.email,
                )
                st.success("Usuário salvo.")
                st.rerun()

    with audit_tab:
        limit = st.slider("Quantidade de eventos", 50, 1000, 250, 50)
        audit = repository.list_audit(limit)
        st.dataframe(audit, hide_index=True, width="stretch", height=600)

    with system_tab:
        st.subheader("Integração e manutenção")
        summary = getattr(repository, "legacy_migration_summary", {})
        if summary:
            st.write("**Migração da aba legada**")
            st.json(summary)
        else:
            st.info("Este backend não possui migração legada automática.")

        ingredient_count = len(repository.list_ingredients(active_only=False))
        diet_count = len(repository.list_diets(user.email, user.perfil))
        c1, c2 = st.columns(2)
        c1.metric("Ingredientes", ingredient_count)
        c2.metric("Dietas", diet_count)

        if hasattr(repository, "clear_cache"):
            if st.button("Limpar cache do Google Sheets"):
                repository.clear_cache()
                st.cache_data.clear()
                st.success("Cache limpo. Os dados serão relidos na próxima ação.")
                st.rerun()


def _user_label(users: pd.DataFrame, user_id: str) -> str:
    row = users[users["user_id"].astype(str).eq(str(user_id))].iloc[0]
    return f"{row['nome']} · {row['email']}"
