# Restrições nutricionais dinâmicas

## Objetivo

A formulação deixou de depender de uma lista fixa `DEFAULT_CONSTRAINTS`.
A tabela de restrições passa a ser montada automaticamente a partir dos nutrientes registrados nos ingredientes selecionados.

## Comportamento

- Se um nutriente tiver pelo menos um valor numérico declarado entre os ingredientes selecionados, ele aparece na tabela.
- `0` é considerado um valor declarado e válido.
- Preencher `Mínimo` e/ou `Máximo` ativa a restrição no solver.
- Deixar os dois campos vazios mantém o nutriente sem restrição, mas seu teor final é calculado quando os dados estiverem completos.
- Se um nutriente sem restrição tiver composição incompleta, ele aparece como `Dados incompletos` / `Não calculado`, sem impedir a formulação.
- Se houver mínimo ou máximo para um nutriente com dados incompletos, a validação bloqueia o cálculo e identifica os ingredientes que precisam ser preenchidos.

## Exemplo: Selênio

Se um composto contendo Selênio for selecionado e houver dados na coluna `Se`, a linha `Se` aparece automaticamente.

- `Se mínimo = vazio` e `Se máximo = vazio`: o teor de Se é apenas calculado.
- `Se mínimo = 0,10` e/ou `Se máximo = 0,30`: Se passa a fazer parte das restrições do problema de programação linear.

## Arquitetura

### `src/config.py`

`NUTRIENT_CODES` continua sendo o catálogo canônico dos nutrientes reconhecidos pelo sistema e mantém seus metadados (nome, unidade e grupo).
A lista fixa `DEFAULT_CONSTRAINTS` foi removida do fluxo de formulação.

### `src/nutrients.py`

Novo módulo responsável por:

- detectar nutrientes disponíveis nos ingredientes selecionados;
- sincronizar dinamicamente a tabela de restrições;
- preservar limites já digitados ao alterar a seleção de ingredientes.

### `src/pages/formulation.py`

A tabela de restrições agora contém automaticamente uma linha para cada nutriente disponível.
O código do nutriente é somente leitura; o usuário edita apenas mínimo e máximo.

A área `Conferir composição nutricional carregada` também mostra dinamicamente todos os nutrientes disponíveis.

### `src/solver.py`

O solver continua usando somente restrições com mínimo e/ou máximo preenchidos para montar `A_ub` e `b_ub`.
Após encontrar a solução, calcula também os nutrientes sem restrição para exibição.

Estados possíveis:

- `Atendida`
- `Fora do limite`
- `Sem restrição`
- `Dados incompletos`

## Limitação atual

A dinâmica ocorre dentro do catálogo de nutrientes já registrado em `NUTRIENTS`/`NUTRIENT_CODES` (MS, NDT, PB, ... Se).

Para permitir que um administrador crie um nutriente totalmente novo no Google Sheets sem alterar código (por exemplo, um novo marcador laboratorial), a evolução futura recomendada é criar uma tabela `rb_nutrientes` com `codigo`, `nome`, `unidade`, `grupo` e `ativo`, e transformar a composição dos ingredientes em um modelo mais dinâmico.

## Testes

Foram adicionados testes para:

- detecção automática de Selênio;
- sincronização das restrições com preservação de valores;
- cálculo de nutriente sem restrição;
- nutriente sem restrição com dado incompleto sem bloquear o solver;
- visualização `Sem restrição`.

A suíte completa possui 37 testes aprovados.
