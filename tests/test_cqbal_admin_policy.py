import json
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.cqbal_catalog import DEFAULT_CODES, FIELDS, default_policy
from src.cqbal_import import (parse_json_report, parse_html_report, convert_report,
                              convert_configured_report, configured_provenance)
from src.models import User
from src.nutrients import available_nutrient_codes, synchronize_constraints
from src.repositories.local import LocalRepository
from src.solver import solve_least_cost

FIXTURE = Path(__file__).parent / 'fixtures' / 'cqbal' / 'milho_fuba.json'
HTML = Path(__file__).parents[1] / 'src' / 'data' / 'milho_fuba_referencia.html'
ADMIN = User('admin', 'admin@local', 'Administrador', 'Administrador')


def policy(*codes):
    return dict(version=1, selected=list(codes), updated_by=ADMIN.email, updated_at='agora')


def test_default_and_json_html_match_legacy():
    report = parse_json_report(FIXTURE.read_bytes())
    html_report = parse_html_report(HTML.read_bytes())
    legacy = convert_report(report, '%')
    new = convert_configured_report(report, '%', default_policy())
    from_html = convert_configured_report(html_report, '%', default_policy())
    assert new[0] == legacy[0] == from_html[0]
    assert new[2] == legacy[2] == from_html[2]
    assert len(new[0]) == 44
    assert report.name == html_report.name == 'MILHO FUBÁ'


def test_selection_zero_and_disabled_fields_preserved(tmp_path):
    repo = LocalRepository(tmp_path); repo.initialize()
    extra = 'CQB_178'  # FDNcp, distinto de FDN
    saved = repo.upsert_ingredient(dict(nome='Milho', tipo='Alimento', PB=99, FDN=88, preco_padrao=3), 'admin')
    p = repo.save_cqbal_import_policy(['MS', extra, 'Gln'], ADMIN, 0)
    values, rows, missing, attributes = convert_configured_report(parse_json_report(FIXTURE.read_bytes()), '%', p)
    assert 'PB' not in values and 'FDN' not in values
    assert values[extra] > 0 and values['Gln'] == 0 and 'Gln' in missing
    assert any(row['campo_base'] == 'PB' and row['tratamento'].startswith('Não selecionado') for row in rows)
    saved.update(values)
    repo.upsert_ingredient(saved, ADMIN.email)
    item = repo.list_ingredients().iloc[0]
    assert float(item['PB']) == 99 and float(item['FDN']) == 88 and float(item['preco_padrao']) == 3
    assert float(item[extra]) == values[extra]
    assert LocalRepository(tmp_path).get_cqbal_import_policy() == p


@pytest.mark.parametrize('role,active', [('Formulador',True), ('Consulta',True), ('Administrador',False)])
def test_repository_rejects_non_admin_and_inactive(tmp_path, role, active):
    repo = LocalRepository(tmp_path); repo.initialize()
    with pytest.raises(PermissionError):
        repo.save_cqbal_import_policy(['MS'], User('u','u@local','U',role,active), 0)
    assert repo.get_cqbal_import_policy() == default_policy()


def test_policy_revision_fresh_sessions_and_audit(tmp_path):
    left, right = LocalRepository(tmp_path), LocalRepository(tmp_path)
    left.initialize()
    assert left.get_cqbal_import_policy() == right.get_cqbal_import_policy() == default_policy()
    updated = left.save_cqbal_import_policy(['MS', 'CQB_178'], ADMIN, 0)
    assert right.get_cqbal_import_policy() == updated
    with pytest.raises(ValueError, match='outro administrador'):
        right.save_cqbal_import_policy(['PB'], ADMIN, 0)
    with pytest.raises(ValueError, match='inválida'):
        right.save_cqbal_import_policy(['FALSO'], ADMIN, 1)
    audit = left.list_audit()
    assert audit.iloc[0]['entidade'] == 'cqbal_importacao'
    assert 'CQB_178' in str(audit.iloc[0]['detalhes'])


def test_google_policy_is_shared_fresh_and_does_not_touch_ingredients():
    from test_cqbal_storage import Sheet
    from src.config import TABLE_SCHEMAS
    from src.repositories.google_sheets import GoogleSheetsRepository
    sheets = {name: Sheet(columns) for name, columns in TABLE_SCHEMAS.items()}
    for sheet in sheets.values():
        sheet.resize = lambda **kwargs: None
    def repository():
        repo=GoogleSheetsRepository.__new__(GoogleSheetsRepository)
        repo._cache={}; repo.cache_ttl_seconds=60
        repo._worksheet=lambda name:sheets[name]
        repo._call=lambda operation:operation()
        return repo
    left,right=repository(),repository()
    assert right.get_cqbal_import_policy()['version']==0
    saved=left.save_cqbal_import_policy(['MS','CQB_178'],ADMIN,0)
    assert right.get_cqbal_import_policy()==saved
    assert sheets['ingredientes'].clears==0 and len(sheets['ingredientes'].values)==1
    assert len(sheets['auditoria'].values)==2


