"""Relatórios completos digitais CQBAL PT/EN, com unidades por nutriente."""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import hashlib
import json
import math
import re

from .config import AMINO_ACID_CODES, NUTRIENT_BY_CODE, NUTRIENT_CODES
from .energy import em_to_kcal_per_g

MACROS = {'CA', 'P', 'Mg', 'Na', 'K', 'Cl', 'S'}
MICROS = {'Fe', 'Cu', 'Mn', 'Zn', 'Co', 'I', 'Se'}
MAPPING = {code: code for code in NUTRIENT_CODES}
MAPPING.pop('NDT', None)
MAPPING.pop('CA', None)
MAPPING.pop('EM', None)
MAPPING.update({'NDT OBS': 'NDT', 'Ca': 'CA',
                'DM': 'MS', 'CP': 'PB', 'ASH': 'MM', 'CF': 'FB',
                'NDF': 'FDN', 'ADF': 'FDA', 'STARCH': 'AMIDO', 'OBS TDN': 'NDT',
                'ZINC': 'Zn', 'Zinc': 'Zn', 'zinc': 'Zn'})
# Somente siglas de três letras. I, K, P e S continuam sendo minerais.
MAPPING.update({code.upper(): code for code in AMINO_ACID_CODES})
# Somente esta estimativa tem correspondência validada nos relatórios de referência.
ENERGY_MAPPING = {'EM_BRCORTE2016': 'EM', 'ME_BRCORTE2016': 'EM'}
CATEGORIES = ('FORRAGENS SECAS', 'FORRAGENS VERDES', 'SILAGENS',
              'CONCENTRADOS PROTÉICOS', 'CONCENTRADOS PROTEICOS',
              'CONCENTRADOS ENERGÉTICOS', 'SUBPRODUTOS', 'FONTES DE MINERAIS', 'MINERAIS')
CATEGORY_ALIASES = {category: category for category in CATEGORIES}
CATEGORY_ALIASES.update({
    'DRY FORAGES': 'FORRAGENS SECAS', 'DRY FORAGE': 'FORRAGENS SECAS',
    'GREEN FORAGES': 'FORRAGENS VERDES', 'GREEN FORAGE': 'FORRAGENS VERDES',
    'SILAGES': 'SILAGENS', 'SILAGE': 'SILAGENS',
    'PROTEIN CONCENTRATE': 'CONCENTRADOS PROTEICOS',
    'PROTEIN CONCENTRATES': 'CONCENTRADOS PROTEICOS',
    'ENERGY CONCENTRATE': 'CONCENTRADOS ENERGÉTICOS',
    'ENERGY CONCENTRATES': 'CONCENTRADOS ENERGÉTICOS',
    'BY-PRODUCTS': 'SUBPRODUTOS', 'BYPRODUCTS': 'SUBPRODUTOS',
    'MINERAL SOURCES': 'FONTES DE MINERAIS', 'MINERALS': 'MINERAIS',
})
CALCULATED_SECTIONS = {'Nutrientes Calculados': 'pt', 'Estimated Nutrients': 'en'}
NUMBER = r'(?:-?\d+(?:[.,]\d+)?|-)'
METRIC = re.compile(r'([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9_/%()+., -]*?)\s+('
                    + NUMBER + r')\s+(\d+|-)\s+(' + NUMBER + r')(?=\s|$)')


@dataclass(frozen=True)
class CQBALReport:
    name: str
    category: str
    records: list[dict]
    sha256: str = ''
    language: str = 'pt'
    category_original: str = ''


def parse_report_text(text: str, sha256: str = '') -> CQBALReport:
    lines = [re.sub(r'\s+', ' ', s).strip() for s in text.splitlines() if s.strip()]
    languages = {CALCULATED_SECTIONS[s] for s in lines if s in CALCULATED_SECTIONS}
    if 'CQBAL' not in text.upper() or not languages:
        raise ValueError('Envie o Relatório Completo digital do CQBAL, com Nutrientes Calculados / Estimated Nutrients.')
    categories = [s for s in lines if s.upper() in CATEGORY_ALIASES]
    if not categories:
        raise ValueError('Categoria do alimento não reconhecida no PDF.')
    names = []
    for i, line in enumerate(lines):
        if line in {'Derivados', 'Derivatives'} and i:
            names.append(lines[i - 1])
    if not names or len(set(names)) != 1:
        raise ValueError('O PDF deve conter exatamente um alimento identificável.')
    records, section, seen = [], 'Composição', {}
    for line in lines:
        if line in CALCULATED_SECTIONS:
            section = 'Calculados'
            continue
        if 'NUTRIENTE' in line or 'https://' in line or 'CQBAL' in line:
            continue
        matches = list(METRIC.finditer(line))
        if not matches:
            continue
        # Linhas da tabela devem conter apenas métricas e espaços/padding.
        residue = METRIC.sub('', line).strip(' -')
        if residue:
            raise ValueError('Linha de composição ambígua; confira o PDF: ' + line[:100])
        for match in matches:
            label, mean, n, s = match.groups()
            label = label.strip()
            values = [None if v == '-' else float(v.replace(',', '.')) for v in [mean, n, s]]
            if any(v is not None and not math.isfinite(v) for v in values):
                raise ValueError('Valor não finito no relatório.')
            record = dict(secao=section, nutriente=label, media=values[0],
                          n=int(values[1]) if values[1] is not None else None, s=values[2],
                          media_original=mean, n_original=n, s_original=s)
            key = (section, label)
            if key in seen:
                if seen[key] != record:
                    raise ValueError('Nutriente repetido com valores diferentes: ' + label)
                continue
            seen[key] = record
            records.append(record)
    if not records or not any(r['secao'] == 'Composição' for r in records):
        raise ValueError('Nenhuma tabela de composição reconhecida. PDFs digitalizados não são aceitos.')
    canonical_categories = {CATEGORY_ALIASES[c.upper()] for c in categories}
    if len(canonical_categories) != 1:
        raise ValueError('O PDF contém categorias incompatíveis; envie um único alimento.')
    return CQBALReport(names[0], CATEGORY_ALIASES[categories[0].upper()], records, sha256,
                       next(iter(languages)) if len(languages) == 1 else 'pt/en', categories[0])


