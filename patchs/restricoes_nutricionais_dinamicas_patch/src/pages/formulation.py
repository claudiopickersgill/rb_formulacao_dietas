from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from ..config import NUTRIENT_BY_CODE, NUTRIENT_CODES
from ..diet_loading import calculation_fingerprint, normalize_loaded_constraints, normalize_loaded_items
from ..exports import export_filenames, make_csv_bytes, make_excel_bytes, make_pdf_bytes
from ..models import SolverResult, User
from ..nutrients import available_nutrient_codes, synchronize_constraints
from ..repositories.base import Repository
from ..result_analysis import nutrient_result_display
from ..solver import solve_least_cost
from ..ui_helpers import page_header
from ..utils import as_bool, as_float, format_brl, new_id

PREFIX = "frm_"
EDITABLE_COLUMNS = [
    "ingredient_id",
    "nome",
    "tipo",
    "classificacao",
    "sem_custo",
    "preco_kg",
    "inclusao_min",
    "inclusao_max",
]

# O st.data_editor guarda as alterações do usuário internamente.  Por isso, a
# entrada ``data=`` de cada editor deve permanecer estável enquanto ele estiver
# sendo preenchido.  Se realimentarmos o widget a cada rerun com o DataFrame que
# acabou de ser retornado, Enter/Tab pode reconstruir o editor a partir de um
# estado intermediário e aparentar desfazer a última edição.
ITEMS_EDITOR_BASE_KEY = PREFIX + "items_editor_base"
ITEMS_EDITOR_SELECTION_KEY = PREFIX + "items_editor_selection"
ITEMS_EDITOR_REVISION_KEY = PREFIX + "items_editor_revision"
CONSTRAINTS_EDITOR_BASE_KEY = PREFIX + "constraints_editor_base"
CONSTRAINTS_EDITOR_REVISION_KEY = PREFIX + "constraints_editor_revision"


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

    _sync_dynamic_constraints(full_items)

    has_previous_result = isinstance(st.session_state.get(PREFIX + "result"), SolverResult)
    calculate_label = "Recalcular dieta" if has_previous_result else "Calcular dieta"

    # Preços, limites, restrições e o comando de cálculo precisam chegar ao
    # backend de forma atômica. Dentro de um form, Enter/Tab apenas edita a
    # grade; os valores são enviados juntos quando o usuário clica em
    # "Calcular dieta". Isso evita que o clique seja consumido apenas para
    # confirmar a última célula ativa do st.data_editor.
    with st.form(
        key=PREFIX + "calculation_form",
        clear_on_submit=False,
        enter_to_submit=False,
        border=False,
    ):
        if full_items.empty:
            st.info("Selecione os ingredientes que poderão participar da mistura.")
            edited = pd.DataFrame(columns=EDITABLE_COLUMNS)
        else:
            editable, items_editor_key = _items_editor_input(full_items, selected_ids)
            edited = st.data_editor(
                editable,
                hide_index=True,
                width="stretch",
                num_rows="fixed",
                key=items_editor_key,
                column_config={
                    "ingredient_id": None,
                    "nome": st.column_config.TextColumn("Ingrediente", disabled=True, width="large"),
                    "tipo": st.column_config.TextColumn("Tipo", disabled=True),
                    "classificacao": st.column_config.TextColumn("Classificação", disabled=True),
                    "sem_custo": st.column_config.CheckboxColumn(
                        "Sem custo",
                        help="Marque apenas quando o ingrediente realmente não tiver custo para a dieta.",
                        default=False,
                    ),
                    "preco_kg": st.column_config.NumberColumn(
                        "Preço (R$/kg)", min_value=0.0, step=0.01, format="R$ %.4f"
                    ),
                    "inclusao_min": st.column_config.NumberColumn(
                        "Mínimo (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.3f"
                    ),
                    "inclusao_max": st.column_config.NumberColumn(
                        "Máximo (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.3f"
                    ),
                },
            )
            st.caption(
                "Preço zero só é aceito quando **Sem custo** estiver marcado. "
                "Caso contrário, o cálculo será bloqueado para evitar preço esquecido."
            )

        with st.expander("Conferir composição nutricional carregada", expanded=False):
            preview_columns = [
                "nome",
                *[code for code in available_nutrient_codes(full_items) if code in full_items.columns],
            ]
            if full_items.empty:
                st.caption("Selecione ingredientes para visualizar a composição enviada ao cálculo.")
            else:
                st.dataframe(
                    full_items[preview_columns],
                    hide_index=True,
                    width="stretch",
                )
                st.caption(
                    "Estes valores vêm do cadastro em rb_ingredientes e são os valores "
                    "nutricionais que serão usados pelo solver."
                )

        st.subheader("Restrições nutricionais")
        constraints_input, constraints_editor_key = _constraints_editor_input()
        if constraints_input.empty:
            st.info("Selecione ingredientes com composição nutricional cadastrada para definir restrições.")
            constraints = constraints_input.copy()
        else:
            constraints = st.data_editor(
                constraints_input,
                hide_index=True,
                width="stretch",
                num_rows="fixed",
                key=constraints_editor_key,
                column_config={
                    "nutriente": st.column_config.TextColumn(
                        "Nutriente", disabled=True, width="medium"
                    ),
                    "minimo": st.column_config.NumberColumn("Mínimo", step=0.01, format="%.4f"),
                    "maximo": st.column_config.NumberColumn("Máximo", step=0.01, format="%.4f"),
                },
            )

        st.caption(
            "A lista é montada automaticamente com os nutrientes presentes nos ingredientes selecionados. "
            "Preencha mínimo e/ou máximo para **ativar uma restrição**; deixe ambos vazios para apenas "
            "calcular o teor final do nutriente. Os valores são enviados juntos ao clicar em **Calcular dieta**."
        )

        b1, b2, b3 = st.columns([1, 1, 3])
        with b1:
            calculate = st.form_submit_button(
                calculate_label,
                type="primary",
                width="stretch",
                disabled=full_items.empty,
            )
        with b2:
            clear = st.form_submit_button("Limpar", width="stretch")

    # "Limpar" tem prioridade: não reaplicamos os valores que acabaram de ser
    # submetidos antes de apagar a formulação.
    if clear:
        _reset_form()
        st.rerun()

    if not full_items.empty:
        full_items = _apply_edits(full_items, edited)
        st.session_state[PREFIX + "items_full"] = full_items

    constraints = constraints[["nutriente", "minimo", "maximo"]].copy().reset_index(drop=True)
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

    current_fingerprint = calculation_fingerprint(full_items, constraints)

    if calculate:
        # Feedback imediato para deixar claro que o submit foi recebido.
        with st.spinner("Calculando a solução de menor custo..."):
            try:
                result = solve_least_cost(full_items, constraints)
            except Exception as exc:  # proteção final da interface
                result = SolverResult(
                    success=False,
                    status="erro_calculo",
                    message="O cálculo não pôde ser concluído.",
                    diagnostics=[f"{type(exc).__name__}: {exc}"],
                )
        st.session_state[PREFIX + "result"] = result
        st.session_state[PREFIX + "result_fingerprint"] = current_fingerprint

    result: SolverResult | None = st.session_state.get(PREFIX + "result")
    if result is not None:
        is_current = st.session_state.get(PREFIX + "result_fingerprint") == current_fingerprint
        _render_result(repository, user, result, is_current, current_fingerprint)


