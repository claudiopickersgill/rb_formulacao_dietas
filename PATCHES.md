# RFB — Histórico consolidado de correções e patches

Consolidação inicial em **17/10/2026**, atualizada em **26/10/2026**, dos documentos de correção do projeto, pacotes arquivados e entregas desta conversa. Informações gerais, instalação, uso e novas funcionalidades ficam em [README.md](README.md). Correções e atualizações são registradas neste `PATCHES.md`.

As entradas abaixo seguem a evolução funcional. Quando a data exata de uma entrega antiga não está documentada, ela não foi inferida. Os identificadores P01–P26 são referências deste histórico, não números oficiais de versão.

## Regras atuais que substituem comportamentos anteriores

| Assunto | Histórico | Regra vigente |
|---|---|---|
| Composição no início do app | Foi criado preenchimento automático usando a tabela legada e um seed | A chamada automática foi desativada; não restaurar a regra antiga ao reaplicar patches |
| Quantidade de nutrientes | O cadastro original tinha 20 campos | São 44: os 23 anteriores, EM e vinte aminoácidos |
| Energia metabolizável | Não havia campo próprio | Origem Mcal/kg, destino kcal/g (fator 1); importar apenas EM/ME_BRCORTE2016, sem derivar do NDT |
| Unidade dos microminerais | A interface antiga mostrava mg/kg | A base usa %; importar mg/kg dividindo por 10.000 |
| Ausentes no CQBAL | A primeira importação deixava campos em branco | A composição importada recebe 0; a ausência continua identificada na procedência |
| NDT do CQBAL | O relatório contém valores observados e várias estimativas | Somente NDT OBS / OBS TDN preenche NDT |
| FDA e FDN | Há variantes corrigidas e frações no relatório | Somente FDA e FDN exatos preenchem os campos correspondentes |
| Cálcio | O código interno é CA | Mostrar Ca na sigla visual; manter CA no cálculo e no Google |
| Dieta inviável | Somente mensagens e faixas de diagnóstico | Acrescentar simulação diagnóstica; continuar sem aprovar ou salvar como dieta válida |
| Persistência de ingredientes | A aba inteira era regravada | Acrescentar/atualizar a linha do ingrediente e confirmar a gravação |

## P01 — Integração do MVP com Google Sheets

**Problema/contexto:** conectar o aplicativo de formulação à estrutura Google já utilizada no projeto, preservando o MVP.

**Entrega:** conexão centralizada por conta de serviço, reconhecimento de `private_gsheets_url`, backend Google, prefixo configurável, cache por TTL, repetição de chamadas em erros temporários e migração legada quando o catálogo de destino está vazio. Foram adotadas as seis tabelas `rb_*`, mantendo a aba de origem.

**Arquivos principais:** `app.py`, `main.py`, `src/google_connection.py`, `src/repositories/google_sheets.py`, `src/repositories/factory.py`, `src/pages/admin.py` e compatibilidade em `pages/conexao/`.

**Evolução posterior:** as regras de gravação de ingredientes e de evolução de cabeçalho foram aprimoradas em P16. A migração inicial não deve ser confundida com o preenchimento automático descrito em P04.

## P02 — Estabilidade dos editores de preços e restrições

**Sintoma:** valores desapareciam ao confirmar uma célula com Enter ou Tab.

**Correção:** separação entre a base estável do `st.data_editor` e o estado corrente da formulação. Os dados editados não realimentam continuamente a mesma base do widget. A seleção de ingredientes, o carregamento de uma dieta e a limpeza do formulário controlam a reconstrução dos editores.

**Arquivo:** `src/pages/formulation.py`.

**Pacote:** `correcao_estado_data_editor_patch.zip`.

## P03 — Proteção contra valores vazios/NaN no solver

**Sintoma:** células vazias do Google chegavam como strings e produziam NaN nas matrizes de otimização, causando erro do `linprog`.

**Correção:** validação numérica antes da otimização, mensagens com ingrediente/nutriente, tratamento defensivo de erros e diagnóstico de faixas possíveis, inclusive mantendo as demais restrições. No tratamento legado do solver, campos vazios de minerais representam contribuição zero; dados incompletos de alimentos em restrições ativas são bloqueados.

**Arquivos:** `src/solver.py`, `src/validators.py` e testes do solver.

**Pacote:** `correcao_solver_nan_patch.zip`.

## P04 — Reconciliação histórica de composição incompleta

**Sintoma:** o catálogo migrado tinha nutrientes vazios, embora existissem valores na base original.

**Correção da época:** uma rotina na inicialização procurava `tipo + nome` na aba legada e no `data/seed_ingredientes.csv`, preenchendo somente células vazias e preservando números existentes, inclusive zero. Registrava data e auditoria.

