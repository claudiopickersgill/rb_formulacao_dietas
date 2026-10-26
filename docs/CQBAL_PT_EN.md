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
| EM_BRCORTE2016 | ME_BRCORTE2016 | EM | kcal/g (origem Mcal/kg, fator 1) | 3,77 |
| Ca | Ca | CA | % | 0,27 se origem %; 0,027 se origem g/kg |
| P, Mg, K, Na, S, Cl | Mesmas siglas | Mesmos campos | % | Conforme unidade confirmada |
| Fe, Cu, Mn, Zn, Co, I, Se | Mesmas siglas; ZINC para Zn | Mesmos campos | % | mg/kg dividido por 10.000 |
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

No algodão, há 25 campos com valor importável e 19 ausentes no registro atual de 44 campos: Cl, S, Fe, Cu, Mn, Zn, Co, I, Se, Ala, Asn, Asp, Cys, Gly, Glu, Gln, Pro, Ser e Trp. Os ausentes recebem zero por política do aplicativo e permanecem identificados como ausentes na procedência. Não devem ser interpretados como análise laboratorial de concentração zero.

## Unidades e base de expressão

Os PDFs de referência não imprimem a unidade ao lado de cada média. Por isso, o idioma não é usado como prova de unidade. A prévia exige a seleção de % ou g/kg para macrominerais e a confirmação das demais unidades e da base de expressão. A implementação usa aminoácidos em % do alimento e EM com origem Mcal/kg e destino kcal/g (fator 1); se a fonte usar % da PB, g/kg, MJ/kg ou kcal/kg para esses campos, é necessário converter antes do cadastro manual. Não há conversão automática seca/natural. O critério de aminoácidos não representa oferta de proteína ou aminoácidos metabolizáveis ao animal.

Para comparar os arquivos, foi usada a mesma escolha de macrominerais em ambos: todos os 44 campos finais são iguais. A escolha de unidade dos minerais só altera esses minerais; não altera aminoácidos ou EM.

## Seleção estrita e dados preservados

- NDT_BRCORTE2016/TDN_BRCORTE2016 (96,35) e NDT(iv)/TDN (IV) (63,50) não substituem o NDT observado de 81,46.
- FDNcp/NDFap e FDAp/ADFp não substituem FDN/NDF e FDA/ADF.
- ED_BRCORTE2016/DE_BRCORTE2016 (4,31) e EB/GE (5,61) não preenchem EM. Importa-se somente EM/ME_BRCORTE2016 (3,77), uma estimativa já presente no relatório.
- N/n e S/se são estatísticas do relatório e permanecem na procedência, sem alimentar os teores.
- Registros não mapeados permanecem no JSON, com rótulo, seção, média e estatísticas originais. Não se adicionam automaticamente novos nutrientes a partir de um texto desconhecido.
- As categorias inglesas reconhecidas são normalizadas para as categorias do cadastro; nomes do alimento ficam no idioma original até revisão do usuário.

## Verificação reproduzível

`tests/fixtures/cqbal/cottonseed_pt.txt` e `cottonseed_en.txt` contêm o texto extraído dos PDFs de referência. A suíte compara composição, estatísticas e regras, sem depender de caminhos do computador do usuário. Durante o preparo do patch também foram processados os PDFs originais com `parse_pdf`, incluindo as duas páginas. As fixtures não substituem validação futura de um layout novo. O importador aceita relatórios completos digitais reconhecidos, não PDFs arbitrários nem imagens digitalizadas.

## Ampliação: relatórios de trigo em português e inglês

Referências adicionais encontradas na mesma pasta de alimentos do projeto: `Trigo - Grao - Br.pdf` e `Trigo - Grao - En.pdf`, ambos de 26/10/2026. Os quatro PDFs reais foram processados, não somente os textos de teste. No trigo, cada arquivo contém 74 registros e as versões geram os mesmos 44 campos finais.

| Português | Inglês | Destino | Valor no trigo |
|---|---|---|---|
| Zn | ZINC | Zn (%) | 64,47 mg/kg ÷ 10.000 = 0,006447% |
| EM_BRCORTE2016 | ME_BRCORTE2016 | EM (kcal/g) | 3,21 Mcal/kg × 1 = 3,21 kcal/g |
| Cys | Cys | Cisteína (%) | 0,52 |
| Trp | Trp | Triptofano (%) | 0,18 |
| Ala | Ala | Alanina (%) | 0,50 |
| Asp | Asp | Aspartato (%) | 0,73 |
| Glu | Glu | Glutamato (%) | 4,14 |
| Gly | Gly | Glicina (%) | 0,57 |
| Pro | Pro | Prolina (%) | 1,72 |
| Ser | Ser | Serina (%) | 0,67 |

O trigo possui 18 dos 20 aminoácidos cadastrados. Asn (asparagina) e Gln (glutamina) não constam nesses arquivos e recebem zero pela política de ausência. Também faltam NDT observado, Cl, S, Co, I e Se; não usar o NDT calculado de 84,29 como substituto.

Os 20 campos são Ala, Arg, Asn, Asp, Cys, Phe, Gly, Glu, Gln, His, Ile, Leu, Lys, Met, Pro, Ser, Tyr, Thr, Trp e Val. A importação aceita as siglas de três letras e as mesmas em maiúsculas. As letras únicas não são aliases automáticos: I, K, P e S já representam minerais. Isso evita importar iodo como isoleucina, potássio como lisina, fósforo como prolina ou enxofre como serina.

A conversão energética é dimensional: 1 Mcal/kg = 1.000 kcal / 1.000 g = 1 kcal/g. Mantém os números e muda a unidade de destino. A procedência versão 3 registra origem Mcal/kg, destino kcal/g e fator 1. Os JSON anteriores são preservados; dietas antigas têm a unidade normalizada apenas na leitura/exportação, sem multiplicar valores ou alterar a base seca/natural.

As fixtures adicionais `tests/fixtures/cqbal/wheat_pt.txt` e `wheat_en.txt` reproduzem os textos integrais extraídos dos relatórios. A equivalência do trigo cobre o alias ZINC e os oito aminoácidos adicionais presentes. Casos sintéticos cobrem Asn e Gln e a importação dos 20 campos, pois esses dois aminoácidos não estão nos PDFs reais disponíveis.
