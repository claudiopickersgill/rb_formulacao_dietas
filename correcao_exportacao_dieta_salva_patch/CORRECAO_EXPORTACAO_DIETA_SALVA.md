# Correção — exportação de dietas salvas

## Problema

Dietas recuperadas do Google Sheets chegam ao aplicativo como texto. Valores numéricos formatados conforme a localidade brasileira, como `1,4958`, não podem ser convertidos com `float()` diretamente.

Na tela **Dietas salvas**, os arquivos de exportação eram gerados imediatamente para alimentar os `download_button`. O Excel chamava `float(metadata['custo_kg'])`, provocando `ValueError` antes mesmo de o usuário clicar em um botão de download.

## Correção

- `normalize_loaded_metadata()` converte custos salvos para `float` usando `as_float()`.
- `normalize_loaded_items()` e `normalize_loaded_constraints()` são usados também pela camada de exportação.
- Excel, PDF e CSV aceitam valores oriundos diretamente do Google Sheets, inclusive vírgula decimal.
- `format_brl()` agora aceita strings pt-BR com segurança.
- A tela `Dietas salvas` normaliza o bundle antes de exibir, exportar, duplicar ou enviar para edição.
- A comparação de dietas também usa a conversão pt-BR.

## Arquivos alterados

- `src/diet_loading.py`
- `src/exports.py`
- `src/pages/diets.py`
- `src/utils.py`
- `tests/test_exports.py`
- `tests/test_saved_diet_loading.py`

## Validação

Foram testados custos e percentuais como `1,4958`, `1,7000`, `42,0582`, `86,90` e `89,0000`.

Resultado: 32 testes aprovados.
