from __future__ import annotations

import hashlib
import json
import pandas as pd
import streamlit as st

from ..cqbal_import import parse_uploaded_report, convert_configured_report, configured_provenance
from ..models import User
from ..repositories.base import Repository
from ..utils import as_bool, new_id, normalize_text, local_now_iso


def render(repository: Repository, user: User) -> None:
    if not user.can_edit:
        return
    st.write('Importe um alimento por vez usando o JSON completo, HTML de conferência ou PDF digital do CQBAL, em português ou inglês.')
    st.caption('Atributos definidos em Administração → Painel de Importação CQBAL. JSON é o formato preferencial; campos selecionados e ausentes recebem zero.')
    uploaded = st.file_uploader('Relatório Completo CQBAL (JSON, HTML ou PDF, até 10 MB)', type=['json', 'html', 'htm', 'pdf'], key='cqbal_pdf')
    if uploaded is None:
        return
    content = uploaded.getvalue()
    digest = hashlib.sha256(content).hexdigest()
    try:
        policy = repository.get_cqbal_import_policy()
    except Exception as exc:
        st.error('Não foi possível ler a configuração CQBAL: ' + str(exc))
        return
    if not policy['selected']:
        st.info('Nenhum atributo está habilitado. Solicite a configuração ao administrador.')
        return
    prefix = 'cqbal_' + digest[:16] + '_v' + str(policy['version'])
    st.caption(f"Configuração global: versão {policy['version']} · {len(policy['selected'])} atributos selecionados.")
    try:
        # Reutiliza somente a extração deste arquivo, sem repetir a leitura a cada widget.
        if st.session_state.get('cqbal_report_hash') != digest:
            st.session_state['cqbal_report'] = parse_uploaded_report(content, uploaded.name)
            st.session_state['cqbal_report_hash'] = digest
        report = st.session_state['cqbal_report']
    except Exception as exc:
        st.error(str(exc))
        return
    st.write(f'Alimento no relatório: **{report.name}**. Categoria: **{report.category}**.')
    st.caption('Idioma identificado: ' + {'pt': 'Português', 'en': 'Inglês'}.get(report.language, report.language)
               + '. A tradução das siglas não altera os valores nem define as unidades.')
    macro_unit = st.selectbox('Unidade de origem dos macrominerais neste relatório',
                              ['Confirmar unidade', '%', 'g/kg'], key=prefix+'_unit')
    if macro_unit == 'Confirmar unidade':
        st.info('Confirme a unidade dos macrominerais para gerar a prévia de conversão.')
        return
    st.info('Aminoácidos: % do alimento, não % da proteína bruta. Energia metabolizável: origem Mcal/kg e destino kcal/g (1 Mcal/kg = 1 kcal/g), '
            'somente EM_BRCORTE2016 / ME_BRCORTE2016. Use a mesma base de expressão dos demais nutrientes. '
            'Se a fonte usar outras unidades, converta antes do cadastro manual.')
    try:
        values, preview, missing, attributes = convert_configured_report(report, macro_unit, policy)
        provenance = configured_provenance(report, macro_unit, uploaded.name, policy)
    except ValueError as exc:
        st.error(str(exc))
        return
    st.subheader('Conferir importação')
    st.dataframe(pd.DataFrame(preview), hide_index=True, width='stretch', column_config={
        'valor_na_base': st.column_config.NumberColumn('Valor na base', format='%.8f'),
        'unidade_destino': 'Unidade na base',
        'media_original': st.column_config.NumberColumn('Média no relatório', format='%.6f'),
    })
    st.download_button('Baixar todos os dados e procedência (JSON)', provenance.encode('utf-8'),
                       file_name='cqbal_composicao.json', mime='application/json', key=prefix+'_download')
    if missing:
        st.warning('Sem informação importável, serão preenchidos com zero: ' + ', '.join(missing))
    name = st.text_input('Nome na nossa base', report.name, key=prefix+'_name').strip()
    default_type = 'Mineral' if report.category in {'MINERAIS', 'FONTES DE MINERAIS'} else 'Alimento'
    kind = st.selectbox('Tipo do ingrediente', ['Alimento', 'Mineral'],
                        index=1 if default_type == 'Mineral' else 0, key=prefix+'_type')
    classification = st.text_input('Classificação', report.category, key=prefix+'_class')
    confirmed = st.checkbox('Conferi os valores, minerais, aminoácidos em % do alimento, EM convertida de Mcal/kg para kcal/g e a base de expressão.',
                             key=prefix+'_confirmed')
    mode = st.radio('Gravação', ['Cadastrar novo', 'Atualizar cadastro existente'], key=prefix+'_mode')
    # A escolha de atualização é por ID; não há correspondência automática por texto aproximado.
    ingredients = repository.list_ingredients(active_only=False)
    existing = None
    if mode == 'Atualizar cadastro existente':
        ids = ingredients['ingredient_id'].astype(str).tolist() if not ingredients.empty else []
        if not ids:
            st.info('Não há cadastro para atualizar.')
            return
        labels = {str(r['ingredient_id']): f"{r['nome']} · {r['ingredient_id']}" for _, r in ingredients.iterrows()}
        selected = st.selectbox('Cadastro que será atualizado', ids, format_func=lambda x: labels[x], key=prefix+'_target')
        existing = ingredients.loc[ingredients['ingredient_id'].astype(str).eq(selected)].iloc[0].to_dict()
        st.warning('Somente os atributos selecionados serão atualizados; ausentes recebem zero. Atributos desmarcados mantêm seus valores anteriores.')
        overwrite = st.checkbox('Confirmo substituir a composição do cadastro selecionado.', key=prefix+'_overwrite')
    else:
        overwrite = True
    if st.session_state.get(prefix+'_saved'):
        st.success('Este relatório já foi importado nesta sessão com esta configuração. Consulte o cadastro antes de repetir a importação.')
        return
    if st.button('Salvar ingrediente importado', type='primary', disabled=not(confirmed and overwrite and name), key=prefix+'_save'):
        try:
            fresh_policy = repository.get_cqbal_import_policy()
            if fresh_policy != policy:
                st.error('O administrador alterou a configuração. Recarregue e confira a nova prévia antes de salvar.')
                return
            provenance = configured_provenance(report, macro_unit, uploaded.name, policy,
                                               (existing or {}).get('cqbal_dados'))
        except Exception as exc:
            st.error('Não foi possível preparar a importação: ' + str(exc))
            return
        payload = dict(existing or {})
        payload.update(values)
        payload.update(ingredient_id=(existing or {}).get('ingredient_id') or new_id('ing'),
                       tipo=kind, nome=name, classificacao=classification, fonte='CQBAL — ' + report.name,
                       ativo=as_bool((existing or {}).get('ativo'), True), cqbal_dados=provenance,
                       qualidade_dados=('CQBAL: composição parcial; preenchidos com zero por ausência de informação: ' + ', '.join(missing)) if missing else '')
        payload['observacoes'] = '\n'.join(filter(None, [str((existing or {}).get('observacoes') or ''),
            f'CQBAL importado em {local_now_iso()}; configuração v{policy["version"]}; arquivo {uploaded.name}; idioma {report.language}; '
            f'{len(policy["selected"])} atributos selecionados; macro origem {macro_unit}; '
            f'unidades e tratamentos por atributo na prévia e no catálogo CQBAL; SHA256 {digest}.']))
        if len(payload['observacoes']) > 45000:
            st.error('Histórico excede o limite de uma célula do Google.')
            return
        try:
            repository.upsert_ingredient(payload, actor=user.email)
            if hasattr(repository, 'clear_cache'):
                repository.clear_cache()
            readback = repository.list_ingredients(active_only=False)
            match = readback.loc[readback['ingredient_id'].astype(str).eq(str(payload['ingredient_id']))]
            if len(match) != 1 or str(match.iloc[0].get('cqbal_dados')) != provenance:
                raise RuntimeError('A confirmação de gravação não corresponde ao arquivo importado. Confira o cadastro antes de repetir.')
        except Exception as exc:
            st.error('Não foi possível confirmar a importação: ' + str(exc))
            return
        st.session_state[prefix+'_saved'] = True
        st.session_state['ingredient_flash'] = f'Ingrediente {name} importado e conferido na base.'
        st.rerun()