def _sync_dynamic_constraints(full_items: pd.DataFrame) -> None:
    """Keep the restriction grid aligned with nutrients in selected ingredients."""
    current = st.session_state.get(PREFIX + "constraints")
    synced = synchronize_constraints(current, full_items)

    current_codes = (
        []
        if not isinstance(current, pd.DataFrame) or current.empty or "nutriente" not in current.columns
        else current["nutriente"].astype(str).tolist()
    )
    synced_codes = synced["nutriente"].astype(str).tolist() if not synced.empty else []

    if not isinstance(current, pd.DataFrame) or current_codes != synced_codes:
        st.session_state[PREFIX + "constraints"] = synced
        st.session_state.pop(CONSTRAINTS_EDITOR_BASE_KEY, None)
        st.session_state[CONSTRAINTS_EDITOR_REVISION_KEY] = (
            int(st.session_state.get(CONSTRAINTS_EDITOR_REVISION_KEY, 0)) + 1
        )
    elif PREFIX + "constraints" not in st.session_state:
        st.session_state[PREFIX + "constraints"] = synced


def _items_editor_input(
    full_items: pd.DataFrame, selected_ids: list[str]
) -> tuple[pd.DataFrame, str]:
    """Retorna uma entrada estável para o editor de ingredientes.

    A base só é reconstruída quando a lista de ingredientes selecionados muda.
    Alterações de preço/mínimo/máximo ficam no estado interno do ``data_editor``
    e no ``items_full``; elas não alteram ``data=`` a cada rerun.
    """

    selection = tuple(str(value) for value in selected_ids)
    previous_selection = tuple(st.session_state.get(ITEMS_EDITOR_SELECTION_KEY, ()))
    base = st.session_state.get(ITEMS_EDITOR_BASE_KEY)

    needs_rebuild = (
        not isinstance(base, pd.DataFrame)
        or previous_selection != selection
        or list(base.columns) != EDITABLE_COLUMNS
    )
    if needs_rebuild:
        st.session_state[ITEMS_EDITOR_BASE_KEY] = (
            full_items[EDITABLE_COLUMNS].copy().reset_index(drop=True)
        )
        st.session_state[ITEMS_EDITOR_SELECTION_KEY] = selection
        st.session_state[ITEMS_EDITOR_REVISION_KEY] = (
            int(st.session_state.get(ITEMS_EDITOR_REVISION_KEY, 0)) + 1
        )

    revision = int(st.session_state.get(ITEMS_EDITOR_REVISION_KEY, 1))
    editor_key = f"{PREFIX}items_editor_{revision}"
    return st.session_state[ITEMS_EDITOR_BASE_KEY].copy(), editor_key


