# Operação

## Execução local

Requisitos: Python 3.11 ou mais recente. O pipeline de produção não possui dependências externas.

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python -m cnes_audit.cli
python -m http.server 8000 --directory site
```

O segundo comando baixa a fonte oficial para `data/work`, processa o CSV diretamente do ZIP e substitui os dois JSON de `site/data` de forma atômica.

Para reproduzir uma fotografia já baixada:

```powershell
$env:PYTHONPATH = "src"
python -m cnes_audit.cli --input caminho/arquivo.zip
```

## Publicação

1. Criar um repositório público no GitHub e enviar a branch `main`.
2. Em **Settings → Pages → Build and deployment**, selecionar **GitHub Actions**.
3. Executar manualmente `Atualizar dados e publicar` na primeira publicação.
4. Conferir a URL exposta pelo ambiente `github-pages`.

Depois disso, o fluxo roda diariamente às 09:17 UTC, além de cada envio para `main`. O agendamento não garante horário exato: o GitHub pode atrasar execuções em períodos de maior carga.

## Evidências de uma execução

- logs do job com quantidade de registros e controles com achados;
- artefato do GitHub Pages com retenção de sete dias;
- `site/data/audit-report.json` publicado, contendo execução, versão do código, hash, metadados da fonte e reconciliação;
- ambiente `github-pages` vinculado ao deployment.

## Falhas esperadas

### A fonte não responde

O download tenta novamente três vezes e encerra com erro. O deploy não roda, preservando a última versão publicada. Verifique o catálogo oficial antes de alterar a URL.

### O schema mudou

O pipeline informa as colunas contratuais ausentes e interrompe a publicação. Compare a fonte com `DATA_CONTEXT.md`, ajuste o contrato e os testes antes de aceitar a mudança.

### A reconciliação falhou

Nenhum artefato novo deve ser promovido. Preserve o ZIP da execução com acesso restrito durante a investigação e não o anexe a issues públicas.

### O site foi publicado com problema visual

Reexecute o deployment do commit anterior na interface do GitHub Actions ou reverta o commit defeituoso. Os dados brutos não precisam ser recuperados para o rollback do site.

## Retenção

- `data/work`: temporário e não versionado;
- artefato de deploy: sete dias;
- JSON agregado e relatório de auditoria: permanecem no site publicado até a próxima execução;
- logs do workflow: conforme a configuração de retenção do repositório.