def parse_pdf(content: bytes) -> CQBALReport:
    if len(content) > 10 * 1024 * 1024:
        raise ValueError('Limite de 10 MB por PDF.')
    if not content.startswith(b'%PDF-'):
        raise ValueError('O arquivo enviado não é um PDF válido.')
    import pdfplumber
    try:
        with pdfplumber.open(BytesIO(content)) as pdf:
            if not 1 <= len(pdf.pages) <= 20:
                raise ValueError('Envie um relatório de um alimento, com até 20 páginas.')
            text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('Não foi possível ler o PDF digital. Gere novamente no CQBAL.') from exc
    return parse_report_text(text, hashlib.sha256(content).hexdigest())


def convert_report(report: CQBALReport, macro_unit: str, *, amino_unit: str = '%',
                   energy_unit: str = 'Mcal/kg') -> tuple[dict, list[dict], list[str]]:
    if macro_unit not in {'%', 'g/kg'}:
        raise ValueError('Confirme a unidade de origem dos macrominerais.')
    if amino_unit != '%' or energy_unit != 'Mcal/kg':
        raise ValueError('Esta versão importa aminoácidos em % do alimento e EM em Mcal/kg. Confira a fonte.')
    composition = {code: None for code in NUTRIENT_CODES}
    preview = []
    for record in report.records:
        source = record['nutriente']
        target = MAPPING.get(source) if record['secao'] == 'Composição' else ENERGY_MAPPING.get(source)
        value = record['media']
        if target and value is not None:
            if not math.isfinite(value) or value < 0:
                raise ValueError('Valor negativo ou não finito em nutriente importável: ' + source)
            unit = ('Mcal/kg' if target == 'EM' else 'mg/kg' if target in MICROS
                    else macro_unit if target in MACROS else '%')
            converted = value / 10000 if target in MICROS else value / 10 if target in MACROS and macro_unit == 'g/kg' else value
            if target == 'EM':
                converted = em_to_kcal_per_g(value, energy_unit)
            if target != 'EM' and converted > 100:
                raise ValueError('Valor convertido acima de 100%; confira a unidade de ' + source)
            if composition[target] is not None and not math.isclose(composition[target], converted, rel_tol=0, abs_tol=1e-12):
                raise ValueError('Duas siglas apresentam valores diferentes para ' + target + '.')
            composition[target] = converted
            status = 'Importar'
        else:
            unit, converted = None, None
            status = 'Ausente' if target else 'Preservar na fonte; não importar'
        preview.append(dict(nutriente_cqbal=source, secao=record['secao'], media_original=value,
                            unidade_origem=unit, campo_base=target, valor_na_base=converted,
                            unidade_destino=NUTRIENT_BY_CODE[target].unit if target else None,
                            valor_em_porcentagem=converted if target != 'EM' else None,
                            N=record['n'], S=record['s'], tratamento=status))
    missing = [code for code, value in composition.items() if value is None]
    for code in missing:
        composition[code] = 0.0
    represented = {row['campo_base'] for row in preview if row['campo_base']}
    for row in preview:
        if row['campo_base'] in missing:
            row['valor_em_porcentagem'] = 0.0
            row['valor_na_base'] = 0.0
            if row['campo_base'] == 'EM':
                row['valor_em_porcentagem'] = None
            row['tratamento'] = 'Ausente no relatório; preencher com zero'
    for code in missing:
        if code not in represented:
            preview.append(dict(nutriente_cqbal=None, secao='Ausente no relatório', media_original=None,
                                unidade_origem=None, campo_base=code, valor_na_base=0.0,
                                unidade_destino=NUTRIENT_BY_CODE[code].unit,
                                valor_em_porcentagem=0.0 if code != 'EM' else None,
                                N=None, S=None, tratamento='Ausente no relatório; preencher com zero'))
    return composition, preview, missing


def provenance_json(report: CQBALReport, macro_unit: str, filename: str) -> str:
    _, _, missing = convert_report(report, macro_unit)
    value = json.dumps(dict(fonte='CQBAL', arquivo=filename, sha256=report.sha256,
                           versao_procedencia=3, idioma=report.language,
                           nome_original=report.name, categoria=report.category,
                           categoria_original=report.category_original or report.category,
                           unidade_macro_origem=macro_unit, unidade_micro_origem='mg/kg',
                           unidade_amino_origem='%', unidade_em_origem='Mcal/kg',
                           conversao_em=dict(unidade_origem='Mcal/kg', unidade_destino='kcal/g',
                                             fator=1000.0 / 1000.0),
                           unidade_destino='por_campo',
                           unidades_destino={code: NUTRIENT_BY_CODE[code].unit for code in NUTRIENT_CODES},
                           metodo_ndt='NDT OBS / OBS TDN', metodo_em='EM_BRCORTE2016 / ME_BRCORTE2016',
                           politica_ausentes='preencher_com_zero', campos_preenchidos_com_zero=missing,
                           registros=report.records),
                       ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    if len(value) > 45000:
        raise ValueError('Relatório muito extenso para armazenar a procedência em uma célula do Google.')
    return value
