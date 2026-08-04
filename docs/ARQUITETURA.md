# Arquitetura do MVP

## Fluxo

```text
Usuário
  ↓
Streamlit UI
  ├── autenticação OIDC/local
  ├── autorização por perfil
  ├── páginas e estado da sessão
  ↓
Serviços de domínio
  ├── validação
  ├── solver linear
  ├── exportadores
  ↓
Repository interface
  ├── LocalRepository (CSV para desenvolvimento)
  └── GoogleSheetsRepository (produção inicial)
  ↓
Tabelas normalizadas
```

## Separação de responsabilidades

- `app.py`: inicialização, menu e roteamento.
- `src/pages/`: componentes de interface.
- `src/solver.py`: matemática independente do Streamlit.
- `src/validators.py`: regras anteriores ao cálculo.
- `src/repositories/`: persistência intercambiável.
- `src/exports.py`: Excel, PDF e CSV.
- `src/auth.py`: identidade e autorização.

Essa separação permite trocar o Google Sheets por PostgreSQL sem alterar o solver ou reconstruir as páginas.

## Perfis

| Ação | Administrador | Formulador | Consulta |
|---|---:|---:|---:|
| Ver ingredientes | Sim | Sim | Sim |
| Criar/editar ingredientes | Sim | Sim | Não |
| Formular | Sim | Sim | Pode simular, não salvar |
| Salvar/exportar | Sim | Sim | Somente exportar dieta acessível |
| Gerir usuários | Sim | Não | Não |
| Ver auditoria | Sim | Não | Não |

## Consistência histórica

Cada linha de `dieta_ingredientes` guarda uma cópia da composição usada. Alterar o cadastro de um alimento não modifica dietas já salvas.

## Evolução recomendada

1. MVP em Google Sheets.
2. PostgreSQL quando houver vários usuários escrevendo simultaneamente.
3. Camada de requisitos por categoria animal.
4. Preços por fornecedor e data.
5. Formulação por matéria natural, consumo diário e custo por animal/dia.
6. Análise de sensibilidade e preços-sombra.