**Arquivo principal:** `src/repositories/google_sheets.py`.

**Pacote:** `correcao_base_nutricional_patch.zip`.

**Situação atual: substituída.** A chamada automática foi desativada em P14 para preservar dados intencionalmente desconhecidos e evitar preenchimento a partir de referências antigas. A rotina auxiliar pode existir no código, mas não é chamada automaticamente.

## P05 — Composição atual do catálogo chegando à formulação

**Problema:** faltava o seed de ingredientes em uma distribuição e a sessão podia manter uma composição desatualizada mesmo após corrigir o cadastro.

**Correção:** inclusão do seed com 82 registros, atualização da composição a partir do catálogo e preservação apenas dos campos próprios da formulação, como preço e limites de inclusão. Foi acrescentada a visualização para conferir a composição carregada antes do cálculo.

**Arquivos:** `data/seed_ingredientes.csv` e `src/pages/formulation.py`.

**Pacote:** `correcao_composicao_nutricional_patch.zip`.

**Nota histórica:** os exemplos numéricos dos documentos antigos não são uma tabela nutricional vigente. Valores posteriormente corrigidos no Google, como NDT do milho e fósforo do farelo de arroz integral, não devem ser restaurados a partir desses exemplos.

## P06 — Conversão de números pt-BR

**Sintoma:** textos como `48,76`, `0,64` ou `1.234,56` eram interpretados como dados ausentes ou geravam erros.

**Correção:** `numeric_series()` passou a reutilizar `as_float()`, centralizando a leitura de vírgula/ponto decimal para composição, preços e limites. A conversão foi incorporada à validação e ao solver.

**Arquivos:** `src/utils.py`, `src/validators.py`, `src/solver.py` e testes de regressão.

**Pacote:** `correcao_numeros_ptbr_patch.zip`.

## P07 — Submissão confiável do cálculo

**Sintoma:** clicar em Calcular dieta podia apenas confirmar a célula ainda aberta, dando a impressão de que o botão não respondeu.

**Correção:** preços, inclusões, restrições e ações passaram a compartilhar um `st.form`; o cálculo usa `st.form_submit_button`. Enter/Tab não submetem o cálculo automaticamente. Há proteção final para apresentar exceções do solver na interface.

**Arquivo:** `src/pages/formulation.py`.

**Dependência registrada:** `streamlit[auth]>=1.61,<2.0`.

**Pacote:** `correcao_calcular_dieta_form_patch.zip`.

## P08 — Fuso horário do aplicativo

**Correção:** utilização de `America/Sao_Paulo`, timestamps ISO com offset e normalização idempotente dos campos de data de ingredientes, usuários, dietas e auditoria. Valores inválidos são preservados; horários antigos sem offset são tratados como locais. `tzdata` foi incluído para compatibilidade, especialmente no Windows.

**Arquivos:** `src/utils.py`, `src/config.py`, repositórios, `requirements.txt` e testes de fuso.

**Pacote:** `correcao_fuso_horario_patch.zip`.

## P09 — Login de vários usuários

**Sintoma:** usuários cadastrados não conseguiam entrar porque o login local validava apenas as credenciais administrativas dos segredos.

**Correção:** senha individual com hash PBKDF2-SHA256, salt aleatório e 310.000 iterações; senha inicial/redefinição na administração; preservação do hash ao editar outros dados; bloqueio de inativos; ocultação do hash na listagem. O administrador configurado nos segredos permanece como recuperação.

**Schema:** nova coluna `password_hash` em usuários.

**Arquivos:** `src/auth.py`, `src/security.py`, `src/config.py`, `src/pages/admin.py`, repositório tabular e seed de usuários.

**Pacote:** `correcao_login_multiusuario_patch.zip`.

## P10 — Melhorias da formulação de 16/08/2026

**Entrega:** coluna Sem custo, preço efetivo zero somente com confirmação, persistência de `sem_custo`, botão Recalcular dieta após o primeiro cálculo e apresentação de margens/situações dos nutrientes.

**Resultado visual:** indicação de nutrientes no limite, próximos, com folga ou fora dos limites; posteriormente complementada pela situação Sem restrição.

**Pacote:** `melhorias_formulacao_patch.zip`.

**Validação histórica:** foi registrada comparação com uma formulação de referência no Excel Solver. Ela protege uma combinação específica de composição, preços e restrições; não fixa o resultado esperado de outras dietas.

## P11 — Reabrir e continuar editando dietas salvas

**Sintoma:** números recuperados como texto e booleanos como TRUE/FALSE causavam erros de soma/formatação. Uma dieta recém-aberta também podia parecer alterada por diferenças nas colunas dos DataFrames.

**Correção:** `src/diet_loading.py` normaliza metadados, composição, custos, inclusões e restrições. O fingerprint passa a considerar os dados efetivos de entrada, sem incluir colunas de resultado ou metadados irrelevantes.

