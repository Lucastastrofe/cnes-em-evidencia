# API pública de leitura

Base: https://lucastastrofe.github.io/cnes-em-evidencia/api/v1

- /index.json: caminhos disponíveis e limitações de consulta
- /ufs.json: perfis das UFs
- /ufs/35.json: perfil de São Paulo
- /tabelas/leitos_uf.json: tabela completa
- /tabelas/servicos_uf_classificacao/ufs/35.json: serviços de SP
- /dicionario.json e /dicionario.csv: definição e origem das colunas
- /fontes.json: referências oficiais
- /metadados.json: execução, atualização e competências
- /csv/{tabela}.csv: mesma tabela em CSV
- /dados.zip: tabelas, SQLite, esquema SQL, dicionário, fontes e auditoria

GET e HEAD são servidos como arquivos estáticos pelo GitHub Pages. Não há execução de
Python ou banco a cada requisição, autenticação, escrita, paginação ou filtros por query
string. Recortes de UF são caminhos pré-gerados; ?uf=35 não filtra uma tabela.
Tabela inexistente ou UF fora do contrato retorna 404 do provedor (pode ser HTML).

As tabelas retornam metadados, total e dados. Os códigos são strings. A versão do contrato
é 2.0. Guarde respostas localmente, use timeout e retentativas limitadas com espera
progressiva; respeite Retry-After quando recebido. Downloads completos são preferíveis a
muitas consultas pequenas para ingestão de todas as UFs. Confira id_execucao ao combinar
respostas e não interprete HTTP 200 como comprovação de que a origem mudou naquele dia.

Gratuito em repositório público. Não há promessa de chamadas ilimitadas ou SLA.
GitHub Pages informa limite flexível de 100 GB/mês de tráfego e pode responder 429:
https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
Esses limites e a política de uso foram consultados em 19/11/2026.
O volume por chamada varia com a tabela; consulte Content-Length, quando disponível.
Não foram realizados testes de carga contra o serviço público.

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
