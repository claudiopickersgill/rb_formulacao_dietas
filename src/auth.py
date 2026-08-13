from __future__ import annotations

from typing import Any, Mapping

import streamlit as st

from .models import User
from .repositories.base import Repository
from .security import has_password, verify_password
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
    return _user_from_record(record, email=email, fallback_name=name)


def _authenticate_local(repository: Repository, settings: Mapping[str, Any]) -> User:
    """Autentica o administrador bootstrap ou usuários de ``rb_usuarios``.

    O par ``local_email``/``local_password`` continua funcionando como acesso
    administrativo de recuperação. Os demais usuários são validados pelo hash
    individual salvo na tabela de usuários.
    """
    default_email = str(settings.get("local_email", "admin@local")).strip().lower()
    default_password = str(settings.get("local_password", "admin"))

    if not st.session_state.get("local_authenticated", False):
        st.title("Formulação RB")
        st.write("Entre com seu email e senha para acessar o sistema.")
        with st.form("local_login"):
            email = st.text_input("Email", value=default_email)
            password = st.text_input("Senha", type="password")
            submit = st.form_submit_button("Entrar", type="primary", width="stretch")

        if submit:
            normalized_email = str(email or "").strip().lower()
            record = repository.get_user_by_email(normalized_email)
            is_bootstrap_admin = (
                normalize_text(normalized_email) == normalize_text(default_email)
                and password == default_password
            )

            if record is not None and not as_bool(record.get("ativo"), True):
                st.error("Seu usuário está inativo. Procure um administrador.")
            elif is_bootstrap_admin:
                if record is None:
                    record = repository.upsert_user(
                        {
                            "email": normalized_email,
                            "nome": str(settings.get("local_name", "Administrador local")),
                            "perfil": "Administrador",
                            "ativo": True,
                        },
                        actor=normalized_email,
                    )
                _start_local_session(normalized_email)
            elif record is None:
                st.error("Email ou senha incorretos.")
            elif not has_password(record.get("password_hash")):
                st.error(
                    "Este usuário está cadastrado, mas ainda não possui uma senha. "
                    "Peça a um administrador para definir uma senha no painel de usuários."
                )
            elif verify_password(password, str(record.get("password_hash") or "")):
                _start_local_session(normalized_email)
            else:
                st.error("Email ou senha incorretos.")
        st.stop()

    email = str(st.session_state.get("local_email", default_email)).strip().lower()
    record = repository.get_user_by_email(email)

    # Compatibilidade com instalações antigas: o administrador configurado nos
    # segredos é criado automaticamente na primeira entrada.
    if record is None and normalize_text(email) == normalize_text(default_email):
        record = repository.upsert_user(
            {
                "email": email,
                "nome": str(settings.get("local_name", "Administrador local")),
                "perfil": "Administrador",
                "ativo": True,
            },
            actor=email,
        )

    if record is None:
        _clear_local_session()
        st.error("O usuário desta sessão não existe mais.")
        st.stop()

    if not as_bool(record.get("ativo"), True):
        _clear_local_session()
        st.error("Seu usuário está inativo. Procure um administrador.")
        st.stop()

    _touch_once(repository, email)
    return _user_from_record(record, email=email, fallback_name="Usuário")


def logout(mode: str) -> None:
    if str(mode).lower() == "oidc":
        st.logout()
    else:
        _clear_local_session()
        st.rerun()


def _start_local_session(email: str) -> None:
    st.session_state["local_authenticated"] = True
    st.session_state["local_email"] = email.strip().lower()
    st.rerun()


def _clear_local_session() -> None:
    st.session_state.pop("local_authenticated", None)
    st.session_state.pop("local_email", None)


def _user_from_record(record: Mapping[str, Any], email: str, fallback_name: str) -> User:
    return User(
        user_id=str(record.get("user_id", "")),
        email=email,
        nome=str(record.get("nome") or fallback_name),
        perfil=str(record.get("perfil") or "Consulta"),
        ativo=True,
    )


def _touch_once(repository: Repository, email: str) -> None:
    key = f"login_touched::{email}"
    if not st.session_state.get(key):
        repository.touch_login(email)
        st.session_state[key] = True
