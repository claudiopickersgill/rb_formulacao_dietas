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
from .cqbal_catalog import DEFAULT_CODES, FIELDS, matching_codes, resolve, validate_selection

MACROS = {'CA', 'P', 'Mg', 'Na', 'K', 'Cl', 'S'}
MICROS = {'Fe', 'Cu', 'Mn', 'Zn', 'Co', 'I', 'Se'}
MAPPING = {code: code for code in DEFAULT_CODES}
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
    if not languages:
        raise ValueError('Envie o Relatório Completo digital do CQBAL, com Nutrientes Calculados / Estimated Nutrients.')
    # Android pode omitir cabeçalho/rodapé de impressão. O título CQBAL
    # nesses adornos não é obrigatório quando a estrutura da tabela existe.
    without_print_title = 'CQBAL' not in text.upper()
    if without_print_title and not any(
        'NUTRIENT' in line.upper() and
        any(word in line.upper() for word in ('MÉDIA', 'MEDIA', 'MEAN', 'AVERAGE'))
        for line in lines
    ):
        raise ValueError('Estrutura da tabela CQBAL não reconhecida. Envie o Relatório Completo digital.')
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
                    if len(matching_codes(section, label)) > 1:
                        # A origem reutiliza siglas para atributos diferentes.
                        # Preserva as ocorrências; a seleção decidirá se são
                        # apenas procedência ou exigem JSON para desambiguar.
                        records.append(record)
                        continue
                    raise ValueError('Nutriente repetido com valores diferentes: ' + label)
                continue
            seen[key] = record
            records.append(record)
    if not records or not any(r['secao'] == 'Composição' for r in records):
        raise ValueError('Nenhuma tabela de composição reconhecida. PDFs digitalizados não são aceitos.')
    if without_print_title and not all(
        any(record['secao'] == section and record['media'] is not None and
            matching_codes(section, record['nutriente']) for record in records)
        for section in ('Composição', 'Calculados')
    ):
        raise ValueError('Relatório incompleto: confira as tabelas de composição e nutrientes calculados do CQBAL.')
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
    composition = {code: None for code in DEFAULT_CODES}
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
                           unidades_destino={code: NUTRIENT_BY_CODE[code].unit for code in DEFAULT_CODES},
                           metodo_ndt='NDT OBS / OBS TDN', metodo_em='EM_BRCORTE2016 / ME_BRCORTE2016',
                           politica_ausentes='preencher_com_zero', campos_preenchidos_com_zero=missing,
                           registros=report.records),
                       ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    if len(value) > 45000:
        raise ValueError('Relatório muito extenso para armazenar a procedência em uma célula do Google.')
    return value


