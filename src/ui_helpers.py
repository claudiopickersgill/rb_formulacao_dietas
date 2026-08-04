from __future__ import annotations

import streamlit as st


APP_CSS = """
<style>
    .block-container {padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1500px;}
    [data-testid="stSidebar"] {border-right: 1px solid #e6edf3;}
    .rb-subtitle {color: #5b6773; margin-top: -0.6rem; margin-bottom: 1rem;}
    .rb-card {border: 1px solid #e5e7eb; border-radius: 12px; padding: 1rem; background: white;}
    .rb-warning {border-left: 4px solid #f59e0b; padding: .65rem .85rem; background: #fffbeb; border-radius: 4px;}
    .rb-success {border-left: 4px solid #16a34a; padding: .65rem .85rem; background: #f0fdf4; border-radius: 4px;}
    div[data-testid="stMetric"] {border: 1px solid #e5e7eb; padding: 0.75rem; border-radius: 12px;}
</style>
"""


def inject_css() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "") -> None:
    st.title(title)
    if subtitle:
        st.markdown(f'<div class="rb-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def go_to(page: str) -> None:
    st.session_state["page"] = page
    st.rerun()
