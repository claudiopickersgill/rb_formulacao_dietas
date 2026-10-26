"""Configuração global de importação CQBAL, exclusiva de administradores."""
from pathlib import Path
import pandas as pd
import streamlit as st

from ..cqbal_catalog import CATALOG, FIELDS, DEFAULT_CODES


def render(repository, user):
    if not user.is_admin or not user.ativo:
        st.error('Apenas administradores ativos podem acessar o Painel de Importação CQBAL.')
        return
    st.subheader('Painel de Importação CQBAL')
    st.write('Escolha os atributos para as próximas importações de todos os alimentos. '
             'Os campos já usados pelo RFB vêm marcados por padrão.')
    st.caption('Marcado e ausente no relatório: importar zero. Desmarcado: não importar e preservar o valor '
               'existente em atualizações. Cadastros e dietas anteriores não são recalculados.')
    try:
        policy = repository.get_cqbal_import_policy()
    except Exception as exc:
        st.error('Não foi possível ler a configuração CQBAL: ' + str(exc))
        return
    flash = st.session_state.pop('cqbal_policy_flash', None)
    if flash:
        st.success(flash)
    a, b, c = st.columns(3)
    a.metric('Atributos no catálogo', len(FIELDS))
    b.metric('Selecionados', len(policy['selected']))
    c.metric('Versão da configuração', policy['version'])
    st.write('**Referência para conferência: Milho Fubá — ID 1.** '
             'O catálogo também inclui atributos encontrados nos demais alimentos.')
    st.caption(f"Catálogo construído a partir de {CATALOG['reports_scanned']} relatórios completos. "
               'O valor no Milho Fubá é apenas referência; nunca preenche outro alimento.')
    reference = Path(__file__).parents[1] / 'data' / 'milho_fuba_referencia.html'
    if reference.exists():
        st.download_button('Baixar HTML do Milho Fubá para conferência', reference.read_bytes(),
                           file_name='milho_fuba_referencia.html', mime='text/html', key='cqbal_reference')
    st.info('Teores compatíveis com a mistura linear ficam disponíveis como restrições após serem importados. '
            'Razões, taxas, pH e campos com unidade ainda não validada podem ser importados para conferência; '
            'a coluna “Uso na formulação” identifica os que exigem um modelo próprio.')
    rows = []
    for code, field in FIELDS.items():
        ref = field['reference'] or {}
        rows.append({'Importar': code in policy['selected'], 'Código': code, 'Atributo': field['label'],
                     'Siglas CQBAL': ' | '.join(dict.fromkeys(alias for _, alias in field['aliases'])),
                     'Grupo': field['group'], 'Unidade destino': field['unit'],
                     'No Milho Fubá': field['reference'] is not None, 'Valor de referência': ref.get('media'),
                     'Uso na formulação': 'Restrição' if field['formula'] else 'Modelo específico necessário',
                     'Tratamento': field['note']})
    with st.form('cqbal_policy_form'):
        edited = st.data_editor(pd.DataFrame(rows), hide_index=True, width='stretch', height=620,
                                disabled=[key for key in rows[0] if key != 'Importar'],
                                key=f"cqbal_policy_editor_{policy['version']}",
                                column_config={'Importar': st.column_config.CheckboxColumn('Importar', required=True),
                                               'Valor de referência': st.column_config.NumberColumn(format='%.6f')})
        saved = st.form_submit_button('Salvar configuração de importação', type='primary')
    if saved:
        selected = edited.loc[edited['Importar'].eq(True), 'Código'].tolist()
        try:
            new_policy = repository.save_cqbal_import_policy(selected, user, policy['version'])
        except Exception as exc:
            st.error('Não foi possível salvar: ' + str(exc))
        else:
            st.session_state['cqbal_policy_flash'] = f"Configuração salva (versão {new_policy['version']}). Válida para as próximas importações."
            st.rerun()
    if st.button('Restaurar seleção padrão do RFB', key='cqbal_restore_defaults'):
        try:
            repository.save_cqbal_import_policy(list(DEFAULT_CODES), user, policy['version'])
        except Exception as exc:
            st.error('Não foi possível restaurar: ' + str(exc))
        else:
            st.session_state['cqbal_policy_flash'] = 'Seleção padrão restaurada.'
            st.rerun()
    if policy['updated_by']:
        st.caption(f"Última alteração: {policy['updated_by']} · {policy['updated_at']}")
