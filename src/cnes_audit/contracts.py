"""Canonical published column names and explicit source lineage."""
from __future__ import annotations

import copy
import sqlite3
import json

PUBLIC_CONTRACT_VERSION = "2.1"

TABLES = {
    "perfil_uf": ("perfil_uf", ["co_uf"], "UF"),
    "beds_by_state": ("leitos_uf", ["co_uf"], "UF na última competência"),
    "bed_history_national": ("leitos_brasil_mensal", ["comp"], "Brasil e mês"),
    "bed_history_by_state": ("leitos_uf_mensal", ["co_uf", "comp"], "UF e mês"),
    "teams_by_state": ("equipes_uf", ["co_uf"], "UF na competência"),
    "teams_by_type": ("equipes_tipo", ["codigo_tipo_equipe"], "Tipo de equipe na competência"),
    "teams_by_state_type": ("equipes_uf_tipo", ["co_uf", "codigo_tipo_equipe"], "UF e tipo de equipe na competência"),
    "services_by_state": ("servicos_uf", ["co_uf"], "UF na competência"),
    "services_by_classification": ("servicos_classificacao", ["codigo_classificacao_servico"], "Classificação na competência"),
    "services_by_state_classification": ("servicos_uf_classificacao", ["co_uf", "codigo_classificacao_servico"], "UF e classificação na competência"),
    "professionals_by_state": ("profissionais_uf", ["co_uf"], "UF na competência"),
    "by_unit_type": ("estabelecimentos_tipo", ["tp_unidade"], "Tipo de unidade"),
    "by_management": ("estabelecimentos_gestao", ["tp_gestao"], "Tipo de gestão"),
    "checks": ("controles_qualidade", ["id_controle"], "Regra de qualidade"),
}

# original is null when there is no single source column: do not invent one.
FIELDS = {
    "code": ("co_uf", "CO_UF / D1C / Unidade da Federação / UF", "Código IBGE da UF; chaves das fontes reconciliadas"),
    "state_code": ("co_uf", "Unidade da Federação", "Código IBGE da UF extraído da dimensão territorial"),
    "name": ("nome_uf", "D1N / Unidade da Federação", "Nome da UF pela dimensão oficial"),
    "state_name": ("nome_uf", "Unidade da Federação", "Nome da UF pela dimensão oficial"),
    "records": ("quantidade_estabelecimentos", "CO_CNES", "Contagem de cadastros no agrupamento; não é coluna original"),
    "issues": ("quantidade_ocorrencias", None, "Ocorrências dos controles no agrupamento"),
    "population": ("populacao_estimada", "V", "Valor da estimativa populacional IBGE, convertido para inteiro"),
    "beds": ("leitos_existentes", "LEITOS_EXISTENTES", "Soma dos leitos existentes no agrupamento"),
    "sus_beds": ("leitos_sus", "LEITOS_SUS", "Soma dos leitos destinados ao SUS no agrupamento"),
    "uti_beds": ("uti_total_exist", "UTI_TOTAL_EXIST", "Soma de leitos UTI existentes"),
    "uti_sus_beds": ("uti_total_sus", "UTI_TOTAL_SUS", "Soma de leitos UTI destinados ao SUS"),
    "competence": ("comp", "COMP", "Competência do arquivo de leitos no formato AAAAMM"),
    "rows_selected": ("quantidade_registros_fonte", None, "Quantidade de linhas da fonte selecionadas no mês"),
    "teams": ("quantidade_equipes", "Quantidade / Total", "Quantidade da consulta TabNet de equipes no agrupamento"),
    "team_code": ("codigo_tipo_equipe", "Tipo da Equipe", "Código extraído do cabeçalho de tipo de equipe"),
    "team_name": ("descricao_tipo_equipe", "Tipo da Equipe", "Descrição extraída do cabeçalho de tipo de equipe"),
    "service_records": ("quantidade_registros_servicos", "Quantidade / Total", "Registros por serviço e classificação; não são estabelecimentos únicos"),
    "classification_code": ("codigo_classificacao_servico", "Classificação do Serviço", "Código composto de seis posições extraído do rótulo"),
    "service_code": ("codigo_servico", "Classificação do Serviço", "Código do serviço extraído do rótulo"),
    "service_name": ("descricao_servico", "Classificação do Serviço", "Descrição do serviço extraída do rótulo"),
    "classification_name": ("descricao_classificacao_servico", "Classificação do Serviço", "Descrição da classificação extraída do rótulo"),
    "professionals": ("quantidade_profissionais", "Total", "Total da consulta TabNet de profissionais por UF"),
    "sus_professionals": ("quantidade_profissionais_sus", "Atende no SUS: Sim", "Quantidade associada ao atendimento SUS na consulta"),
    "non_sus_professionals": ("quantidade_profissionais_nao_sus", "Atende no SUS: Não", "Quantidade não associada ao SUS na consulta"),
    "sus_share": ("proporcao_profissionais_sus", None, "Profissionais SUS divididos pelo total; intervalo de zero a um"),
    "id": ("id_controle", None, "Identificador estável da regra de qualidade"),
    "label": ("descricao", None, "Descrição da categoria ou controle"),
    "dimension": ("dimensao", None, "Dimensão de qualidade avaliada"),
    "severity": ("severidade", None, "Severidade definida pela regra"),
    "status": ("situacao", None, "Resultado da regra nesta execução"),
    "evaluated": ("quantidade_avaliada", None, "Quantidade avaliada pela regra"),
    "failures": ("quantidade_falhas", None, "Quantidade que não atendeu à regra"),
    "failure_rate": ("proporcao_falhas", None, "Falhas divididas pela quantidade avaliada; zero a um"),
}
RATES = {
    "establishments_per_100k": "estabelecimentos_por_100_mil_habitantes",
    "beds_per_100k": "leitos_existentes_por_100_mil_habitantes",
    "sus_beds_per_100k": "leitos_sus_por_100_mil_habitantes",
    "uti_beds_per_100k": "uti_total_exist_por_100_mil_habitantes",
    "uti_sus_beds_per_100k": "uti_total_sus_por_100_mil_habitantes",
    "teams_per_100k": "equipes_por_100_mil_habitantes",
    "service_records_per_100k": "registros_servicos_por_100_mil_habitantes",
    "professionals_per_100k": "profissionais_por_100_mil_habitantes",
}


