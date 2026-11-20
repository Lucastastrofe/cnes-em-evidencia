"""Source-named aggregate distributions and governed metadata."""
from __future__ import annotations

from cnes_audit.beds import UF_CODES

PUBLIC_CONTRACT_VERSION = "3.0"

API_BASE = "https://lucastastrofe.github.io/cnes-em-evidencia/api/v1"
UF_ABBREVIATIONS = {value: key for key, value in UF_CODES.items()}


def source_tables(dashboard: dict) -> tuple[dict, list[dict]]:
    """Preserve source dimension names; never label these aggregates as raw microdata."""
    definitions = {
        "fonte_leitos": ("CNES Hospitais e Leitos", ["comp", "uf"], "UF e competência; soma dos registros da fonte", {
            "comp": ("COMP", "string", "competencia_aaaamm", "Competência mensal da fonte"),
            "uf": ("UF", "string", "sigla_uf", "Sigla estadual da fonte; dimensão oficial de UFs"),
            "leitos_existentes": ("LEITOS_EXISTENTES", "integer", "leitos", "Soma dos leitos existentes por UF e mês"),
            "leitos_sus": ("LEITOS_SUS", "integer", "leitos", "Soma dos leitos SUS por UF e mês"),
            "uti_total_exist": ("UTI_TOTAL_EXIST", "integer", "leitos", "Soma de leitos UTI existentes por UF e mês"),
            "uti_total_sus": ("UTI_TOTAL_SUS", "integer", "leitos", "Soma de leitos UTI SUS por UF e mês"),
        }),
        "fonte_equipes": ("CNES TabNet Equipes", ["unidade_da_federacao", "tipo_da_equipe"], "UF e tipo na competência consultada", {
            "unidade_da_federacao": ("Unidade da Federação", "string", "codigo_ibge_uf", "Código extraído da dimensão territorial do TabNet"),
            "tipo_da_equipe": ("Tipo da Equipe", "string", "categoria", "Código e descrição da dimensão de equipe; tabela cruzada convertida em linhas"),
            "quantidade": ("Quantidade", "integer", "equipes", "Medida Quantidade da consulta por UF e tipo"),
        }),
        "fonte_servicos": ("CNES TabNet Serviços", ["unidade_da_federacao", "classificacao_do_servico"], "UF e classificação na competência consultada", {
            "unidade_da_federacao": ("Unidade da Federação", "string", "codigo_ibge_uf", "Código extraído da dimensão territorial do TabNet"),
            "classificacao_do_servico": ("Classificação do Serviço", "string", "categoria", "Código composto e descrições reunidos a partir dos componentes extraídos pelo parser; não é cópia literal do rótulo original"),
            "quantidade": ("Quantidade", "integer", "registros_servico_classificacao", "Medida Quantidade; não conta estabelecimentos únicos"),
        }),
        "fonte_profissionais": ("CNES TabNet Profissionais", ["unidade_da_federacao", "atende_no_sus"], "UF e categoria SUS na competência consultada", {
            "unidade_da_federacao": ("Unidade da Federação", "string", "codigo_ibge_uf", "Código extraído da dimensão territorial do TabNet"),
            "atende_no_sus": ("Atende no SUS", "string", "categoria_sim_nao", "Dimensão SUS da consulta, convertida de colunas para linhas"),
            "quantidade": ("Quantidade", "integer", "profissionais", "Medida Quantidade da consulta por UF e categoria SUS"),
        }),
        "fonte_populacao": ("IBGE SIDRA", ["co_uf", "ano_referencia"], "UF e ano", {
            "co_uf": ("D1C", "string", "codigo_ibge_uf", "Código da UF retornado pelo SIDRA; nome descritivo para o campo D1C"),
            "nome_uf": ("D1N", "string", "nome_uf", "Nome da UF retornado pelo SIDRA; nome descritivo para o campo D1N"),
            "ano_referencia": ("D3C", "integer", "ano", "Ano de referência retornado pelo SIDRA, convertido para inteiro"),
            "populacao_estimada": ("V", "integer", "habitantes", "Valor da estimativa convertido de texto para inteiro; nome descritivo para o campo V"),
        }),
    }
    tables = {
        "fonte_leitos": [{"comp": r["competence"], "uf": UF_ABBREVIATIONS[r["code"]], "leitos_existentes": r["beds"], "leitos_sus": r["sus_beds"], "uti_total_exist": r["uti_beds"], "uti_total_sus": r["uti_sus_beds"]} for r in dashboard["bed_history"]["by_state"]],
        "fonte_equipes": [{"unidade_da_federacao": r["state_code"], "tipo_da_equipe": f"{r['team_code']} {r['team_name']}", "quantidade": r["teams"]} for r in dashboard["teams"]["by_state_type"]],
        "fonte_servicos": [{"unidade_da_federacao": r["state_code"], "classificacao_do_servico": f"{r['classification_code']} {r['service_code']} {r['service_name']} / {r['classification_name']}", "quantidade": r["service_records"]} for r in dashboard["services"]["by_state_classification"]],
        "fonte_profissionais": [{"unidade_da_federacao": r["code"], "atende_no_sus": label, "quantidade": r[field]} for r in dashboard["professionals"]["by_state"] for label, field in (("Sim", "sus_professionals"), ("Não", "non_sus_professionals"))],
        "fonte_populacao": [{"co_uf": r["code"], "nome_uf": r["name"], "ano_referencia": dashboard["summary"]["population_reference_year"], "populacao_estimada": r["population"]} for r in dashboard["by_state"] if r["population"] is not None],
    }
    dictionary = []
    for name, rows in tables.items():
        origin, keys, grain, fields = definitions[name]
        for field, (original, kind, unit, definition) in fields.items():
            dictionary.append({"tabela": name, "coluna": field, "nome_na_fonte": original, "tipo": kind, "aceita_nulo": False, "chave": field in keys, "grao": grain, "definicao_transformacao": definition, "unidade": unit, "papel": "dimensao_ou_medida_da_fonte", "origem": origin, "camada": "fonte_normalizada_agregada"})
        if len({tuple(r[k] for k in keys) for r in rows}) != len(rows):
            raise ValueError(f"Chave duplicada em {name}")
    return tables, dictionary


