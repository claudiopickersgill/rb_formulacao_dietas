# Melhorias da formulação — 2026-08-16

Esta atualização mantém o motor de otimização e acrescenta quatro melhorias de uso e validação.

## 1. Preço zero com confirmação explícita

A tabela de ingredientes passa a ter a coluna **Sem custo**.

Regras:
- preço maior que zero: funcionamento normal;
- preço zero ou vazio sem marcar **Sem custo**: cálculo bloqueado;
- **Sem custo** marcado: o solver utiliza preço efetivo igual a zero;
- se houver preço positivo e **Sem custo** estiver marcado, o preço é desconsiderado e o app emite um aviso.

A informação `sem_custo` também passa a fazer parte de `dieta_ingredientes`, para ser preservada ao salvar e reabrir dietas. O schema do Google Sheets é atualizado pela rotina já existente de evolução de tabelas.

## 2. Aba Nutrientes melhorada

A aba de resultados passa a mostrar:
- mínimo;
- resultado;
- máximo;
- limite mais próximo;
- margem até esse limite;
- situação visual.

Situações:
- 🟡 No limite
- 🟠 Próximo ao limite
- 🟢 Com folga
- 🔴 Fora do limite

Também são exibidos quatro indicadores com a quantidade de nutrientes em cada situação.

## 3. Destaque de nutrientes próximos dos limites

Quando houver nutriente no limite ou próximo dele, o app exibe um aviso com os códigos envolvidos.

Critério padrão:
- com mínimo e máximo: próximo quando a margem for até 10% da largura da faixa;
- com apenas um limite: próximo quando a margem for até 5% do valor de referência, com piso numérico de 0,01.

## 4. Recalcular dieta

Antes do primeiro cálculo o botão se chama **Calcular dieta**.
Depois que houver qualquer resultado armazenado na sessão, ele passa a se chamar **Recalcular dieta**.

## Validação

A suíte possui 27 testes aprovados. Foi acrescentado um teste de regressão que reproduz a dieta validada no Excel Solver:
- custo aproximado: R$ 1,4958/kg;
- milho: 42,0582%;
- farelo de soja: 29,9907%;
- casquinha de soja: 25,9511%;
- fosfato: 1%;
- calcário: 1%.

Isso ajuda a proteger o motor contra alterações futuras que mudem a solução de referência.