def field_contract(table: str, field: str) -> tuple[str, str | None, str]:
    if field == "code" and table.startswith(("beds_", "bed_history_")):
        return "co_uf", "UF", "Sigla UF convertida para o código IBGE por dimensão oficial; identificador derivado"
    if field == "code" and table.endswith("by_state") and table.startswith(("teams", "professionals", "services")):
        return "co_uf", "Unidade da Federação", "Código IBGE extraído da dimensão da consulta TabNet"
    if field == "code" and table == "perfil_uf":
        return "co_uf", "CO_UF", "Chave de UF do cadastro usada para integrar as demais fontes"
    if field in ("name", "state_name") and table != "teams_by_type":
        return "nome_uf", None, "Nome obtido da dimensão oficial de UFs; não é contagem nem identificador de estabelecimento"
    if field in RATES:
        return RATES[field], None, "Quantidade dividida pela população estimada × 100000; arredondada a duas casas no pipeline"
    if table == "by_unit_type" and field == "code":
        return "tp_unidade", "TP_UNIDADE", "Código original de tipo de unidade"
    if table == "by_management" and field == "code":
        return "tp_gestao", "TP_GESTAO", "Código original de gestão"
    if table == "teams_by_type" and field in ("code", "name"):
        return FIELDS["team_code" if field == "code" else "team_name"]
    if table == "checks" and field == "label":
        return "descricao_controle", None, "Descrição da regra executada pelo projeto"
    return FIELDS[field]


def field_source(table: str, field: str) -> str:
    if field == "population":
        return "IBGE/SIDRA"
    if field in RATES or field in ("issues", "sus_share") or table == "checks":
        return "Indicador calculado pelo projeto; consultar transformação e tabela de origem"
    if field in ("beds", "sus_beds", "uti_beds", "uti_sus_beds", "competence") or table.startswith(("beds", "bed_history")):
        return "CNES Hospitais e Leitos"
    if field in ("teams", "professionals", "sus_professionals", "non_sus_professionals", "service_records") or table.startswith(("teams", "services", "professionals")):
        return "CNES TabNet"
    return "CNES Estabelecimentos / dimensão oficial de UFs"


def canonical_tables(tables: dict) -> tuple[dict, list[dict]]:
    result, dictionary = {}, []
    for legacy, rows in tables.items():
        name, keys, grain = TABLES[legacy]
        result[name] = [{field_contract(legacy, key)[0]: value for key, value in row.items()} for row in rows]
        for field in rows[0]:
            published, original, definition = field_contract(legacy, field)
            sample = next((row[field] for row in rows if row[field] is not None), None)
            kind = "integer" if isinstance(sample, int) else "number" if isinstance(sample, float) else "string"
            dictionary.append({"tabela": name, "coluna": published, "nome_na_fonte": original,
                "tipo": kind, "aceita_nulo": any(row[field] is None for row in rows),
                "chave": published in keys, "grao": grain, "definicao_transformacao": definition,
                "unidade": "identificador" if published in keys or published.startswith("codigo_") else "habitantes" if field == "population" else "por 100 mil habitantes" if field in RATES else "proporcao_0_a_1" if published.startswith("proporcao_") else "contagem" if kind == "integer" else "texto",
                "papel": "indicador_calculado" if field in RATES or original is None else "campo_transformado_ou_agregado",
                "origem": field_source(legacy, field)})
        seen = set()
        for row in result[name]:
            key = tuple(row[column] for column in keys)
            if None in key or key in seen:
                raise ValueError(f"Chave nula ou duplicada: {name} {key}")
            seen.add(key)
    return result, dictionary


