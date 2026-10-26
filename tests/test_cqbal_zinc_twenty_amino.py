from src.cqbal_catalog import DEFAULT_CODES
from io import BytesIO
import json
from pathlib import Path

import pandas as pd
import pdfplumber
import pytest
from streamlit.testing.v1 import AppTest

from src.config import AMINO_ACID_CODES, NUTRIENT_BY_CODE, NUTRIENT_CODES, TABLE_SCHEMAS
from src.cqbal_import import convert_report, parse_report_text, provenance_json
from src.diet_loading import normalize_loaded_constraints
from src.energy import em_to_kcal_per_g
from src.exports import make_pdf_bytes
from src.repositories.local import LocalRepository
from src.solver import solve_least_cost

FIXTURES = Path(__file__).parent / 'fixtures' / 'cqbal'
EXPECTED = {'Ala','Arg','Asn','Asp','Cys','Phe','Gly','Glu','Gln','His',
            'Ile','Leu','Lys','Met','Pro','Ser','Tyr','Thr','Trp','Val'}


def source(body):
    return parse_report_text('CQBAL 4.0\nENERGY CONCENTRATE\nwheat grain\nDerivatives\n'
                             + body + '\nEstimated Nutrients\nME_BRCORTE2016 3.21 1 -')


def test_wheat_reports_match_zinc_and_eighteen_amino_acids():
    reports = [parse_report_text((FIXTURES/f'wheat_{lang}.txt').read_text(encoding='utf-8'))
               for lang in ['pt','en']]
    left, _, missing = convert_report(reports[0], '%')
    right, rows, en_missing = convert_report(reports[1], '%')
    assert left == right and missing == en_missing
    assert len(left) == 44 and len(AMINO_ACID_CODES) == 20
    assert right['Zn'] == pytest.approx(64.47 / 10000)
    assert right['EM'] == 3.21
    assert right['Cys'] == .52 and right['Trp'] == .18
    assert right['Ala'] == .50 and right['Asp'] == .73
    assert right['Glu'] == 4.14 and right['Gly'] == .57
    assert right['Pro'] == 1.72 and right['Ser'] == .67
    assert right['Asn'] == right['Gln'] == 0
    assert set(missing) == {'NDT','Cl','S','Co','I','Se','Asn','Gln'}
    zinc = next(row for row in rows if row['nutriente_cqbal'] == 'ZINC')
    assert zinc['campo_base'] == 'Zn' and zinc['unidade_origem'] == 'mg/kg'
    assert zinc['unidade_destino'] == '%'
    provenance = json.loads(provenance_json(reports[1], '%', 'wheat_en.pdf'))
    assert provenance['versao_procedencia'] == 3
    assert provenance['conversao_em'] == dict(unidade_origem='Mcal/kg', unidade_destino='kcal/g', fator=1)
    assert provenance['unidade_em_origem'] == 'Mcal/kg'
    assert provenance['unidades_destino']['EM'] == 'kcal/g'
    assert provenance['unidades_destino']['Gln'] == '%'
    assert any(r['nutriente']=='ZINC' for r in provenance['registros'])


@pytest.mark.parametrize('label', ['Zn', 'ZINC', 'Zinc', 'zinc'])
def test_zinc_aliases_and_conflicts(label):
    assert convert_report(source(f'{label} 64.47 1 -'), '%')[0]['Zn'] == pytest.approx(.006447)
    with pytest.raises(ValueError, match='valores diferentes'):
        convert_report(source('Zn 64.47 1 - ZINC 65 1 -'), '%')


@pytest.mark.parametrize('uppercase', [False, True])
def test_twenty_three_letter_codes_import_and_minerals_do_not_collide(uppercase):
    assert set(AMINO_ACID_CODES) == EXPECTED and len(DEFAULT_CODES) == 44 and set(DEFAULT_CODES) <= set(NUTRIENT_CODES)
    body='\n'.join(f'{code.upper() if uppercase else code} 0.5 2 0.1' for code in sorted(EXPECTED))
    body+='\nP 0.34 1 - K 0.39 1 -\nS 0.2 1 - I 1 1 -\nA 99 1 - R 99 1 - N 99 1 -'
    values, _, missing = convert_report(source(body), '%')
    assert all(values[code] == .5 and code not in missing for code in EXPECTED)
    assert values['P'] == .34 and values['K'] == .39 and values['S'] == .2
    assert values['I'] == .0001  # Iodo: mg/kg -> %, não isoleucina.


