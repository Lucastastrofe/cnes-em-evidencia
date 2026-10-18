# Contexto dos dados

## Fonte

- Conjunto: CNES — Cadastro Nacional de Estabelecimentos de Saúde.
- Responsável pela publicação: Ministério da Saúde.
- Catálogo: <https://dadosabertos.saude.gov.br/dataset/cnes-cadastro-nacional-de-estabelecimentos-de-saude>
- Recurso usado: CSV compactado, atualizado pela fonte.
- Frequência informada no catálogo em 2026-10-03: diária.
- Licença exibida pelo portal: Creative Commons Atribuição-SemDerivações 3.0.

O hash, tamanho, horário de obtenção e cabeçalho observado são registrados a cada execução no relatório de auditoria.

### População

- Conjunto: Estimativas da População do IBGE.
- Tabela SIDRA: 6579.
- Variável: 9324 — População residente estimada.
- Recorte: 27 Unidades da Federação.
- Período: último ano disponível na API.
- Unidade: pessoas.

O JSON bruto do SIDRA permanece apenas em `data/work`. O artefato público mantém população agregada por UF, ano de referência, URL e hash da resposta usada.

### Leitos

- Conjunto: Hospitais e Leitos — CNES Hospital Leito.
- Responsável pela publicação: Ministério da Saúde.
- Catálogo: <https://dadosabertos.saude.gov.br/dataset/hospitais-e-leitos>.
- Recurso: arquivo CSV compactado do ano corrente, organizado por competência mensal.
- Recorte publicado: maior competência válida encontrada no arquivo.
- Unidade: leitos cadastrados.

O ZIP bruto permanece apenas em `data/work`. O processamento lê somente `COMP`, `UF`, `CNES`, `LEITOS_EXISTENTES`, `LEITOS_SUS`, `UTI_TOTAL_EXIST` e `UTI_TOTAL_SUS`. Nomes, endereços, contatos e linhas de estabelecimentos não entram nos artefatos públicos.

### Equipes de saúde

- Conjunto: CNES — Equipes de Saúde.
- Responsável pela publicação: Ministério da Saúde, via TabNet/DATASUS.
- Consulta: quantidade por tipo de equipe segundo Unidade da Federação.
- Recorte: maior competência disponível no formulário nacional.
- Unidade: registros de equipes ativas.

A resposta HTML da consulta permanece em `data/work`. O artefato público contém somente contagens agregadas por UF e tipo de equipe, além de competência, URL e hash. Não são consultados nomes de profissionais, estabelecimentos ou registros individuais.

### Serviços cadastrados

- Conjunto: CNES — Estabelecimentos — Classificação do Serviço.
- Responsável pela publicação: Ministério da Saúde, via TabNet/DATASUS.
- Consulta: quantidade por Unidade da Federação segundo classificação do serviço.
- Recorte: maior competência disponível no formulário nacional.
- Unidade: registros de serviço/classificação.

A resposta HTML da consulta permanece em `data/work`. O artefato público contém somente contagens agregadas por UF e classificação, além de competência, URL e hash. Como um estabelecimento pode informar mais de uma classificação, a soma não representa estabelecimentos únicos.

## Unidade de análise

Uma linha do arquivo de estabelecimentos. `CO_CNES` é tratado como chave esperada para o controle de unicidade. Essa expectativa é um contrato do projeto e uma violação é publicada como alerta, sem remoção silenciosa.

## Campos usados no processamento

- `CO_CNES`: unicidade e completude;
- `CO_UF`: agrupamento e validade;
- `CO_IBGE`: completude e formato do código municipal;
- `TP_UNIDADE`: agrupamento por tipo;
- `TP_GESTAO`: distribuição de gestão;
- `NU_LATITUDE` e `NU_LONGITUDE`: completude conjunta e validade de faixa, sem publicação dos valores.

O pipeline falha se um campo obrigatório ao contrato desaparecer. Demais campos da fonte não são copiados para o site.

## Classificação e privacidade

O arquivo de origem inclui atributos institucionais e campos que podem servir como contato ou permitir identificação indireta. O ZIP bruto fica apenas no ambiente temporário da execução e é ignorado pelo Git.

Os artefatos públicos contêm contagens agregadas. Ficam proibidos por contrato: nomes, razão social, nome fantasia, telefone, e-mail, logradouro, número, bairro, CEP, CNPJ, latitude, longitude e qualquer linha individual.

## Interpretação

Os indicadores descrevem o arquivo processado. Não medem qualidade do atendimento, conformidade sanitária, disponibilidade em tempo real ou desempenho da gestão local. Diferenças por UF podem refletir processos distintos de cadastramento e atualização.

A taxa integrada é calculada como `registros do CNES na UF / população estimada da UF × 100.000`. Ela permite comparar presença cadastral relativa entre UFs de tamanhos diferentes. Não mede quantidade de leitos, equipes, procedimentos, capacidade instalada, acesso ou suficiência da rede. O numerador é uma fotografia corrente do CNES; o denominador é uma estimativa anual do IBGE, e essa diferença temporal deve permanecer visível.

Na terceira parte, `leitos existentes por 100 mil habitantes` e `leitos SUS por 100 mil habitantes` usam os totais da competência mensal mais recente como numerador e a estimativa anual do IBGE como denominador. `LEITOS_SUS` é uma parcela de `LEITOS_EXISTENTES`, não uma categoria adicional. Os indicadores descrevem capacidade cadastrada; não informam ocupação, disponibilidade imediata, produção, acesso efetivo ou qualidade assistencial.

Na quarta parte, `equipes por 100 mil habitantes` usa os registros ativos da competência mais recente do TabNet e a estimativa anual do IBGE. O total descreve registros de equipes, não profissionais únicos, atendimentos, cobertura populacional ou qualidade da assistência. Categorias históricas e atuais permanecem separadas conforme a fonte; o projeto não cria equivalências sem uma regra oficial versionada.

Na quinta parte, `registros de serviço/classificação por 100 mil habitantes` usa as contagens da competência mais recente do TabNet e a estimativa anual do IBGE. O indicador permite comparar presença cadastral relativa. Ele não mede atendimentos, disponibilidade operacional, capacidade instalada, produção, acesso ou suficiência. Os códigos e descrições permanecem como publicados pela fonte.
