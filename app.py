from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from src.auth import authenticate, logout
from src.pages import admin, dashboard, diets, formulation, ingredients
from src.repositories.factory import build_repository
from src.ui_helpers import inject_css

PROJECT_ROOT = Path(__file__).resolve().parent
LOGO_PATH = PROJECT_ROOT / "assets" / "logo_rfb.png"

st.set_page_config(
    page_title="RFB | Diet Formulation System",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()


def _secret_section(name: str) -> dict[str, Any]:
    try:
        return dict(st.secrets[name])
    except (KeyError, FileNotFoundError, TypeError):
        return {}


def _secret_value(name: str, default: Any = "") -> Any:
    try:
        return st.secrets[name]
    except (KeyError, FileNotFoundError, TypeError):
        return default


app_settings = _secret_section("app")
google_settings = _secret_section("google_sheets")
service_account = _secret_section("gcp_service_account")
# Compatibilidade direta com o secrets.toml do repositório original.
if not google_settings.get("spreadsheet_url"):
    google_settings["spreadsheet_url"] = str(_secret_value("private_gsheets_url", ""))
google_settings.setdefault("table_prefix", "rb_")
google_settings.setdefault("auto_migrate_legacy", True)
google_settings.setdefault("legacy_worksheet_index", 0)
google_settings.setdefault("cache_ttl_seconds", 60)
google_settings.setdefault("max_retries", 5)
repository_mode = str(
    app_settings.get(
        "repository",
        "google_sheets" if service_account and google_settings.get("spreadsheet_url") else "local",
    )
)
auth_mode = str(app_settings.get("auth_mode", "local"))


@st.cache_resource
def get_repository(mode: str, google: tuple, service: tuple):
    repo = build_repository(
        mode=mode,
        project_root=PROJECT_ROOT,
        settings=dict(google),
        service_account=dict(service),
    )
    repo.initialize()
    return repo


try:
    repository = get_repository(
        repository_mode,
        tuple(sorted(google_settings.items())),
        tuple(sorted(service_account.items())),
    )
except Exception as exc:
    st.error("Não foi possível inicializar o repositório de dados.")
    st.exception(exc)
    st.info(
        "Confirme se a conta de serviço tem acesso à planilha e se "
        "private_gsheets_url está correto no secrets.toml."
    )
    st.stop()

migration_summary = getattr(repository, "legacy_migration_summary", {})
if migration_summary.get("executed") and not st.session_state.get("legacy_migration_notified"):
    st.toast(
        f"{migration_summary.get('rows', 0)} ingredientes copiados da aba "
        f"'{migration_summary.get('source', '')}'.",
        icon="✅",
    )
    st.session_state["legacy_migration_notified"] = True

backfill_summary = getattr(repository, "ingredient_backfill_summary", {})
if backfill_summary.get("executed") and not st.session_state.get("ingredient_backfill_notified"):
    st.toast(
        f"Base nutricional reparada: {backfill_summary.get('cells_filled', 0)} campo(s) "
        f"em {backfill_summary.get('rows_changed', 0)} ingrediente(s).",
        icon="🧩",
    )
    st.session_state["ingredient_backfill_notified"] = True

user = authenticate(repository, auth_mode, app_settings)
with st.sidebar:
    # Marca RFB: logo centralizada, seguida do nome e subtítulo do sistema.
    logo_left, logo_center, logo_right = st.columns([1, 3.2, 1])
    with logo_center:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width="stretch")
        else:
            st.caption("Logo não encontrada em assets/logo_rfb.png")

    st.markdown("## RFB")
    st.caption("Diet Formulation System")
    st.divider()

    st.caption(f"{user.nome}\n\n{user.email}\n\n**{user.perfil}**")
    pages = ["Visão geral", "Nova formulação", "Dietas salvas", "Ingredientes"]
    if user.is_admin:
        pages.append("Administração")
    if st.session_state.get("page") not in pages:
        st.session_state["page"] = pages[0]
    page = st.radio("Menu", pages, key="page")
    st.divider()
    source_label = "Google Sheets" if repository_mode == "google_sheets" else "modo local"
    st.caption(f"Dados: {source_label}")
    if repository_mode == "google_sheets":
        st.caption(f"Abas do app: `{google_settings.get('table_prefix', 'rb_')}*`")
    if st.button("Sair", width="stretch"):
        logout(auth_mode)

if page == "Visão geral":
    dashboard.render(repository, user)
elif page == "Nova formulação":
    formulation.render(repository, user)
elif page == "Dietas salvas":
    diets.render(repository, user)
elif page == "Ingredientes":
    ingredients.render(repository, user)
elif page == "Administração":
    admin.render(repository, user)
