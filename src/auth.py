from __future__ import annotations

from typing import Any, Mapping

import streamlit as st

from .models import User
from .repositories.base import Repository
from .utils import as_bool, normalize_text


def authenticate(
    repository: Repository,
    mode: str,
    settings: Mapping[str, Any] | None = None,
) -> User:
    settings = settings or {}
    if str(mode).lower() == "oidc":
        return _authenticate_oidc(repository, settings)
    return _authenticate_local(repository, settings)


def _authenticate_oidc(repository: Repository, settings: Mapping[str, Any]) -> User:
    if not st.user.is_logged_in:
        st.title("Formulação RB")
        st.write("Entre com sua conta para acessar o sistema.")
        provider = str(settings.get("oidc_provider", "google") or "google")
        if st.button("Entrar com Google", type="primary", width="stretch"):
            st.login(provider)
        st.stop()

    email = str(getattr(st.user, "email", "") or st.user.get("email", "")).strip().lower()
    name = str(getattr(st.user, "name", "") or st.user.get("name", "") or email)
    if not email:
        st.error("O provedor de login não retornou um email.")
        if st.button("Sair"):
            st.logout()
        st.stop()

    record = repository.get_user_by_email(email)
    bootstrap_email = normalize_text(settings.get("bootstrap_admin_email", ""))
    if record is None and bootstrap_email and normalize_text(email) == bootstrap_email:
        record = repository.upsert_user(
            {"email": email, "nome": name, "perfil": "Administrador", "ativo": True},
            actor=email,
        )

    if record is None:
        st.error("Seu email ainda não está autorizado para acessar este aplicativo.")
        st.caption(f"Conta identificada: {email}")
        if st.button("Sair"):
            st.logout()
        st.stop()

    if not as_bool(record.get("ativo"), True):
        st.error("Seu usuário está inativo. Procure um administrador.")
        if st.button("Sair"):
            st.logout()
        st.stop()

    _touch_once(repository, email)
    return User(
        user_id=str(record.get("user_id", "")),
        email=email,
        nome=str(record.get("nome") or name),
        perfil=str(record.get("perfil") or "Consulta"),
        ativo=True,
    )


def _authenticate_local(repository: Repository, settings: Mapping[str, Any]) -> User:
    default_email = str(settings.get("local_email", "admin@local"))
    default_password = str(settings.get("local_password", "admin"))

    if not st.session_state.get("local_authenticated", False):
        st.title("Formulação RB — modo local")
        st.info("Este login é apenas para desenvolvimento. No ambiente online, use OIDC/Google.")
        with st.form("local_login"):
            email = st.text_input("Email", value=default_email)
            password = st.text_input("Senha", type="password")
            submit = st.form_submit_button("Entrar", type="primary", width="stretch")
        if submit:
            if normalize_text(email) == normalize_text(default_email) and password == default_password:
                st.session_state["local_authenticated"] = True
                st.session_state["local_email"] = email.strip().lower()
                st.rerun()
            else:
                st.error("Email ou senha incorretos.")
        st.stop()

    email = str(st.session_state.get("local_email", default_email)).strip().lower()
    record = repository.get_user_by_email(email)
    if record is None:
        record = repository.upsert_user(
            {
                "email": email,
                "nome": str(settings.get("local_name", "Administrador local")),
                "perfil": "Administrador",
                "ativo": True,
            },
            actor=email,
        )
    _touch_once(repository, email)
    return User(
        user_id=str(record.get("user_id", "")),
        email=email,
        nome=str(record.get("nome") or "Administrador local"),
        perfil=str(record.get("perfil") or "Administrador"),
        ativo=True,
    )


def logout(mode: str) -> None:
    if str(mode).lower() == "oidc":
        st.logout()
    else:
        st.session_state.pop("local_authenticated", None)
        st.session_state.pop("local_email", None)
        st.rerun()


def _touch_once(repository: Repository, email: str) -> None:
    key = f"login_touched::{email}"
    if not st.session_state.get(key):
        repository.touch_login(email)
        st.session_state[key] = True
