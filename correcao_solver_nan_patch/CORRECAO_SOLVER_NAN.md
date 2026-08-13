# Correção do solver — valores vazios do Google Sheets

## Problema

O Google Sheets devolve células vazias como strings vazias (`""`). A validação anterior verificava apenas `NaN`/`None` na coluna original. Quando `pd.to_numeric(..., errors="coerce")` era executado no solver, essas strings viravam `NaN` e eram inseridas em `A_ub`, causando `ValueError` no `scipy.optimize.linprog`.

## Alterações

- Validação agora converte a composição usada nas restrições para número antes do solver.
- Células vazias/não numéricas em **alimentos** geram mensagem amigável com o nome do ingrediente e nutriente.
- Células vazias em **minerais** são tratadas como contribuição zero para o nutriente, evitando erro quando a planilha mantém em branco nutrientes que não fazem parte da composição declarada do mineral.
- O solver possui uma guarda defensiva para não derrubar o Streamlit se algum valor inválido escapar da validação.
- `ValueError` do `linprog` é convertido em `SolverResult` de dados inválidos.
- O diagnóstico de inviabilidade foi melhorado: cada nutriente é reavaliado mantendo as demais restrições, permitindo apontar conflitos conjuntos.

## Formulação mostrada nas imagens

Usando os valores da base do projeto para:

- Farelo de soja
- Milho
- Farelo de arroz integral
- Farelo de arroz desengordurado
- Casquinha de soja
- Calcário calcítico
- Fosfato de cálcio (dibásico)

com as restrições mostradas, a solução continua inviável depois de remover o erro de NaN. O diagnóstico calculado é:

- **FDN:** mantendo as demais restrições, o menor valor alcançável é aproximadamente **23,57%**, acima do máximo solicitado de **20%**.
- **FDA:** mantendo as demais restrições, o maior valor alcançável é aproximadamente **12,23%**, abaixo do mínimo solicitado de **15%**.

Assim, o comportamento correto do aplicativo é informar inviabilidade, não apresentar traceback.

## Arquivos alterados

- `src/solver.py`
- `src/validators.py`
- `tests/test_solver.py`

## Testes

A suíte completa passou com 18 testes.
