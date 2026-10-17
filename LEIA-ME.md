# Atualização da qualidade dos ingredientes

## Aplicação por substituição
1. Faça backup do projeto e duplique a aba rb_ingredientes no Google Sheets.
2. Extraia este ZIP em uma pasta temporária.
3. Copie as pastas src e tests deste pacote para a raiz do projeto, mesclando pastas e substituindo somente os arquivos incluídos. Não substitua a pasta src inteira por uma pasta vazia.
4. Reinicie o WebApp/limpe o cache do Streamlit.
5. Confira: para a base inspecionada em 17/10/2026, 74 ativos e 1 ativo com pendência (Brasão 60P).

Alternativa: aplique atualizacao.patch com git apply --ignore-space-change atualizacao.patch, em vez de copiar os arquivos. Não use os dois métodos. Antes, valide com git apply --check --ignore-space-change atualizacao.patch. O patch foi preparado a partir da cópia local fornecida; alterações posteriores precisam ser conciliadas.

## Comportamento
- O dashboard conta e exibe somente ingredientes ativos com pendências.
- A nova coluna observacoes guarda informações que não geram alerta e aparece na consulta, edição e exportação.
- A classificação das notas antigas ocorre na leitura, por regras conservadoras. Não há migração em massa das células de qualidade_dados: a nota original permanece na planilha até que o cadastro seja salvo pelo app. Ao salvar, observações e pendências são gravadas separadamente.
- A inicialização do repositório Google acrescenta observacoes ao schema existente, usando o mecanismo de atualização de schema do app. Esse mecanismo regrava a tabela; faça o backup antes do primeiro reinício. Nenhuma alteração foi executada no Google durante a preparação do pacote.
- Textos desconhecidos permanecem como pendência. Avisos de duplicidade legada só são reclassificados quando existe exatamente uma ocorrência ativa do mesmo tipo e nome. Isso não substitui validação nutricional.
- Os 11 inativos continuam disponíveis na consulta. A tabela do dashboard exibe todas as pendências ativas, sem o corte anterior de dez registros.
- Edição e reativação verificam duplicatas ativas; a camada de armazenamento também protege gravações e importações. Inativos podem coexistir para preservar IDs históricos. O seletor de edição mostra situação e ID.
- O preenchimento automático de nutrientes ao iniciar foi desabilitado para todos os ingredientes. A rotina auxiliar permanece no código para manutenção explícita, sem chamada na inicialização; seu registro informativo passa para observacoes.
- Nenhum valor nutricional foi corrigido ou confirmado por este patch. Os campos desconhecidos do Brasão permanecem desconhecidos.

## Arquivos
src/config.py
src/ingredient_quality.py (novo)
src/pages/dashboard.py
src/pages/ingredients.py
src/repositories/tabular.py
src/repositories/google_sheets.py
tests/test_ingredient_backfill.py
tests/test_ingredient_quality.py (novo)

## Validação realizada
- Sintaxe de todos os arquivos Python do pacote.
- Snapshot da base: 24 textos originais -> 1 pendência ativa e 23 observações; classificação idempotente sem modificar o snapshot original.
- Testes de edição, preservação de observações, criação de duplicata, bloqueio e liberação de reativação.
- Teste existente de CRUD local.
- Inicialização Google simulada: nutrientes vazios permanecem vazios.
- Não foi feita gravação real no Sheets nem teste visual em um app publicado.
- O executor pytest não está instalado no ambiente de preparação. Os testes novos foram executados com unittest e os testes existentes selecionados foram chamados diretamente.

Para repetir os testes novos na raiz do projeto:
python -m unittest discover -s tests -p test_ingredient_quality.py -v

Com pytest instalado, execute também a suíte do projeto:
python -m pytest tests -q

## Reversão
Restaure os arquivos de código do backup. Caso volte ao código antigo, restaure também a cópia da aba ou preserve observacoes separadamente: o mecanismo antigo de schema pode remover essa coluna por não reconhecê-la.

originais_sha256.json registra os hashes dos arquivos de origem para conferência; não contém credenciais.
