# Revisão de gráficos e leitura

## Revisão de navegação — 20/11/2026

Necessidade: quem chega pela primeira vez precisa escolher uma pergunta, entender o
recorte e consultar o detalhe sem conhecer a sequência semanal do projeto. Pesquisadores
e analistas precisam encontrar tabela, recorte e formato sem percorrer a documentação.

Problemas identificados na estrutura e no comportamento:

| Problema | Impacto | Alteração |
| --- | --- | --- |
| Temas exigiam conhecimento prévio do projeto | Alto | Seletor apresenta perguntas que cada análise responde; rotas publicadas continuam válidas |
| Seleção da UF aparecia depois do mapa | Alto | Seleção antecipada; clique no mapa e seleção manual mantêm o mesmo estado e contorno |
| Filtros do mapa apareciam no perfil e no método | Médio | Controles de medida e unidade aparecem apenas no mapa |
| Taxa por população era apresentada como um interruptor | Alto | Escolha explícita entre taxa e quantidade, com definição e aviso de arredondamento |
| Explicações repetidas precediam os filtros | Médio | Orientação de leitura sob demanda e menor espaçamento; fonte, período e limites permanecem visíveis |
| Base completa competia com download de tabela | Médio | Pacotes em expansão própria; fluxo principal é tabela → UF → formato, prévia opcional |
| Orientação de exportação citava um menu inexistente | Médio | Link direto para Dados e documentação |

Aceite: manter contagens e cálculos; preservar UF ao trocar mapa/perfil/método;
não exibir controles sem função; manter formatos individuais, fontes e limitações.
Verificação funcional com Streamlit AppTest para troca manual da UF e retorno ao mapa.
O callback de seleção tem teste separado com evento simulado, sem clique real em navegador.
A inspeção visual completa em desktop e mobile continua pendente: não há controle
de navegador disponível nesta sessão. Não se afirma validação de viewport ou de toque.

## Gráficos e unidades

### Ajustes a partir das capturas do usuário

- Menu: os links personalizados usam `stPageLink`, enquanto o estilo anterior mirava
  `stSidebarNav`. Os rótulos agora são Análises, Dados e fontes e Qualidade. O estilo
  atinge o componente correto, permite quebra de linha e mantém área de ação e foco
  de teclado. O parágrafo explicativo abaixo dos links foi removido.
- Perfil de leitos: substituída a barra dependente de eixo/legenda por composição
  proporcional com rótulos permanentes fora da barra. Total, quantidades SUS e demais,
  percentuais e cores aparecem juntos, sem depender de hover. As parcelas pequenas
  continuam identificadas; não se força um tamanho mínimo que distorça a proporção.
- Exemplo de aceite da captura: Acre, total 1.847 = SUS 1.635 + demais 212;
  participações exibidas de 88,5% e 11,5%. Contagens inteiras com ponto de milhar.
- Sem leitos, exibir aviso e não calcular percentual. Com 0% ou 100% SUS,
  preservar os dois rótulos e os valores, mesmo que um segmento tenha largura zero.
- Composição com figura semântica e resumo acessível. Os rótulos usam grade fluida;
  não há texto dentro da barra para ser cortado em telas estreitas.

Verificação: testes de apresentação e carregamento das páginas. A ferramenta de
controle do navegador falhou ao iniciar nesta sessão; não houve nova captura real
da aplicação nem validação visual de viewport mobile.

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
