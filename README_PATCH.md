# Correção — custos das dietas na Visão geral

## Problema
O Google Sheets devolve `custo_kg` como texto no padrão pt-BR, por exemplo:

    1,343255887

O `dashboard.py` usava `pd.to_numeric(..., errors="coerce")`.
O pandas não interpreta a vírgula decimal nesse caso e converte o valor para `NaN`.

Consequências:
- `Custo médio/kg` aparecia como `—`;
- `Custo/kg` das dietas recentes aparecia como `None`.

Os valores estavam persistidos corretamente em `rb_dietas`; o problema era somente de leitura/exibição.

## Correção
O dashboard passa a usar `numeric_series()` de `src.utils`, que reutiliza
`as_float()` e entende tanto vírgula decimal quanto ponto decimal.

Nenhuma alteração de schema, Google Sheets ou dietas salvas é necessária.

## Aplicação
Copie o conteúdo deste patch para a raiz do projeto, permitindo substituir:

    src/pages/dashboard.py

Depois:

    git add src/pages/dashboard.py
    git commit -m "Corrige custos no dashboard"
    git push origin main
