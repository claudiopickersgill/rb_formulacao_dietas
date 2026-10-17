"""Leitura de PDFs digitais CQBAL e conversão explícita para porcentagem."""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import hashlib
import json
import math
import re

from .config import NUTRIENT_CODES

MACROS = {'CA', 'P', 'Mg', 'Na', 'K', 'Cl', 'S'}
MICROS = {'Fe', 'Cu', 'Mn', 'Zn', 'Co', 'I', 'Se'}
MAPPING = {code: code for code in NUTRIENT_CODES}
MAPPING.pop('NDT', None)
MAPPING.pop('CA', None)
MAPPING.update({'NDT OBS': 'NDT', 'Ca': 'CA'})
CATEGORIES = ('FORRAGENS SECAS', 'FORRAGENS VERDES', 'SILAGENS',
              'CONCENTRADOS PROTÉICOS', 'CONCENTRADOS PROTEICOS',
              'CONCENTRADOS ENERGÉTICOS', 'SUBPRODUTOS', 'FONTES DE MINERAIS', 'MINERAIS')
NUMBER = r'(?:-?\d+(?:[.,]\d+)?|-)'
METRIC = re.compile(r'([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9_/%()+., -]*?)\s+('
                    + NUMBER + r')\s+(\d+|-)\s+(' + NUMBER + r')(?=\s|$)')


@dataclass(frozen=True)
class CQBALReport:
    name: str
    category: str
    records: list[dict]
    sha256: str = ''


def parse_report_text(text: str, sha256: str = '') -> CQBALReport:
    lines = [re.sub(r'\s+', ' ', s).strip() for s in text.splitlines() if s.strip()]
    if 'CQBAL' not in text.upper() or 'Nutrientes Calculados' not in text:
        raise ValueError('Envie o Relatório Completo digital do CQBAL, com Nutrientes Calculados.')
    categories = [s for s in lines if s in CATEGORIES]
    if not categories:
        raise ValueError('Categoria do alimento não reconhecida no PDF.')
    names = []
    for i, line in enumerate(lines):
        if line == 'Derivados' and i:
            names.append(lines[i - 1])
    if not names or len(set(names)) != 1:
        raise ValueError('O PDF deve conter exatamente um alimento identificável.')
    records, section, seen = [], 'Composição', {}
    for line in lines:
        if line == 'Nutrientes Calculados':
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
    return CQBALReport(names[0], categories[0], records, sha256)


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


def convert_report(report: CQBALReport, macro_unit: str) -> tuple[dict, list[dict], list[str]]:
    if macro_unit not in {'%', 'g/kg'}:
        raise ValueError('Confirme a unidade de origem dos macrominerais.')
    composition = {code: None for code in NUTRIENT_CODES}
    preview = []
    for record in report.records:
        source = record['nutriente']
        target = MAPPING.get(source) if record['secao'] == 'Composição' else None
        value = record['media']
        if target and value is not None:
            if value < 0:
                raise ValueError('Valor negativo em nutriente importável: ' + source)
            unit = 'mg/kg' if target in MICROS else macro_unit if target in MACROS else '%'
            converted = value / 10000 if target in MICROS else value / 10 if target in MACROS and macro_unit == 'g/kg' else value
            if converted > 100:
                raise ValueError('Valor convertido acima de 100%; confira a unidade de ' + source)
            composition[target] = converted
            status = 'Importar'
        else:
            unit, converted = None, None
            status = 'Ausente' if target else 'Preservar na fonte; não importar'
        preview.append(dict(nutriente_cqbal=source, secao=record['secao'], media_original=value,
                            unidade_origem=unit, campo_base=target, valor_em_porcentagem=converted,
                            N=record['n'], S=record['s'], tratamento=status))
    missing = [code for code, value in composition.items() if value is None]
    return composition, preview, missing


def provenance_json(report: CQBALReport, macro_unit: str, filename: str) -> str:
    value = json.dumps(dict(fonte='CQBAL', arquivo=filename, sha256=report.sha256,
                           nome_original=report.name, categoria=report.category,
                           unidade_macro_origem=macro_unit, unidade_micro_origem='mg/kg',
                           unidade_destino='%', metodo_ndt='NDT OBS', registros=report.records),
                       ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    if len(value) > 45000:
        raise ValueError('Relatório muito extenso para armazenar a procedência em uma célula do Google.')
    return value
