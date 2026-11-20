# Contrato publicado 2.0

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
