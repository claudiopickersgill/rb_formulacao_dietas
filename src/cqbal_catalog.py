"""Catálogo CQBAL versionado: aliases por seção, sem misturar modelos."""
from __future__ import annotations
import json
import re
from pathlib import Path

CATALOG = json.loads((Path(__file__).parent / 'data' / 'cqbal_catalog.json').read_text(encoding='utf-8'))
FIELDS = {field['code']: field for field in CATALOG['fields']}
DEFAULT_CODES = tuple(code for code, field in FIELDS.items() if field['default'])


def normalize(value: str) -> str:
    return re.sub(r'\s+', ' ', str(value).strip()).casefold()


def matching_codes(section: str, source: str) -> list[str]:
    # O CQBAL usa Ash para CZ e ASH para MM: a caixa pode distinguir campos.
    exact = re.sub(r'\s+', ' ', str(source).strip())
    matches = [code for code, field in FIELDS.items()
               if any(s == section and re.sub(r'\s+', ' ', alias.strip()) == exact
                      for s, alias in field['aliases'])]
    return matches or [code for code, field in FIELDS.items()
                      if any(s == section and normalize(alias) == normalize(source) for s, alias in field['aliases'])]


def resolve(section: str, source: str) -> str | None:
    matches = matching_codes(section, source)
    if len(matches) > 1:
        raise ValueError('Sigla CQBAL ambígua: ' + source + '. Use o JSON original com siglas em português.')
    return matches[0] if matches else None


def default_policy() -> dict:
    return dict(version=0, selected=list(DEFAULT_CODES), updated_by='', updated_at='')


def validate_selection(selected) -> list[str]:
    if not isinstance(selected, (list, tuple)) or any(not isinstance(x, str) or x not in FIELDS for x in selected):
        raise ValueError('Seleção de atributos CQBAL inválida.')
    return [code for code in FIELDS if code in set(selected)]
