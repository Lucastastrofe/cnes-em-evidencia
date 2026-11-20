# Revisão de gráficos e leitura

- Leitos: barras para total, linhas para SUS e total menos SUS. Uma escala, sem eixo
  secundário. O restante é calculado com contagens exatas, antes do arredondamento visual.
  Unidades absoluta e populacional são selecionáveis; o recorte dos dez maiores/menores
  segue a unidade escolhida. Linhas entre UFs não indicam evolução temporal.
- Evolução estadual: mesma composição em barras e linhas, com meses no eixo horizontal.
- Mapa: seleção por contorno, sem reduzir a opacidade dos estados e distorcer a escala
  de cores. Uma aba em barras permite comparar os mesmos valores; tabela continua disponível.
- População: dispersão para relação entre duas medidas, sem transformar presença em acesso.
- Equipes e serviços: barras para categorias e detalhes em tabelas; descrições completas
  permanecem acessíveis no tooltip e na tabela. O padrão de fontes e legendas foi ampliado.
- Profissionais: posição relativa e associação ao SUS permanecem em dispersão com referências.
- Qualidade: painel de controle com reconciliação e ocorrências relativas por UF. Não é
  uma nota de conformidade institucional, e um achado não é inferência assistencial.
- Downloads: duas escolhas completas (SQLite ou ZIP) e um fluxo tabela → recorte → formato.
  CSV, Parquet e JSON são isolados e usam a mesma seleção.

Verificação: testes funcionais de todas as análises; composição reconciliada e gráfico
de leitos renderizado em PNG para inspeção. A revisão visual da aplicação completa em
navegador/mobile não foi refeita nesta rodada por indisponibilidade do controle do navegador.
