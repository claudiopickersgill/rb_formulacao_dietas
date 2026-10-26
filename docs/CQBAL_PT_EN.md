# Referência CQBAL em português e inglês

Referências: relatórios completos digitais enviados pelo usuário para Algodão Caroço, português (17/10/2026) e inglês (26/10/2026), CQBAL 4.0. Cada PDF tem duas páginas e 118 registros de composição/estimativas. Os números dos nutrientes são iguais; nomes, siglas e cabeçalhos estão traduzidos. Isso não constitui conversão para um sistema imperial de unidades.

## Correspondência importada

| Português | Inglês | Campo da base | Unidade de destino | Valor no exemplo |
|---|---|---|---|---|
| MS | DM | MS | % | 90,66 |
| PB | CP | PB | % | 22,94 |
| EE | EE | EE | % | 20,06 |
| MM | ASH | MM | % | 4,28 |
| FB | CF | FB | % | 25,39 |
| FDN | NDF | FDN | % | 45,65 |
| FDA | ADF | FDA | % | 33,81 |
| AMIDO | STARCH | AMIDO | % | 0,65 |
| NDT OBS | OBS TDN | NDT | % | 81,46 |
| EM_BRCORTE2016 | ME_BRCORTE2016 | EM | Mcal/kg | 3,77 |
| Ca | Ca | CA | % | 0,27 se origem %; 0,027 se origem g/kg |
| P, Mg, K, Na, S, Cl | Mesmas siglas | Mesmos campos | % | Conforme unidade confirmada |
| Fe, Cu, Mn, Zn, Co, I, Se | Mesmas siglas | Mesmos campos | % | mg/kg dividido por 10.000 |
| Lys | Lys | Lys — Lisina | % | 1,17 |
| Met | Met | Met — Metionina | % | 0,37 |
| Thr | Thr | Thr — Treonina | % | 0,79 |
| Phe | Phe | Phe — Fenilalanina | % | 1,42 |
| Leu | Leu | Leu — Leucina | % | 1,50 |
| Ile | Ile | Ile — Isoleucina | % | 0,85 |
| Val | Val | Val — Valina | % | 1,14 |
| His | His | His — Histidina | % | 0,71 |
| Arg | Arg | Arg — Arginina | % | 2,82 |
| Tyr | Tyr | Tyr — Tirosina | % | 0,33 |

Há 25 campos com valor importável e nove ausentes nestes relatórios: Cl, S, Fe, Cu, Mn, Zn, Co, I e Se. Os ausentes recebem zero por política do aplicativo e permanecem identificados como ausentes na procedência. Não devem ser interpretados como análise laboratorial de concentração zero.

## Unidades e base de expressão

Os PDFs de referência não imprimem a unidade ao lado de cada média. Por isso, o idioma não é usado como prova de unidade. A prévia exige a seleção de % ou g/kg para macrominerais e a confirmação das demais unidades e da base de expressão. A implementação usa aminoácidos em % do alimento e EM em Mcal/kg; se a fonte usar % da PB, g/kg, MJ/kg ou kcal/kg para esses campos, é necessário converter antes do cadastro manual. Não há conversão automática seca/natural. O critério de aminoácidos não representa oferta de proteína ou aminoácidos metabolizáveis ao animal.

Para comparar os arquivos, foi usada a mesma escolha de macrominerais em ambos: todos os 34 campos finais são iguais. A escolha de unidade dos minerais só altera esses minerais; não altera aminoácidos ou EM.

## Seleção estrita e dados preservados

- NDT_BRCORTE2016/TDN_BRCORTE2016 (96,35) e NDT(iv)/TDN (IV) (63,50) não substituem o NDT observado de 81,46.
- FDNcp/NDFap e FDAp/ADFp não substituem FDN/NDF e FDA/ADF.
- ED_BRCORTE2016/DE_BRCORTE2016 (4,31) e EB/GE (5,61) não preenchem EM. Importa-se somente EM/ME_BRCORTE2016 (3,77), uma estimativa já presente no relatório.
- N/n e S/se são estatísticas do relatório e permanecem na procedência, sem alimentar os teores.
- Registros não mapeados permanecem no JSON, com rótulo, seção, média e estatísticas originais. Não se adicionam automaticamente novos nutrientes a partir de um texto desconhecido.
- As categorias inglesas reconhecidas são normalizadas para as categorias do cadastro; nomes do alimento ficam no idioma original até revisão do usuário.

## Verificação reproduzível

`tests/fixtures/cqbal/cottonseed_pt.txt` e `cottonseed_en.txt` contêm o texto extraído dos PDFs de referência. A suíte compara composição, estatísticas e regras, sem depender de caminhos do computador do usuário. Durante o preparo do patch também foram processados os PDFs originais com `parse_pdf`, incluindo as duas páginas. As fixtures não substituem validação futura de um layout novo. O importador aceita relatórios completos digitais reconhecidos, não PDFs arbitrários nem imagens digitalizadas.