def encode_dashboard(dashboard: dict) -> dict:
    if "_contrato_colunas" in dashboard:
        return dashboard
    result = copy.deepcopy(dashboard)
    mappings = {}
    for key, value in result.items():
        sections = [(key, value, "perfil_uf" if key == "by_state" else key)] if isinstance(value, list) else [(f"{key}/{child}", rows, f"{key}_{child}") for child, rows in value.items() if isinstance(rows, list)] if isinstance(value, dict) else []
        for path, rows, table in sections:
            if not rows:
                continue
            mapping = {field_contract(table, field)[0]: field for field in rows[0]}
            mappings[path] = mapping
            renamed = [{field_contract(table, field)[0]: item for field, item in row.items()} for row in rows]
            if "/" in path:
                parent, child = path.split("/")
                result[parent][child] = renamed
            else:
                result[path] = renamed
    result["_contrato_colunas"] = mappings
    return result


def decode_dashboard(dashboard: dict) -> dict:
    result = copy.deepcopy(dashboard)
    mappings = result.pop("_contrato_colunas", {})
    for path, mapping in mappings.items():
        if "/" in path:
            parent, child = path.split("/")
            result[parent][child] = [{mapping[field]: value for field, value in row.items()} for row in result[parent][child]]
        else:
            result[path] = [{mapping[field]: value for field, value in row.items()} for row in result[path]]
    return result


def encode_profile(profile: dict) -> dict:
    result = copy.deepcopy(profile)
    tables, dictionary = canonical_tables({"perfil_uf": profile["rows"]})
    result["rows"] = tables["perfil_uf"]
    result["dictionary"] = dictionary
    result["schema_version"] = "2.1"
    result["_colunas_legadas"] = {field_contract("perfil_uf", field)[0]: field for field in profile["rows"][0]}
    return result


def decode_profile(profile: dict) -> dict:
    result = copy.deepcopy(profile)
    mapping = result.pop("_colunas_legadas", {})
    if mapping:
        result["rows"] = [{mapping[field]: value for field, value in row.items()} for row in result["rows"]]
    return result


def relational_snapshot(tables: dict, dictionary: list[dict]) -> tuple[str, bytes]:
    """A portable, typed SQLite snapshot; no database server or credentials."""
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys=ON")
    statements = []
    try:
        for table, rows in tables.items():
            columns = [item for item in dictionary if item["tabela"] == table]
            keys = [item["coluna"] for item in columns if item["chave"]]
            definitions = []
            for item in columns:
                column = item["coluna"]
                sql_type = {"string": "TEXT", "integer": "INTEGER", "number": "REAL"}[item["tipo"]]
                nullability = " NOT NULL" if not item["aceita_nulo"] or item["chave"] else ""
                definitions.append(f'"{column}" {sql_type}{nullability}')
            definitions.append("PRIMARY KEY (" + ", ".join(f'"{key}"' for key in keys) + ")")
            if "co_uf" in rows[0] and table != "perfil_uf":
                definitions.append('FOREIGN KEY ("co_uf") REFERENCES "perfil_uf" ("co_uf")')
            statement = f'CREATE TABLE "{table}" (' + ", ".join(definitions) + ");"
            statements.append(statement)
            connection.execute(statement)
            names = list(rows[0])
            connection.executemany(f'INSERT INTO "{table}" VALUES (' + ",".join("?" for _ in names) + ")", [tuple(row[name] for name in names) for row in rows])
        metadata_statement = 'CREATE TABLE "__metadados" ("chave" TEXT PRIMARY KEY, "valor" TEXT NOT NULL);'
        statements.append(metadata_statement)
        connection.execute(metadata_statement)
        reference = dictionary[0]
        metadata = {"id_execucao": reference.get("id_execucao", "Consultar manifesto"), "atualizado_em": reference.get("atualizado_em", "Consultar manifesto"), "versao_contrato": reference.get("versao_contrato", "2.1"), "dicionario_json": json.dumps(dictionary, ensure_ascii=False)}
        connection.executemany('INSERT INTO "__metadados" VALUES (?,?)', metadata.items())
        connection.commit()
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Falha de integridade na base relacional")
        return "\n".join(statements) + "\n", connection.serialize()
    finally:
        connection.close()
