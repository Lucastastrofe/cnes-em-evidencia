# Contexto do projeto

## Propósito

O CNES em Evidência permite inspecionar a cobertura cadastral e os problemas observáveis de qualidade na base aberta de estabelecimentos de saúde. O produto é dirigido a pessoas que usam dados públicos de saúde em análises e precisam avaliar a fonte antes de interpretar seus números.

## Pergunta principal

Quais problemas de completude, unicidade e validade aparecem no cadastro nacional e como eles se distribuem entre as unidades federativas?

## Escopo do primeiro incremento

- processar a fotografia corrente do arquivo CSV oficial do CNES;
- medir volume, completude de campos selecionados, duplicidade da chave CNES e validade de UF, município e coordenadas;
- publicar somente resultados agregados por UF e por tipo de unidade;
- expor fonte, horário, hash do arquivo, regras executadas, resultados e limitações;
- atualizar e publicar o site automaticamente pelo GitHub Actions.

## Escopo do segundo incremento

- extrair a estimativa populacional anual mais recente do IBGE pela API SIDRA;
- validar ano único, valores positivos, unicidade e cobertura das 27 UFs;
- integrar CNES e IBGE pelo código da UF;
- calcular registros cadastrais do CNES por 100 mil habitantes;
- publicar hash, referência e metadados das duas fontes na trilha de auditoria;
- comparar UFs sem interpretar a taxa como oferta, acesso ou capacidade assistencial.

## Escopo do terceiro incremento

- processar o arquivo anual oficial de Hospitais e Leitos do CNES;
- selecionar somente a competência mensal mais recente disponível no arquivo;
- validar schema, competência, domínio das UFs, unicidade por CNES e valores não negativos;
- agregar leitos existentes, leitos destinados ao SUS e leitos de UTI por UF;
- integrar os agregados à estimativa populacional já validada pelo projeto;
- calcular leitos existentes e leitos SUS por 100 mil habitantes;
- publicar somente resultados agregados e os metadados da nova fonte;
- deixar explícito que o cadastro não informa ocupação nem disponibilidade em tempo real.

## Fora de escopo

- avaliar qualidade assistencial ou desempenho de estabelecimentos;
- identificar profissionais, pacientes ou outras pessoas naturais;
- publicar registros individuais, contatos, endereços, CNPJ ou coordenadas;
- criar uma nota composta de qualidade com pesos arbitrários;
- manter histórico longitudinal antes de haver execuções suficientes para comparação.
- explicar as diferenças entre UFs por causalidade ou avaliar suficiência da rede.

## Critérios de aceite

1. Uma execução local processa o ZIP sem extrair o CSV e gera JSON agregado para o site.
2. O total de registros lidos reconcilia com a soma por UF, incluindo a categoria de UF inválida.
3. Cada controle informa regra, dimensão, severidade, registros avaliados, falhas e resultado.
4. Nenhum campo de contato, endereço, CNPJ, nome ou coordenada aparece nos artefatos públicos.
5. O painel Streamlit possui filtro por UF, estado de erro e leitura adequada em tela estreita.
6. Testes automatizados cobrem normalização, controles, reconciliação e contrato de privacidade.
7. O fluxo agendado baixa novamente a fonte, testa, gera e publica o mesmo artefato validado.
8. O ETL interrompe a publicação se a fonte populacional não trouxer uma única estimativa para as 27 UFs.
9. A junção entre CNES e IBGE não aceita UF válida sem correspondência populacional.
10. O painel apresenta a taxa por 100 mil habitantes, o ano do denominador e seu limite de interpretação.
11. O relatório de auditoria identifica URL, hash, referência e horário de obtenção das duas fontes.
12. O processamento de leitos usa apenas a maior competência válida presente no arquivo anual.
13. O total nacional de leitos reconcilia com a soma das 27 UFs na competência selecionada.
14. A publicação é interrompida se houver UF inválida, CNES repetido ou quantidade negativa na competência selecionada.
15. O painel apresenta total, parcela SUS e taxas por 100 mil habitantes sem expor estabelecimentos, contatos ou endereços.
16. A rastreabilidade identifica competência, URL, hash, quantidade de linhas e horário de obtenção da fonte de leitos.

## Restrições e riscos

- A base é autodeclarada e enviada por gestores locais; uma falha cadastral não prova problema assistencial.
- A fonte pode alterar schema, nome interno do ZIP ou disponibilidade. Mudança incompatível deve interromper a publicação.
- O portal informa atualização diária, mas a automação deve comparar o hash e aceitar execuções sem mudança.
- O aplicativo Streamlit é público. Somente agregados aprovados pelo contrato de privacidade podem entrar em `data/published`.

## Evidências de conclusão

- saída dos testes e do gerador;
- `data/published/dashboard.json` e `data/published/audit-report.json` gerados a partir da fonte real;
- inspeção visual em desktop e mobile;
- histórico Git com incrementos separados;
- execução do workflow no GitHub após a publicação do repositório.

## Situação em 2026-10-03

Fato verificado: o recurso CSV oficial responde em `https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/CNES/cnes_estabelecimentos_csv.zip` e continha `cnes_estabelecimentos.csv` com cabeçalho separado por ponto e vírgula. Em 2026-10-03, a entrega foi alterada de site estático para um único painel Streamlit por decisão do usuário. A publicação externa ainda não foi executada.

## Situação em 2026-10-10

Fato verificado: a API SIDRA da tabela 6579, variável 9324, retornou estimativas de 2026 para as 27 UFs. O ETL integrado foi executado com as fontes reais, reconciliou 638.867 registros do CNES e publicou população total de 214.211.951 pessoas. A taxa nacional calculada foi de 298,24 registros cadastrais por 100 mil habitantes.

## Situação em 2026-10-11

Fato verificado: a execução manual nº 11 do workflow terminou com sucesso para o commit `a26a931` e gerou o commit de dados `5ea3be3`. O Streamlit público apresentou a verificação das 15:20, os dois painéis em rotas próprias e a parte 2 com definições, filtros, gráfico e tabela. A interface mostra taxas arredondadas, mantendo os valores decimais no cálculo e no ordenamento.

## Situação em 2026-10-17

Fato verificado localmente: o arquivo oficial `Leitos_csv_2026.zip` continha 57.608 linhas de janeiro a agosto de 2026. O processamento selecionou somente as 7.220 linhas da competência 08/2026, com cobertura das 27 UFs, e reconciliou 523.117 leitos existentes, 354.435 leitos destinados ao SUS, 64.063 leitos de UTI e 32.096 leitos de UTI destinados ao SUS. Com a estimativa populacional de 2026, a taxa nacional calculada foi de 244,21 leitos existentes e 165,46 leitos SUS por 100 mil habitantes. A publicação externa da parte 3 ainda depende de commit e execução do fluxo no GitHub.
