# CNES em Evidência

Aplicação Streamlit e pipeline de dados abertos do CNES. A navegação separa qualidade cadastral, presença por população, capacidade hospitalar, equipes e serviços cadastrados; a explicação completa do projeto fica no portfólio.

## Resultado atual

A fotografia processada em 10 de outubro de 2026 continha 638.867 registros. Sete dos oito controles não encontraram ocorrências; o controle de completude geográfica encontrou 59.174 registros sem o par completo de coordenadas, ou 9,3% da base.

A segunda parte integra a fotografia do CNES à estimativa populacional de 2026 do IBGE. O resultado nacional foi de 298,24 registros cadastrais por 100 mil habitantes. A taxa permite comparar presença cadastral relativa, mas não mede oferta, acesso ou capacidade assistencial.

A terceira parte processa a competência 08/2026 da fonte oficial de Hospitais e Leitos. Foram reconciliados 523.117 leitos existentes, dos quais 354.435 destinados ao SUS. Isso corresponde a 244,21 leitos existentes e 165,46 leitos SUS por 100 mil habitantes. Os números descrevem capacidade cadastrada, não ocupação ou disponibilidade em tempo real.

A quarta parte consulta a competência 09/2026 de Equipes de Saúde no TabNet. Foram reconciliados 124.459 registros de equipes nas 27 UFs e em 40 tipos com quantidade maior que zero, o equivalente a 58,10 registros por 100 mil habitantes. O total não representa profissionais, atendimentos ou cobertura efetiva.

A quinta parte consulta a competência 09/2026 de serviço/classificação no TabNet. Foram reconciliados 1.060.015 registros nas 27 UFs e em 342 classificações, o equivalente a 494,84 registros por 100 mil habitantes. O resultado pode incluir várias classificações do mesmo estabelecimento e não informa atendimento realizado, disponibilidade, capacidade ou produção.

Esses resultados descrevem o arquivo processado. Eles não medem qualidade assistencial, conformidade sanitária ou disponibilidade atual de serviços.

## O que o projeto demonstra

- processamento de um CSV de 231 MB diretamente do ZIP, sem carregar a base inteira na memória;
- controles reproduzíveis de completude, unicidade e validade;
- reconciliação entre registros lidos e agregados;
- cinco painéis interativos em uma única aplicação Streamlit;
- verificação diária da fonte e regeneração dos agregados pelo GitHub Actions;
- ETL integrado entre CNES e estimativas populacionais do IBGE;
- comparação por UF usando população como denominador explícito;
- seleção automática da competência mais recente da fonte anual de leitos;
- comparação de leitos existentes e destinados ao SUS por 100 mil habitantes;
- descoberta automática da competência mais recente de equipes no TabNet;
- reconciliação de equipes por UF e por tipo antes da publicação;
- descoberta e reconciliação de serviços por UF e classificação;
- filtros para comparar UFs e alternar entre todas, as dez maiores e as dez menores taxas;
- minimização de dados e contrato automatizado de privacidade.

## Fluxo

```text
CNES estabelecimentos (ZIP/CSV) ─→ qualidade ──────────┐
IBGE (SIDRA/JSON) ───────────────→ população por UF ───┼─→ agregados + auditoria ─→ Streamlit
CNES leitos (ZIP/CSV) ───────────→ última competência ─┘
```

As consultas nacionais de equipes e serviços do TabNet entram no mesmo fluxo e usam a maior competência disponível antes de gerar os agregados.

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
- o primeiro incremento não guarda série histórica;
- a taxa por população descreve cadastro relativo e não permite concluir suficiência da rede.
- os dados de leitos têm competência mensal e não informam ocupação ou disponibilidade;
- os registros de equipes não informam quantidade de profissionais, atendimentos ou cobertura efetiva;
- os registros de serviço/classificação não informam atendimento, disponibilidade ou produção;
- o TabNet mantém tipos históricos e atuais de equipe, que permanecem separados no painel;
- a URL do arquivo de leitos é anual e precisa ser revisada na mudança de ano.

## Licença

O código deste repositório é distribuído sob a licença MIT. Os dados permanecem sujeitos aos termos informados pelo publicador original.
