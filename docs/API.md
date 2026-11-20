# API pública de leitura

Base: https://lucastastrofe.github.io/cnes-em-evidencia/api/v1

- /index.json: caminhos disponíveis e limitações de consulta
- /catalogo.json: todas as tabelas, camadas, grãos, linhas, colunas e formatos
- /catalogo-dcat.json: catálogo de distribuições em JSON-LD usando termos DCAT
- /sqlite.json: manifesto do snapshot SQLite, hash e URL imutável
- /ufs.json: perfis das UFs
- /ufs/35.json: perfil de São Paulo
- /tabelas/leitos_uf.json: tabela completa
- /tabelas/servicos_uf_classificacao/ufs/35.json: serviços de SP
- /dicionario.json e /dicionario.csv: definição e origem das colunas
- /fontes.json: referências oficiais
- /metadados.json: execução, atualização e competências
- /csv/{tabela}.csv: mesma tabela em CSV
- /parquet/{tabela}.parquet: mesma tabela com tipos e dicionário preservados
- /dados.zip: tabelas, SQLite, esquema SQL, dicionário, fontes e auditoria

GET e HEAD são servidos como arquivos estáticos pelo GitHub Pages. Não há execução de
Python ou banco a cada requisição, autenticação, escrita, paginação ou filtros por query
string. Recortes de UF são caminhos pré-gerados; ?uf=35 não filtra uma tabela.
Tabela inexistente ou UF fora do contrato retorna 404 do provedor (pode ser HTML).

As tabelas retornam metadados, total e dados. Os códigos são strings. A versão do contrato
é 3.0. Guarde respostas localmente, use timeout e retentativas limitadas com espera
progressiva; respeite Retry-After quando recebido. Downloads completos são preferíveis a
muitas consultas pequenas para ingestão de todas as UFs. Confira id_execucao ao combinar
respostas e não interprete HTTP 200 como comprovação de que a origem mudou naquele dia.

Gratuito em repositório público. Não há promessa de chamadas ilimitadas ou SLA.
GitHub Pages informa limite flexível de 100 GB/mês de tráfego e pode responder 429:
https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
Esses limites e a política de uso foram consultados em 19/11/2026.
O volume por chamada varia com a tabela; consulte Content-Length, quando disponível.
Não foram realizados testes de carga contra o serviço público.

## Alternativa principal para consultas SQL

O cliente src/cnes_audit/snapshot_client.py obtém sqlite.json, valida tamanho e SHA-256,
baixa o arquivo identificado pelo hash e abre uma cópia local com mode=ro e immutable=1.
A conexão não é uma conexão SQLite direta por HTTP. As consultas rodam no ambiente do
consumidor, que deve buscar atualizações quando necessário e guardar a versão usada
para reproduzir uma pesquisa. As sete últimas versões de conteúdo são retidas no host.
A API JSON continua disponível como alternativa e para descoberta do catálogo.

## Uso em Python

```python
import requests

url = "https://lucastastrofe.github.io/cnes-em-evidencia/api/v1/tabelas/leitos_uf.json"
response = requests.get(url, timeout=30)
response.raise_for_status()
payload = response.json()
print(payload["metadados"]["id_execucao"])
print(payload["dados"][0]["leitos_existentes"])
```
