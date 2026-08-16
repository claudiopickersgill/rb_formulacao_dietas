# Correção — números com vírgula decimal (pt-BR)

## Causa
O Google Sheets pode retornar valores numéricos formatados como texto conforme a localidade da planilha, por exemplo `48,76`, `9,8` e `0,04`.

O projeto já possuía `as_float()`, que entende vírgula decimal, porém o validador e o solver ainda usavam `pd.to_numeric()` diretamente. Para esses textos, `pd.to_numeric(..., errors="coerce")` gera `NaN`, fazendo nutrientes preenchidos parecerem ausentes.

## Correção
- criada `numeric_series()` em `src/utils.py`, baseada em `as_float()`;
- validação de nutrientes e limites passa a aceitar formatos pt-BR e en-US;
- vetores nutricionais do solver passam a aceitar vírgula decimal;
- preços usados pelo solver também passam pela mesma conversão;
- adicionados testes de regressão com `48,76`, `11,9`, `66,7`, `0,64` e `0,13`.

## Efeito esperado
Os valores exibidos em **Conferir composição nutricional carregada** deixam de ser marcados como ausentes apenas por utilizarem vírgula decimal.