def governance_dictionary(dictionary: list[dict], dataset: dict, audit: dict) -> list[dict]:
    enriched = []
    for field in dictionary:
        item = dict(field)
        name = item["tabela"]
        nullable = item["aceita_nulo"]
        item.update({
            "camada": item.get("camada", "visao_analitica"),
            "responsavel_publicacao": "Mantenedor do CNES em Evidência",
            "canal_contato": "https://github.com/Lucastastrofe/cnes-em-evidencia/issues",
            "classificacao_acesso": "publico_agregado",
            "versao_contrato": "3.0", "id_execucao": dataset["id_execucao"],
            "atualizado_em": dataset["atualizado_em"],
            "regra_nulidade": "Ausência preservada como null; não imputar zero" if nullable else "Não foram observados nulos nesta execução; não constitui garantia de completude futura",
            "dominio_formato": "AAAAMM" if item["coluna"] == "comp" else "Duas posições; código IBGE da UF" if item["coluna"] in ("co_uf", "unidade_da_federacao", "d1c") else "Sim ou Não" if item["coluna"] == "atende_no_sus" else "Número inteiro não negativo" if item["tipo"] == "integer" else "Conforme definição e unidade",
            "regra_qualidade": "Chave não nula e única no grão" if item["chave"] else "Tipo consistente e reconciliação com os agregados de origem",
            "politica_atualizacao": "Verificação diária; novas competências dependem do publicador original",
            "referencia_temporal": str(dataset.get("ano_populacao", "Consultar metadados")) if item["origem"].startswith("IBGE") else str(dataset.get("competencias", {})) if name == "perfil_uf" else "Competência da fonte na execução; consultar catálogo da tabela",
            "licenca_dados": "Condições de cada fonte; consultar fontes.json. MIT aplica-se ao código.",
        })
        enriched.append(item)
    return enriched


def table_catalog(dataset: dict) -> list[dict]:
    result = []
    sources = {s["id"]: s for s in dataset["fontes"]}
    for name, rows in dataset["tabelas"].items():
        fields = [item for item in dataset["dicionario"] if item["tabela"] == name]
        source_id = "population_source" if "populacao" in name else "beds_source" if "leitos" in name else "teams_source" if "equipes" in name else "services_source" if "servicos" in name else "professionals_source" if "profissionais" in name else "source"
        result.append({"tabela": name, "camada": fields[0]["camada"], "linhas": len(rows), "colunas": len(rows[0]), "grao": fields[0]["grao"], "chave_primaria": [f["coluna"] for f in fields if f["chave"]], "referencia": "Múltiplas fontes; consultar metadados" if name == "perfil_uf" else sources[source_id]["reference"], "url_fonte": sources[source_id]["catalog_url"], "json": f"{API_BASE}/tabelas/{name}.json", "csv": f"{API_BASE}/csv/{name}.csv", "campo_uf": "co_uf" if "co_uf" in rows[0] else "unidade_da_federacao" if "unidade_da_federacao" in rows[0] else "d1c" if "d1c" in rows[0] else "uf" if "uf" in rows[0] else None})
    for item in result:
        item["parquet"] = f"{API_BASE}/parquet/{item['tabela']}.parquet"
    return result


def dcat_catalog(dataset: dict) -> dict:
    """Use DCAT terms without claiming independent certification."""
    return {"@context": {"dcat": "http://www.w3.org/ns/dcat#", "dct": "http://purl.org/dc/terms/", "foaf": "http://xmlns.com/foaf/0.1/"},
        "@type": "dcat:Catalog", "dct:title": "CNES em Evidência · catálogo de distribuições agregadas",
        "dct:modified": dataset["atualizado_em"],
        "dct:publisher": {"@type": "foaf:Agent", "foaf:name": "CNES em Evidência · projeto independente"},
        "dcat:dataset": [{"@type": "dcat:Dataset", "@id": f"{API_BASE}/tabelas/{item['tabela']}.json",
            "dct:identifier": item["tabela"], "dct:title": item["tabela"], "dct:description": item["grao"],
            "dct:source": {"@id": item["url_fonte"]}, "dct:modified": dataset["atualizado_em"],
            "dct:accessRights": "Público agregado", "dct:rights": "Condições das fontes em fontes.json; MIT licencia apenas o código",
            "dcat:distribution": [{"@type": "dcat:Distribution", "dcat:downloadURL": {"@id": item[fmt]}, "dcat:mediaType": media} for fmt, media in (("json", "application/json"), ("csv", "text/csv"), ("parquet", "application/vnd.apache.parquet"))]}
            for item in table_catalog(dataset)]}
