from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd
import streamlit as st

from ..config import INGREDIENT_COLUMNS, NUTRIENTS
from ..models import User
from ..repositories.base import Repository
from ..ui_helpers import page_header
from ..utils import as_bool, as_float, new_id, normalize_text


def render(repository: Repository, user: User) -> None:
    page_header("Ingredientes", "Gerencie alimentos e minerais utilizados nas formulações.")
    ingredients = repository.list_ingredients(active_only=False)
    tabs = ["Consultar"]
    if user.can_edit:
        tabs.extend(["Novo ingrediente", "Editar", "Importar CSV"])
    selected_tabs = st.tabs(tabs)

    with selected_tabs[0]:
        _list_ingredients(ingredients)

    if not user.can_edit:
        return

    with selected_tabs[1]:
        payload = _ingredient_form(None, "new")
        if payload is not None:
            duplicate = _find_duplicate(ingredients, payload["tipo"], payload["nome"])
            if duplicate is not None:
                st.error("Já existe um ingrediente com o mesmo tipo e nome.")
            else:
                repository.upsert_ingredient(payload, actor=user.email)
                st.success("Ingrediente cadastrado.")
                st.rerun()

    with selected_tabs[2]:
        if ingredients.empty:
            st.info("Não há ingredientes para editar.")
        else:
            ids = ingredients["ingredient_id"].astype(str).tolist()
            label_map = {
                str(row["ingredient_id"]): f"{row['nome']} · {row['tipo']}"
                for _, row in ingredients.iterrows()
            }
            selected_id = st.selectbox(
                "Ingrediente",
                ids,
                format_func=lambda value: label_map.get(str(value), str(value)),
                key="edit_ingredient_id",
            )
            existing = ingredients[ingredients["ingredient_id"].astype(str).eq(selected_id)].iloc[0].to_dict()
            payload = _ingredient_form(existing, f"edit_{selected_id}")
            if payload is not None:
                duplicate = _find_duplicate(
                    ingredients,
                    payload["tipo"],
                    payload["nome"],
                    ignore_id=selected_id,
                )
                if duplicate is not None:
                    st.error("Já existe outro ingrediente com o mesmo tipo e nome.")
                else:
                    repository.upsert_ingredient(payload, actor=user.email)
                    st.success("Ingrediente atualizado.")
                    st.rerun()
            active = as_bool(existing.get("ativo"), True)
            if st.button("Inativar" if active else "Reativar", key=f"toggle_{selected_id}"):
                repository.set_ingredient_active(selected_id, not active, actor=user.email)
                st.rerun()

    with selected_tabs[3]:
        _bulk_import(repository, ingredients, user)


def _list_ingredients(ingredients: pd.DataFrame) -> None:
    c1, c2, c3 = st.columns([2, 1, 1])
    query = c1.text_input("Pesquisar", placeholder="Nome, classificação ou fonte")
    type_filter = c2.selectbox("Tipo", ["Todos", "Alimento", "Mineral"])
    status_filter = c3.selectbox("Situação", ["Ativos", "Todos", "Inativos"])

    filtered = ingredients.copy()
    if query.strip():
        mask = pd.Series(False, index=filtered.index)
        for col in ["nome", "classificacao", "fonte", "formula_quimica"]:
            mask |= filtered[col].fillna("").astype(str).str.contains(query, case=False, na=False)
        filtered = filtered[mask]
    if type_filter != "Todos":
        filtered = filtered[filtered["tipo"].astype(str).eq(type_filter)]
    active_mask = filtered["ativo"].map(lambda value: as_bool(value, True))
    if status_filter == "Ativos":
        filtered = filtered[active_mask]
    elif status_filter == "Inativos":
        filtered = filtered[~active_mask]

    visible = [
        "tipo",
        "nome",
        "classificacao",
        "preco_padrao",
        "MS",
        "NDT",
        "PB",
        "FDN",
        "FDA",
        "CA",
        "P",
        "ativo",
        "qualidade_dados",
    ]
    st.dataframe(filtered[visible], hide_index=True, width="stretch", height=500)
    st.caption(f"{len(filtered)} registro(s) exibido(s).")
    st.download_button(
        "Exportar ingredientes em CSV",
        data=ingredients.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
        file_name="ingredientes.csv",
        mime="text/csv",
    )


