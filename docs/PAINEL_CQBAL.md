# Painel de Importação CQBAL

## Uso

1. Entre como administrador e abra **Administração > Painel de Importação CQBAL**.
2. Compare os campos com o HTML do **Milho Fubá, ID 1**, disponível para baixar no painel. O valor exibido na referência não é usado para preencher outros alimentos.
3. Marque ou desmarque a coluna **Importar** e clique em **Salvar configuração de importação**. Os 44 campos já utilizados pelo RFB são o padrão inicial.
4. Em **Ingredientes > Importar CQBAL**, envie preferencialmente o `completo.json` de um alimento. Também são aceitos os HTMLs de conferência produzidos pelo exportador e os PDFs digitais anteriores.
5. Confirme as unidades e a prévia. Um campo selecionado sem valor importável recebe zero; um desmarcado não é importado. Ao atualizar um cadastro, os desmarcados mantêm os valores anteriores.
6. Após importar um novo teor compatível, selecione o ingrediente na formulação. O atributo aparece nas restrições dinâmicas e pode receber mínimo e máximo. A dieta salva preserva o valor utilizado.

Use **Restaurar seleção padrão do RFB** para voltar aos 44 campos anteriores. Isso só altera futuras importações; não recalcula dietas nem apaga ingredientes.

## Catálogo e interpretação

O catálogo é a união de 2.245 arquivos completos encontrados nos downloads, não apenas a lista do alimento com mais campos. São 347 campos, dos quais 230 estão presentes no Milho Fubá. Há atributos próprios de outros alimentos e modelos de estimativa. Esses números representam campos distintos por definição/identidade CQBAL, não o ranking anterior que deduplicava apenas pela sigla.

Os campos anteriores continuam usando seus códigos e conversões. NDT observado continua em NDT; NDT estimado por modelos diferentes fica em campos separados. EM BR-CORTE 2016 continua em EM; outras estimativas não a substituem. Micro e macrominerais mantêm suas conversões anteriores. Campos adicionais em porcentagem exigem a mesma base de expressão dos ingredientes da dieta.

Há 144 campos cadastrados como compatíveis com a mistura linear, incluindo os 44 anteriores e 100 adicionais. Os demais podem ser selecionados para importação/conferência e ficam na procedência. Não são disponibilizados ao solver como se fossem concentrações: razões em % da PB/FDN, taxas cinéticas, pH e unidades ainda não validadas precisam de conversão ou modelo específico. A coluna **Uso na formulação** mostra essa distinção antes de salvar a seleção.

Um mínimo/máximo em pH ou taxa não é equivalente à média linear dos valores de cada ingrediente. Essa evolução não implementa modelos específicos para esses parâmetros. Ativá-los para conferência não resolve essa diferença de cálculo.

Um valor zero é preenchido apenas nos atributos selecionados. Valores negativos, não finitos e teores percentuais acima de 100 nos atributos selecionados causam erro de validação, em vez de serem silenciosamente convertidos para zero. O preenchimento com zero é uma regra de importação definida pelo administrador, não uma declaração de ausência real do nutriente.

Algumas siglas inglesas são reutilizadas pelo próprio CQBAL para definições diferentes. Quando a seleção torna uma dessas siglas ambígua, o importador solicita o JSON original, que contém siglas portuguesas e IDs. Não escolhe um atributo arbitrariamente. As duas metades das linhas JSON são lidas; IDs zero dos calculados não são usados para juntar modelos distintos.

## Persistência e permissões

- A seleção é global: armazenada em `rb_cqbal_config` no Google Sheets ou `cqbal_config.csv` no backend local.
- O backend valida administrador ativo para salvar, independentemente da proteção da tela.
- Cada alteração incrementa a versão e registra autor, data e seleção anterior/nova na auditoria.
- A leitura ignora o cache dessa configuração. O formulário de importação usa a versão na identificação dos controles e confere novamente a política antes de gravar.
- Há verificação de versão esperada e bloqueio no mesmo processo para evitar sobrescritas administrativas acidentais. Google Sheets não oferece uma transação entre configuração, importação e auditoria; não há garantia de atomicidade entre múltiplos servidores independentes.
- A procedência versão 4 guarda a configuração aplicada, valores importados, atributos preservados e registros originais reconhecidos. Nomes/unidades ficam no catálogo versionado, para que a seleção integral caiba no limite de 45.000 caracteres adotado para uma célula.
- Campos antigos desmarcados continuam disponíveis em ingredientes/dietas que já possuem valores. A seleção administra a importação, não revoga restrições nutricionais anteriores.

O catálogo é distribuído com o código (`src/data/cqbal_catalog.json`). Novas definições da origem requerem atualização desse catálogo e revisão de unidade/modelo; campos desconhecidos não são incorporados automaticamente ao solver.

## Aplicação

Pacote baseado no código local `d37c5e7` — Correção ZINC e Mcal, com P25 aplicado. Copie o conteúdo nos mesmos caminhos do projeto, incluindo `src/data/`, e publique/reinicie pelo fluxo habitual. Não há dependência nova.

No primeiro início, a inicialização de schema cria a tabela de configuração e acrescenta 100 colunas aos schemas de ingredientes e itens de dietas, ao final dos cabeçalhos existentes no Google Sheets. Valores antigos não são preenchidos. Faça cópia das abas e do código antes da atualização, como nas migrações anteriores.

Para reverter o código, restaure o backup. Não remova automaticamente as colunas ou a tabela nova: podem conter importações e dietas criadas com esta versão. A base de produção não foi alterada durante a preparação do pacote.

## Validação

107 testes aprovados na preparação, incluindo a seleção pelo editor administrativo, restauração do padrão, bloqueio de formulador/consulta/admin inativo, política compartilhada em Google Sheets simulado, versão desatualizada, JSON/HTML do Milho Fubá, preservação de campos desmarcados, zero para selecionados ausentes e novo teor importado, usado no solver, salvo e reaberto em dieta.

A suíte também cobre os fluxos anteriores de minerais, aminoácidos, energia, armazenamento, autenticação e formulação. O teste de Google usa uma simulação, sem chamadas à planilha real. Não houve publicação nem validação de produção.
