# Correção — botão Calcular dieta sem resposta

A área de preços, limites de inclusão, restrições nutricionais e o botão de cálculo foi agrupada em um `st.form`.

## Motivo

Os `st.data_editor` e o `st.button` funcionavam em reruns independentes. Quando uma célula ainda estava ativa, o clique em **Calcular dieta** podia ser usado pelo navegador/editor para confirmar a célula, sem que o cálculo fosse submetido com todos os valores atuais.

## Mudança

- `st.button("Calcular dieta")` -> `st.form_submit_button("Calcular dieta")`;
- `enter_to_submit=False`, portanto Enter/Tab só navega/edita e não calcula;
- preços, mínimos, máximos e restrições são enviados em lote no mesmo submit;
- `Limpar` também é um botão de submit do form;
- foi adicionada proteção final para qualquer exceção inesperada do solver, garantindo que a tela sempre mostre uma mensagem em vez de ficar aparentemente sem resposta.

## Arquivo alterado

- `src/pages/formulation.py`

## Dependência

`requirements.txt` passa a exigir `streamlit[auth]>=1.61,<2.0`. A versão 1.61.0 corrigiu o problema em que uma célula aberta do `st.data_editor` não era necessariamente confirmada ao clicar fora da grade.
