# Formulação RB — WebApp com Google Sheets

Aplicativo Streamlit para formulação de dietas de ruminantes por custo mínimo. Esta versão mantém o layout e as funcionalidades do pacote `formulacao_rb_webapp_mvp` e adapta somente a camada de dados para reutilizar a conexão Google já empregada no repositório `claudiopickersgill/formulacoes_dietas`.

## Funcionalidades preservadas

- painel inicial;
- login local ou Google/OIDC;
- perfis Administrador, Formulador e Consulta;
- cadastro, edição, inativação e importação de ingredientes;
- formulação por custo mínimo com limites de inclusão;
- restrições mínimas e máximas para 20 nutrientes;
- diagnóstico de dados ausentes e problemas inviáveis;
- salvamento, edição, duplicação, comparação e exclusão de dietas;
- exportação em Excel, PDF e CSV;
- auditoria de alterações;
- modo local para desenvolvimento.

## Integração implementada

A autenticação da conta de serviço segue a mesma lógica do repositório original:

```python
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=["https://www.googleapis.com/auth/spreadsheets"],
)
gc = gspread.authorize(credentials)
sheet = gc.open_by_url(st.secrets["private_gsheets_url"])
```

Essa lógica foi centralizada em `src/google_connection.py`. Os arquivos `pages/conexao/conexao.py` e `pages/conexao/cria_df.py` permanecem disponíveis para compatibilidade com imports do projeto antigo.

## Abas utilizadas

Para não alterar nem apagar a primeira aba já existente, o aplicativo cria:

- `rb_ingredientes`
- `rb_usuarios`
- `rb_dietas`
- `rb_dieta_ingredientes`
- `rb_dieta_restricoes`
- `rb_auditoria`

O prefixo `rb_` pode ser modificado em `[google_sheets].table_prefix`.

### Migração automática

Quando `rb_ingredientes` estiver vazia, o aplicativo procura uma aba antiga com colunas semelhantes a `Tipo`, `Ingredientes`, `Classificação`, `MS`, `NDT`, `PB` etc. Os dados são copiados para `rb_ingredientes`, enquanto a aba original permanece intacta.

A migração ocorre apenas uma vez, porque deixa de ser executada quando a nova tabela já contém registros.

## Executar localmente

Recomendado: Python 3.11 ou 3.12.

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .streamlit/secrets.toml.example .streamlit/secrets.toml
streamlit run app.py
```

Caso o PowerShell bloqueie a ativação:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

O arquivo `main.py` também pode ser usado para compatibilidade:

```bash
streamlit run main.py
```

## Configuração mínima para Google Sheets

Edite `.streamlit/secrets.toml`:

```toml
private_gsheets_url = "https://docs.google.com/spreadsheets/d/SEU_ID/edit"

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "...@....iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."

[app]
repository = "google_sheets"
auth_mode = "local"
local_email = "admin@local"
local_password = "TROQUE_ESTA_SENHA"
local_name = "Administrador"

[google_sheets]
table_prefix = "rb_"
cache_ttl_seconds = 60
max_retries = 5
auto_migrate_legacy = true
legacy_worksheet_index = 0
legacy_worksheet_title = ""
```

Compartilhe a planilha com o email indicado em `client_email`, concedendo permissão de editor.

## Login Google/OIDC

Depois de validar o banco, altere:

```toml
[app]
repository = "google_sheets"
auth_mode = "oidc"
oidc_provider = "google"
bootstrap_admin_email = "seu-email@gmail.com"
```

E configure:

```toml
[auth]
redirect_uri = "https://SEU-APP.streamlit.app/oauth2callback"
cookie_secret = "CHAVE_ALEATORIA_LONGA"

[auth.google]
client_id = "CLIENT_ID_GOOGLE"
client_secret = "CLIENT_SECRET_GOOGLE"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

O login humano e a conta de serviço são independentes: o OIDC identifica o usuário; a conta de serviço acessa a planilha; `rb_usuarios` controla as permissões.

## Publicar no Streamlit Community Cloud

1. Envie o projeto ao GitHub sem `.streamlit/secrets.toml`.
2. Crie um aplicativo no Streamlit Community Cloud.
3. Selecione `app.py` como arquivo principal.
4. Abra **Advanced settings > Secrets**.
5. Cole o conteúdo do `secrets.toml` real.
6. Faça o deploy.

O arquivo `.gitignore` já impede o envio do segredo local.

## Testes

```bash
pytest -q
```

A suíte cobre:

- solver de custo mínimo;
- problema inviável;
- nutrientes ausentes;
- persistência local;
- exportações;
- conversão da tabela antiga;
- criação das abas `rb_*` e migração com uma planilha Google simulada.

## Verificação do ambiente

```bash
python scripts/check_setup.py
```

## Estrutura principal

```text
app.py                         # entrada principal do Streamlit
main.py                        # compatibilidade com o projeto antigo
pages/conexao/                 # funções de conexão compatíveis
src/google_connection.py       # autenticação Google centralizada
src/repositories/google_sheets.py
src/pages/                     # layout e telas originais do MVP
src/solver.py                  # otimização
src/exports.py                 # Excel, PDF e CSV
```

## Observações de produção

O Google Sheets é adequado para o MVP e para poucos usuários simultâneos. Como cada operação de alteração regrava uma tabela lógica, um uso intenso e concorrente deverá futuramente migrar para PostgreSQL ou outro banco transacional. O aplicativo já separa a interface do repositório para facilitar essa troca.
