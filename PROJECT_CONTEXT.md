# Contexto do projeto

## Propósito

O CNES em Evidência permite inspecionar a cobertura cadastral e os problemas observáveis de qualidade na base aberta de estabelecimentos de saúde. O produto é dirigido a pessoas que usam dados públicos de saúde em análises e precisam avaliar a fonte antes de interpretar seus números.

## Pergunta principal

Quais problemas de completude, unicidade e validade aparecem no cadastro nacional e como eles se distribuem entre as unidades federativas?

## Escopo do primeiro incremento

- processar a fotografia corrente do arquivo CSV oficial do CNES;
- medir volume, completude de campos selecionados, duplicidade da chave CNES e validade de UF, município e coordenadas;
- publicar somente resultados agregados por UF e por tipo de unidade;
- expor fonte, horário, hash do arquivo, regras executadas, resultados e limitações;
- atualizar e publicar o site automaticamente pelo GitHub Actions.

## Fora de escopo

- avaliar qualidade assistencial ou desempenho de estabelecimentos;
- identificar profissionais, pacientes ou outras pessoas naturais;
- publicar registros individuais, contatos, endereços, CNPJ ou coordenadas;
- criar uma nota composta de qualidade com pesos arbitrários;
- manter histórico longitudinal antes de haver execuções suficientes para comparação.

## Critérios de aceite

1. Uma execução local processa o ZIP sem extrair o CSV e gera JSON agregado para o site.
2. O total de registros lidos reconcilia com a soma por UF, incluindo a categoria de UF inválida.
3. Cada controle informa regra, dimensão, severidade, registros avaliados, falhas e resultado.
4. Nenhum campo de contato, endereço, CNPJ, nome ou coordenada aparece nos artefatos públicos.
5. O painel Streamlit possui filtro por UF, estado de erro e leitura adequada em tela estreita.
6. Testes automatizados cobrem normalização, controles, reconciliação e contrato de privacidade.
7. O fluxo agendado baixa novamente a fonte, testa, gera e publica o mesmo artefato validado.

## Restrições e riscos

- A base é autodeclarada e enviada por gestores locais; uma falha cadastral não prova problema assistencial.
- A fonte pode alterar schema, nome interno do ZIP ou disponibilidade. Mudança incompatível deve interromper a publicação.
- O portal informa atualização diária, mas a automação deve comparar o hash e aceitar execuções sem mudança.
- O aplicativo Streamlit é público. Somente agregados aprovados pelo contrato de privacidade podem entrar em `data/published`.

## Evidências de conclusão

- saída dos testes e do gerador;
- `data/published/dashboard.json` e `data/published/audit-report.json` gerados a partir da fonte real;
- inspeção visual em desktop e mobile;
- histórico Git com incrementos separados;
- execução do workflow no GitHub após a publicação do repositório.

## Situação em 2026-10-03

Fato verificado: o recurso CSV oficial responde em `https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/CNES/cnes_estabelecimentos_csv.zip` e continha `cnes_estabelecimentos.csv` com cabeçalho separado por ponto e vírgula. Em 2026-10-03, a entrega foi alterada de site estático para um único painel Streamlit por decisão do usuário. A publicação externa ainda não foi executada.