**Arquivos:** `src/diet_loading.py`, `src/pages/formulation.py` e testes de carregamento.

**Pacote:** `correcao_carregar_dieta_salva_patch.zip`.

## P12 — Exportação de dietas salvas

**Sintoma:** valores pt-BR causavam erro durante a geração de Excel/PDF/CSV, inclusive antes de clicar em baixar.

**Correção:** normalização compartilhada para exibição, exportação, duplicação, comparação e continuação da edição; `format_brl()` aceita strings pt-BR.

**Arquivos:** `src/diet_loading.py`, `src/exports.py`, `src/pages/diets.py` e `src/utils.py`.

**Pacote:** `correcao_exportacao_dieta_salva_patch.zip`.

## P13 — Restrições dinâmicas e custo no dashboard

### Restrições dinâmicas

A tabela de restrições deixou de depender apenas de uma lista fixa. Nutrientes com algum número declarado nos ingredientes aparecem automaticamente, incluindo zero. Limites digitados são preservados ao mudar a seleção. Nutrientes sem restrição podem ser calculados; dados incompletos só bloqueiam o cálculo quando necessários a uma restrição ativa.

**Arquivos:** `src/nutrients.py`, `src/pages/formulation.py`, `src/solver.py` e registro de nutrientes.

**Pacote:** `restricoes_nutricionais_dinamicas_patch.zip`.

### Custos na Visão geral

Custos estavam salvos no Google, mas `pd.to_numeric()` transformava strings com vírgula em NaN. A troca por `numeric_series()` corrigiu o custo médio e os custos das dietas recentes, sem modificar as dietas gravadas.

**Arquivo:** `src/pages/dashboard.py`.

**Pacote:** `correcao_custos_dashboard_patch.zip`.

## P14 — Migração da base e qualidade dos ingredientes

### Atualização da base em 07/09/2026

Foram atualizados 11 alimentos, preservando IDs e preços. Triguilho e aveia preta receberam composição revisada. Dez duplicatas antigas e o fosfato monossódico foram inativados, sem exclusão dos IDs históricos.

Na etapa seguinte, foram incluídos Sal mineral Pampa Beef Recria, Sal mineral Brasão 60P e Núcleo Pró Leite Agroceres. O Brasão foi cadastrado com composição parcial identificada. Os backups registrados foram `rb_ingredientes_backup_20260907` e `rb_ingredientes_backup_etapa2_20260907`.

O fósforo de 1,77% do farelo de arroz integral foi confirmado pelo usuário como o valor correto da base Google para a comparação realizada; exemplos antigos com 0,12% ficaram superados.

### Diagnóstico dos 24 alertas em 17/10/2026

O número correspondia a 24 registros com texto em `qualidade_dados`: 11 inativos, dez ativos com nota antiga de duplicidade, duas notas informativas de importação e uma pendência explícita de composição parcial do Brasão.

A inspeção encontrou 85 registros, 74 ativos e 11 inativos, sem IDs duplicados. Cada par de nomes duplicados possuía uma ocorrência ativa e uma inativa. Essas contagens são um retrato daquela inspeção, não constantes do sistema.

### Correção

Separação entre pendência e histórico pela coluna `observacoes`; reclassificação conservadora de notas legadas na leitura; dashboard com pendências apenas de ativos; correção da verificação de duplicatas/reativação; desativação do preenchimento automático de nutrientes na inicialização.

**Arquivos:** `src/config.py`, `src/ingredient_quality.py`, dashboard, tela de ingredientes e repositórios.

**Pacote:** `patch_qualidade_ingredientes.zip`.

**Comportamento de migração:** a reclassificação na leitura não limpa em massa os textos antigos do Google. O cadastro passa a gravar observações e pendências separadas quando é salvo pelo app.

## P15 — Padronização dos nomes e apresentação do cálcio

**Nomes de alimentos:** foi adotado o padrão ingrediente primeiro, seguido da forma, por exemplo Soja, farelo; Arroz, farelo integral; Trigo, farelo. A alteração fica nas células de `nome`, mantendo `ingredient_id` e cabeçalhos.

**Cálcio:** o ajuste inicial mostrava Ca na tabela de restrições e restaurava CA antes do cálculo. Não houve renomeação do cabeçalho Google. Esse ajuste visual foi posteriormente ampliado para todos os nutrientes em P21.

Essas alterações foram orientações de edição/padronização, não um pacote independente de migração de nomes.

## P16 — Cadastro por perfil e persistência de ingredientes

**Investigação:** Administrador e Formulador tinham permissão no código. A primeira tentativa de inclusão relatada não foi localizada na base nem na auditoria; sua causa específica não foi comprovada. Testes posteriores do usuário mostraram os cadastros Teste e Teste 2, com aumento do total de ativos.

