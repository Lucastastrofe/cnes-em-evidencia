# Parte 8: consulta territorial

Objetivo: permitir comparar a presença cadastral por UF e reutilizar os agregados com origem e período identificados.

Revisão de interação: o clique no mapa deve atualizar a UF do perfil. As abas mostram
composição dos leitos SUS, tipos de equipe, classificações de serviços e evolução mensal.
Busca e exportação preservam o recorte estadual. Validado no navegador com clique em Mato Grosso.

Aceite: 27 UFs na malha e no produto; totais reconciliados por indicador; chave única;
contagens inteiras; nulos preservados; comparação absoluta e por população; tabela acessível;
download CSV/JSON; períodos por fonte; navegação legível em telas estreitas.

Persistência: uf-profile.json e uf-profile.csv são projeções da mesma execução de dashboard.json.
O pipeline completo deve ser reexecutado para reconstrução. Não editar os valores publicados à mão.
A escrita usa arquivos temporários; a publicação pelo commit do pipeline promove o conjunto.
A interface bloqueia leitura de perfil com run_id diferente do dashboard.

Não se somam unidades diferentes nem se cria escore de desempenho. Os indicadores descrevem
cadastros. O mapa estadual não depende da completude de coordenadas de estabelecimentos.
O arquivo cartográfico está versionado e não exige chamada externa durante o uso do painel.

Evolução possível: detalhamento municipal condicionado à cobertura e compatibilidade de cada
fonte; nesse cenário, avaliar Parquet/DuckDB com consultas representativas antes da adoção.
