from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from ..config import DEFAULT_CONSTRAINTS, NUTRIENT_BY_CODE, NUTRIENT_CODES
from ..exports import export_filenames, make_csv_bytes, make_excel_bytes, make_pdf_bytes
from ..models import SolverResult, User
from ..repositories.base import Repository
from ..solver import solve_least_cost
from ..ui_helpers import page_header
from ..utils import as_float, dataframe_fingerprint, format_brl, new_id

PREFIX = "frm_"
EDITABLE_COLUMNS = [
    "ingredient_id",
    "nome",
    "tipo",
    "classificacao",
    "preco_kg",
    "inclusao_min",
    "inclusao_max",
]


def render(repository: Repository, user: User) -> None:
    _load_pending_bundle()
    page_header(
        "Nova formulação",
        "Selecione ingredientes, informe preços e limites, defina as exigências e calcule a dieta de menor custo.",
    )
    catalog = repository.list_ingredients(active_only=False)
    if catalog.empty:
        st.error("Não há ingredientes ativos. Cadastre pelo menos um ingrediente antes de formular.")
        return

    with st.container(border=True):
        st.subheader("Identificação")
        c1, c2 = st.columns([2, 1])
        c1.text_input("Nome da dieta *", key=PREFIX + "name", placeholder="Ex.: Concentrado terminação")
        c2.text_input("Categoria animal", key=PREFIX + "category", placeholder="Ex.: Novilhos em terminação")
        st.text_area("Descrição", key=PREFIX + "description", height=75)
        c3, c4 = st.columns(2)
        c3.selectbox("Base", ["Matéria seca", "Matéria natural"], key=PREFIX + "base")
        c4.selectbox("Objetivo", ["Custo mínimo"], key=PREFIX + "objective")

    active_mask = catalog["ativo"].fillna(True).astype(str).str.lower().isin(["true", "1", "sim", "ativo"])
    selected_from_state = [str(value) for value in st.session_state.get(PREFIX + "selected_ids", [])]
    option_ids = catalog.loc[active_mask, "ingredient_id"].astype(str).tolist()
    option_ids += [value for value in selected_from_state if value not in option_ids and value in set(catalog["ingredient_id"].astype(str))]
    catalog_index = catalog.set_index(catalog["ingredient_id"].astype(str), drop=False)
    label_map = {
        str(row["ingredient_id"]): f"{row['nome']} · {row['tipo']}"
        for _, row in catalog.iterrows()
    }

    st.subheader("Ingredientes")
    selected_ids = st.multiselect(
        "Ingredientes da dieta",
        options=option_ids,
        format_func=lambda value: label_map.get(str(value), str(value)),
        key=PREFIX + "selected_ids",
        placeholder="Escolha um ou mais ingredientes",
    )
    full_items = _merge_selected_items(selected_ids, catalog_index)

    if full_items.empty:
        st.info("Selecione os ingredientes que poderão participar da mistura.")
    else:
        editable = full_items[EDITABLE_COLUMNS].copy()
        edited = st.data_editor(
            editable,
            hide_index=True,
            width="stretch",
            num_rows="fixed",
            key=PREFIX + "items_editor",
            column_config={
                "ingredient_id": None,
                "nome": st.column_config.TextColumn("Ingrediente", disabled=True, width="large"),
                "tipo": st.column_config.TextColumn("Tipo", disabled=True),
                "classificacao": st.column_config.TextColumn("Classificação", disabled=True),
                "preco_kg": st.column_config.NumberColumn(
                    "Preço (R$/kg)", min_value=0.0, step=0.01, format="R$ %.4f", required=True
                ),
                "inclusao_min": st.column_config.NumberColumn(
                    "Mínimo (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.3f"
                ),
                "inclusao_max": st.column_config.NumberColumn(
                    "Máximo (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.3f"
                ),
            },
        )
        full_items = _apply_edits(full_items, edited)
        st.session_state[PREFIX + "items_full"] = full_items

    st.subheader("Restrições nutricionais")
    if PREFIX + "constraints" not in st.session_state:
        st.session_state[PREFIX + "constraints"] = pd.DataFrame(
            [{"nutriente": code, "minimo": None, "maximo": None} for code in DEFAULT_CONSTRAINTS]
        )
    constraints = st.data_editor(
        st.session_state[PREFIX + "constraints"],
        hide_index=True,
        width="stretch",
        num_rows="dynamic",
        key=PREFIX + "constraints_editor",
        column_config={
            "nutriente": st.column_config.SelectboxColumn(
                "Nutriente", options=NUTRIENT_CODES, required=True, width="medium"
            ),
            "minimo": st.column_config.NumberColumn("Mínimo", step=0.01, format="%.4f"),
            "maximo": st.column_config.NumberColumn("Máximo", step=0.01, format="%.4f"),
        },
    )
    constraints = constraints[["nutriente", "minimo", "maximo"]].copy()
    st.session_state[PREFIX + "constraints"] = constraints
    active_codes = constraints.loc[
        constraints["minimo"].notna() | constraints["maximo"].notna(), "nutriente"
    ].astype(str)
    if not active_codes.empty:
        units = ", ".join(
            f"{code}: {NUTRIENT_BY_CODE[code].unit}"
            for code in active_codes.unique()
            if code in NUTRIENT_BY_CODE
        )
        st.caption(f"Unidades utilizadas — {units}")

    current_fingerprint = dataframe_fingerprint(full_items, constraints)
    b1, b2, b3 = st.columns([1, 1, 3])
    calculate = b1.button("Calcular dieta", type="primary", width="stretch", disabled=full_items.empty)
    if b2.button("Limpar", width="stretch"):
        _reset_form()
        st.rerun()

    if calculate:
        with st.spinner("Calculando a solução de menor custo..."):
            result = solve_least_cost(full_items, constraints)
        st.session_state[PREFIX + "result"] = result
        st.session_state[PREFIX + "result_fingerprint"] = current_fingerprint

    result: SolverResult | None = st.session_state.get(PREFIX + "result")
    if result is not None:
        is_current = st.session_state.get(PREFIX + "result_fingerprint") == current_fingerprint
        _render_result(repository, user, result, is_current, current_fingerprint)