def _ingredient_form(existing: dict[str, Any] | None, prefix: str) -> dict[str, Any] | None:
    existing = existing or {}
    with st.form(f"ingredient_form_{prefix}"):
        c1, c2, c3 = st.columns([1, 2, 1])
        tipo = c1.selectbox(
            "Tipo *",
            ["Alimento", "Mineral"],
            index=0 if str(existing.get("tipo", "Alimento")) != "Mineral" else 1,
        )
        nome = c2.text_input("Nome *", value=str(existing.get("nome") or ""))
        classificacao = c3.text_input("Classificação", value=str(existing.get("classificacao") or ""))
        c4, c5, c6 = st.columns([1, 1, 1])
        formula = c4.text_input("Fórmula química", value=str(existing.get("formula_quimica") or ""))
        fonte = c5.text_input("Fonte", value=str(existing.get("fonte") or ""))
        price = c6.text_input(
            "Preço padrão (R$/kg)",
            value=_text_number(existing.get("preco_padrao")),
            placeholder="Opcional",
        )
        quality = st.text_area(
            "Observação sobre a qualidade dos dados",
            value=str(existing.get("qualidade_dados") or ""),
            placeholder="Ex.: NDT precisa ser revisado; valor proveniente de tabela antiga.",
        )
        active = st.checkbox("Ativo", value=as_bool(existing.get("ativo"), True))

        st.markdown("**Composição nutricional**")
        st.caption("Deixe vazio quando o valor for desconhecido. Não use zero para representar dado ausente.")
        values: dict[str, Any] = {}
        groups: dict[str, list] = {}
        for nutrient in NUTRIENTS:
            groups.setdefault(nutrient.group, []).append(nutrient)
        for group, nutrients in groups.items():
            with st.expander(group, expanded=group == "Macronutrientes"):
                cols = st.columns(4)
                for idx, nutrient in enumerate(nutrients):
                    values[nutrient.code] = cols[idx % 4].text_input(
                        f"{nutrient.code} ({nutrient.unit})",
                        value=_text_number(existing.get(nutrient.code)),
                        key=f"{prefix}_{nutrient.code}",
                    )

        submit = st.form_submit_button("Salvar ingrediente", type="primary")
    if not submit:
        return None
    if not nome.strip():
        st.error("O nome é obrigatório.")
        return None
    parsed_price = as_float(price)
    if price.strip() and parsed_price is None:
        st.error("O preço padrão não é válido.")
        return None
    payload: dict[str, Any] = {
        "ingredient_id": existing.get("ingredient_id") or new_id("ing"),
        "tipo": tipo,
        "nome": nome.strip(),
        "classificacao": classificacao.strip(),
        "formula_quimica": formula.strip(),
        "fonte": fonte.strip(),
        "preco_padrao": parsed_price,
        "ativo": active,
        "qualidade_dados": quality.strip(),
        "created_by": existing.get("created_by", ""),
        "created_at": existing.get("created_at", ""),
    }
    invalid = []
    for code, raw in values.items():
        parsed = as_float(raw)
        if raw.strip() and parsed is None:
            invalid.append(code)
        payload[code] = parsed
    if invalid:
        st.error("Valores nutricionais inválidos: " + ", ".join(invalid) + ".")
        return None
    return payload


def _bulk_import(repository: Repository, ingredients: pd.DataFrame, user: User) -> None:
    st.write("O arquivo pode usar os cabeçalhos do WebApp ou os cabeçalhos da planilha original.")
    uploaded = st.file_uploader("Arquivo CSV", type=["csv"])
    update_existing = st.checkbox("Atualizar registros com mesmo tipo e nome", value=False)
    if uploaded is None:
        return
    try:
        frame = pd.read_csv(uploaded, sep=None, engine="python")
    except Exception as exc:
        st.error(f"Não foi possível ler o CSV: {exc}")
        return
    frame = _normalize_import_columns(frame)
    st.dataframe(frame.head(20), hide_index=True, width="stretch")
    if not {"tipo", "nome"}.issubset(frame.columns):
        st.error("O CSV deve conter as colunas Tipo e Nome/Ingredientes.")
        return
    if st.button("Importar registros", type="primary"):
        created = 0
        updated = 0
        skipped = 0
        for _, row in frame.iterrows():
            tipo = str(row.get("tipo") or "").strip()
            nome = str(row.get("nome") or "").strip()
            if not tipo or not nome:
                skipped += 1
                continue
            duplicate = _find_duplicate(ingredients, tipo, nome)
            if duplicate is not None and not update_existing:
                skipped += 1
                continue
            payload = {col: row.get(col, "") for col in INGREDIENT_COLUMNS}
            payload["ingredient_id"] = (
                duplicate.get("ingredient_id") if duplicate is not None else new_id("ing")
            )
            payload["tipo"] = tipo
            payload["nome"] = nome
            payload["ativo"] = as_bool(row.get("ativo"), True)
            for nutrient in NUTRIENTS:
                payload[nutrient.code] = as_float(row.get(nutrient.code))
            payload["preco_padrao"] = as_float(row.get("preco_padrao"))
            repository.upsert_ingredient(payload, actor=user.email)
            if duplicate is None:
                created += 1
            else:
                updated += 1
        st.success(f"Importação concluída: {created} criados, {updated} atualizados e {skipped} ignorados.")
        st.rerun()


def _normalize_import_columns(frame: pd.DataFrame) -> pd.DataFrame:
    mapping = {
        "Tipo": "tipo",
        "Ingredientes": "nome",
        "Ingrediente": "nome",
        "Nome": "nome",
        "Classificação": "classificacao",
        "Classificacao": "classificacao",
        "Fórmula": "formula_quimica",
        "Formula": "formula_quimica",
        "Fonte": "fonte",
        "R$": "preco_padrao",
        "Preço": "preco_padrao",
        "Preco": "preco_padrao",
        "Ativo": "ativo",
    }
    renamed = frame.rename(columns={col: mapping.get(str(col).strip(), str(col).strip()) for col in frame.columns})
    nutrient_mapping = {nutrient.code.lower(): nutrient.code for nutrient in NUTRIENTS}
    renamed = renamed.rename(
        columns={col: nutrient_mapping.get(str(col).strip().lower(), col) for col in renamed.columns}
    )
    return renamed


def _find_duplicate(
    ingredients: pd.DataFrame,
    tipo: str,
    nome: str,
    ignore_id: str = "",
) -> dict[str, Any] | None:
    if ingredients.empty:
        return None
    mask = ingredients["tipo"].map(normalize_text).eq(normalize_text(tipo))
    mask &= ingredients["nome"].map(normalize_text).eq(normalize_text(nome))
    if ignore_id:
        mask &= ~ingredients["ingredient_id"].astype(str).eq(str(ignore_id))
    if not mask.any():
        return None
    return ingredients.loc[mask].iloc[0].to_dict()


def _text_number(value: Any) -> str:
    parsed = as_float(value)
    if parsed is None:
        return ""
    return f"{parsed:g}".replace(".", ",")
