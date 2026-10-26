"""Casos reais CQBAL PT/EN e integração dos novos nutrientes."""
from io import BytesIO
import json
from pathlib import Path

import pandas as pd
import pdfplumber
import pytest
from streamlit.testing.v1 import AppTest

from src.config import AMINO_ACID_CODES, NUTRIENT_BY_CODE, NUTRIENT_CODES, TABLE_SCHEMAS
from src.cqbal_import import convert_report, parse_report_text, provenance_json
from src.exports import make_excel_bytes, make_pdf_bytes
from src.nutrients import synchronize_constraints
from src.repositories.local import LocalRepository
from src.solver import solve_least_cost

FIXTURES = Path(__file__).parent / 'fixtures' / 'cqbal'
AMINOS = dict(Lys=1.17, Met=.37, Thr=.79, Phe=1.42, Leu=1.50,
              Ile=.85, Val=1.14, His=.71, Arg=2.82, Tyr=.33)


def report(language):
    return parse_report_text((FIXTURES / f'cottonseed_{language}.txt').read_text(encoding='utf-8'))


def minimal(body, estimated='EM_BRCORTE2016 3.77 1 -'):
    return parse_report_text('CQBAL 4.0\nCONCENTRADOS PROTEICOS\nALGODÃO CAROÇO\nDerivados\n'
                             + body + '\nNutrientes Calculados\n' + estimated)


def test_actual_reports_have_identical_composition():
    pt, en = report('pt'), report('en')
    assert pt.language == 'pt' and en.language == 'en'
    assert pt.name == 'ALGODÃO CAROÇO' and en.name == 'whole cottonseed'
    assert en.category == 'CONCENTRADOS PROTEICOS'
    assert en.category_original == 'PROTEIN CONCENTRATE'
    assert len(pt.records) == len(en.records)
    left, _, missing = convert_report(pt, '%')
    right, _, en_missing = convert_report(en, '%')
    assert left == right and missing == en_missing
    assert left['MS'] == 90.66 and left['PB'] == 22.94
    assert left['MM'] == 4.28 and left['FB'] == 25.39 and left['AMIDO'] == .65
    assert left['NDT'] == 81.46  # Não 96.35 calculado nem 63.50 in vitro.
    assert left['FDN'] == 45.65 and left['FDA'] == 33.81
    assert left['EM'] == 3.77  # Não 4.31 de ED nem 5.61 de EB.
    assert {code: left[code] for code in AMINOS} == AMINOS
    assert all(left[code] == 0 for code in missing)


def test_preview_and_provenance_preserve_units_and_statistics():
    source = report('en')
    _, rows, _ = convert_report(source, '%')
    energy = next(r for r in rows if r['campo_base'] == 'EM')
    assert energy['valor_na_base'] == 3.77 and energy['unidade_destino'] == 'Mcal/kg'
    assert energy['valor_em_porcentagem'] is None
    assert energy['N'] == 1 and energy['S'] is None
    dry = next(r for r in rows if r['campo_base'] == 'MS')
    assert dry['N'] == 64 and dry['S'] == 1.353
    provenance = json.loads(provenance_json(source, '%', 'english.pdf'))
    assert provenance['idioma'] == 'en' and provenance['versao_procedencia'] == 2
    assert provenance['unidades_destino']['EM'] == 'Mcal/kg'
    assert provenance['unidades_destino']['Lys'] == '%'
    assert provenance['registros'] == source.records


@pytest.mark.parametrize('language', ['pt', 'en'])
def test_macro_conversion_only_changes_minerals(language):
    source = report(language)
    pct = convert_report(source, '%')[0]
    grams = convert_report(source, 'g/kg')[0]
    assert grams['CA'] == pytest.approx(.027)
    assert grams['P'] == pytest.approx(.074)
    assert grams['EM'] == pct['EM'] and grams['Lys'] == pct['Lys']


def test_alias_conflict_is_rejected():
    with pytest.raises(ValueError, match='valores diferentes'):
        convert_report(minimal('MS 90 1 - DM 80 1 -'), '%')
    assert convert_report(minimal('MS 90 1 - DM 90 1 -'), '%')[0]['MS'] == 90


