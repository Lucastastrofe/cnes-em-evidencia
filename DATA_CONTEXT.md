# Contexto dos dados

## Fonte

- Conjunto: CNES — Cadastro Nacional de Estabelecimentos de Saúde.
- Responsável pela publicação: Ministério da Saúde.
- Catálogo: <https://dadosabertos.saude.gov.br/dataset/cnes-cadastro-nacional-de-estabelecimentos-de-saude>
- Recurso usado: CSV compactado, atualizado pela fonte.
- Frequência informada no catálogo em 2026-10-03: diária.
- Licença exibida pelo portal: Creative Commons Atribuição-SemDerivações 3.0.

O hash, tamanho, horário de obtenção e cabeçalho observado são registrados a cada execução no relatório de auditoria.

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