@pytest.mark.parametrize('value', [0, 3.21, 3.77, 10.5])
def test_energy_conversion_has_factor_one_and_is_idempotent(value):
    assert em_to_kcal_per_g(value, 'Mcal/kg') == value
    assert em_to_kcal_per_g(em_to_kcal_per_g(value), 'kcal/g') == value
    with pytest.raises(ValueError):
        em_to_kcal_per_g(value, 'MJ/kg')


def test_saved_energy_unit_changes_without_changing_limits_results_or_source():
    original = pd.DataFrame([
        dict(nutriente='EM',unidade='Mcal/kg',minimo='3,0',maximo='3,5',resultado='3,21'),
        dict(nutriente='EM',unidade='kcal/g',minimo=None,maximo=4,resultado=3.77),
        dict(nutriente='Lys',unidade='%',minimo=.2,maximo=2,resultado=.4),
    ])
    snapshot=original.copy(deep=True)
    normalized=normalize_loaded_constraints(original)
    assert normalized.unidade.tolist() == ['kcal/g','kcal/g','%']
    assert normalized.iloc[0]['resultado'] == 3.21
    assert normalized.iloc[0]['minimo'] == 3 and normalized.iloc[0]['maximo'] == 3.5
    pd.testing.assert_frame_equal(original,snapshot)
    pd.testing.assert_frame_equal(normalized,normalize_loaded_constraints(normalized))
    with pdfplumber.open(BytesIO(make_pdf_bytes(dict(nome='Legada'),pd.DataFrame(),original))) as pdf:
        text='\n'.join(page.extract_text() for page in pdf.pages)
    assert 'kcal/g' in text and 'Mcal/kg' not in text


def test_google_append_ten_fields_preserves_prior_thirty_four_schema():
    from test_cqbal_storage import Sheet
    from src.repositories.google_sheets import GoogleSheetsRepository
    added={'Ala','Asn','Asp','Cys','Gly','Glu','Gln','Pro','Ser','Trp'}
    for table in ['ingredientes','dieta_ingredientes']:
        old=[c for c in TABLE_SCHEMAS[table] if c not in added]
        row=[''] * len(old)
        row[old.index('EM')]='3,21'
        row[old.index('Lys')]='0,4'
        sheet=Sheet(old)
        sheet.values.append(row[:])
        repo=GoogleSheetsRepository.__new__(GoogleSheetsRepository)
        repo._cache={}
        repo._worksheet=lambda name: sheet
        repo._call=lambda operation: operation()
        repo._ensure_table(table,TABLE_SCHEMAS[table])
        assert sheet.values[0][:len(old)] == old
        assert set(sheet.values[0][len(old):]) == added
        assert sheet.values[1] == row and sheet.clears == 0


def test_manual_twenty_amino_save_solve_and_reload(tmp_path):
    app = AppTest.from_string('''import streamlit as st
from src.pages.ingredients import _ingredient_form
payload=_ingredient_form(None,'new')
if payload is not None:st.session_state['payload']=payload
''').run()
    next(x for x in app.text_input if x.label=='Nome *').set_value('20 aminoácidos')
    for code in EXPECTED:
        app.text_input(key='new_'+code).set_value('0,5')
    app.text_input(key='new_EM').set_value('3,21')
    app.button[0].click().run()
    assert not app.exception
    payload=app.session_state['payload']
    assert all(payload[code]==.5 for code in EXPECTED)
    assert payload['EM']==3.21 and NUTRIENT_BY_CODE['EM'].unit=='kcal/g'
    repo=LocalRepository(tmp_path)
    repo.initialize()
    saved=repo.upsert_ingredient(payload,'tester')
    row=repo.list_ingredients().iloc[0]
    assert all(float(row[code])==.5 for code in EXPECTED)
    items=pd.DataFrame([dict(saved,preco_kg=1,inclusao_min=0,inclusao_max=100)])
    limits=pd.DataFrame([dict(nutriente='EM',minimo=3,maximo=3.3)] +
                        [dict(nutriente=c,minimo=.4,maximo=.6) for c in sorted(EXPECTED)])
    result=solve_least_cost(items,limits)
    assert result.success,result.message
    energy=result.constraints.set_index('nutriente').loc['EM']
    assert energy['resultado']==3.21 and energy['unidade']=='kcal/g'
    diet_id=repo.save_diet(dict(nome='20 aminoácidos'),result.items,result.constraints,'tester')
    loaded=repo.get_diet(diet_id)
    assert all(float(loaded['items'].iloc[0][code])==.5 for code in EXPECTED)