**Problema reproduzido:** uma instância com catálogo em cache podia regravar a aba inteira e eliminar uma inclusão recente de outra instância.

**Correção entregue no módulo CQBAL:** leitura atual antes de gravar, append para novas linhas, atualização apenas do registro editado, conferência por ID e valores, auditoria por append e confirmação persistente após recarregamento. Evolução de schema passa a acrescentar colunas sem limpar/reordenar o catálogo.

**Limitação:** a trava protege operações no mesmo processo, não transações distribuídas. As rotinas de outras entidades não foram integralmente substituídas.

**Pacote que incorpora a correção:** `patch_importacao_cqbal.zip`.

## P17 — Base de referência CQBAL e definição de unidades

Foram consultados cinco exemplos de cada uma de sete categorias e extraídos 35 relatórios completos, com 1.156 registros e 200 códigos de nutrientes/estimativas. Foram entregues planilha, CSVs e transcrições HTML com procedência. Esse trabalho foi uma extração de referência, não uma importação automática desses 35 alimentos para a base do app.

A comparação mostrou que nem todos os nutrientes da base aparecem em cada relatório. Iodo e selênio não constavam nos 35 exemplos. N e S das colunas estatísticas não devem ser confundidos com teores de nitrogênio e enxofre.

**Decisão adotada:** todos os teores da base em %, incluindo microminerais; macrominerais da fonte em g/kg ou % com escolha explícita; microminerais da fonte em mg/kg. Não deduzir a unidade pela magnitude do número e não converter automaticamente entre matéria natural e matéria seca.

## P18 — Importação do Relatório Completo CQBAL

**Nova interface:** Ingredientes > Importar CQBAL, para Administrador e Formulador, com um PDF digital por alimento, identificação, prévia, confirmação e escolha entre criação e atualização por ID.

**Mapeamento:** MS, PB, EE, MM, FB e AMIDO em %; NDT apenas de NDT OBS; FDA/FDN apenas dos códigos exatos. Variantes e estimativas ficam na procedência.

**Conversões:** macrominerais g/kg ÷ 10; microminerais mg/kg ÷ 10.000; valores já em % são mantidos. A confirmação de unidade é obrigatória. O registro antigo não é reconvertido.

**Schema:** EE, MM e FB ampliam o catálogo de 20 para 23 nutrientes; `cqbal_dados` preserva a procedência. Os novos nutrientes também entram na estrutura dos itens de dieta. Rótulos de microminerais passam de mg/kg para % e a apresentação nutricional ganha precisão de oito casas decimais.

**Procedência:** arquivo, hash, nome original, categoria, regras de unidade, método NDT e registros completos reconhecidos, incluindo N e S. Consulta/baixamento disponíveis na edição.

**Limites:** PDF digital de um alimento, até 10 MB/20 páginas, com seção Nutrientes Calculados; sem OCR. Dados ambíguos, inválidos ou procedência acima do limite adotado são recusados.

**Arquivos principais:** `src/cqbal_import.py`, `src/pages/cqbal.py`, `src/pages/ingredients.py`, `src/config.py`, repositórios, `src/exports.py`, `src/pages/formulation.py` e `requirements.txt`.

**Dependência:** pdfplumber.

**Pacote:** `patch_importacao_cqbal.zip`.

## P19 — Revisão da importação: ausentes recebem zero

**Pedido posterior:** todo nutriente sem informação importável deve receber 0 na composição.

**Alteração:** campos sem média, ausentes ou sem código exato elegível são preenchidos com zero. Isso inclui NDT quando NDT OBS não existe; nenhuma estimativa alternativa é usada. A prévia mostra os preenchimentos e a procedência registra `politica_ausentes` e `campos_preenchidos_com_zero`.

Zeros realmente publicados continuam distinguíveis dos zeros inseridos por ausência de informação. N e S ausentes permanecem ausentes na procedência, pois são estatísticas. O cadastro mantém uma pendência identificando a composição parcial.

**Escopo:** importações e atualizações pelo módulo CQBAL. Não houve conversão retroativa de todas as células vazias da base.

**Arquivos de produção alterados nessa revisão:** `src/cqbal_import.py` e `src/pages/cqbal.py`.

**Pacote:** revisão do mesmo `patch_importacao_cqbal.zip`; substitui a regra de campos em branco da primeira entrega.

**Validação registrada da versão revisada:** 11 testes novos executados e um teste de solver não executado por ausência de SciPy; oito testes existentes selecionados; conferência das transcrições dos 35 relatórios e do PDF real de algodão; testes de interface para Administrador, Formulador e Consulta. Esses números descrevem a entrega, não o total atual da suíte.

## P20 — Prévia de diagnóstico da dieta inviável