def test_no_fallback_for_unvalidated_energy_or_fiber():
    source = minimal('MS 90 1 - NDFap 55 1 -\nADFp 30 1 - TDN (IV) 60 1 -',
                     'ED_BRCORTE2016 4.31 1 - EM_BRCORTE2010 3.1 1 -')
    values, rows, missing = convert_report(source, '%')
    for code in ['EM', 'NDT', 'FDN', 'FDA']:
        assert values[code] == 0 and code in missing
    energy = next(r for r in rows if r['campo_base'] == 'EM')
    assert energy['unidade_destino'] == 'Mcal/kg' and energy['valor_em_porcentagem'] is None


@pytest.mark.parametrize('body', ['Lys -1 1 -', 'Lys 101 1 -'])
def test_invalid_amino_values_rejected(body):
    with pytest.raises(ValueError):
        convert_report(minimal(body), '%')


def test_unsupported_source_units_rejected():
    with pytest.raises(ValueError):
        convert_report(report('en'), '%', amino_unit='%PB')
    with pytest.raises(ValueError):
        convert_report(report('en'), '%', energy_unit='MJ/kg')


def test_formulation_solves_energy_and_amino_in_their_own_units(tmp_path):
    items = pd.DataFrame([
        dict(ingredient_id='a', nome='A', tipo='Alimento', preco_kg=1,
             inclusao_min=0, inclusao_max=100, EM=2, Lys=.5),
        dict(ingredient_id='b', nome='B', tipo='Alimento', preco_kg=2,
             inclusao_min=0, inclusao_max=100, EM=4, Lys=1.5),
    ])
    limits = pd.DataFrame([dict(nutriente='EM', minimo=3, maximo=3),
                           dict(nutriente='Lys', minimo=1, maximo=1)])
    assert set(synchronize_constraints(limits, items).nutriente) == {'EM', 'Lys'}
    result = solve_least_cost(items, limits)
    assert result.success, result.message
    assert result.items.inclusao_calculada.tolist() == pytest.approx([50, 50])
    nutrients = result.constraints.set_index('nutriente')
    assert nutrients.loc['EM', 'resultado'] == pytest.approx(3)
    assert nutrients.loc['EM', 'unidade'] == 'Mcal/kg'
    assert nutrients.loc['Lys', 'resultado'] == pytest.approx(1)
    assert nutrients.loc['Lys', 'unidade'] == '%'
    repo = LocalRepository(tmp_path)
    repo.initialize()
    saved = repo.upsert_ingredient(dict(nome='A', tipo='Alimento', EM=2, Lys=.5), 'tester')
    assert float(repo.list_ingredients().iloc[0]['EM']) == 2
    diet_id = repo.save_diet(dict(nome='Dieta teste', custo_kg=1.5), result.items,
                             result.constraints, 'tester')
    loaded = repo.get_diet(diet_id)
    assert loaded['items'].EM.tolist() == [2, 4]
    assert loaded['items'].Lys.tolist() == [.5, 1.5]
    assert loaded['constraints'].loc[loaded['constraints'].nutriente.eq('EM'), 'unidade'].iloc[0] == 'Mcal/kg'
    assert make_excel_bytes(loaded['metadata'], loaded['items'], loaded['constraints']).startswith(b'PK')
    with pdfplumber.open(BytesIO(make_pdf_bytes(loaded['metadata'], loaded['items'], loaded['constraints']))) as pdf:
        assert 'Mcal/kg' in '\n'.join(page.extract_text() for page in pdf.pages)