def convert_configured_report(report: CQBALReport, macro_unit: str, policy: dict):
    """Retorna apenas campos selecionados; os desmarcados não são sobrescritos."""
    if macro_unit not in {'%', 'g/kg'}:
        raise ValueError('Confirme a unidade de origem dos macrominerais.')
    selected = validate_selection(policy['selected'])
    attributes, preview = {}, []
    for record in report.records:
        source, section = record['nutriente'], record['secao']
        direct = record.get('catalog_code')
        if direct in FIELDS and any(s == section and a.strip().casefold() == source.strip().casefold()
                                    for s, a in FIELDS[direct]['aliases']):
            target = direct
        else:
            try:
                candidates = matching_codes(section, source)
                if len(candidates) > 1 and any(code in selected for code in candidates):
                    raise ValueError('Sigla CQBAL ambígua: ' + source + '. Use o JSON original.')
                target = resolve(section, source) if len(candidates) <= 1 else None
            except ValueError:
                # Não escolhe entre aliases ingleses ambíguos nem os transforma em zero.
                if any(code in selected and any(s == section and a.strip().casefold() == source.strip().casefold()
                           for s, a in field['aliases']) for code, field in FIELDS.items()):
                    raise ValueError('Sigla CQBAL ambígua: ' + source + '. Use o JSON original com siglas e IDs.')
                target = None
        value = record['media']
        converted, unit = None, None
        enabled = target in selected
        if enabled and value is not None:
            if not math.isfinite(value) or value < 0:
                raise ValueError('Valor negativo ou não finito em atributo selecionado: ' + source)
            unit = ('Mcal/kg' if FIELDS[target]['unit'] == 'kcal/g' else 'mg/kg' if target in MICROS
                    else macro_unit if target in MACROS else FIELDS[target]['unit'])
            converted = value / 10000 if target in MICROS else value / 10 if target in MACROS and macro_unit == 'g/kg' else value
            if FIELDS[target]['unit'] == '%' and converted > 100:
                raise ValueError('Valor acima de 100%; confira a unidade de ' + source)
            if target in attributes and not math.isclose(attributes[target], converted, abs_tol=1e-12, rel_tol=0):
                raise ValueError('Duas siglas apresentam valores diferentes para ' + target)
            attributes[target] = converted
        preview.append(dict(nutriente_cqbal=source, secao=section, media_original=value,
                            unidade_origem=unit, campo_base=target, valor_na_base=converted,
                            unidade_destino=FIELDS[target]['unit'] if target else None,
                            N=record.get('n'), S=record.get('s'),
                            tratamento='Importar' if enabled and converted is not None else
                            'Ausente; preencher com zero' if enabled else 'Não selecionado; preservar cadastro',
                            uso_formulacao=bool(enabled and FIELDS[target]['formula'])))
    missing = [code for code in selected if code not in attributes]
    for code in missing:
        attributes[code] = 0.0
        for row in preview:
            if row['campo_base'] == code:
                row['valor_na_base'] = 0.0
        if not any(row['campo_base'] == code for row in preview):
            preview.append(dict(nutriente_cqbal=None, secao='Ausente no relatório', media_original=None,
                                campo_base=code, valor_na_base=0.0, unidade_origem=None,
                                unidade_destino=FIELDS[code]['unit'], N=None, S=None,
                                tratamento='Ausente; preencher com zero', uso_formulacao=FIELDS[code]['formula']))
    composition = {code: value for code, value in attributes.items() if FIELDS[code]['formula']}
    return composition, preview, missing, attributes


