# Notas da versão integrada

## Resultado

Versão do `formulacao_rb_webapp_mvp` adaptada para usar a conexão Google Sheets do repositório `claudiopickersgill/formulacoes_dietas`.

## Preservado do MVP

- `app.py` como entrada principal;
- layout e navegação;
- autenticação e perfis;
- páginas de dashboard, formulação, dietas e ingredientes;
- solver;
- exportações;
- modo local;
- base inicial e scripts.

## Adicionado

- reconhecimento de `private_gsheets_url`;
- autenticação por `service_account.Credentials.from_service_account_info`;
- compatibilidade com `pages.conexao.conexao.faz_conexao`;
- seis abas Google com prefixo configurável;
- migração automática da primeira aba de ingredientes;
- preservação da tabela original;
- cache por TTL;
- retry para HTTP 429 e erros 5xx;
- painel administrativo de sistema;
- testes de integração com planilha simulada;
- documentação para Streamlit Community Cloud.

## Verificação

- 7 testes aprovados;
- todos os módulos compilados sem erro de sintaxe;
- nenhum arquivo real de credenciais incluído.

## Limitação

O acesso à planilha privada real não foi executado porque as credenciais não foram fornecidas. O teste de integração usa objetos simulados com o mesmo contrato do gspread.