**Problema:** a tela mostrava somente mensagens de erro e faixas de nutrientes, sem uma mistura para visualizar os teores.

**Correção:** um segundo problema de otimização é executado quando o cálculo normal é inviável. Inclusões e soma de 100% são mantidas; restrições nutricionais recebem folgas normalizadas. O objetivo é minimizar a soma dos desvios relativos, não o custo.

**Interface:** tabela com mínimo, teor simulado, máximo, falta e excesso; mistura e custo simulados; aviso de resultado desatualizado após mudar dados. A prévia permanece marcada como não aprovada e o fluxo retorna antes das opções de salvar uma dieta válida.

**Arquivos:** `src/solver.py` e `src/pages/formulation.py`.

**Pacote:** `patch_previa_inviabilidade.zip`.

**Ocorrência na aplicação:** a primeira imagem após a instalação mostrava só as mensagens. A inspeção local encontrou o solver atualizado e a tela de formulação antiga. Foi orientada a substituição também de `src/pages/formulation.py`, no caminho exato.

**Teste de uso proposto:** milho com PB 8,5% e farelo de soja com PB 45%, ambos com inclusão de 0–100%, e exigência única de PB mínima de 50%. A mistura não pode alcançar 50%; a prévia esperada atinge 45%, faltando cinco pontos percentuais. Esses números dependem da composição cadastrada.

**Validação da entrega:** seis cenários conferidos com referência independente por enumeração de vértices e teste da interface. A execução com SciPy/HiGHS ficou pendente no ambiente de preparação, pois a instalação da dependência foi bloqueada. O pacote inclui testes para execução no ambiente do projeto. A suíte completa não foi declarada aprovada nessa entrega.

## P21 — Nomes completos nas restrições nutricionais

**Pedido:** substituir siglas isoladas por nome completo, sigla e unidade entre parênteses.

**Correção:** o editor usa rótulos derivados de `NUTRIENT_BY_CODE`, como Matéria seca - MS (%), Proteína bruta - PB (%) e Cálcio - Ca (%). Os rótulos são convertidos de volta para os códigos antes de calcular/salvar. A coluna foi ampliada e a chave visual do editor atualizada para não reaproveitar o estado antigo.

**Arquivo:** `src/pages/formulation.py`.

**Pacote:** `patch_nomes_restricoes.zip`.

**Validação:** sintaxe e correspondência de ida/volta dos 23 rótulos, preservando os códigos internos. Não há alteração do schema Google.

## P22 — Persistência de preço e limites na seleção de ingredientes — 26/10/2026

**Base:** branch `main` do GitHub, commit `f627c44126c83aaebd1e28029f87bd75f1504b62` (Organização de arquivos).

**Sintoma:** ao adicionar outro ingrediente antes de calcular, preços e limites já digitados podiam voltar aos padrões do catálogo.

**Causa:** o editor de ingredientes estava dentro de um formulário, que só enviava suas alterações no cálculo. A seleção ficava fora do formulário; ao mudar, reconstruía o editor sem as alterações ainda não submetidas.

**Correção:** a grade de ingredientes passa a enviar cada edição confirmada para a sessão. Callbacks do editor e da seleção reconciliam as alterações com a base estável anterior, usando `ingredient_id` e não a posição na seleção nova. A base do editor continua estável durante o preenchimento normal. As restrições nutricionais e o comando de cálculo mantêm submissão explícita pelo formulário.

**Comportamento esperado:** adicionar, remover ou reordenar ingredientes preserva os valores dos que permanecem. Apenas os novos recebem o preço padrão e os limites de 0–100%. Preço zero, Sem custo e limite máximo zero são preservados. Um preço apagado não é reposto silenciosamente pelo catálogo. Um ingrediente removido e depois reinserido recebe os padrões de uma nova inclusão. Remover todos limpa a seleção corrente. Carregar outra dieta ou usar Limpar não reaplica alterações antigas.

**Escopo:** valores da formulação na sessão. Não grava preços/limites no catálogo Google e não altera nutrientes, unidades, solver, exportação PDF ou login. A composição nutricional continua sendo atualizada pelo catálogo.

**Arquivos:** `src/pages/formulation.py`, `tests/test_formulation_item_state.py` e `PATCHES.md`. `README.md` foi mantido sem alteração, pois esta entrega corrige um comportamento existente, sem adicionar funcionalidade.

**Pacote:** `patch_persistencia_formulacao_20261026.zip`.

**Validação:** 10 novos testes aprovados, incluindo teste de interface Streamlit que muda a seleção sem calcular, confirma a preservação por ID e verifica a posição do editor fora do formulário. A suíte completa executou 66 testes: 64 passaram e duas falharam. As mesmas duas falhas foram reproduzidas no código original do commit de base: os testes `test_exact_codes_and_missing` e `test_no_ndt_fallback`, em `tests/test_cqbal_import.py`, ainda esperam None para ausentes, embora a regra vigente do importador seja zero. Esses testes e o importador CQBAL não foram alterados nesta atualização.

