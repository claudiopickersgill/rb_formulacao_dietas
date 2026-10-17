# Prévia de diagnóstico para dietas inviáveis

## Aplicação

1. Faça backup do projeto.
2. Extraia este pacote em uma pasta temporária.
3. Copie o conteúdo de `src` e `tests` para a raiz do projeto, mesclando pastas e substituindo somente os arquivos incluídos.
4. Reinicie/republique o app.

Alternativa à cópia: valide `git apply --check --ignore-space-change atualizacao.patch` e aplique com `git apply --ignore-space-change atualizacao.patch`, na raiz do projeto. Use apenas um dos métodos. O patch foi gerado contra o código local atual; alterações posteriores devem ser conciliadas antes da substituição.

Arquivos de produção alterados: `src/solver.py` e `src/pages/formulation.py`. Nenhuma dependência nova; SciPy já consta nos requisitos do projeto. Nenhuma alteração na estrutura da planilha Google.

## O que aparece

Se o cálculo normal resultar em inviabilidade, os diagnósticos anteriores continuam na tela. Abaixo deles, uma prévia adicional apresenta:

- mistura simulada e percentuais de inclusão;
- custo simulado por kg;
- mínimo solicitado, teor simulado e máximo solicitado de cada nutriente;
- quanto falta para o mínimo e quanto excede o máximo;
- situação de cada nutriente, incluindo os sem restrição.

Uma mistura inviável não é uma solução válida retornada pelo cálculo de menor custo. Por isso, a prévia vem de um segundo cálculo, usado exclusivamente para diagnóstico.

## Critério da simulação

A soma de inclusões continua igual a 100% e os limites de inclusão dos ingredientes permanecem obrigatórios. Apenas as restrições nutricionais recebem folgas. A simulação minimiza a soma dos desvios relativos dessas restrições. Cada desvio é normalizado pela maior magnitude dos limites definidos para aquele nutriente, evitando que a escala de um macronutriente domine automaticamente a de um micromineral. Para limites iguais a zero, usa-se a escala da composição.

O objetivo não considera o custo. O custo exibido é apenas o custo da mistura de diagnóstico. Pode existir mais de uma mistura com o mesmo desvio total; a prévia não é necessariamente única nem constitui recomendação de fornecimento.

Os dados nutricionais originais e as restrições solicitadas não são modificados. O resultado continua com `success=False` e status inviável. A tela retorna antes dos controles de salvar/exportar uma dieta aprovada. Alterações posteriores dos ingredientes ou limites exibem aviso de que a prévia corresponde ao cálculo anterior.

Erros de preenchimento, preços inválidos ou dados ausentes continuam no fluxo de validação. Se os limites de inclusão não permitirem somar 100%, não será apresentada uma mistura artificial que viole esses limites. Falhas numéricas também não geram prévia apresentada como solução.

## Testes

O pacote inclui seis cenários: proteína inalcançável, respeito ao máximo de inclusão, conflito entre nutrientes com micromineral, excesso acima de máximo, manutenção da solução viável e rejeição de entrada inválida.

No ambiente de preparação, os seis cenários foram exercitados com uma implementação independente de referência por enumeração de vértices para os pequenos problemas de teste. A interface Streamlit também foi verificada: duas tabelas presentes, aviso de cálculo antigo e ausência de botão de salvar para a prévia.

Isso não substitui a execução com SciPy/HiGHS. SciPy não estava instalado no ambiente de preparação; a rede e a política de aprovação bloquearam seu download. A execução numérica real com esse backend permanece pendente.

No ambiente do projeto, com as dependências instaladas, execute:

`python -m unittest discover -s tests -p test_infeasible_preview.py -v`

Depois execute a suíte existente:

`python -m pytest tests -q`

Não houve gravação no Google Sheets nem alteração do repositório original. Para reverter, restaure os dois arquivos de produção a partir do backup. `originais_sha256.json` identifica os arquivos usados como base.
