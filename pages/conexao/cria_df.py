from __future__ import annotations

import pandas as pd
import streamlit as st

from pages.conexao.conexao import faz_conexao


@st.cache_data(ttl=300, show_spinner=False)
def cria_df() -> pd.DataFrame:
    """Leitura legada da primeira aba, com cache para evitar excesso de requisições."""
    return pd.DataFrame(faz_conexao().get_all_records())
