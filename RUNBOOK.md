# Operação

## Execução local

Requisitos: Python 3.11 ou mais recente. O pipeline de produção não possui dependências externas.

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python -m cnes_audit.cli
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

O segundo comando baixa o cadastro do CNES, a estimativa populacional mais recente do IBGE, o arquivo anual de leitos e as consultas nacionais de equipes e serviços do TabNet para `data/work`. O processamento valida as cinco fontes, seleciona as competências mais recentes, integra por UF e substitui os dois JSON de `data/published` de forma atômica.

Para reproduzir uma fotografia já baixada:

```powershell
$env:PYTHONPATH = "src"
python -m cnes_audit.cli --input caminho/cnes.zip --population-input caminho/populacao.json --beds-input caminho/leitos.zip --teams-input caminho/equipes.html --teams-competence 202609 --services-input caminho/servicos.html --services-competence 202609
```

## Publicação no Streamlit Community Cloud

1. Criar um repositório público no GitHub e enviar a branch `main`.
2. Entrar em <https://share.streamlit.io> com a conta do GitHub.
3. Criar o app apontando para o repositório, branch `main` e `streamlit_app.py`.
4. Selecionar Python 3.13 nas configurações avançadas.
5. Executar manualmente `Atualizar dados do painel` na primeira publicação.

Depois disso, o fluxo roda diariamente a partir das 09:17 UTC e registra cada verificação concluída. O Streamlit acompanha o repositório e atualiza o app quando o commit chega. A interface separa o horário da verificação da data informada pela fonte: uma execução nova não significa, por si só, que o publicador alterou o arquivo. O agendamento não garante horário exato; o GitHub pode atrasar execuções em períodos de maior carga.

## Evidências de uma execução

- logs do job com quantidade de registros e controles com achados;
- commit automatizado contendo apenas os agregados alterados;
- `data/published/audit-report.json`, contendo execução, versão do código, hash, metadados da fonte e reconciliação;
- metadados separados do CNES e do IBGE, incluindo hashes e ano populacional usado;
- metadados da fonte de leitos, incluindo hash, competência e linhas selecionadas;
- metadados da consulta de equipes, incluindo hash, competência e totais reconciliados;
- metadados da consulta de serviços, incluindo hash, competência e totais reconciliados;
- logs do Streamlit Community Cloud para diagnóstico do aplicativo.

## Falhas esperadas

### A fonte não responde

O download tenta novamente três vezes e encerra com erro. O deploy não roda, preservando a última versão publicada. Verifique o catálogo oficial antes de alterar a URL.

### O schema mudou

O pipeline informa as colunas contratuais ausentes e interrompe a publicação. Compare a fonte com `DATA_CONTEXT.md`, ajuste o contrato e os testes antes de aceitar a mudança.

### A população não cobre as 27 UFs

O ETL interrompe a publicação se a API do IBGE retornar mais de um ano, códigos repetidos, valor não positivo ou cobertura diferente das 27 UFs. Confirme a tabela 6579 e a variável 9324 antes de alterar o contrato.

### A fonte de leitos falhou

O processamento interrompe a publicação quando o ZIP não contém um único CSV, o schema contratado muda, a maior competência não cobre as 27 UFs, um CNES aparece repetido ou uma quantidade é negativa ou inconsistente. Confirme também se `DEFAULT_BEDS_URL` aponta para o arquivo do ano corrente; o portal publica um recurso separado a cada ano.

### A reconciliação falhou

Quando a consulta de equipes não informa competência, altera o formato, omite alguma UF ou apresenta totais diferentes entre estados, tipos e Brasil, a publicação é interrompida. Confirme o formulário nacional de Equipes de Saúde antes de alterar o contrato.

Quando a consulta de serviços não informa competência, altera o formato, omite alguma UF ou apresenta totais diferentes entre UFs, classificações e Brasil, a publicação é interrompida. Confirme o formulário nacional de Serviço/Classificação antes de alterar o contrato.

Nenhum artefato novo deve ser promovido. Preserve o ZIP da execução com acesso restrito durante a investigação e não o anexe a issues públicas.

### O painel foi publicado com problema visual

Reverta o commit defeituoso. O Streamlit atualizará o app a partir do estado anterior do repositório. Os dados brutos não precisam ser recuperados para o rollback.

## Retenção

- `data/work`: temporário e não versionado;
- JSON agregado e relatório de auditoria: permanecem versionados até a próxima execução com mudança;
- logs do workflow: conforme a configuração de retenção do repositório.
