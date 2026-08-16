# Correção de fuso horário

O aplicativo passou a utilizar o fuso IANA `America/Sao_Paulo`, correspondente ao horário de Brasília e ao horário utilizado no Rio Grande do Sul.

## Novo formato armazenado

Antes:

```text
2026-08-04T14:23:28+00:00
```

Depois:

```text
2026-08-04T11:23:28-03:00
```

O offset `-03:00` permanece no valor armazenado para que o horário seja inequívoco.

## Campos abrangidos

- `rb_ingredientes.created_at`
- `rb_ingredientes.updated_at`
- `rb_usuarios.created_at`
- `rb_usuarios.updated_at`
- `rb_usuarios.last_login`
- `rb_dietas.created_at`
- `rb_dietas.updated_at`
- `rb_auditoria.timestamp`

As tabelas `rb_dieta_ingredientes` e `rb_dieta_restricoes` não possuem campos de data/hora.

## Conversão dos registros existentes

Na primeira inicialização após a atualização, o repositório percorre os campos acima e converte valores ISO com offset para `America/Sao_Paulo`.

A conversão é idempotente:

- registros em UTC são convertidos;
- registros já em `-03:00` permanecem iguais;
- campos vazios permanecem vazios;
- valores inválidos são preservados para evitar perda de dados;
- uma tabela só é regravada quando algum valor realmente muda.

Valores antigos sem offset são tratados como horários locais já registrados e passam apenas a receber `-03:00`.

## Compatibilidade

Foi adicionada a dependência `tzdata` para garantir o funcionamento da base IANA também no Windows.

A função antiga `utc_now_iso()` foi mantida como alias de compatibilidade, mas novos pontos do código utilizam `local_now_iso()`.

## Arquivos alterados

- `src/utils.py`
- `src/config.py`
- `src/repositories/tabular.py`
- `src/repositories/google_sheets.py`
- `requirements.txt`
- `tests/test_timezone.py`

## Verificação

Foram executados:

```text
15 testes aprovados
compilação de todos os módulos aprovada
```
