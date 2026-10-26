# RFB — Formulação de Dietas para Ruminantes

Aplicativo web em Streamlit para formular dietas de ruminantes por custo mínimo, com cadastro de ingredientes, restrições nutricionais, importação de relatórios CQBAL, armazenamento no Google Sheets e exportação de resultados.

Documentação consolidada em **17/10/2026**, atualizada em **26/10/2026**, com base no código local e no histórico de atualizações. O histórico das correções e das regras substituídas está em [PATCHES.md](PATCHES.md).

Repositório: [claudiopickersgill/rb_formulacao_dietas](https://github.com/claudiopickersgill/rb_formulacao_dietas).

## Funcionalidades

- **Visão geral:** ingredientes ativos, pendências de qualidade, dietas acessíveis e custos.
- **Ingredientes:** consulta, cadastro, edição, inativação, reativação e importação por CSV ou PDF do CQBAL em português ou inglês, com aminoácidos e Energia Metabolizável (EM).
- **Nova formulação:** seleção de ingredientes, preços, limites de inclusão e restrições nutricionais dinâmicas.
- **Resultado:** composição da mistura, custo, teores nutricionais e comparação com os limites solicitados.
- **Diagnóstico de inviabilidade:** mensagens de conflito e simulação de uma mistura com restrições nutricionais flexibilizadas.
- **Dietas salvas:** consulta, continuação da edição, duplicação, comparação e exclusão conforme o perfil.
- **Exportações:** Excel, PDF e CSV.
- **Administração:** usuários, auditoria e recursos de diagnóstico do sistema.

## Perfis de acesso

| Recurso | Administrador | Formulador | Consulta |
|---|---|---|---|
| Consultar ingredientes | Sim | Sim | Sim |
| Cadastrar, editar e importar ingredientes | Sim | Sim | Não |
| Formular e simular dietas | Sim | Sim | Sim |
| Salvar alterações em dietas | Sim | Sim, conforme propriedade | Não |
| Acessar dietas | Todas | Próprias | Próprias |
| Exportar resultados/dietas acessíveis | Sim | Sim | Sim |
| Gerir usuários e consultar auditoria | Sim | Não | Não |

O login do usuário e a conexão com o Google Sheets são independentes. O usuário recebe permissões pelo cadastro; a conta de serviço acessa a planilha.

## Formulação

O cálculo principal minimiza o custo por kg de uma mistura cuja soma das inclusões é **100%**. São respeitados os mínimos e máximos de inclusão e as restrições nutricionais preenchidas.

Preço zero ou ausente exige a marcação explícita **Sem custo**. Quando marcada, o preço efetivo usado no cálculo é zero.

As restrições são montadas a partir dos nutrientes com algum valor numérico declarado nos ingredientes selecionados. Zero é um valor declarado. Preencher mínimo ou máximo ativa a restrição; deixar ambos vazios permite apenas calcular o teor final quando há dados suficientes.

A tabela apresenta nomes completos, siglas e unidades, por exemplo **Matéria seca - MS (%)** e **Cálcio - Ca (%)**. Os códigos usados nos cálculos e no armazenamento são preservados; cálcio continua identificado internamente por `CA`.

Quando ingredientes ou limites são alterados após o cálculo, é necessário recalcular antes de salvar. As dietas salvas preservam a composição utilizada no momento da gravação.

### Quando não há solução viável

O app mantém os diagnósticos e pode mostrar uma **prévia de diagnóstico** com mistura, custo simulado, teores, falta para o mínimo e excesso sobre o máximo.

Essa simulação mantém os limites de inclusão e a soma de 100%, mas flexibiliza as restrições nutricionais para minimizar os desvios relativos. Ela não minimiza custo, não é uma dieta aprovada e não oferece salvamento como solução válida. Erros de preenchimento ou limites de inclusão incompatíveis podem impedir a geração da prévia.

## Nutrientes e unidades

O registro atual possui **44 nutrientes**: os 23 anteriores, Energia Metabolizável (EM) e os 20 aminoácidos padrão. Todos são armazenados em **porcentagem**, exceto **EM em kcal/g**:

| Grupo | Nutrientes |
|---|---|
| Composição principal | MS, NDT, PB, FDN, FDA, EE, MM, FB e AMIDO (%) |
| Energia | EM (kcal/g) |
| Macrominerais | Ca (`CA`), P, Mg, Na, K, Cl e S |
| Microminerais | Fe, Cu, Mn, Zn, Co, I e Se |
| Aminoácidos | Lisina (Lys), Metionina (Met), Treonina (Thr), Fenilalanina (Phe), Leucina (Leu), Isoleucina (Ile), Valina (Val), Histidina (His), Arginina (Arg) Tirosina (Tyr), Alanina (Ala), Asparagina (Asn), Aspartato (Asp), Cisteína (Cys), Glicina (Gly), Glutamato (Glu), Glutamina (Gln), Prolina (Pro), Serina (Ser) e Triptofano (Trp) |

EM e aminoácidos estão disponíveis no cadastro manual, na edição, no CSV, nas restrições dinâmicas, nas dietas salvas e nas exportações. Os aminoácidos representam % do alimento, não % da PB, nem oferta de aminoácidos metabolizáveis ao animal. O cadastro manual mantém campos desconhecidos em branco; a regra de zero abaixo é específica da importação CQBAL.

Os limites nutricionais devem usar as mesmas unidades da composição: uma EM mínima de 3,0 significa 3,0 kcal/g, não 3,0%. O sistema não converte automaticamente uma dieta entre matéria natural e matéria seca: a base de expressão dos dados deve ser coerente.

## Importação CQBAL

Em **Ingredientes > Importar CQBAL**:

1. Envie o PDF digital do **Relatório Completo** de um único alimento, em português ou inglês. O idioma e as siglas são reconhecidos automaticamente; o nome do alimento é preservado no idioma original e pode ser editado.
2. Confirme se os macrominerais da fonte estão em `%` ou `g/kg`.
3. Confira a prévia, incluindo as unidades de cada campo e os zeros por ausência. Confirme aminoácidos em % do alimento e EM de origem Mcal/kg, convertida para kcal/g; o idioma não determina a unidade ou a base seca/natural.
4. Revise nome, tipo e classificação; escolha cadastrar ou atualizar explicitamente um registro por ID.
5. Confirme os valores e a base de expressão e salve.

### Regras de importação

| Informação da fonte | Tratamento |
|---|---|
| MS, PB, EE, MM, FB e AMIDO | Importar em % |
| NDT | Usar exclusivamente `NDT OBS` / `OBS TDN` |
| EM | Importar apenas `EM_BRCORTE2016` / `ME_BRCORTE2016`, com origem Mcal/kg e conversão para kcal/g, da seção calculada |
| Vinte aminoácidos | Importar as siglas exatas em % do alimento, sem converter em % da PB |
| FDA e FDN | Usar somente os códigos exatos; não substituir por variantes |
| Macrominerais em g/kg | Dividir por 10 para armazenar em % |
| Macrominerais em % | Manter o valor |
| Microminerais em mg/kg ou ppm | Dividir por 10.000 para armazenar em %; `ZINC` em inglês corresponde a `Zn` |
| Nutriente sem informação importável | Gravar 0 e identificar o preenchimento na procedência |
| Colunas estatísticas N e S e demais dados não mapeados | Preservar na procedência; não converter em teores da dieta |

Exemplos: **12 g/kg = 1,2%**; **50 mg/kg = 0,005%**.

Os valores antigos da base não são reconvertidos: foram considerados já expressos em porcentagem. A regra de preencher ausentes com zero é aplicada à composição importada pelo CQBAL; não é uma limpeza retroativa de todos os cadastros nem dos campos estatísticos N e S.

A atualização de um ingrediente substitui sua composição: nutrientes ausentes no PDF recebem zero. Preço e demais informações existentes são preservados conforme o fluxo de atualização.

O campo `cqbal_dados` guarda nome original, idioma, arquivo, hash SHA256, categoria original e normalizada, unidades de origem e por campo de destino, métodos de NDT e EM, registros reconhecidos e campos preenchidos com zero. A procedência nova usa versão 3, com origem/destino e fator da conversão energética; os JSON antigos continuam legíveis. A procedência pode ser consultada e baixada na edição do ingrediente.

A correspondência validada das siglas e os resultados dos dois relatórios de referência estão em [docs/CQBAL_PT_EN.md](docs/CQBAL_PT_EN.md). Não há estimativa local da EM a partir do NDT: importa-se a estimativa BR-CORTE 2016 que consta do relatório. Outros métodos de energia permanecem na procedência.

**Limites:** um alimento por arquivo, PDF digital de até 10 MB e 20 páginas, com seção de nutrientes calculados. Não há OCR. A procedência deve caber no limite de 45.000 caracteres adotado para uma célula do Google Sheets.

### Atualização de uma base existente

Ao reiniciar, o mecanismo de schema acrescenta ao final de `rb_ingredientes` e `rb_dieta_ingredientes` apenas os campos ainda ausentes. Para quem já aplicou a atualização dos dez aminoácidos, são dez novas colunas: `Ala`, `Asn`, `Asp`, `Cys`, `Gly`, `Glu`, `Gln`, `Pro`, `Ser` e `Trp`. Não reordena cabeçalhos nem preenche registros antigos. Faça backup das abas antes da publicação e confira a expansão no primeiro acesso. Dietas antigas mantêm a composição histórica; reimportar um ingrediente é uma ação explícita e não atualiza suas dietas salvas.

**EM:** 1 Mcal/kg = (1.000 kcal)/(1.000 g) = 1 kcal/g. A importação faz essa conversão automaticamente, com fator 1; por exemplo, 3,21 Mcal/kg resulta em 3,21 kcal/g. Os valores antigos já armazenados em Mcal/kg permanecem numericamente corretos. Na leitura e na exportação de dietas antigas, a unidade Mcal/kg é apresentada como kcal/g sem alterar mínimos, máximos e resultados. Não há regravação retroativa das planilhas ou da procedência original.

**Siglas dos aminoácidos:** o importador usa três letras (`Ala`, `Asn`, `Gln` etc.), também reconhecidas em maiúsculas. Não interpreta automaticamente letras únicas como aminoácidos, pois `P`, `S`, `K` e `I` já representam minerais. Ausentes no CQBAL continuam recebendo zero, com identificação na procedência; campos manuais desconhecidos continuam em branco.

## Qualidade dos cadastros

- `qualidade_dados` registra pendências que exigem revisão.
- `observacoes` guarda histórico e informações de procedência.
- O dashboard considera pendências de ingredientes ativos.
- Notas legadas conhecidas são reclassificadas na leitura. Uma observação desconhecida não é descartada automaticamente.
- Registros inativos são preservados para manter os IDs históricos.
- O preenchimento automático de nutrientes a partir de referências antigas na inicialização está desativado.

## Armazenamento

O backend de produção inicial é Google Sheets. O modo local usa arquivos CSV para desenvolvimento.

| Aba padrão | Conteúdo |
|---|---|
| `rb_ingredientes` | Catálogo, composição, situação, qualidade e procedência |
| `rb_usuarios` | Usuários, perfis, situação e autenticação local |
| `rb_dietas` | Metadados e custo das dietas |
| `rb_dieta_ingredientes` | Ingredientes, inclusões e composição usada em cada dieta |
| `rb_dieta_restricoes` | Limites nutricionais das dietas |
| `rb_auditoria` | Operações registradas pelo sistema |

O prefixo é configurável. A migração legada só copia ingredientes quando a tabela de destino está vazia. A tabela legada permanece preservada.

Criação e edição de ingredientes no Google usam gravação por registro e confirmação por leitura. A auditoria acrescenta linhas. Isso evita a sobrescrita da aba inteira nesses fluxos, mas não constitui transação distribuída. Outras entidades mantêm suas rotinas anteriores; uso concorrente intenso requer evolução da persistência.

## Executar localmente

Recomendado: Python 3.11 ou 3.12, em ambiente virtual.

No PowerShell, a partir da raiz do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .streamlit/secrets.toml.example .streamlit/secrets.toml
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Configure o arquivo de segredos antes de usar o Google Sheets. `main.py` permanece como entrada de compatibilidade.

### Configuração Google Sheets

Use o modelo `.streamlit/secrets.toml.example`. Os principais campos são:

```toml
private_gsheets_url = "https://docs.google.com/spreadsheets/d/SEU_ID/edit"

[app]
repository = "google_sheets"
auth_mode = "local"

[google_sheets]
table_prefix = "rb_"
cache_ttl_seconds = 60
max_retries = 5
auto_migrate_legacy = true
legacy_worksheet_index = 0
```

Complete também `[gcp_service_account]` e as credenciais de autenticação conforme o modelo. Compartilhe a planilha com o `client_email` da conta de serviço, com permissão de editor. Não publique o arquivo real de segredos.

Para desenvolvimento com CSV, use `[app].repository = "local"`. O login local usa senhas individuais armazenadas como hash; o acesso administrativo configurado nos segredos permanece como recuperação. O login Google/OIDC é opcional e requer a configuração específica de `[auth]`, do provedor e de `auth_mode = "oidc"`.

### Publicar

No Streamlit Community Cloud, selecione `app.py`, mantenha `requirements.txt` atualizado e configure os segredos no painel do aplicativo. Após trocar arquivos, publique e reinicie/recalcule para não reutilizar resultados anteriores da sessão.

## Estrutura principal

```text
app.py                         Inicialização e navegação
src/pages/                     Telas efetivamente usadas pelo app
src/config.py                  Nutrientes, unidades e schemas
src/solver.py                  Otimização e diagnóstico
src/validators.py              Validação anterior ao cálculo
src/nutrients.py               Restrições dinâmicas
src/cqbal_import.py            Extração e conversão de PDFs CQBAL
src/pages/cqbal.py             Prévia e confirmação da importação
src/ingredient_quality.py      Classificação de notas legadas
src/diet_loading.py            Normalização de dietas salvas
src/repositories/              Google Sheets e CSV local
src/exports.py                 Excel, PDF e CSV
src/auth.py                    Autenticação
src/security.py                Senhas e hashes
tests/                         Testes automatizados
readme.md                      Informações gerais
PATCHES.md                     Histórico consolidado de evoluções
```

Existem arquivos de compatibilidade fora de `src/pages`. Ao aplicar uma correção de tela, confira o caminho exato: por exemplo, `src/pages/formulation.py` é o arquivo usado pelo fluxo atual de formulação.

## Testes e atualizações

Com as dependências completas instaladas:

```powershell
python -m pytest tests -q
python scripts/check_setup.py
```

Testes específicos dos módulos recentes:

```powershell
python -m unittest discover -s tests -p "test_cqbal*.py" -v
python -m unittest discover -s tests -p test_infeasible_preview.py -v
```

Antes de atualizar, faça backup do código e das tabelas afetadas. Evite gravar na base durante a aplicação. Patches antigos que substituem arquivos inteiros podem desfazer melhorias posteriores: consulte a sequência e as regras vigentes em [PATCHES.md](PATCHES.md).

Os resultados e as limitações de validação de cada entrega estão registrados no histórico; este documento não declara uma nova execução da suíte completa.
