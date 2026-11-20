# CNES em Evidência

## Dados, dicionário e API

O contrato publicado 2.1 usa os nomes da fonte normalizados quando há correspondência
direta; agregações e indicadores calculados têm nomes e transformações explícitos.
O mesmo contrato alimenta arquivos persistidos, CSVs, JSONs e uma cópia SQLite com
chaves primárias e relacionamentos. O pacote inclui o esquema SQL e o dicionário completo.

- [Central de dados](https://cnes-em-evidencia.streamlit.app/dados)
- [Índice da API](https://lucastastrofe.github.io/cnes-em-evidencia/api/v1/index.json)
- [Contrato e migração](docs/CONTRATO-DADOS.md)
- [Documentação da API gratuita e seus limites](docs/API.md)
- [Divulgação e uso responsável](docs/USO-RESPONSAVEL.md)

A API entrega respostas estáticas por tabela e UF, geradas na atualização diária.
Não depende de manter o Streamlit acordado. O serviço gratuito está sujeito aos limites
do GitHub Pages; não há promessa de chamadas ilimitadas ou de disponibilidade contínua.

Para gerar os contratos e arquivos HTTP a partir da última execução validada:

```bash
python -m cnes_audit.publish
```

## Produto de dados e estudo aplicado

O produto final separa cinco distribuições de fontes normalizadas e agregadas das 14
visões analíticas. As primeiras preservam nomes como comp, uf, leitos_existentes,
unidade_da_federacao, quantidade e os campos D1C/D1N/D3C/V do SIDRA em minúsculas.
As visões reúnem contagens, taxas e integrações derivadas. Nenhuma distribuição é
apresentada como microdado bruto: o pipeline já agrega e reorganiza consultas.

O mapa agora é o estudo aplicado **Leitos e participação do SUS**, sem numeração de etapa.
Ele compara capacidade cadastrada, participação SUS e evolução mensal em relação à população.
O produto pode ser reutilizado em outros estudos, independentemente da apresentação da série.

Na central, cada tabela pode ser baixada em CSV, JSON ou Parquet, com o mesmo recorte.
SQLite e esquema SQL são downloads separados. O SQLite inclui a tabela técnica __metadados;
o Parquet incorpora o dicionário no metadata do arquivo. Esses formatos mantêm a informação
de procedência mesmo quando usados fora do painel.

O catálogo da API lista todas as distribuições e seus formatos. A central consulta esse
catálogo por HTTP e permite carregar os dados públicos diretamente, sem apresentar cópias
locais como se fossem respostas remotas.

Para uso principal em pesquisa e análise SQL, recomendamos o snapshot SQLite: o cliente
verifica SHA-256 e tamanho, mantém cópia local pelo hash e abre em modo somente leitura.
Uma nova execução do cliente procura a versão publicada; não é um banco remoto em streaming.
As últimas sete versões de conteúdo ficam hospedadas; estudos devem guardar sua própria cópia.

Os downloads ficam na [central de dados](https://cnes-em-evidencia.streamlit.app/dados).
A central separa arquivos, fontes oficiais e orientações de uso em três abas.
É possível escolher uma tabela, filtrar por UF quando aplicável, conferir uma prévia e
baixar o recorte. O pacote completo permanece disponível sem filtros.

O resumo integrado tem 27 linhas, uma por UF. Ele não substitui as tabelas detalhadas.
Na seção de downloads, o pacote ZIP reúne os CSVs de todos os agregados públicos,
incluindo equipes por tipo e UF, serviços por classificação e UF e leitos por mês e UF.
Inclui também o JSON completo do painel, metadados do perfil, auditoria e orientações de uso.
Os arquivos são gerados a partir da execução publicada e acompanham sua atualização.
O pacote não acrescenta microdados nem municípios: mantém os recortes processados pelo projeto.

O catálogo de fontes informa instituição, links oficiais, recorte publicado, referência,
data de obtenção, hash e limitações. `fontes.json` acompanha o pacote para consumo automatizado.
`manifesto.json` identifica a execução e relaciona cada CSV com linhas, colunas, codificação,
separador, representação de ausências e SHA-256 dos bytes exportados. Preserve os códigos como texto.
Os termos de reutilização devem ser verificados em cada catálogo oficial; MIT licencia o código.

[Abrir o mapa interativo](https://cnes-em-evidencia.streamlit.app/)

A página inicial reúne as dimensões estudadas nas sete etapas em uma consulta por UF.
No menu, abra **Leitos e participação do SUS**. O clique em um estado atualiza o perfil:
composição dos leitos SUS, tipos de equipe, serviços e classificações com busca e download,
e série mensal de leitos. A seleção pelo campo de UF oferece o mesmo detalhamento.
Escolha estabelecimentos, leitos, parcela SUS, equipes, serviços ou profissionais e alterne
entre contagens e taxas por 100 mil habitantes. A tabela oferece os valores do mapa sem
depender de cores ou de passar o mouse. O perfil estadual permite consultar outras dimensões.

O pipeline persiste `data/published/uf-profile.json` e `uf-profile.csv` em cada execução.
O JSON inclui versão do contrato, execução, atualização, competências por fonte e dicionário.
O mapa lê esse produto publicado, sem consultar as fontes durante a navegação. O fluxo diário
existente versiona os arquivos no GitHub e a aplicação usa a atualização seguinte.

São 27 UFs agregadas: arquivos versionados atendem ao consumo atual. DuckDB passa a ser uma
opção quando o produto incorporar histórico amplo ou granularidade municipal. O JSON público
é um arquivo para consumo automatizado, sem serviço de API dedicado ou garantia de disponibilidade.

A integração rejeita chaves duplicadas, contagens fracionárias e códigos de UF inválidos.
Ausências permanecem nulas. Os testes reconciliam cada indicador com os agregados de origem.
Competências diferentes continuam explícitas e a estimativa populacional mantém seu ano.
O mapa não informa acesso, ocupação, disponibilidade ou suficiência assistencial.

**Cartografia:** malha simplificada oficial do IBGE, API de Malhas v3, obtida em 19/11/2026:
<https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/vnd.geo+json&qualidade=minima&intrarregiao=UF>.
A malha é versionada com o projeto; sua atualização é independente da atualização cadastral.
O desenho usa os códigos de UF, não coordenadas dos estabelecimentos. Cinza significa ausência
de indicador, sem substituir por zero. Contagens aparecem inteiras; taxas têm arredondamento de exibição.

Aplicação Streamlit e pipeline de dados abertos do CNES. A navegação separa qualidade cadastral, presença por população, capacidade hospitalar, equipes, serviços cadastrados, evolução mensal de leitos e profissionais cadastrados. A explicação completa do projeto fica no portfólio.

## Resultado atual

A fotografia processada em 10 de outubro de 2026 continha 638.867 registros. Sete dos oito controles não encontraram ocorrências; o controle de completude geográfica encontrou 59.174 registros sem o par completo de coordenadas, ou 9,3% da base.

A segunda parte integra a fotografia do CNES à estimativa populacional de 2026 do IBGE. O resultado nacional foi de 298,24 registros cadastrais por 100 mil habitantes. A taxa permite comparar presença cadastral relativa, mas não mede oferta, acesso ou capacidade assistencial.

A terceira parte processa a competência 08/2026 da fonte oficial de Hospitais e Leitos. Foram reconciliados 523.117 leitos existentes, dos quais 354.435 destinados ao SUS. Isso corresponde a 244,21 leitos existentes e 165,46 leitos SUS por 100 mil habitantes. Os números descrevem capacidade cadastrada, não ocupação ou disponibilidade em tempo real.

A quarta parte consulta a competência 09/2026 de Equipes de Saúde no TabNet. Foram reconciliados 124.459 registros de equipes nas 27 UFs e em 40 tipos com quantidade maior que zero, o equivalente a 58,10 registros por 100 mil habitantes. O total não representa profissionais, atendimentos ou cobertura efetiva.

A quinta parte consulta a competência 09/2026 de serviço/classificação no TabNet. Foram reconciliados 1.060.015 registros nas 27 UFs e em 342 classificações, o equivalente a 494,84 registros por 100 mil habitantes. O resultado pode incluir várias classificações do mesmo estabelecimento e não informa atendimento realizado, disponibilidade, capacidade ou produção.

A sexta parte compara as nove competências disponíveis no arquivo anual de leitos, de 01/2026 a 09/2026. O total nacional passou de 521.602 para 524.000 leitos cadastrados no período. O painel permite acompanhar Brasil ou até cinco UFs, alternando entre total, parcela SUS, UTI e UTI SUS, em quantidade ou por 100 mil habitantes. As variações descrevem o cadastro e não permitem concluir melhora ou piora assistencial.

A sétima parte usa a competência 09/2026 de Profissionais do CNES. A consulta oficial reconciliou 4.763.485 profissionais nas 27 UFs, dos quais 3.704.496 aparecem associados ao atendimento no SUS. O painel combina taxa por 100 mil habitantes e participação no SUS para comparar perfis estaduais. O cadastro não informa jornada, disponibilidade, produtividade, cobertura ou suficiência da força de trabalho.

Esses resultados descrevem o arquivo processado. Eles não medem qualidade assistencial, conformidade sanitária ou disponibilidade atual de serviços.

## O que o projeto demonstra

- processamento de um CSV de 231 MB diretamente do ZIP, sem carregar a base inteira na memória;
- controles reproduzíveis de completude, unicidade e validade;
- reconciliação entre registros lidos e agregados;
- oito páginas interativas em uma única aplicação Streamlit;
- verificação diária da fonte e regeneração dos agregados pelo GitHub Actions;
- ETL integrado entre CNES e estimativas populacionais do IBGE;
- comparação por UF usando população como denominador explícito;
- validação independente de todas as competências da fonte anual de leitos;
- comparação de leitos existentes e destinados ao SUS por 100 mil habitantes;
- série mensal de leitos com seleção de indicador, escala e até cinco UFs;
- descoberta automática da competência mais recente de equipes no TabNet;
- reconciliação de equipes por UF e por tipo antes da publicação;
- descoberta e reconciliação de serviços por UF e classificação;
- descoberta e reconciliação de profissionais por UF e vínculo de atendimento ao SUS;
- comparação entre presença relativa de profissionais e participação associada ao SUS;
- filtros para comparar UFs e alternar entre todas, as dez maiores e as dez menores taxas;
- minimização de dados e contrato automatizado de privacidade.

## Fluxo

```text
CNES estabelecimentos (ZIP/CSV) ─→ qualidade ──────────┐
IBGE (SIDRA/JSON) ───────────────→ população por UF ───┼─→ agregados + auditoria ─→ Streamlit
CNES leitos (ZIP/CSV) ───────────→ competências mensais ┤
CNES profissionais (TabNet) ─────→ vínculo SUS por UF ──┘
```

As consultas nacionais de equipes, serviços e profissionais do TabNet entram no mesmo fluxo e usam a maior competência disponível antes de gerar os agregados.

## Privacidade

O arquivo de origem contém campos que não são necessários ao dashboard. Nomes, contatos, endereços, identificação fiscal, coordenadas e registros individuais não entram nos dados publicados. O painel recebe somente contagens agregadas e o relatório da execução.

Essa minimização reduz exposição desnecessária, mas não transforma o projeto em parecer jurídico sobre a LGPD.

## Fonte e licença dos dados

- [CNES — Cadastro Nacional de Estabelecimentos de Saúde](https://dadosabertos.saude.gov.br/dataset/cnes-cadastro-nacional-de-estabelecimentos-de-saude)
- Publicador: Ministério da Saúde
- Frequência informada pelo catálogo em 3 de outubro de 2026: diária
- Licença exibida pelo portal: Creative Commons Atribuição-SemDerivações 3.0

## Executar

O projeto requer Python 3.11 ou mais recente e não possui dependências de produção.

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python -m cnes_audit.cli
streamlit run streamlit_app.py
```

Abra a URL local exibida pelo Streamlit. Instruções de publicação, diagnóstico e rollback estão em [`RUNBOOK.md`](RUNBOOK.md).

## Organização

```text
src/cnes_audit/   download, leitura, controles e geração
streamlit_app.py  painel interativo
data/published/   agregados e rastreabilidade da execução
tests/            regras, fonte, privacidade e contrato da página
.github/workflows verificação e atualização dos dados
```

O escopo e os critérios de aceite estão em [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md). A classificação e as limitações dos dados estão em [`DATA_CONTEXT.md`](DATA_CONTEXT.md).

## Limitações

- a fonte pode refletir ritmos diferentes de atualização entre gestores;
- uma ausência cadastral não comprova ausência de estrutura ou serviço;
- tipos de estabelecimento aparecem por código até que uma tabela oficial versionada seja incorporada;
- a taxa por população descreve cadastro relativo e não permite concluir suficiência da rede.
- os dados de leitos têm competência mensal e não informam ocupação ou disponibilidade;
- a série histórica disponível começa em 01/2026 e usa a estimativa populacional de 2026 como denominador fixo;
- os registros de equipes não informam quantidade de profissionais, atendimentos ou cobertura efetiva;
- os registros de serviço/classificação não informam atendimento, disponibilidade ou produção;
- o cadastro de profissionais não informa jornada, disponibilidade, produtividade, cobertura ou suficiência;
- o TabNet mantém tipos históricos e atuais de equipe, que permanecem separados no painel;
- a URL do arquivo de leitos é anual e precisa ser revisada na mudança de ano.

## Licença

O código deste repositório é distribuído sob a licença MIT. Os dados permanecem sujeitos aos termos informados pelo publicador original.