**Aplicação:** substituir o arquivo de tela no caminho exato, incluir o teste e atualizar este histórico; reiniciar/republicar. Não aplicar versões antigas de `src/pages/formulation.py` sobre esta correção. Testar com uma formulação nova após a atualização, pois edições já perdidas pela versão anterior não são recuperadas.

## P23 — Identificação do login e símbolo do cálcio no PDF — 26/10/2026

**Base:** branch `main` do GitHub, commit `50bbbc4f527d0ea84dc953606bec3f1c76e5eda0`, já com a atualização de persistência P22.

**Correções:** a entrada por email/senha e a entrada Google passam a mostrar o título `RFB - RUMINANT DIET FORMULATION SYSTEM`, seguido de `PLATAFORMA WEB PARA FORMULAÇÃO E OTIMIZAÇÃO DE DIETAS PARA RUMINANTES`. O nome e a descrição são apresentados em dois blocos para facilitar a leitura. Na tabela de restrições do PDF, o código `CA` é exibido como `Ca`.

**Escopo:** apresentação. A autenticação mantém seu funcionamento; `CA` continua como código interno e nas tabelas Google. Não há mudança em cálculos, unidades, CSV/Excel, dietas salvas ou importação CQBAL. A correção P22 permanece intacta.

**Arquivos:** `src/auth.py`, `src/exports.py` e `PATCHES.md`. `README.md` permanece inalterado porque não há nova funcionalidade.

**Validação:** 15 testes existentes aprovados (exportações, segurança e persistência de ingredientes). Verificação adicional com Streamlit AppTest dos dois modos de login, sem autenticação real. PDF gerado, conteúdo extraído e página renderizada inspecionada: Ca correto, outros símbolos e valores preservados e sem alteração dos dados de entrada. Nenhuma gravação Google ou implantação foi realizada. A suíte completa não foi repetida nesta etapa; as duas falhas preexistentes CQBAL documentadas em P22 não foram tratadas.

**Pacote:** `patch_visual_login_pdf_20261026.zip`. Aplicar depois de P22, copiar os arquivos nos mesmos caminhos e publicar/reiniciar. Nenhuma migração da planilha ou dependência nova é necessária.

## P24 — CQBAL em português/inglês, EM e aminoácidos — 26/10/2026

**Base:** `main`, commit `6da09b26abe8ee6fc5b9d4f82bfdb8c0e545310f` (Correções visuais tela login e pdf exportado), com P22 e P23 aplicados.

**Funcionalidades:** importador bilíngue com identificação automática de idioma, correspondência exata de siglas, dez aminoácidos e Energia Metabolizável em cadastro, edição, formulação, persistência e exportações. As funcionalidades e o uso estão documentados em `README.md` e `docs/CQBAL_PT_EN.md`.

**Regras:** MS/DM, PB/CP, MM/ASH, FB/CF, FDN/NDF, FDA/ADF, AMIDO/STARCH e NDT OBS/OBS TDN. O idioma traduz nomes e siglas, não converte valores. Mantidas as conversões explícitas de macrominerais e microminerais e o zero para ausentes no CQBAL. Apenas EM_BRCORTE2016/ME_BRCORTE2016 da seção calculada preenche EM (Mcal/kg). Aminoácidos Lys, Met, Thr, Phe, Leu, Ile, Val, His, Arg e Tyr em % do alimento. O usuário confirma unidades e base de expressão; não há inferência de unidades pelo idioma ou conversão seca/natural. Valores conflitantes de siglas equivalentes são rejeitados. Os campos estatísticos e demais dados não mapeados continuam na procedência.

**Procedência e interface:** JSON versão 2 registra idioma, categoria original, unidades por campo e método energético. A prévia passa a usar valor e unidade de destino em colunas distintas, evitando chamar EM de porcentagem. O campo legado `valor_em_porcentagem` é preservado na função de conversão para compatibilidade, mas fica vazio para EM. O nome do alimento não é traduzido automaticamente; atualizar um cadastro exige seleção por ID.

**Schema:** o registro central passa de 23 para 34 nutrientes. O mecanismo existente acrescenta as 11 colunas novas ao final de rb_ingredientes e rb_dieta_ingredientes durante a inicialização; não reordena colunas nem preenche linhas antigas. Não houve acesso de escrita ao Google durante a preparação. Solver e exportadores já usam o registro central; não precisaram de substituição. Seus cálculos ponderam todos os teores pela fração de inclusão, inclusive Mcal/kg.