def _constraints_editor_input() -> tuple[pd.DataFrame, str]:
    """Retorna a base estável do editor de restrições nutricionais."""

    base = st.session_state.get(CONSTRAINTS_EDITOR_BASE_KEY)
    if not isinstance(base, pd.DataFrame):
        current = st.session_state[PREFIX + "constraints"]
        st.session_state[CONSTRAINTS_EDITOR_BASE_KEY] = (
            current[["nutriente", "minimo", "maximo"]].copy().reset_index(drop=True)
        )
        st.session_state[CONSTRAINTS_EDITOR_REVISION_KEY] = (
            int(st.session_state.get(CONSTRAINTS_EDITOR_REVISION_KEY, 0)) + 1
        )

    revision = int(st.session_state.get(CONSTRAINTS_EDITOR_REVISION_KEY, 1))
    editor_key = f"{PREFIX}constraints_editor_{revision}"
    return st.session_state[CONSTRAINTS_EDITOR_BASE_KEY].copy(), editor_key


def _invalidate_editor_bases() -> None:
    """Força reconstrução dos editores após carregar outra dieta."""

    for key in (
        ITEMS_EDITOR_BASE_KEY,
        ITEMS_EDITOR_SELECTION_KEY,
        CONSTRAINTS_EDITOR_BASE_KEY,
    ):
        st.session_state.pop(key, None)
    st.session_state[ITEMS_EDITOR_REVISION_KEY] = (
        int(st.session_state.get(ITEMS_EDITOR_REVISION_KEY, 0)) + 1
    )
    st.session_state[CONSTRAINTS_EDITOR_REVISION_KEY] = (
        int(st.session_state.get(CONSTRAINTS_EDITOR_REVISION_KEY, 0)) + 1
    )