def test_google_schema_upgrade_preserves_old_columns_and_values():
    from test_cqbal_storage import Sheet
    from src.repositories.google_sheets import GoogleSheetsRepository
    added = {'EM', *AMINO_ACID_CODES}
    old_header = [c for c in TABLE_SCHEMAS['ingredientes'] if c not in added]
    row = [''] * len(old_header)
    row[old_header.index('ingredient_id')] = 'old'
    row[old_header.index('PB')] = '22,94'
    sheet = Sheet(old_header)
    sheet.values.append(row)
    repo = GoogleSheetsRepository.__new__(GoogleSheetsRepository)
    repo._cache = {}
    repo.cache_ttl_seconds = 0
    repo._call = lambda operation: operation()
    repo._worksheet = lambda name: sheet
    repo._ensure_table('ingredientes', TABLE_SCHEMAS['ingredientes'])
    assert sheet.values[0][:len(old_header)] == old_header
    assert sheet.values[1] == row and sheet.clears == 0
    assert set(sheet.values[0][len(old_header):]) == added
    repo._ensure_table('ingredientes', TABLE_SCHEMAS['ingredientes'])
    assert len(sheet.values[0]) == len(set(sheet.values[0]))
    # Mesma expansão também deve funcionar na tabela de composição das dietas.
    old_diet = [c for c in TABLE_SCHEMAS['dieta_ingredientes'] if c not in added]
    diet_sheet = Sheet(old_diet)
    repo._worksheet = lambda name: diet_sheet
    repo._ensure_table('dieta_ingredientes', TABLE_SCHEMAS['dieta_ingredientes'])
    assert diet_sheet.values[0][:len(old_diet)] == old_diet
    assert set(diet_sheet.values[0][len(old_diet):]) == added


def test_manual_form_has_new_fields_and_saves_payload():
    source = '''import streamlit as st
from src.pages.ingredients import _ingredient_form
value = _ingredient_form(None, 'new')
if value is not None:
    st.session_state['saved_payload'] = value
'''
    app = AppTest.from_string(source).run()
    assert not app.exception
    next(x for x in app.text_input if x.label == 'Nome *').set_value('Ingrediente manual')
    app.text_input(key='new_EM').set_value('3,77')
    app.text_input(key='new_Lys').set_value('1,17')
    app.button[0].click().run()
    assert not app.exception
    saved = app.session_state['saved_payload']
    assert saved['EM'] == 3.77 and saved['Lys'] == 1.17
    assert set(AMINO_ACID_CODES) <= set(saved)
    assert NUTRIENT_BY_CODE['EM'].unit == 'Mcal/kg' and len(NUTRIENT_CODES) == 34


@pytest.mark.parametrize('language', ['pt', 'en'])
def test_import_screen_saves_new_fields_and_preserves_price(tmp_path, language):
    # Exercita seleção de unidades, prévia e gravação da tela sem usar Google real.
    # A extração dos PDFs reais também é validada no preparo da entrega.
    repo = LocalRepository(tmp_path)
    repo.initialize()
    repo.upsert_ingredient(dict(ingredient_id='existing', nome='Existente', tipo='Alimento',
                               preco_padrao=2.8, observacoes='Histórico anterior'), 'tester')
    fixture = str(FIXTURES / f'cottonseed_{language}.txt')
    source = f'''from types import SimpleNamespace
from pathlib import Path
import streamlit as st
import src.pages.cqbal as page
from src.cqbal_import import parse_report_text
from src.models import User
from src.repositories.local import LocalRepository
page.st.file_uploader = lambda *a, **k: SimpleNamespace(getvalue=lambda: b'reference', name='reference.pdf')
page.parse_pdf = lambda content: parse_report_text(Path({fixture!r}).read_text(encoding='utf-8'))
repo = LocalRepository({str(tmp_path)!r})
repo.initialize()
page.render(repo, User('u', 'tester', 'Teste', 'Formulador', True))
'''
    # Limita a substituição do widget a esta verificação.
    from unittest.mock import patch
    import streamlit as st
    import src.pages.cqbal as page
    with patch.object(st, 'file_uploader', st.file_uploader), patch.object(page, 'parse_pdf', page.parse_pdf):
        app = AppTest.from_string(source).run()
        assert not app.exception
        app.selectbox[0].select('%').run()
        assert not app.exception
        assert app.dataframe
        app.radio[0].set_value('Atualizar cadastro existente').run()
        for box in app.checkbox:
            box.check()
        app.run()
        app.button[0].click().run()
        assert not app.exception and not app.error
    row = repo.list_ingredients().iloc[0]
    assert float(row['EM']) == 3.77 and float(row['Lys']) == 1.17
    assert float(row['preco_padrao']) == 2.8
    assert 'Histórico anterior' in row['observacoes']
    assert json.loads(row['cqbal_dados'])['idioma'] == language
