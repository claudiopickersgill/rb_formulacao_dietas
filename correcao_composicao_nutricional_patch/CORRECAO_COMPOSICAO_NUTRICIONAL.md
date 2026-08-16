# Correção — composição nutricional não chegando ao solver

## Causa encontrada

A versão atual do repositório contém a rotina de backfill em `src/repositories/google_sheets.py`, mas a pasta `data/` publicada no GitHub possui apenas `seed_usuarios.csv`. O arquivo `data/seed_ingredientes.csv`, usado como fallback pela rotina, não está presente.

Quando a aba legada não é encontrada ou não contém os valores esperados, os campos vazios de `rb_ingredientes` permanecem vazios e a validação bloqueia o cálculo.

Existe ainda um segundo problema de estado: `_merge_selected_items()` reaproveitava a linha inteira armazenada em `st.session_state["frm_items_full"]`. Assim, mesmo depois de a composição do ingrediente ser corrigida no catálogo, a formulação aberta podia continuar carregando NDT/PB/FDN/FDA/Ca/P antigos ou vazios.

## Correções aplicadas

1. Inclusão de `data/seed_ingredientes.csv`, extraído da planilha Excel original v1.2, com 82 registros.
2. `_merge_selected_items()` agora sempre recebe a composição nutricional da versão atual do catálogo (`rb_ingredientes`).
3. Do estado anterior são preservados somente os campos específicos da formulação: preço e limites de inclusão.
4. Foi acrescentado o expander **Conferir composição nutricional carregada**, permitindo visualizar NDT, PB, FDN, FDA, Ca e P antes de executar o solver.

## O que deve acontecer após o deploy

Na inicialização, `GoogleSheetsRepository.initialize()` chama `_backfill_missing_ingredient_nutrients()`. Com o seed presente, células nutricionais realmente vazias em `rb_ingredientes` são preenchidas sem sobrescrever valores numéricos já existentes, inclusive zeros.

Para os ingredientes usados no teste, a referência contém, entre outros:

- Milho: NDT 80, PB 8, FDN 9,8, FDA 3,6, Ca 0,04, P 0,31.
- Farelo de soja: NDT 85, PB 45, FDN 11,9, FDA 7,2, Ca 0,30, P 0,70.
- Farelo de arroz integral: NDT 75, PB 14,8, FDN 23,1, FDA 13,8, Ca 0,78, P 0,12.
- Farelo de arroz desengordurado: NDT 70, PB 18,5, FDN 25,9, FDA 12,7, Ca 0,83, P 2,48.
- Casquinha de soja: NDT 48,76, PB 11,9, FDN 66,7, FDA 47,9, Ca 0,64, P 0,13.

## Arquivos do patch

- `src/pages/formulation.py`
- `data/seed_ingredientes.csv`

Após substituir os arquivos, faça um novo deploy/reboot do app. Recomenda-se clicar em **Limpar** antes de remontar a formulação para remover qualquer estado antigo da sessão.
