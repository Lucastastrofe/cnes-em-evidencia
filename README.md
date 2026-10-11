# CNES em Evidência

Aplicação Streamlit e pipeline de qualidade da base aberta de estabelecimentos de saúde do CNES. A navegação separa o painel de qualidade cadastral do painel de comparação por população; a explicação completa do projeto fica no portfólio.

## Resultado atual

A fotografia processada em 10 de outubro de 2026 continha 638.867 registros. Sete dos oito controles não encontraram ocorrências; o controle de completude geográfica encontrou 59.174 registros sem o par completo de coordenadas, ou 9,3% da base.

A segunda parte integra a fotografia do CNES à estimativa populacional de 2026 do IBGE. O resultado nacional foi de 298,24 registros cadastrais por 100 mil habitantes. A taxa permite comparar presença cadastral relativa, mas não mede oferta, acesso ou capacidade assistencial.

Esses resultados descrevem o arquivo processado. Eles não medem qualidade assistencial, conformidade sanitária ou disponibilidade atual de serviços.

## O que o projeto demonstra

- processamento de um CSV de 231 MB diretamente do ZIP, sem carregar a base inteira na memória;
- controles reproduzíveis de completude, unicidade e validade;
- reconciliação entre registros lidos e agregados;
- dois painéis interativos em uma única aplicação Streamlit;
- verificação diária da fonte e regeneração dos agregados pelo GitHub Actions;
- ETL integrado entre CNES e estimativas populacionais do IBGE;
- comparação por UF usando população como denominador explícito;
- filtros para comparar UFs e alternar entre todas, as dez maiores e as dez menores taxas;
- minimização de dados e contrato automatizado de privacidade.

## Fluxo

```text
CNES (ZIP/CSV) ──→ validação + auditoria ──┐
                                           ├─→ junção por UF ─→ agregados + auditoria ─→ Streamlit
IBGE (SIDRA/JSON) ─→ validação das 27 UFs ─┘
```

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
- o primeiro incremento não guarda série histórica.
- a taxa por população descreve cadastro relativo e não permite concluir suficiência da rede.

## Licença

O código deste repositório é distribuído sob a licença MIT. Os dados permanecem sujeitos aos termos informados pelo publicador original.
