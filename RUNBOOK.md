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

O segundo comando baixa a fonte oficial para `data/work`, processa o CSV diretamente do ZIP e substitui os dois JSON de `data/published` de forma atômica.

Para reproduzir uma fotografia já baixada:

```powershell
$env:PYTHONPATH = "src"
python -m cnes_audit.cli --input caminho/arquivo.zip
```

## Publicação no Streamlit Community Cloud

1. Criar um repositório público no GitHub e enviar a branch `main`.
2. Entrar em <https://share.streamlit.io> com a conta do GitHub.
3. Criar o app apontando para o repositório, branch `main` e `streamlit_app.py`.
4. Selecionar Python 3.13 nas configurações avançadas.
5. Executar manualmente `Atualizar dados do painel` na primeira publicação.

Depois disso, o fluxo roda diariamente às 09:17 UTC e cria um commit apenas quando os agregados mudarem. O Streamlit acompanha o repositório e atualiza o app quando o commit chega. O agendamento não garante horário exato: o GitHub pode atrasar execuções em períodos de maior carga.

## Evidências de uma execução

- logs do job com quantidade de registros e controles com achados;
- commit automatizado contendo apenas os agregados alterados;
- `data/published/audit-report.json`, contendo execução, versão do código, hash, metadados da fonte e reconciliação;
- logs do Streamlit Community Cloud para diagnóstico do aplicativo.

## Falhas esperadas

### A fonte não responde

O download tenta novamente três vezes e encerra com erro. O deploy não roda, preservando a última versão publicada. Verifique o catálogo oficial antes de alterar a URL.

### O schema mudou

O pipeline informa as colunas contratuais ausentes e interrompe a publicação. Compare a fonte com `DATA_CONTEXT.md`, ajuste o contrato e os testes antes de aceitar a mudança.

### A reconciliação falhou

Nenhum artefato novo deve ser promovido. Preserve o ZIP da execução com acesso restrito durante a investigação e não o anexe a issues públicas.

### O painel foi publicado com problema visual

Reverta o commit defeituoso. O Streamlit atualizará o app a partir do estado anterior do repositório. Os dados brutos não precisam ser recuperados para o rollback.

## Retenção

- `data/work`: temporário e não versionado;
- JSON agregado e relatório de auditoria: permanecem versionados até a próxima execução com mudança;
- logs do workflow: conforme a configuração de retenção do repositório.
