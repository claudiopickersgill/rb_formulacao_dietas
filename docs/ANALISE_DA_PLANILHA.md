# Análise técnica — Software de Formulação RB v1.2

## 1. Estrutura encontrada

A pasta de trabalho possui seis abas:

1. **Formulação 1**
2. **Formulação 2**
3. **Formulação 3**
4. **Formulação 4**
5. **TabelaIngredientes**
6. **OBS**

As quatro abas de formulação repetem a mesma estrutura. Cada uma possui 15 posições fixas para ingredientes, preenchimento automático da composição e uma área de restrições nutricionais.

### Campos da formulação

- Tipo
- Mineral/Alimento
- Classificação
- Preço em R$
- MS
- NDT
- PB
- FDN
- FDA
- Amido
- Ca
- P
- Mg
- Na
- K
- Cl
- S
- Fe
- Cu
- Mn
- Zn
- Co
- I
- Se
- Participação na mistura
- Inclusão mínima
- Inclusão máxima

A dieta é apresentada em base de matéria seca e a soma da mistura deve ser igual a 100%.

## 2. Funcionamento atual

### Seleção dos ingredientes

A coluna **Tipo** utiliza uma lista com os valores cadastrados na tabela de ingredientes. A coluna **Mineral/Alimento** utiliza uma lista dependente:

- quando o tipo é `Mineral`, mostra a lista de minerais;
- quando o tipo é `Alimento`, mostra a lista de alimentos;
- quando o tipo está vazio, não mostra opções.

A classificação e os valores nutricionais são recuperados por fórmulas de busca na tabela `TabelaDeIngredientes`.

### Cálculo nutricional

Para cada nutriente, a planilha calcula:

`resultado da dieta = soma(composição do ingrediente × inclusão do ingrediente)`

O custo é calculado por:

`custo da dieta = soma(preço do ingrediente × inclusão do ingrediente)`

### Otimização pretendida

O modelo pretendido é uma programação linear de custo mínimo:

- minimizar o custo da dieta;
- soma das inclusões igual a 100%;
- inclusão de cada ingrediente entre seu mínimo e máximo;
- composição nutricional entre o mínimo e o máximo estabelecidos;
- inclusões não negativas.

## 3. Problemas técnicos encontrados

### 3.1 Macro desalinhada com a planilha atual

Os botões das quatro formulações chamam a macro `CalcularMistura`.

A macro ainda utiliza referências de uma versão anterior:

- variável de decisão: `X3:X17`;
- soma da mistura: `X18`;
- limites: `Y3:Z17`;
- célula objetivo: `C24`.

Na versão enviada:

- a coluna **X** é `Se`;
- a coluna **Y** é `Mistura`;
- a coluna **Z** é `Mínimo`;
- a coluna **AA** é `Máximo`;
- a fórmula do custo está em **D24**.

Portanto, a macro está alterando a coluna de selênio em vez da mistura e não está minimizando a célula que contém o custo real.

### 3.2 Selênio não é carregado automaticamente

As fórmulas de busca dos ingredientes vão de `D` até `W`. A coluna `X`, correspondente ao selênio, permanece com zero e não recupera o valor da tabela de ingredientes.

### 3.3 Resultado salvo não respeita as restrições

A Formulação 1 possui uma mistura armazenada que soma 100%, porém apresenta resultados incompatíveis com os limites configurados. Entre os exemplos:

- NDT calculado abaixo do mínimo;
- PB muito acima do máximo;
- FDA abaixo do mínimo;
- cálcio abaixo do mínimo;
- fósforo abaixo do mínimo.

Esse resultado não pode ser tratado como uma dieta válida.

### 3.4 Formulação atual é inviável com os dados cadastrados

Na Formulação 1, o triguilho está cadastrado com NDT igual a zero. Com os ingredientes selecionados e NDT mínimo de 70%, o maior FDA possível é aproximadamente 5,81%, enquanto o mínimo exigido é 15%.

Isso mostra a necessidade de distinguir:

- valor realmente igual a zero;
- valor desconhecido;
- valor ainda não informado.

O WebApp deve bloquear a otimização quando um parâmetro necessário estiver ausente.

### 3.5 Duplicidades na base

Foram encontrados **82 registros**:

- 11 alimentos;
- 71 minerais.

Há pelo menos dez nomes duplicados, incluindo:

