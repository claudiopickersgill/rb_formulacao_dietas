"""Compatibilidade com a conexão do repositório original.

O novo aplicativo usa ``src.repositories.GoogleSheetsRepository``. Estas funções
permanecem para que códigos antigos que importem ``faz_conexao`` continuem funcionando.
"""
from __future__ import annotations

import streamlit as st

from src.google_connection import open_spreadsheet


@st.cache_resource
def abre_planilha():
    service_account = dict(st.secrets["gcp_service_account"])
    try:
        url = str(st.secrets["private_gsheets_url"])
    except (KeyError, FileNotFoundError):
        url = str(st.secrets.get("google_sheets", {}).get("spreadsheet_url", ""))
    spreadsheet_id = str(st.secrets.get("google_sheets", {}).get("spreadsheet_id", ""))
    return open_spreadsheet(
        service_account,
        spreadsheet_url=url,
        spreadsheet_id=spreadsheet_id,
    )


def faz_conexao():
    """Retorna a primeira aba, preservando a assinatura do código original."""
    return abre_planilha().get_worksheet(0)
