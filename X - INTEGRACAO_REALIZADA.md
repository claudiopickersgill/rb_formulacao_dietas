# Integração realizada

## Base adotada

O código, as páginas, o layout, o solver, os exportadores e as regras de acesso vieram do arquivo `formulacao_rb_webapp_mvp.zip`.

## Elementos incorporados do GitHub

Do repositório `claudiopickersgill/formulacoes_dietas` foi adotado o padrão:

- `st.secrets["gcp_service_account"]`;
- `service_account.Credentials.from_service_account_info(...)`;
- escopo `https://www.googleapis.com/auth/spreadsheets`;
- `gspread.authorize(credentials)`;
- `st.secrets["private_gsheets_url"]`;
- `gc.open_by_url(sheet_url)`.

## Arquivos modificados ou adicionados

- `app.py`: reconhece automaticamente os segredos antigos e inicializa Google Sheets;
- `main.py`: entrada compatível com o nome usado no repositório antigo;
- `src/google_connection.py`: conexão centralizada;
- `src/repositories/google_sheets.py`: várias abas, cache, retry e migração;
- `src/repositories/factory.py`: novas opções do backend;
- `pages/conexao/*`: compatibilidade com os imports antigos;
- `.streamlit/secrets.toml.example`: configuração pronta para Streamlit Cloud;
- `src/pages/admin.py`: painel de diagnóstico e limpeza de cache;
- `tests/test_legacy_google_migration.py`;
- `tests/test_google_repository_integration.py`.

## Comportamento da primeira execução

1. O aplicativo abre a planilha informada em `private_gsheets_url`.
2. Cria as seis abas `rb_*` que estiverem ausentes.
3. Detecta a tabela antiga de ingredientes.
4. Copia os dados para `rb_ingredientes`.
5. Mantém a tabela antiga sem modificações.
6. Cria ou atualiza o usuário administrativo conforme o modo de login.

## Arquivo principal no Streamlit Cloud

Use:

```text
app.py
```