- Fosfato de cálcio (dibásico);
- Fosfato de cálcio (monobásico);
- Sulfato de cálcio dihidratado;
- Calcário dolomítico;
- Fosfato defluorado;
- Cloreto de magnésio hexahidratado;
- Cloreto de potássio;
- Cloreto de sódio;
- Sulfato de magnésio heptahidratado;
- Sulfato de potássio.

Como a planilha utiliza busca pelo nome, o primeiro registro encontrado pode ocultar os demais.

### 3.6 Problemas na classificação

Dos 82 registros, 59 não possuem classificação preenchida. Algumas linhas de minerais possuem letras como `a`, `b`, `d`, `f`, `g`, `h`, `i`, `j` e `k`, aparentemente originadas de notas de rodapé. Há também mineral classificado como energético.

### 3.7 Preços incompletos

Somente quatro ingredientes possuem preço diferente de zero. O preço deve ser tratado como informação da formulação, podendo haver um preço padrão opcional no cadastro.

### 3.8 Ingrediente repetido na mesma dieta

A Formulação 1 contém ureia duas vezes. O WebApp deve impedir repetição do mesmo ingrediente ou consolidar automaticamente as linhas.

## 4. Arquitetura proposta

## 4.1 Autenticação e autorização

### Autenticação

Usar login por conta Google com OIDC.

### Autorização

Manter uma tabela `usuarios` com:

- email;
- nome;
- perfil;
- ativo;
- data de criação;
- último acesso.

Perfis recomendados:

- **Administrador**: gerencia usuários, alimentos e todas as dietas;
- **Formulador**: cria alimentos próprios, formula, salva e exporta dietas;
- **Consulta**: apenas visualiza dietas autorizadas.

A autenticação confirma quem é o usuário. A autorização define o que ele pode fazer.

## 4.2 Estrutura sugerida no Google Sheets

### Aba `usuarios`

- user_id
- email
- nome
- perfil
- ativo
- created_at
- last_login

### Aba `ingredientes`

- ingredient_id
- tipo
- nome
- classificacao
- formula_quimica
- fonte
- preco_padrao
- MS
- NDT
- PB
- FDN
- FDA
- AMIDO
- CA
- P
- Mg
- Na
- K
- Cl
- S
- Fe
- Cu
- Mn
- Zn
- Co
- I
- Se
- ativo
- created_by
- created_at
- updated_at

### Aba `dietas`

- diet_id
- nome
- descricao
- proprietario
- base
- objetivo
- status
- custo
- created_at
- updated_at

### Aba `dieta_ingredientes`

- diet_id
- ingredient_id
- ordem
- preco
- inclusao_min
- inclusao_max
- inclusao_calculada

### Aba `dieta_restricoes`

- diet_id
- nutriente
- minimo
- maximo
- resultado

### Aba `auditoria`

- timestamp
- usuario
- acao
- entidade
- entity_id
- detalhes

## 4.3 Motor de otimização

O motor deve ser independente do Streamlit e do Google Sheets.

Entrada:

- ingredientes selecionados;
- composição nutricional;
- preços;
- limites individuais;
- restrições nutricionais.

Saída:

- inclusão calculada;
- custo;
- composição final;
- situação de cada restrição;
- mensagem de viabilidade;
- diagnóstico quando não houver solução.

Modelo:

`minimizar Σ preço_i × inclusão_i`

Sujeito a:

`Σ inclusão_i = 1`

`mínimo_i ≤ inclusão_i ≤ máximo_i`

`mínimo_nutriente_j ≤ Σ composição_ij × inclusão_i ≤ máximo_nutriente_j`

`inclusão_i ≥ 0`

## 5. Layout proposto

## 5.1 Menu lateral

- Início
- Nova formulação
- Dietas salvas
- Ingredientes
- Administração
- Sair

Também deve mostrar nome, email e perfil do usuário.

## 5.2 Tela inicial

Indicadores:

- número de dietas;
- número de ingredientes ativos;
- última dieta criada;
- custo médio das dietas recentes.

Atalhos:

- Nova dieta
- Abrir última dieta
- Cadastrar ingrediente

## 5.3 Nova formulação

### Cabeçalho

- nome da dieta;
- descrição;
- categoria animal;
- base da formulação;
- objetivo.

### Ingredientes

Tabela editável com:

- ingrediente;
- classificação;
- preço;
- mínimo;
- máximo;
- inclusão calculada;
- custo parcial.

A tabela deve permitir adicionar e remover linhas dinamicamente.

### Restrições

Tabela editável com:

- nutriente;
- mínimo;
- máximo;
- resultado;
- diferença;
- situação.

