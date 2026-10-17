# Atualização: importar Relatório Completo do CQBAL

## Aplicar

1. Faça backup do projeto e das abas `rb_ingredientes` e `rb_dieta_ingredientes`. Aplique com o app parado e sem outros usuários gravando.
2. Extraia o ZIP em uma pasta temporária. Copie o conteúdo de `src`, `tests` e `requirements.txt` para a raiz do projeto, mesclando as pastas e substituindo somente os arquivos incluídos. Não substitua a pasta src inteira por uma pasta vazia.
3. Instale/atualize as dependências com `python -m pip install -r requirements.txt`. Foi acrescentado pdfplumber para ler os PDFs digitais.
4. Publique as alterações e reinicie o app. No Streamlit Cloud, mantenha requirements.txt na raiz para a instalação automática.
5. Abra Ingredientes > Importar CQBAL. Envie o PDF de um único alimento. Confirme a unidade dos macrominerais, confira a prévia, escolha cadastrar ou atualizar e confirme o salvamento.

Alternativa à cópia: na raiz do projeto, valide `git apply --check --ignore-space-change atualizacao.patch` e depois execute `git apply --ignore-space-change atualizacao.patch`. Use apenas um dos métodos. O patch foi preparado para a cópia local fornecida nesta conversa; alterações posteriores devem ser conciliadas antes de substituir os arquivos.

## Regras da importação

- MS, PB, EE, MM, FB, FDA, FDN, AMIDO e NDT ficam em porcentagem.
- NDT recebe exclusivamente NDT OBS. NDT calculado ou in vitro não preenche esse campo.
- FDA e FDN recebem exclusivamente os códigos exatos. FDAp, FDNcp, FDNi e demais variantes são preservados na procedência, sem substituição.
- Macrominerais: a unidade de origem deve ser confirmada. g/kg é dividido por 10; % é mantido. Isso inclui Cl quando presente, além de Ca, P, Mg, K, Na e S.
- Microminerais Fe, Cu, Mn, Zn, Co, I e Se: origem mg/kg; o valor é dividido por 10.000 para armazenar em %.
- Nutrientes ausentes, sem média ou sem código importável recebem 0 na composição. Zeros publicados são preservados. A prévia diferencia os zeros publicados dos zeros usados por ausência de dados; a procedência lista os campos preenchidos com zero. N e S ausentes na fonte continuam sem valor na procedência, pois são informações estatísticas, não teores nutricionais.
- Os valores existentes da base NÃO são convertidos. Conforme combinado, foram considerados já expressos em %. Os rótulos de microminerais passam para %.
- A importação exige confirmação da base de expressão. Ela não converte matéria natural para matéria seca. Só importe após conferir que a base corresponde à usada no cadastro/dieta.
- PDFs digitalizados, corrompidos, com vários alimentos ou sem a seção Nutrientes Calculados são rejeitados. Limites: 10 MB e 20 páginas. Não há OCR.
- Nutrientes calculados, valores negativos calculados, N e S e todos os dados reconhecidos das tabelas são guardados em `cqbal_dados` (JSON). Valores negativos em campos importáveis são rejeitados.
- Nome e classificação podem ser revisados. A atualização é escolhida explicitamente por ID. Ela substitui a composição; campos ausentes no relatório recebem zero. Preço e demais dados do cadastro existente são preservados.
- Não há comparação aproximada de nomes. Um nome invertido como “Caroço de algodão” pode não coincidir com “Algodão caroço”; para atualizar, selecione explicitamente o cadastro correto.
- A procedência pode ser consultada/baixada na aba Editar. Ela registra o arquivo, hash SHA256, nome original, categoria, unidades escolhidas, método do NDT, médias, N e S. A data e o responsável permanecem nos campos de cadastro/auditoria e nas observações.
- Há limite de 45.000 caracteres para armazenar procedência em uma célula. Relatórios maiores são recusados sem gravação.

## Estrutura e gravação

- Novos campos nutricionais: EE, MM e FB. Aparecem no cadastro, nas restrições dinâmicas e na exportação. Só aparecem na formulação quando há composição declarada.
- Nova coluna de ingredientes: `cqbal_dados`. EE/MM/FB também entram na estrutura dos itens de dieta.
- A inicialização acrescenta colunas ausentes ao final dos cabeçalhos Google, sem limpar ou reordenar os registros. Não renomeie os cabeçalhos existentes manualmente.
- Criação/edição de ingredientes no Google passa a acrescentar/atualizar apenas a linha correspondente. O salvamento lê dados atuais e confirma os valores gravados. A auditoria acrescenta linhas sem regravar a aba inteira.
- Edição e reativação verificam duplicatas ativas. As mensagens de sucesso persistem após o recarregamento para cadastro manual e CQBAL.
- O preenchimento automático de nutrientes ao iniciar continua desabilitado.
- A trava de gravação cobre sessões no mesmo processo. Não é uma transação distribuída: edições simultâneas do mesmo registro em processos distintos ainda exigem coordenação. Outras entidades (dietas e usuários) mantêm suas rotinas anteriores.
- Se a gravação do ingrediente for confirmada mas a auditoria falhar, o ingrediente é mantido e a falha de auditoria é registrada nos logs. Não se tenta desfazer um ingrediente já confirmado.
- A precisão visual dos nutrientes nas restrições/resultados e exportações sobe para oito casas para preservar microminerais pequenos. Custos e inclusões mantêm suas regras anteriores.
- Dietas antigas não são convertidas; confira seus rótulos/unidades antes de reutilizá-las.

## Validação

- 11 testes novos executados: parsing, conversões, campos exatos, preenchimento de ausentes com zero, distinção de zeros publicados, procedência, rejeição de entradas, PDF digital, gravação Google simulada, cache, duplicatas e evolução de cabeçalho.
- 1 teste adicional de solver foi incluído, mas não executado aqui porque SciPy não está instalado no ambiente de preparação.
- 8 testes existentes selecionados executados diretamente: CRUD, Google simulado, inicialização, migração, exportação e apresentação.
- Parsing conferido nas transcrições dos 35 relatórios extraídos na conversa (1.156 registros) e no PDF real de Algodão — Caroço.
- Testes de interface Streamlit: prévia e salvamento para Administrador e Formulador, acesso negado a Consulta, mensagem persistente e nenhuma nova gravação em simples recarregamento.
- Não houve gravação no Google real nem modificação do repositório original. Não foi executada a suíte pytest completa neste ambiente.

Para repetir os testes novos:

`python -m unittest discover -s tests -p "test_cqbal*.py" -v`

Com as dependências completas instaladas, rode também:

`python -m pytest tests -q`

## Reversão

Restaure o backup do código e das abas. Antes de restaurar a base, preserve os cadastros feitos após a atualização. Versões antigas podem remover colunas que não reconhecem ao regravar tabelas.

`originais_sha256.json` registra os hashes dos arquivos de origem usados para gerar o patch.