def _merge_selected_items(selected_ids: list[str], catalog_index: pd.DataFrame) -> pd.DataFrame:
    previous = st.session_state.get(PREFIX + "items_full", pd.DataFrame())
    previous_map = {}
    if isinstance(previous, pd.DataFrame) and not previous.empty:
        previous_map = {str(row["ingredient_id"]): row.to_dict() for _, row in previous.iterrows()}

    rows: list[dict[str, Any]] = []
    for ingredient_id in selected_ids:
        key = str(ingredient_id)
        if key in previous_map:
            rows.append(previous_map[key])
            continue
        catalog_row = catalog_index.loc[key]
        if isinstance(catalog_row, pd.DataFrame):
            catalog_row = catalog_row.iloc[0]
        row = catalog_row.to_dict()
        row["ingredient_id"] = key
        row["preco_kg"] = as_float(row.get("preco_padrao"))
        row["inclusao_min"] = 0.0
        row["inclusao_max"] = 100.0
        row["inclusao_calculada"] = None
        row["custo_parcial"] = None
        rows.append(row)
    return pd.DataFrame(rows)


def _apply_edits(full: pd.DataFrame, edited: pd.DataFrame) -> pd.DataFrame:
    edit_map = {str(row["ingredient_id"]): row.to_dict() for _, row in edited.iterrows()}
    rows = []
    for _, row in full.iterrows():
        data = row.to_dict()
        changes = edit_map.get(str(data["ingredient_id"]), {})
        data.update(changes)
        rows.append(data)
    return pd.DataFrame(rows)


def _render_result(
    repository: Repository,
    user: User,
    result: SolverResult,
    is_current: bool,
    current_fingerprint: str,
) -> None:
    st.divider()
    st.subheader("Resultado")
    if not result.success:
        st.error(result.message)
        for diagnostic in result.diagnostics:
            st.write(f"• {diagnostic}")
        return

    if not is_current:
        st.warning("Os ingredientes ou as restrições foram alterados depois do cálculo. Calcule novamente antes de salvar.")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Custo por kg", format_brl(result.cost_per_kg, 4))
    m2.metric("Soma da mistura", f"{result.items['inclusao_calculada'].sum():.4f}%")
    m3.metric("Ingredientes usados", int((result.items["inclusao_calculada"] > 1e-8).sum()))
    attended = 0 if result.constraints.empty else int(result.constraints["situacao"].eq("Atendida").sum())
    m4.metric("Restrições atendidas", f"{attended}/{len(result.constraints)}")

    tab1, tab2, tab3 = st.tabs(["Mistura", "Nutrientes", "Composição usada"])
    with tab1:
        display = result.items[
            ["nome", "preco_kg", "inclusao_min", "inclusao_max", "inclusao_calculada", "custo_parcial"]
        ].copy()
        display = display[display["inclusao_calculada"] > 1e-9]
        st.dataframe(
            display,
            hide_index=True,
            width="stretch",
            column_config={
                "nome": "Ingrediente",
                "preco_kg": st.column_config.NumberColumn("Preço/kg", format="R$ %.4f"),
                "inclusao_min": st.column_config.NumberColumn("Mínimo", format="%.3f%%"),
                "inclusao_max": st.column_config.NumberColumn("Máximo", format="%.3f%%"),
                "inclusao_calculada": st.column_config.ProgressColumn(
                    "Inclusão", min_value=0, max_value=100, format="%.4f%%"
                ),
                "custo_parcial": st.column_config.NumberColumn("Custo parcial", format="R$ %.4f"),
            },
        )
    with tab2:
        st.dataframe(
            result.constraints,
            hide_index=True,
            width="stretch",
            column_config={
                "nutriente": "Código",
                "descricao": "Nutriente",
                "unidade": "Unidade",
                "minimo": st.column_config.NumberColumn("Mínimo", format="%.4f"),
                "maximo": st.column_config.NumberColumn("Máximo", format="%.4f"),
                "resultado": st.column_config.NumberColumn("Resultado", format="%.4f"),
                "situacao": "Situação",
            },
        )
    with tab3:
        columns = ["nome", *[code for code in NUTRIENT_CODES if code in result.items.columns]]
        st.dataframe(result.items[columns], hide_index=True, width="stretch")

    if result.diagnostics:
        with st.expander("Avisos do cálculo"):
            for warning in result.diagnostics:
                st.write(f"• {warning}")

    metadata = _metadata(user, result)
    filenames = export_filenames(metadata)
    st.subheader("Salvar e exportar")
    s1, s2, s3 = st.columns(3)
    can_persist = user.can_edit and is_current and bool(str(metadata["nome"]).strip())
    if s1.button("Salvar dieta", type="primary", width="stretch", disabled=not can_persist):
        diet_id = str(st.session_state.get(PREFIX + "diet_id") or new_id("diet"))
        metadata["diet_id"] = diet_id
        saved_id = repository.save_diet(metadata, result.items, result.constraints, actor=user.email)
        st.session_state[PREFIX + "diet_id"] = saved_id
        st.success("Dieta salva com sucesso.")
    if s2.button("Salvar como nova versão", width="stretch", disabled=not can_persist):
        metadata["parent_diet_id"] = str(st.session_state.get(PREFIX + "diet_id") or "")
        metadata["diet_id"] = new_id("diet")
        saved_id = repository.save_diet(metadata, result.items, result.constraints, actor=user.email)
        st.session_state[PREFIX + "diet_id"] = saved_id
        st.success("Nova versão salva com sucesso.")
    s3.caption("Para salvar, informe o nome e recalcule após qualquer alteração.")

    d1, d2, d3 = st.columns(3)
    d1.download_button(
        "Baixar Excel",
        data=make_excel_bytes(metadata, result.items, result.constraints),
        file_name=filenames["xlsx"],
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )
    d2.download_button(
        "Baixar PDF",
        data=make_pdf_bytes(metadata, result.items, result.constraints),
        file_name=filenames["pdf"],
        mime="application/pdf",
        width="stretch",
    )
    d3.download_button(
        "Baixar CSV",
        data=make_csv_bytes(result.items),
        file_name=filenames["csv"],
        mime="text/csv",
        width="stretch",
    )


