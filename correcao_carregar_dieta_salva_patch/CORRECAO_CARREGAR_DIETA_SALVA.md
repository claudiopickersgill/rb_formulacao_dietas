# Correção — Continuar editando dieta salva

## Problema

Ao abrir uma dieta salva no Google Sheets e clicar em **Continuar editando**, os dados retornavam para o formulador como texto. O Google Sheets (`get_all_values`) devolve números como strings, por exemplo:

- `"42,0582"` para inclusão;
- `"1,70"` para preço;
- `"89,0"` para restrição;
- `"TRUE"`/`"FALSE"` para `sem_custo`.

O `SolverResult` carregado usava esses valores diretamente. Assim, a tela tentava executar operações numéricas em strings, por exemplo a soma de `inclusao_calculada` seguida da formatação `:.4f`, provocando `ValueError`.

## Correção

Foi criado `src/diet_loading.py`, responsável por normalizar dietas recuperadas do armazenamento:

- preços, mínimos, máximos, inclusões e custos voltam a `float`;
- todos os nutrientes voltam a `float`;
- limites e resultados nutricionais voltam a `float`;
- `sem_custo` volta a `bool`;
- valores com vírgula decimal continuam aceitos.

## Fingerprint

O fingerprint anterior comparava DataFrames inteiros. Uma dieta salva não contém exatamente as mesmas colunas do catálogo e ainda possui colunas de saída do solver. Isso fazia uma dieta recém-aberta aparecer como alterada.

Agora o fingerprint considera somente:

- `ingredient_id`;
- `sem_custo`;
- preço;
- inclusão mínima e máxima;
- composição nutricional;
- mínimo e máximo das restrições.

Colunas de saída como `inclusao_calculada`, `custo_parcial` e `resultado` não interferem na comparação.

## Arquivos alterados

- `src/pages/formulation.py`
- `src/diet_loading.py`
- `tests/test_saved_diet_loading.py`

## Testes

A suíte completa passou com **30 testes aprovados**.