def _merge_selected_items(selected_ids: list[str], catalog_index: pd.DataFrame) -> pd.DataFrame:
    """Monta a formulação sempre a partir do catálogo nutricional atual.

    O estado anterior é usado somente para campos específicos da formulação
    (preço e limites). A composição nutricional nunca é reaproveitada do
    ``session_state``. Isso evita que valores vazios antigos continuem sendo
    enviados ao solver depois que ``rb_ingredientes`` foi corrigida/backfilled.
    """

    previous = st.session_state.get(PREFIX + "items_full", pd.DataFrame())
    previous_map: dict[str, dict[str, Any]] = {}
    if isinstance(previous, pd.DataFrame) and not previous.empty:
        previous_map = {str(row["ingredient_id"]): row.to_dict() for _, row in previous.iterrows()}

    rows: list[dict[str, Any]] = []
    for ingredient_id in selected_ids:
        key = str(ingredient_id)
        catalog_row = catalog_index.loc[key]
        if isinstance(catalog_row, pd.DataFrame):
            catalog_row = catalog_row.iloc[0]

        # Sempre parte do registro atual do catálogo. Assim NDT, PB, FDN, FDA,
        # minerais etc. refletem a versão mais recente do Google Sheets.
        row = catalog_row.to_dict()
        row["ingredient_id"] = key

        previous_row = previous_map.get(key, {})

        row["sem_custo"] = as_bool(previous_row.get("sem_custo"), False)
        previous_price = as_float(previous_row.get("preco_kg"))
        row["preco_kg"] = (
            previous_price
            if previous_price is not None
            else as_float(row.get("preco_padrao"))
        )

        previous_min = as_float(previous_row.get("inclusao_min"))
        previous_max = as_float(previous_row.get("inclusao_max"))
        row["inclusao_min"] = 0.0 if previous_min is None else previous_min
        row["inclusao_max"] = 100.0 if previous_max is None else previous_max

        # Resultados anteriores podem permanecer para exibição até novo cálculo,
        # mas nunca sobrescrevem a composição do catálogo.
        row["inclusao_calculada"] = as_float(previous_row.get("inclusao_calculada"))
        row["custo_parcial"] = as_float(previous_row.get("custo_parcial"))
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
    if result.constraints.empty:
        attended = 0
        restricted_total = 0
    else:
        restricted_mask = result.constraints["minimo"].notna() | result.constraints["maximo"].notna()
        restricted_total = int(restricted_mask.sum())
        attended = int((restricted_mask & result.constraints["situacao"].eq("Atendida")).sum())
    m4.metric("Restrições atendidas", f"{attended}/{restricted_total}")

    tab1, tab2, tab3 = st.tabs(["Mistura", "Nutrientes", "Composição usada"])
    with tab1:
        mix = result.items.copy()
        if "sem_custo" not in mix.columns:
            mix["sem_custo"] = False
        display = mix[
            [
                "nome",
                "sem_custo",
                "preco_kg",
                "inclusao_min",
                "inclusao_max",
                "inclusao_calculada",
                "custo_parcial",
            ]
        ].copy()
        display = display[display["inclusao_calculada"] > 1e-9]
        st.dataframe(
            display,
            hide_index=True,
            width="stretch",
            column_config={
                "nome": "Ingrediente",
                "sem_custo": st.column_config.CheckboxColumn("Sem custo", disabled=True),
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
        nutrient_display = nutrient_result_display(result.constraints)
        no_limit = nutrient_display["situacao_visual"].eq("🟡 No limite").sum() if not nutrient_display.empty else 0
        near_limit = nutrient_display["situacao_visual"].eq("🟠 Próximo ao limite").sum() if not nutrient_display.empty else 0
        with_slack = nutrient_display["situacao_visual"].eq("🟢 Com folga").sum() if not nutrient_display.empty else 0
        outside = nutrient_display["situacao_visual"].eq("🔴 Fora do limite").sum() if not nutrient_display.empty else 0
        unrestricted = nutrient_display["situacao_visual"].eq("⚪ Sem restrição").sum() if not nutrient_display.empty else 0

        n1, n2, n3, n4, n5 = st.columns(5)
        n1.metric("No limite", int(no_limit))
        n2.metric("Próximos ao limite", int(near_limit))
        n3.metric("Com folga", int(with_slack))
        n4.metric("Sem restrição", int(unrestricted))
        n5.metric("Fora do limite", int(outside))

        attention = nutrient_display.loc[
            nutrient_display["situacao_visual"].isin(["🟡 No limite", "🟠 Próximo ao limite"]),
            "nutriente",
        ].astype(str).tolist()
        if attention:
            st.warning(
                "Atenção aos nutrientes com pouca margem: " + ", ".join(attention) + ". "
                "Pequenas alterações de preço, inclusão ou composição podem mudar a solução."
            )

        st.dataframe(
            nutrient_display,
            hide_index=True,
            width="stretch",
            column_config={
                "nutriente": "Código",
                "descricao": "Nutriente",
                "unidade": "Unidade",
                "minimo": st.column_config.NumberColumn("Mínimo", format="%.4f"),
                "resultado": st.column_config.NumberColumn("Resultado", format="%.4f"),
                "maximo": st.column_config.NumberColumn("Máximo", format="%.4f"),
                "limite_proximo": "Limite mais próximo",
                "margem_limite": st.column_config.NumberColumn("Margem", format="%.4f"),
                "situacao_visual": "Situação",
            },
        )
        st.caption(
            "Nutrientes sem mínimo e máximo continuam sendo calculados e aparecem como **Sem restrição**. "
            "Um nutriente restrito é marcado como **próximo ao limite** quando a margem até o limite mais próximo "
            "é de até 10% da faixa permitida. Quando há apenas um limite, usa-se 5% desse valor como referência."
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
    items = normalize_loaded_items(bundle["items"])
    constraints = normalize_loaded_constraints(bundle["constraints"])
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
    _invalidate_editor_bases()
    result = SolverResult(
        success=True,
        status="salva",
        message="Dieta carregada.",
        cost_per_kg=as_float(metadata.get("custo_kg")),
        items=items,
        constraints=constraints,
    )
    fingerprint = calculation_fingerprint(items, st.session_state[PREFIX + "constraints"])
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
