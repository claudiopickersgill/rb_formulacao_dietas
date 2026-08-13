# Integração com Google Sheets

## Origem da conexão

A integração reproduz a estratégia usada no repositório original:

1. lê `[gcp_service_account]` do `st.secrets`;
2. cria `service_account.Credentials` com o escopo de planilhas;
3. autoriza o cliente `gspread`;
4. abre a planilha usando `private_gsheets_url`.

A implementação reutilizável está em `src/google_connection.py`.

## Compatibilidade

Os arquivos abaixo preservam a interface do código antigo:

```text
pages/conexao/conexao.py
pages/conexao/cria_df.py
```

`faz_conexao()` continua retornando a primeira worksheet. O aplicativo completo, entretanto, usa o objeto `Spreadsheet` para trabalhar com várias abas.

## Abas gerenciadas

Por padrão, o aplicativo cria:

```text
rb_ingredientes
rb_usuarios
rb_dietas
rb_dieta_ingredientes
rb_dieta_restricoes
rb_auditoria
```

O prefixo evita que uma aba antiga seja reformatada ou apagada.

## Migração da primeira aba

Se `rb_ingredientes` estiver vazia e `auto_migrate_legacy = true`, o repositório procura uma aba não gerenciada que contenha:

- uma coluna de tipo;
- uma coluna de ingrediente/nome;
- pelo menos um nutriente reconhecido.

A cópia converte cabeçalhos, números com vírgula decimal e campos conhecidos. A origem não é modificada. Duplicidades e classificações suspeitas são registradas em `qualidade_dados`.

## Cache e repetição de chamadas

- o repositório é mantido com `st.cache_resource`;
- cada tabela tem cache interno por TTL;
- erros HTTP 429 e falhas 5xx são repetidos com espera exponencial;
- após uma gravação, o cache recebe imediatamente o DataFrame atualizado.

O administrador pode limpar o cache em **Administração > Sistema**.

## Segurança

- nunca envie `.streamlit/secrets.toml` ao GitHub;
- compartilhe a planilha somente com o `client_email` da conta de serviço;
- use login OIDC para usuários humanos no ambiente público;
- use `rb_usuarios` para autorizações;
- troque a senha do login local antes de qualquer teste remoto.

## Limitação de concorrência

O backend atual regrava cada aba lógica para manter o CRUD simples e previsível. Isso é suficiente para o MVP, mas duas gravações simultâneas podem competir. Em uma etapa comercial, substitua o backend por PostgreSQL mantendo o mesmo contrato `Repository`.
