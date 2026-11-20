# Contrato publicado 3.0

Mudança de nomes na população: consumidores da versão 2.1 devem substituir d1c por co_uf,
d1n por nome_uf, d3c por ano_referencia e v por populacao_estimada. O ano passa a inteiro.
A mudança é identificada como versão 3.0 do contrato; não é compatível com consultas que
usam os nomes anteriores dessa tabela. Os nomes das demais fontes permanecem preservados.

## Camadas e governança

Exceção de nomenclatura acordada: na tabela de população por UF, D1C → co_uf,
D1N → nome_uf, D3C → ano_referencia e V → populacao_estimada. O dicionário registra
os nomes originais. As demais distribuições de fonte mantêm os nomes originais
normalizados; nomes analíticos permanecem restritos às visões calculadas.

Cinco distribuições fonte_* preservam os nomes das dimensões e medidas originais
normalizados. São consultas agregadas, não microdados: fonte_leitos soma por UF e mês;
as consultas TabNet foram convertidas de tabelas cruzadas para linhas. O rótulo de
classificação de serviços é recomposto de componentes extraídos e não é cópia literal.
As demais 14 distribuições são visões analíticas com contagens e indicadores derivados.

O dicionário é a fonte canônica das definições de coluna. Ele registra a camada, origem,
transformação, grão, tipo, unidade, chave, nulabilidade observada, domínio/formato, regra
de qualidade, referência temporal, execução, atualização, responsável pela publicação,
canal de contato, classificação de acesso e condições de reutilização. Não se declara
certificação formal. O catálogo JSON-LD usa termos do DCAT 3 para descrever distribuições:
https://www.w3.org/TR/vocab-dcat-3/

Formatos isolados: CSV, JSON e Parquet por tabela; SQLite e SQL para a base completa;
dicionário e fontes separados. O Parquet incorpora o dicionário em seus metadados.
O SQLite inclui __metadados para identificar a versão e as definições sem depender do ZIP.

O código de ingestão preserva os nomes das colunas de entrada. A publicação preserva
os nomes reconhecíveis da fonte em snake_case: LEITOS_EXISTENTES → leitos_existentes,
LEITOS_SUS → leitos_sus, UTI_TOTAL_EXIST → uti_total_exist, TP_GESTAO → tp_gestao.
Quantidades agregadas, códigos extraídos do TabNet e indicadores recebem nomes derivados
explícitos. CO_CNES não é exportado como se fosse uma contagem: seu agregado se chama
quantidade_estabelecimentos. Valores V do SIDRA são integrados como populacao_estimada;
o dicionário informa o campo V e a conversão, sem afirmar que o nome já existia na fonte.

Fonte canônica dos mapeamentos: src/cnes_audit/contracts.py. A geração publica o dicionário
em JSON e CSV, com tabela, coluna, campo na fonte, tipo, nulabilidade observada, chave,
grão, unidade, origem e transformação. Não se inventam campos originais para indicadores.
A nulabilidade informada retrata a execução; consumidores devem aceitar ausências nos
indicadores e comparar versão do contrato antes de incorporar novas atualizações.

As tabelas detalhadas mantêm unidades diferentes. Chaves compostas identificam UF/tipo,
UF/classificação e UF/mês. Códigos são texto; contagens são inteiras; taxas são reais.
Zeros e ausências permanecem distintos. O SQLite inclui chaves primárias e referências
à dimensão de UF representada pelo perfil; sua integridade é verificada antes de exportar.

Todos os valores são conferidos na migração: a conversão do dashboard é reversível.
Os painéis usam um adaptador de leitura para conservar a lógica já validada, enquanto
os arquivos persistidos e os contratos de consumo usam os novos nomes. Metadados técnicos
da execução não foram confundidos com nomes de colunas da fonte. A API e os downloads
compartilham a mesma projeção pública e a mesma execução.

API v1 é a primeira interface HTTP; contrato de dados 2.0 substitui os CSVs anteriores.
Os nomes antigos e o vínculo com os novos estão no dicionário. Não existe API antiga a
desativar. Código que consumia os CSVs em inglês precisa atualizar seus nomes de coluna.

## Atualização e recuperação

O pipeline diário valida as fontes, grava os agregados e gera a API estática antes do commit.
O GitHub Pages publica a pasta docs. Se o pipeline falhar antes do commit, permanece a
última versão válida. A implantação é atômica pelo serviço; caches podem servir versões
anteriores por algum tempo. Cada resposta contém id_execucao para detectar diferenças.
Rollback: reverter o commit da geração e verificar a publicação do Pages.

Os arquivos são snapshots, sem consultas de escrita ou atualização por chamada. Nenhuma
informação pessoal individual de paciente ou profissional é publicada no contrato.