**Testes corrigidos:** os dois testes antigos do CQBAL que ainda exigiam None para ausentes agora verificam zero, conforme a política já vigente; a contagem da prévia passa a permitir linhas sintéticas dos ausentes. Não se alterou a política para satisfazer testes antigos.

**Validação:** os dois PDFs digitais reais fornecidos foram lidos integralmente: 118 registros cada, mesmos 34 campos finais e mesmas nove ausências. Comparação congelada em fixtures textuais. Foram acrescentados 14 testes de equivalência, seleção estrita, conversões, procedência, conflito de aliases, cadastro manual, importação pela tela nos dois idiomas, preservação de preço/histórico, solver com EM e Lys, salvamento/carregamento e expansão de cabeçalhos Google simulados. A suíte completa teve 80 testes aprovados. Exportação PDF também foi renderizada e conferida visualmente. Nenhuma implantação ou gravação no Google real foi executada.

**Pacote:** `patch_cqbal_bilingue_em_aminoacidos_20261026.zip`. Aplicar após P23, com backup das planilhas. A reinicialização em produção acrescentará cabeçalhos; a aplicação do pacote não reimporta o catálogo. PDFs de outros sistemas, digitalizados ou com layouts não reconhecidos não são cobertos.

## P25 — ZINC, EM em kcal/g e vinte aminoácidos — 26/10/2026

**Base:** `main`, commit `d69dd3669dcb0c74287c26fe22b9c6b6fbb80cea` (Importação CQBal em Br e Ing), com P24 aplicado.

**Correções e ampliação:** alias inglês ZINC para Zn, mantendo a conversão de microminerais mg/kg para %. EM importada de Mcal/kg e convertida automaticamente para kcal/g; fator 1, portanto 3,21 permanece 3,21. Cadastro, restrições, resultados e exportações usam kcal/g. Adicionados Ala, Asn, Asp, Cys, Gly, Glu, Gln, Pro, Ser e Trp aos dez aminoácidos existentes: vinte aminoácidos e 44 nutrientes no total.

**Compatibilidade:** não mapear letras únicas como aminoácidos; I, K, P e S continuam sendo minerais. Os campos por três letras e suas formas em maiúsculas são reconhecidos. Mantidos zero para ausentes no CQBAL, seleção estrita de NDT observado/FDA/FDN, método energético BR-CORTE 2016, conversões de minerais e preservação da procedência completa. Valores divergentes de Zn e ZINC no mesmo relatório são rejeitados como conflito.

**Energia legada:** a normalização de leitura de restrições apresenta EM antes identificada por Mcal/kg como kcal/g, convertendo também limites e resultados pelo fator 1. Não há alteração dos números nem da base seca/natural, regravação automática das planilhas ou edição do JSON de procedência antigo. A normalização é idempotente e é utilizada na visualização, reabertura e exportação das dietas. Procedência nova versão 3 registra unidade de origem, destino e fator energético.

**Schema:** o mecanismo existente acrescenta somente as dez colunas novas ao final de rb_ingredientes e rb_dieta_ingredientes, sem reordenar, limpar ou completar retroativamente as linhas. A EM existente não precisa de migração numérica.

**Validação:** os quatro PDFs reais de algodão e trigo, nos dois idiomas, foram processados integralmente. Algodão: 118 registros por PDF. Trigo: 74 registros por PDF, 18 aminoácidos presentes e ZINC 64,47 mg/kg corretamente convertido para Zn 0,006447%. Ambos os pares PT/EN geraram os mesmos 44 campos finais. O trigo não possui Asn/Gln; esses dois campos são cobertos por casos sintéticos de importação dos 20 aminoácidos. Testes adicionais cobrem cadastro manual dos vinte campos, persistência e solver, conflito de aliases, preservação dos minerais de uma letra, leitura de energia antiga, fator dimensional 1 e expansão aditiva dos cabeçalhos. A suíte completa teve 94 testes aprovados. Exportação de PDF conferida visualmente. Nenhuma gravação Google ou publicação foi realizada na preparação.

**Documentação e pacote:** funcionalidades e regras atuais em README.md e docs/CQBAL_PT_EN.md. Pacote `patch_zinc_em_kcalg_20_aminoacidos_20261026.zip`, aplicar após P24. A reinicialização em produção acrescenta as dez colunas, sem reimportar ingredientes. Cadastros importados anteriormente com ZINC ignorado devem ser reimportados explicitamente por ID para recuperar esse valor; somente trocar o código não repara essas composições históricas.

## P26 — Painel administrativo de importação CQBAL — 26/10/2026

**Base:** código local d37c5e7 (Correção ZINC e Mcal), após P25.

**Comportamento:** Administração ganha um painel exclusivo de administradores ativos para selecionar os atributos das próximas importações CQBAL. Os 44 campos anteriores são o padrão. Selecionados e ausentes recebem zero; desmarcados não sobrescrevem valores existentes. Configuração global persistida e auditada, com versão e conferência antes da gravação.

