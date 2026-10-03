# CNES em Evidência

Dashboard e pipeline de auditoria da base aberta de estabelecimentos de saúde do CNES. O projeto mostra os indicadores e, junto deles, a origem, o hash do arquivo, as regras executadas, os achados e a reconciliação da execução.

## Resultado atual

A fotografia processada em 3 de outubro de 2026 continha 637.996 registros. Sete dos oito controles não encontraram ocorrências; o controle de completude geográfica encontrou 59.184 registros sem o par completo de coordenadas, ou 9,3% da base.

Esses resultados descrevem o arquivo processado. Eles não medem qualidade assistencial, conformidade sanitária ou disponibilidade atual de serviços.

## O que o projeto demonstra

- processamento de um CSV de 231 MB diretamente do ZIP, sem carregar a base inteira na memória;
- controles reproduzíveis de completude, unicidade e validade;
- reconciliação entre registros lidos e agregados;
- dashboard estático, responsivo e sem backend;
- atualização diária e publicação no GitHub Pages;
- minimização de dados e contrato automatizado de privacidade.

## Fluxo

```text
Arquivo oficial do CNES
        ↓
validação do schema e leitura em fluxo
        ↓
controles e agregações por UF
        ↓
reconciliação + relatório de auditoria
        ↓
site estático publicado no GitHub Pages
```

## Privacidade

O arquivo de origem contém campos que não são necessários ao dashboard. Nomes, contatos, endereços, identificação fiscal, coordenadas e registros individuais não entram nos artefatos públicos. O site recebe somente contagens agregadas e o relatório da execução.

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
python -m http.server 8000 --directory site
```

Abra `http://localhost:8000`. Instruções de publicação, diagnóstico e rollback estão em [`RUNBOOK.md`](RUNBOOK.md).

## Organização

```text
src/cnes_audit/   download, leitura, controles e geração
site/             interface e artefatos agregados
tests/            regras, fonte, privacidade e contrato da página
.github/workflows verificação, atualização e publicação
```

O escopo e os critérios de aceite estão em [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md). A classificação e as limitações dos dados estão em [`DATA_CONTEXT.md`](DATA_CONTEXT.md).

## Limitações

- a fonte pode refletir ritmos diferentes de atualização entre gestores;
- uma ausência cadastral não comprova ausência de estrutura ou serviço;
- tipos de estabelecimento aparecem por código até que uma tabela oficial versionada seja incorporada;
- o primeiro incremento não guarda série histórica.

## Licença

O código deste repositório é distribuído sob a licença MIT. Os dados permanecem sujeitos aos termos informados pelo publicador original.