def test_new_field_import_solve_save_and_reload(tmp_path):
    code = 'CQB_178'
    report = parse_json_report(FIXTURE.read_bytes())
    values, _, _, _ = convert_configured_report(report, '%', policy('MS',code))
    repo = LocalRepository(tmp_path); repo.initialize()
    item = repo.upsert_ingredient(dict(nome=report.name,tipo='Alimento',preco_padrao=2,**values), ADMIN.email)
    work = pd.DataFrame([dict(item,preco_kg=2,inclusao_min=0,inclusao_max=100)])
    assert code in available_nutrient_codes(work)
    limits = synchronize_constraints(pd.DataFrame([dict(nutriente=code,minimo=values[code]-.1,maximo=values[code]+.1)]),work)
    result = solve_least_cost(work,limits)
    assert result.success, result.message
    assert result.constraints.set_index('nutriente').loc[code,'resultado'] == pytest.approx(values[code])
    diet_id = repo.save_diet(dict(nome='CQBAL extra'), result.items, result.constraints, ADMIN.email)
    loaded = LocalRepository(tmp_path).get_diet(diet_id)
    assert float(loaded['items'].iloc[0][code]) == values[code]
    assert code in loaded['constraints']['nutriente'].tolist()


def test_full_catalog_fits_storage_and_preserves_unselected_attributes():
    report = parse_json_report(FIXTURE.read_bytes())
    all_policy = policy(*FIELDS)
    source = configured_provenance(report, '%', 'completo.json', all_policy)
    assert len(source) < 45000
    doc = json.loads(source)
    assert len(doc['atributos_importados']) == len(FIELDS)
    assert len(doc['registros']) == len(report.records)
    # pH é preservado, mas não recebe um cálculo linear incorreto.
    ph = next(code for code, field in FIELDS.items() if field['reference'] and field['reference']['sigla']=='pH')
    values, _, _, attrs = convert_configured_report(report, '%', all_policy)
    assert ph in attrs and ph not in values
    new = json.loads(configured_provenance(report, '%', 'novo.json', policy('MS'), source))
    assert ph in new['atributos_preservados'] and 'MS' not in new['atributos_preservados']


def test_html_alias_ambiguity_requires_json_instead_of_wrong_zero():
    report = parse_html_report(HTML.read_bytes())
    with pytest.raises(ValueError, match='ambígua'):
        convert_configured_report(report, '%', policy(*FIELDS))


def test_admin_panel_guards_and_renders_reference():
    app = AppTest.from_string('''from src.pages.cqbal_admin import render
from src.models import User
render(None, User('u','u@local','U','Formulador'))
''').run()
    assert not app.exception and app.error and not app.button


def test_admin_panel_saves_default_restore(tmp_path):
    repo = LocalRepository(tmp_path); repo.initialize()
    repo.save_cqbal_import_policy(['MS','CQB_178'],ADMIN,0)
    app = AppTest.from_string(f'''from src.pages.cqbal_admin import render
from src.models import User
from src.repositories.local import LocalRepository
repo=LocalRepository({str(tmp_path)!r})
repo.initialize()
render(repo, User('admin','admin@local','Admin','Administrador'))
''').run()
    assert not app.exception and app.dataframe
    assert any('Milho Fubá' in text.value for text in app.markdown)
    next(button for button in app.button if button.label=='Restaurar seleção padrão do RFB').click().run()
    assert not app.exception
    assert repo.get_cqbal_import_policy()['selected'] == list(DEFAULT_CODES)


def test_panel_checkbox_then_importer_and_solver_field(tmp_path):
    repo = LocalRepository(tmp_path); repo.initialize()
    source = f'''from src.pages.cqbal_admin import render
from src.models import User
from src.repositories.local import LocalRepository
repo=LocalRepository({str(tmp_path)!r})
repo.initialize()
render(repo, User('admin','admin@local','Admin','Administrador'))
'''
    app = AppTest.from_string(source).run()
    index = list(FIELDS).index('CQB_178')
    app.session_state['cqbal_policy_editor_0'] = dict(edited_rows={index: {'Importar':True}}, added_rows=[], deleted_rows=[])
    next(b for b in app.button if b.label=='Salvar configuração de importação').click().run()
    assert not app.exception and not app.error
    assert 'CQB_178' in repo.get_cqbal_import_policy()['selected']
    # Exercita a tela com o JSON real e um formulador, que usa a política mas não a altera.
    source = f'''from types import SimpleNamespace
from pathlib import Path
import src.pages.cqbal as page
from src.models import User
from src.repositories.local import LocalRepository
page.st.file_uploader=lambda *a,**k: SimpleNamespace(getvalue=lambda:Path({str(FIXTURE)!r}).read_bytes(),name='completo.json')
repo=LocalRepository({str(tmp_path)!r})
repo.initialize()
page.render(repo,User('f','formulador@local','Formulador','Formulador'))
'''
    from unittest.mock import patch
    import streamlit as st
    with patch.object(st,'file_uploader',st.file_uploader):
        app=AppTest.from_string(source).run()
        app.selectbox[0].select('%').run()
        assert not app.exception and not app.error
        app.checkbox[0].check().run()
        next(b for b in app.button if b.label=='Salvar ingrediente importado').click().run()
        assert not app.exception and not app.error
    saved=repo.list_ingredients().iloc[0]
    assert float(saved['CQB_178']) > 0
    assert json.loads(saved['cqbal_dados'])['configuracao_importacao']['version'] == 1
