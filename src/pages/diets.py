from __future__ import annotations

import pandas as pd
import streamlit as st

from ..exports import export_filenames, make_csv_bytes, make_excel_bytes, make_pdf_bytes
from ..models import User
from ..repositories.base import Repository
from ..ui_helpers import go_to, page_header
from ..utils import format_brl, new_id


def render(repository: Repository, user: User) -> None:
    page_header("Dietas salvas", "Consulte, compare, duplique, exporte ou retome uma formulação.")
    diets = repository.list_diets(user.email, user.perfil)
    if diets.empty:
        st.info("Nenhuma dieta disponível para este usuário.")
        if st.button("Criar a primeira dieta", type="primary"):
            go_to("Nova formulação")
        return

    query = st.text_input("Buscar", placeholder="Nome, categoria ou autor")
    filtered = diets.copy()
    if query.strip():
        mask = pd.Series(False, index=filtered.index)
        for col in ["nome", "categoria_animal", "proprietario", "status"]:
            mask |= filtered[col].fillna("").astype(str).str.contains(query, case=False, na=False)
        filtered = filtered[mask]

    st.dataframe(
        filtered[["nome", "categoria_animal", "status", "custo_kg", "proprietario", "updated_at"]],
        hide_index=True,
        width="stretch",
        column_config={
            "nome": "Dieta",
            "categoria_animal": "Categoria",
            "status": "Status",
            "custo_kg": st.column_config.NumberColumn("Custo/kg", format="R$ %.4f"),
            "proprietario": "Autor",
            "updated_at": "Atualizada em",
        },
    )

    if filtered.empty:
        return

    ids = filtered["diet_id"].astype(str).tolist()
    label_map = {
        str(row["diet_id"]): f"{row['nome']} · {row.get('updated_at', '')}"
        for _, row in filtered.iterrows()
    }
    selected_id = st.selectbox(
        "Abrir dieta",
        ids,
        format_func=lambda value: label_map.get(str(value), str(value)),
    )
    bundle = repository.get_diet(selected_id)
    if bundle is None:
        st.error("Não foi possível carregar a dieta selecionada.")
        return

    metadata = bundle["metadata"]
    items = bundle["items"]
    constraints = bundle["constraints"]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Custo/kg", format_brl(pd.to_numeric(pd.Series([metadata.get("custo_kg")]), errors="coerce").iloc[0], 4))
    m2.metric("Ingredientes", len(items))
    m3.metric("Status", str(metadata.get("status") or "—"))
    m4.metric("Autor", str(metadata.get("proprietario") or "—"))

    tab1, tab2, tab3 = st.tabs(["Ingredientes", "Nutrientes", "Informações"])
    with tab1:
        visible = [
            "nome",
            "preco_kg",
            "inclusao_min",
            "inclusao_max",
            "inclusao_calculada",
            "custo_parcial",
        ]
        st.dataframe(items[[c for c in visible if c in items.columns]], hide_index=True, width="stretch")
    with tab2:
        st.dataframe(constraints, hide_index=True, width="stretch")
    with tab3:
        st.write(metadata.get("descricao") or "Sem descrição.")
        st.json({key: value for key, value in metadata.items() if key not in {"descricao"}})

    actions = st.columns(4)
    if actions[0].button(
    "Continuar editando",
    type="primary",
    width="stretch",
    on_click=go_to,
    args=("Nova formulação",),
    kwargs={"frm_load_bundle": bundle},
    )

    can_modify = user.can_edit and (
        user.is_admin or str(metadata.get("proprietario", "")).lower() == user.email.lower()
    )
    if actions[1].button("Duplicar", width="stretch", disabled=not can_modify):
        duplicate_meta = dict(metadata)
        duplicate_meta["diet_id"] = new_id("diet")
        duplicate_meta["parent_diet_id"] = selected_id
        duplicate_meta["nome"] = f"Cópia de {metadata.get('nome', 'dieta')}"
        duplicate_meta["proprietario"] = user.email
        repository.save_diet(duplicate_meta, items, constraints, actor=user.email)
        st.success("Dieta duplicada.")
        st.rerun()

    confirm_delete = actions[2].checkbox("Confirmar exclusão", disabled=not can_modify)
    if actions[3].button("Excluir", width="stretch", disabled=not (can_modify and confirm_delete)):
        repository.delete_diet(selected_id, actor=user.email)
        st.success("Dieta excluída.")
        st.rerun()

    st.subheader("Exportar")
    filenames = export_filenames(metadata)
    e1, e2, e3 = st.columns(3)
    e1.download_button(
        "Excel",
        make_excel_bytes(metadata, items, constraints),
        filenames["xlsx"],
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )
    e2.download_button(
        "PDF",
        make_pdf_bytes(metadata, items, constraints),
        filenames["pdf"],
        "application/pdf",
        width="stretch",
    )
    e3.download_button(
        "CSV",
        make_csv_bytes(items),
        filenames["csv"],
        "text/csv",
        width="stretch",
    )

    st.subheader("Comparar dietas")
    compare_ids = st.multiselect(
        "Selecione até três dietas",
        options=ids,
        max_selections=3,
        format_func=lambda value: label_map.get(str(value), str(value)),
    )
    if len(compare_ids) >= 2:
        _render_comparison(repository, compare_ids)


def _render_comparison(repository: Repository, diet_ids: list[str]) -> None:
    cost_rows = []
    nutrient_frames = []
    for diet_id in diet_ids:
        bundle = repository.get_diet(diet_id)
        if not bundle:
            continue
        meta = bundle["metadata"]
        name = str(meta.get("nome") or diet_id)
        cost_rows.append(
            {
                "Dieta": name,
                "Custo/kg": pd.to_numeric(pd.Series([meta.get("custo_kg")]), errors="coerce").iloc[0],
                "Status": meta.get("status", ""),
            }
        )
        constraints = bundle["constraints"]
        if not constraints.empty:
            nutrient_frames.append(
                constraints[["nutriente", "resultado"]]
                .rename(columns={"resultado": name})
                .set_index("nutriente")
            )
    st.dataframe(pd.DataFrame(cost_rows), hide_index=True, width="stretch")
    if nutrient_frames:
        comparison = pd.concat(nutrient_frames, axis=1).reset_index()
        st.dataframe(comparison, hide_index=True, width="stretch")
