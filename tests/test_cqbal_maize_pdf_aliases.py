"""Regressão dos PDFs reais Milho Fubá BR/EN de 26/10/2026."""
import json
from pathlib import Path

import pytest

from src.cqbal_catalog import default_policy, matching_codes, resolve
from src.cqbal_import import (parse_report_text, convert_configured_report,
                              configured_provenance, parse_json_report)

FIXTURES = Path(__file__).parent / 'fixtures' / 'cqbal'


def maize(language):
    return parse_report_text((FIXTURES / f'maize_{language}.txt').read_text(encoding='utf8'))


def test_real_reports_default_policy_matches_both_languages():
    left = convert_configured_report(maize('pt'), '%', default_policy())
    right = convert_configured_report(maize('en'), '%', default_policy())
    assert left[0] == right[0]
    assert len(left[0]) == 44
    assert left[0]['MS'] == 87.88 and left[0]['PB'] == 8.96
    assert left[0]['MM'] == 1.62 and left[0]['EM'] == 3.25
    assert left[2] == right[2] == ['I','Asn','Gln']


@pytest.mark.parametrize('language,label,means', [('pt','CHO A',[13.50,3.46]), ('en','DEE',[100.0,21.11])])
def test_ambiguous_duplicates_preserved_in_provenance(language,label,means):
    report = maize(language)
    rows = [r for r in report.records if r['secao']=='Composição' and r['nutriente']==label]
    assert [r['media'] for r in rows] == means
    doc=json.loads(configured_provenance(report,'%',f'milho_{language}.pdf',default_policy()))
    assert [r['media'] for r in doc['registros'] if r['secao']=='Composição' and r['nutriente']==label] == means
    values,preview,_,_=convert_configured_report(report,'%',default_policy())
    assert all(r['tratamento'].startswith('Não selecionado') for r in preview if r['nutriente_cqbal']==label)


@pytest.mark.parametrize('language,label', [('pt','CHO A'), ('en','DEE')])
def test_selected_ambiguous_field_requests_json(language,label):
    candidates=matching_codes('Composição',label)
    assert len(candidates)>1
    policy=default_policy()
    policy['selected'].append(candidates[0])
    with pytest.raises(ValueError,match='ambígua.*JSON'):
        convert_configured_report(maize(language),'%',policy)


def test_exact_case_aliases_preserve_cz_and_mm_as_separate_fields():
    assert resolve('Composição','Ash') == 'CQB_348'
    assert resolve('Composição','ASH') == 'MM'
    policy=default_policy();policy['selected'].append('CQB_348')
    left=convert_configured_report(maize('pt'),'%',policy)[0]
    right=convert_configured_report(maize('en'),'%',policy)[0]
    assert left==right and left['MM']==1.62 and left['CQB_348']==1.27


def test_json_ids_disambiguate_cho_a_instead_of_using_reference_values():
    raw=json.loads((FIXTURES/'milho_fuba.json').read_text(encoding='utf8'))
    report=parse_json_report(json.dumps(raw).encode())
    codes=matching_codes('Composição','CHO A')
    policy=default_policy();policy['selected'] += codes
    values,_,_,_=convert_configured_report(report,'%',policy)
    assert values['MS']>0
    # CHO A não é aditivo; os dois valores ficam na procedência, pelos IDs.
    doc=json.loads(configured_provenance(report,'%', 'completo.json',policy))
    assert all(code in doc['atributos_importados'] for code in codes)
    assert all(code not in values for code in codes)


def test_repeated_unambiguous_ms_still_rejected():
    text=(FIXTURES/'maize_pt.txt').read_text(encoding='utf8')
    text=text.replace('Nutrientes Calculados','MS 1 1 -\nNutrientes Calculados')
    with pytest.raises(ValueError,match='repetido com valores diferentes: MS'):
        parse_report_text(text)