def configured_provenance(report, macro_unit, filename, policy, previous_source=None):
    _, _, missing, attributes = convert_configured_report(report, macro_unit, policy)
    document = dict(fonte='CQBAL', arquivo=filename, sha256=report.sha256, versao_procedencia=4,
                    idioma=report.language, nome_original=report.name, categoria=report.category,
                    categoria_original=report.category_original, unidade_macro_origem=macro_unit,
                    configuracao_importacao=policy, campos_preenchidos_com_zero=missing,
                    catalogo_versao=1,
                    # Metadados ficam no catálogo versionado para não exceder a
                    # célula de 50.000 caracteres do Sheets ao marcar todos.
                    atributos_importados={code: dict(valor=value)
                                          for code, value in attributes.items()}, registros=report.records)
    if previous_source:
        try:
            old = json.loads(previous_source)
            preserved = dict(old.get('atributos_preservados', {}))
            preserved.update(old.get('atributos_importados', {}))
            document['atributos_preservados'] = {code: value for code, value in preserved.items()
                                                 if code not in attributes}
        except (ValueError, TypeError, AttributeError):
            pass
    value = json.dumps(document, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    if len(value) > 45000:
        raise ValueError('Procedência excede o limite de uma célula Google. Reduza os campos selecionados.')
    return value


def parse_json_report(content: bytes) -> CQBALReport:
    if len(content) > 10 * 1024 * 1024:
        raise ValueError('Limite de 10 MB por arquivo.')
    root = json.loads(content.decode('utf-8-sig'))
    if not isinstance(root, dict) or root.get('errors'):
        raise ValueError('JSON CQBAL inválido.')
    data = root.get('data', root)
    if not isinstance(data, dict) or not isinstance(data.get('lista'), list) or not isinstance(data.get('dadosCalculados'), list):
        raise ValueError('Envie o completo.json de um alimento CQBAL.')
    records, seen = [], {}
    food_ids = set()
    for section, key in [('Composição', 'lista'), ('Calculados', 'dadosCalculados')]:
        for row in data[key]:
            for suffix in ('', '2'):
                source = str(row.get('NUTRIENTE'+suffix) or row.get('NUTRIENT'+suffix) or '').strip()
                if source.casefold() in {'', 'undefined', 'null', 'none'}:
                    continue
                if row.get('der_id'+suffix) is not None:
                    food_ids.add(str(row['der_id'+suffix]))
                val = row.get('media'+suffix)
                if val in (None, '', '-'):
                    val = None
                else:
                    if isinstance(val, bool):
                        raise ValueError('Média inválida em ' + source)
                    val = float(str(val).replace(',', '.'))
                    if not math.isfinite(val):
                        raise ValueError('Valor não finito em ' + source)
                # IDs resolvem siglas repetidas na própria origem; ID 0 não é chave.
                direct = 'CQB_' + str(row.get('nut_id'+suffix))
                record = dict(secao=section, nutriente=source, media=val,
                              n=row.get('n'+suffix), s=row.get('desvio'+suffix))
                if direct in FIELDS and section == 'Composição':
                    record['catalog_code'] = direct
                unique = (section, source, record.get('catalog_code'))
                if unique in seen:
                    if seen[unique] != record:
                        raise ValueError('Atributo duplicado com valores diferentes: ' + source)
                    continue
                seen[unique] = record
                records.append(record)
    if len(food_ids) > 1:
        raise ValueError('O JSON deve conter exatamente um alimento.')
    name = str(data.get('subtitulo3') or data.get('subtitulo3Ingles') or '').strip()
    category = str(data.get('titulo') or data.get('tituloIngles') or '').strip()
    if not name or not category or not records:
        raise ValueError('Nome, categoria ou composição ausentes no JSON.')
    return CQBALReport(name, CATEGORY_ALIASES.get(category.upper(), category), records,
                       hashlib.sha256(content).hexdigest(), 'pt', category)


def parse_html_report(content: bytes) -> CQBALReport:
    """Lê HTMLs de conferência do exportador, sem executar scripts."""
    from html.parser import HTMLParser
    if len(content) > 10 * 1024 * 1024:
        raise ValueError('Limite de 10 MB por arquivo.')
    class Reader(HTMLParser):
        def __init__(self):
            super().__init__(); self.tag = ''; self.text = []; self.heading = ''; self.name = ''; self.rows = []; self.cells = []
        def handle_starttag(self, tag, attrs):
            if tag in {'h1', 'h2', 'td', 'th'}:
                self.tag = tag; self.text = []
            if tag == 'tr': self.cells = []
        def handle_data(self, text):
            if self.tag: self.text.append(text)
        def handle_endtag(self, tag):
            if tag == self.tag:
                text = ''.join(self.text).strip()
                if tag == 'h1': self.name = text
                elif tag == 'h2': self.heading = text
                elif tag in {'td', 'th'}: self.cells.append(text)
                self.tag = ''
            if tag == 'tr' and self.cells:
                self.rows.append((self.heading, self.cells))
    reader = Reader(); reader.feed(content.decode('utf-8-sig'))
    records = []
    for heading, cells in reader.rows:
        if len(cells) != 5 or cells[0].casefold() in {'nutriente', 'nutrient'}:
            continue
        if heading not in {'Dados analiticos', 'Dados analíticos', 'Analytical data', 'Dados calculados', 'Calculated data'}:
            raise ValueError('Seção HTML desconhecida; prefira o completo.json.')
        value = None if cells[2] in {'', '-'} else float(cells[2].replace(',', '.'))
        if value is not None and not math.isfinite(value):
            raise ValueError('Valor não finito no HTML.')
        records.append(dict(secao='Calculados' if heading in {'Dados calculados', 'Calculated data'} else 'Composição',
                            nutriente=cells[0], media=value, n=cells[3], s=cells[4]))
    if not reader.name or not records or not any(row['secao'] == 'Calculados' for row in records):
        raise ValueError('HTML de conferência não reconhecido. Use o completo.json da mesma pasta.')
    raw = content.decode('utf-8-sig')
    category = next((cat for cat in CATEGORIES if cat in raw.upper()), 'CQBAL')
    return CQBALReport(reader.name, category, records, hashlib.sha256(content).hexdigest(),
                       'en' if 'Analytical data' in raw else 'pt', category)


def parse_uploaded_report(content: bytes, filename: str) -> CQBALReport:
    extension = filename.rsplit('.', 1)[-1].lower()
    if extension == 'json': return parse_json_report(content)
    if extension in {'html', 'htm'}: return parse_html_report(content)
    if extension == 'pdf': return parse_pdf(content)
    raise ValueError('Use JSON, HTML de conferência ou PDF CQBAL.')