def _metadata(user: User, result: SolverResult) -> dict[str, Any]:
    return {
        "diet_id": st.session_state.get(PREFIX + "diet_id", ""),
        "parent_diet_id": st.session_state.get(PREFIX + "parent_diet_id", ""),
        "nome": st.session_state.get(PREFIX + "name", ""),
        "descricao": st.session_state.get(PREFIX + "description", ""),
        "categoria_animal": st.session_state.get(PREFIX + "category", ""),
        "base": st.session_state.get(PREFIX + "base", "Matéria seca"),
        "objetivo": st.session_state.get(PREFIX + "objective", "Custo mínimo"),
        "proprietario": user.email,
        "status": "Ótima",
        "custo_kg": result.cost_per_kg,
    }


def _load_pending_bundle() -> None:
    bundle = st.session_state.pop(PREFIX + "load_bundle", None)
    if not bundle:
        _ensure_defaults()
        return
    metadata = bundle["metadata"]
    items = bundle["items"].copy()
    constraints = bundle["constraints"].copy()
    st.session_state[PREFIX + "diet_id"] = metadata.get("diet_id", "")
    st.session_state[PREFIX + "parent_diet_id"] = metadata.get("parent_diet_id", "")
    st.session_state[PREFIX + "name"] = metadata.get("nome", "")
    st.session_state[PREFIX + "description"] = metadata.get("descricao", "")
    st.session_state[PREFIX + "category"] = metadata.get("categoria_animal", "")
    st.session_state[PREFIX + "base"] = metadata.get("base", "Matéria seca")
    st.session_state[PREFIX + "objective"] = metadata.get("objetivo", "Custo mínimo")
    st.session_state[PREFIX + "selected_ids"] = items["ingredient_id"].astype(str).tolist()
    st.session_state[PREFIX + "items_full"] = items
    st.session_state[PREFIX + "constraints"] = constraints[["nutriente", "minimo", "maximo"]].copy()
    result = SolverResult(
        success=True,
        status="salva",
        message="Dieta carregada.",
        cost_per_kg=as_float(metadata.get("custo_kg")),
        items=items,
        constraints=constraints,
    )
    fingerprint = dataframe_fingerprint(items, st.session_state[PREFIX + "constraints"])
    st.session_state[PREFIX + "result"] = result
    st.session_state[PREFIX + "result_fingerprint"] = fingerprint


def _ensure_defaults() -> None:
    defaults = {
        PREFIX + "name": "",
        PREFIX + "description": "",
        PREFIX + "category": "",
        PREFIX + "base": "Matéria seca",
        PREFIX + "objective": "Custo mínimo",
        PREFIX + "selected_ids": [],
        PREFIX + "items_full": pd.DataFrame(),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _reset_form() -> None:
    for key in list(st.session_state):
        if key.startswith(PREFIX):
            del st.session_state[key]
