# Correção — valores desaparecendo ao pressionar Enter ou Tab

## Sintoma

Nos editores da tela **Nova formulação**, um valor digitado em:

- preço do ingrediente;
- inclusão mínima;
- inclusão máxima;
- mínimo nutricional;
- máximo nutricional;

podia desaparecer depois de confirmar a célula com **Enter** ou **Tab**.

## Causa

`st.data_editor` é um widget stateful. Cada edição provoca um rerun do script e o próprio widget mantém as diferenças editadas no estado da sessão.

A implementação anterior fazia duas coisas ao mesmo tempo:

1. recebia o DataFrame editado retornado pelo `st.data_editor`;
2. salvava esse DataFrame em `st.session_state` e o fornecia novamente como `data=` do mesmo editor na execução seguinte.

Assim, o DataFrame-base do widget mudava a cada edição. Em reruns rápidos — especialmente ao confirmar uma célula com Enter/Tab — o componente podia ser reconstruído a partir de um estado intermediário e o valor recém-digitado aparentava voltar ao valor anterior.

## Solução aplicada

Foi separado o estado em duas camadas:

### Base estável do editor

É o DataFrame entregue em `data=` ao `st.data_editor`. Ele não muda durante o preenchimento normal.

### Estado corrente da formulação

É o DataFrame retornado pelo editor e utilizado para:

- cálculo;
- fingerprint da formulação;
- salvamento;
- exportação;
- preservação dos valores caso a seleção de ingredientes seja alterada.

O estado corrente não substitui mais a base do editor a cada rerun.

## Editor de ingredientes

A base é reconstruída somente quando:

- os ingredientes selecionados mudam;
- uma dieta salva é carregada;
- o formulário é limpo.

Preço, mínimo e máximo permanecem no estado do editor enquanto o usuário navega entre as células.

## Editor de restrições

A tabela-base de restrições também permanece estável. Linhas adicionadas/removidas e valores de mínimo/máximo continuam sendo devolvidos pelo `st.data_editor` e usados normalmente pelo solver, sem realimentar `data=` em cada alteração.

## Arquivo alterado

- `src/pages/formulation.py`

## Validação

- 18 testes automatizados aprovados;
- todos os módulos Python compilados sem erros de sintaxe.
