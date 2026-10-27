from pathlib import Path

import pytest

from src.cqbal_catalog import default_policy
from src.cqbal_import import parse_report_text, convert_configured_report

FIXTURES = Path(__file__).parent / 'fixtures' / 'cqbal'


def source(name):
    return (FIXTURES / f'flaked_maize_{name}.txt').read_text(encoding='utf8')


def test_android_without_print_title_matches_desktop():
    text=source('android')
    assert 'CQBAL' not in text.upper()
    mobile=parse_report_text(text)
    desktop=parse_report_text(source('desktop'))
    assert mobile.name==desktop.name=='MILHO FLOCULADO'
    left=convert_configured_report(mobile,'%',default_policy())
    right=convert_configured_report(desktop,'%',default_policy())
    assert left[0]==right[0] and left[2]==right[2]
    assert left[0]['MS']==88.23 and left[0]['PB']==8.48 and left[0]['EM']==3.25


def test_android_english_structure_without_cqbal_marker():
    text=source('android').replace('CONCENTRADOS ENERGÉTICOS','ENERGY CONCENTRATE')
    text=text.replace('Derivados','Derivatives').replace('Nutrientes Calculados','Estimated Nutrients')
    text=text.replace('NUTRIENTE','NUTRIENT').replace('MÉDIA','AVERAGE')
    report=parse_report_text(text)
    assert report.language=='en'
    assert convert_configured_report(report,'%',default_policy())[0]['MS']==88.23


@pytest.mark.parametrize('missing', ['category','name','header','composition','calculated_values','calculated_title'])
def test_missing_print_title_does_not_bypass_structure_validation(missing):
    text=source('android')
    if missing=='category': text=text.replace('CONCENTRADOS ENERGÉTICOS','OUTRA CATEGORIA')
    if missing=='name': text=text.replace('Derivados','')
    if missing=='header':
        text='\n'.join(line for line in text.splitlines() if 'NUTRIENTE' not in line)
    if missing=='composition':
        start=text.index('MS 88.23');end=text.index('Nutrientes Calculados')
        text=text[:start]+text[end:]
    if missing=='calculated_values': text=text[:text.index('EEvD_BRCORTE2016')]
    if missing=='calculated_title': text=text.replace('Nutrientes Calculados','')
    with pytest.raises(ValueError): parse_report_text(text)
