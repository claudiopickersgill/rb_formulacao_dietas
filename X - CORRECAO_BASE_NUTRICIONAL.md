# Correção — base nutricional incompleta no Google Sheets

## Sintoma

Após a validação do solver ser corrigida, a formulação passou a informar que NDT, PB, FDN, FDA, CA e P estavam ausentes para diversos alimentos.

Isso não é um novo erro do solver. A validação passou a revelar que a aba `rb_ingredientes`, criada por versões anteriores do aplicativo, contém células nutricionais vazias.

## Valores presentes na base original v1.2

Os ingredientes usados no teste possuem, na base original:

| Ingrediente | NDT | PB | FDN | FDA | CA | P |
|---|---:|---:|---:|---:|---:|---:|
| Milho | 80.00 | 8.0 | 9.8 | 3.6 | 0.04 | 0.31 |
| Farelo de soja | 85.00 | 45.0 | 11.9 | 7.2 | 0.30 | 0.70 |
| Farelo de arroz integral | 75.00 | 14.8 | 23.1 | 13.8 | 0.78 | 0.12 |
| Farelo de arroz desengordurado | 70.00 | 18.5 | 25.9 | 12.7 | 0.83 | 2.48 |
| Casquinha de soja | 48.76 | 11.9 | 66.7 | 47.9 | 0.64 | 0.13 |

Portanto, esses campos não devem estar vazios em `rb_ingredientes`.

## Correção implementada

Na inicialização do repositório Google, o app agora executa uma reconciliação conservadora da composição:

1. lê `rb_ingredientes`;
2. procura o mesmo ingrediente, por `tipo + nome`, na aba legada do Google Sheets;
3. usa `data/seed_ingredientes.csv` como fallback;
4. preenche somente células nutricionais realmente vazias;
5. nunca sobrescreve valor numérico existente, inclusive `0`;
6. atualiza `updated_at` dos registros reparados;
7. registra a operação em `rb_auditoria`.

A rotina é idempotente: depois que os campos são preenchidos, novas inicializações não alteram esses valores.

## Arquivos envolvidos

- `src/repositories/google_sheets.py`
- `data/seed_ingredientes.csv`
- `app.py`
- `src/pages/formulation.py` (incluído novamente porque o arquivo efetivo em `src/pages` precisa receber a correção de estado do `data_editor`)

## Depois do deploy

O Streamlit deve reiniciar o processo. Na primeira inicialização, a aba `rb_ingredientes` será reparada automaticamente e um aviso será exibido informando quantos campos foram complementados.

Depois, abra **Ingredientes** e confira os valores de composição. Em seguida, use **Limpar** em Nova formulação e monte a dieta novamente para descartar qualquer estado de sessão anterior.
