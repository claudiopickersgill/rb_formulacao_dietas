# Correção do login de usuários cadastrados

## Problema identificado

O modo `auth_mode = "local"` validava apenas o par configurado em:

```toml
[app]
local_email = "admin@local"
local_password = "..."
```

A tela administrativa permitia cadastrar outros emails na aba `rb_usuarios`, mas não solicitava nem armazenava senha individual. Por isso, um usuário como `junior@rb.com.br` aparecia como ativo e com perfil `Formulador`, mas o login retornava `Email ou senha incorretos`.

## Alterações realizadas

1. A tabela `rb_usuarios` passou a possuir a coluna `password_hash`.
2. O formulário administrativo agora solicita senha inicial para novos usuários.
3. Ao editar um usuário, é possível definir ou redefinir sua senha.
4. O login local consulta `rb_usuarios` e valida a senha individual.
5. A senha é armazenada com PBKDF2-SHA256, salt aleatório e 310.000 iterações.
6. O hash não aparece na tabela exibida no painel administrativo.
7. Alterar nome, perfil ou status sem preencher nova senha preserva a senha existente.
8. Usuários inativos são bloqueados, inclusive quando já possuíam uma sessão aberta.
9. O acesso administrativo definido no `secrets.toml` continua funcionando como credencial de recuperação.

## Como liberar o usuário junior@rb.com.br

Após publicar esta versão:

1. Entre com o administrador configurado no `secrets.toml`.
2. Abra `Administração` > `Usuários`.
3. Em `Registro existente`, selecione o usuário Junior.
4. Preencha `Nova senha (opcional)` e `Confirmar senha`.
5. Confira se `Ativo` está marcado e o perfil é `Formulador`.
6. Clique em `Salvar usuário`.
7. Saia do administrador e entre com `junior@rb.com.br` e a nova senha.

A coluna `password_hash` será adicionada automaticamente à aba existente. Não é necessário apagar nem recriar `rb_usuarios`.

## Arquivos alterados

- `src/auth.py`
- `src/security.py`
- `src/config.py`
- `src/pages/admin.py`
- `src/repositories/tabular.py`
- `data/seed_usuarios.csv`
- `tests/test_security.py`
- `tests/test_repository.py`

## Verificação

Foram executados 11 testes automatizados, incluindo:

- criação e validação de hash;
- rejeição de senha incorreta;
- salt diferente para senhas iguais;
- preservação do hash ao editar perfil ou nome;
- ocultação do hash na listagem administrativa;
- repositórios, solver e exportações existentes.