### Resumo

- custo por kg de MS;
- soma da mistura;
- status da solução;
- número de restrições atendidas;
- avisos sobre dados ausentes.

### Ações

- Calcular
- Salvar
- Salvar nova versão
- Duplicar
- Exportar
- Limpar

## 5.4 Cadastro de ingredientes

- pesquisa por nome;
- filtros por tipo e classificação;
- criação;
- edição;
- inativação;
- validação de duplicidade;
- indicação de campos ausentes;
- histórico de alteração.

## 5.5 Dietas salvas

- busca;
- filtros por usuário, data e status;
- abrir;
- duplicar;
- comparar;
- exportar;
- excluir conforme permissão.

## 6. Exportações

Formatos recomendados:

- **Excel**: memória completa da formulação;
- **PDF**: relatório visual para entrega;
- **CSV**: ingredientes e inclusões;
- **JSON**: intercâmbio e backup técnico.

O relatório deve conter:

- identificação da dieta;
- autor e data;
- ingredientes;
- inclusões;
- preço;
- composição nutricional;
- limites;
- avisos;
- fontes dos ingredientes.

## 7. Regras de negócio recomendadas

1. A soma da mistura deve ser 100%.
2. Inclusão mínima não pode ser maior que a máxima.
3. O mesmo ingrediente não pode aparecer duas vezes.
4. Ingrediente inativo não pode entrar em nova formulação.
5. Parâmetro desconhecido deve ser `nulo`, não zero.
6. O cálculo deve ser bloqueado quando faltar dado usado em uma restrição.
7. O usuário deve visualizar quais restrições causaram inviabilidade.
8. Dieta salva deve guardar uma cópia dos valores utilizados, evitando mudança retroativa quando o cadastro do ingrediente for alterado.
9. Alterações em ingredientes devem ser registradas.
10. Usuários só podem editar dietas conforme seu perfil e propriedade.
11. Preços devem poder sobrescrever o preço padrão em cada dieta.
12. Resultados devem ser arredondados somente para exibição; o cálculo deve usar precisão completa.

## 8. Estrutura sugerida do projeto

```text
formulacao_rb/
├── app.py
├── pages/
│   ├── dashboard.py
│   ├── formulacao.py
│   ├── dietas.py
│   ├── ingredientes.py
│   └── administracao.py
├── services/
│   ├── auth_service.py
│   ├── sheets_service.py
│   ├── ingredient_service.py
│   ├── diet_service.py
│   ├── solver_service.py
│   └── export_service.py
├── models/
│   ├── ingredient.py
│   ├── diet.py
│   └── user.py
├── utils/
│   ├── validators.py
│   ├── formatting.py
│   └── constants.py
├── tests/
│   ├── test_solver.py
│   ├── test_validators.py
│   └── test_permissions.py
├── requirements.txt
└── .streamlit/
    ├── config.toml
    └── secrets.toml.example
```

## 9. Ordem de implementação

### Etapa 1 — saneamento e migração

- remover duplicidades;
- corrigir classificações;
- identificar zeros que significam ausência;
- definir unidades;
- criar IDs únicos;
- migrar a base limpa para o Google Sheets.

### Etapa 2 — núcleo funcional

- autenticação;
- autorização;
- leitura da base;
- cadastro de ingredientes;
- tela de formulação;
- motor de custo mínimo;
- diagnóstico de inviabilidade.

### Etapa 3 — persistência

- salvar dieta;
- editar;
- duplicar;
- versionar;
- histórico.

### Etapa 4 — exportação

- Excel;
- CSV;
- PDF;
- relatório completo.

### Etapa 5 — administração e qualidade

- gestão de usuários;
- logs;
- testes;
- tratamento de concorrência;
- backups.

## 10. Decisões necessárias antes da implementação

1. O acesso será restrito a uma lista de emails ou aberto para cadastro?
2. Cada usuário poderá ver somente suas dietas ou haverá dietas compartilhadas?
3. Usuários comuns poderão criar ingredientes globais ou somente ingredientes particulares?
4. Os preços serão sempre digitados na dieta ou haverá preços padrão?
5. A formulação permanecerá apenas em base de matéria seca?
6. Quais nutrientes serão obrigatórios no primeiro lançamento?
7. O PDF precisa seguir uma identidade visual específica?
8. Haverá necessidade de comparar duas ou mais dietas?
9. O Google Sheets continuará como banco definitivo ou será apenas a primeira versão?