**Referência e catálogo:** Milho Fubá ID 1, com HTML para conferência. União de 2.245 relatórios: 347 campos, 230 presentes no alimento de referência. 144 campos compatíveis com mistura linear (100 adicionais ao cadastro anterior); parâmetros de razões, cinética, pH e unidades não validadas são preservados para conferência e exigem modelos próprios antes de uso como restrição.

**Importador:** aceita JSON completo e HTML de conferência além dos PDFs anteriores. Prévia aplica a seleção global. Novos teores habilitados são persistidos em ingredientes e snapshots de dietas e aparecem nas restrições dinâmicas. Procedência versão 4 preserva a política aplicada e atributos anteriores desmarcados. Siglas ambíguas solicitam o JSON com IDs.

**Schema:** nova tabela cqbal_config (prefixo padrão rb_); 100 colunas adicionais nos schemas de ingredientes e itens de dietas. A migração acrescenta cabeçalhos no Sheets sem preencher retroativamente os valores. Catálogo e referência ficam em src/data. Não há dependência nova nem mudança nas fórmulas do solver linear.

**Validação:** 107 testes aprovados, incluindo permissões no backend, editor administrativo, política compartilhada com Google simulado, importação JSON/HTML, preservação de desmarcados, zeros e novo atributo usado em dieta salva/reaberta. Sem chamadas ao Google real, alterações na base de produção ou publicação. Detalhes em docs/PAINEL_CQBAL.md.

**Pacote:** patch_painel_importacao_cqbal_20261026.zip. README e documentação atualizados. Aplicar como conjunto de arquivos sobre a base indicada; preservar backups de código e abas antes de publicar.

## Inventário dos pacotes documentados

| Pacote | Entrada |
|---|---|
| `correcao_estado_data_editor_patch.zip` | P02 |
| `correcao_solver_nan_patch.zip` | P03 |
| `correcao_base_nutricional_patch.zip` | P04 — comportamento automático superado |
| `correcao_composicao_nutricional_patch.zip` | P05 |
| `correcao_numeros_ptbr_patch.zip` | P06 |
| `correcao_calcular_dieta_form_patch.zip` | P07 |
| `correcao_fuso_horario_patch.zip` | P08 |
| `correcao_login_multiusuario_patch.zip` | P09 |
| `melhorias_formulacao_patch.zip` | P10 |
| `correcao_carregar_dieta_salva_patch.zip` | P11 |
| `correcao_exportacao_dieta_salva_patch.zip` | P12 |
| `restricoes_nutricionais_dinamicas_patch.zip` | P13 |
| `correcao_custos_dashboard_patch.zip` | P13 |
| `patch_qualidade_ingredientes.zip` | P14 |
| `patch_importacao_cqbal.zip` | P16, P18 e revisão P19 |
| `patch_previa_inviabilidade.zip` | P20 |
| `patch_nomes_restricoes.zip` | P21 |
| `patch_persistencia_formulacao_20261026.zip` | P22 |
| `patch_visual_login_pdf_20261026.zip` | P23 |
| `patch_cqbal_bilingue_em_aminoacidos_20261026.zip` | P24 |
| `patch_zinc_em_kcalg_20_aminoacidos_20261026.zip` | P25 |
| `patch_painel_importacao_cqbal_20261026.zip` | P26 |

Os arquivos originais de integração e entrega do MVP também foram considerados na consolidação, mesmo sem um ZIP separado nesta lista.

## Como aplicar novas evoluções sem perder as anteriores

1. Faça backup do código e das abas afetadas; pare as gravações durante a atualização.
2. Confira a versão de origem e os caminhos dos arquivos do pacote. Várias evoluções substituem `src/pages/formulation.py`; aplicar uma versão antiga por último pode remover melhorias recentes.
3. Use cópia dos arquivos ou `git apply`, não os dois métodos. Faça a verificação do patch antes da aplicação e resolva diferenças de código.
4. Atualize as dependências quando o pacote alterar `requirements.txt`.
5. Publique, reinicie e recalcule; estados e resultados antigos de uma sessão não confirmam que o código novo foi executado.
6. Verifique os fluxos afetados com os perfis apropriados e confira a gravação no backend correto.
7. Rode os testes no ambiente com todas as dependências. Resultados históricos de testes são registros de entregas específicas, não uma nova validação da versão atual.

Esta consolidação substitui a necessidade de manter narrativas concorrentes nos vários arquivos de correção. Ela não apaga os documentos antigos nem os pacotes; eles podem permanecer arquivados como evidência histórica. Nenhuma execução de código, migração de dados ou implantação é feita por estes documentos.
