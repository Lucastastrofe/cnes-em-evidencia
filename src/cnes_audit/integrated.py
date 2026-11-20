"""Public state-level data contract, shared by exports and the interactive map."""
from __future__ import annotations

import csv
import io
import json
import hashlib
from zipfile import ZIP_DEFLATED, ZipFile
from typing import Any
from cnes_audit.quality import UF_NAMES
from cnes_audit.contracts import canonical_tables, relational_snapshot

METRICS = {
    "records": ("Estabelecimentos", None),
    "beds": ("Leitos", "beds"),
    "sus_beds": ("Leitos SUS", "beds"),
    "teams": ("Equipes", "teams"),
    "service_records": ("Registros de serviços", "services"),
    "professionals": ("Profissionais", "professionals"),
    "sus_professionals": ("Profissionais associados ao SUS", "professionals"),
}


def build_profile(dashboard: dict[str, Any]) -> dict[str, Any]:
    indexes = {}
    for section in ("beds", "teams", "services", "professionals"):
        rows = dashboard[section]["by_state"]
        index = {str(row["code"]): row for row in rows}
        if len(index) != len(rows):
            raise ValueError(f"UF duplicada: {section}")
        indexes[section] = index
    rows = []
    seen = set()
    states = list(dashboard["by_state"])
    base_codes = {str(row["code"]) for row in states}
    extra_codes = set().union(*(set(index) for index in indexes.values())) - base_codes
    for code in sorted(extra_codes):
        reference = next(index[code] for index in indexes.values() if code in index)
        states.append({"code": code, "name": reference["name"], "population": reference.get("population"), "issues": None})
    for state in states:
        code = str(state["code"])
        if code not in UF_NAMES:
            raise ValueError("UF fora do domínio oficial")
        if code in seen:
            raise ValueError("UF duplicada: estabelecimentos")
        seen.add(code)
        population = state["population"]
        if population is not None and population <= 0:
            raise ValueError("População precisa ser positiva")
        row = {key: state[key] for key in ("code", "name", "population", "issues")}
        for metric, (_, section) in METRICS.items():
            value = state.get(metric) if section is None else indexes[section].get(code, {}).get(metric)
            if value is not None and (not isinstance(value, int) or value < 0):
                raise ValueError(f"Contagem inválida: {metric}")
            row[metric] = value
        rows.append(row)
    return {
        "schema_version": "1.0",
        "run_id": dashboard["metadata"]["run_id"],
        "generated_at": dashboard["metadata"]["generated_at"],
        "population_reference_year": dashboard["summary"]["population_reference_year"],
        "periods": {section: dashboard[section]["summary"]["competence"] for section in indexes},
        "dictionary": {metric: {"label": label, "unit": "cadastros", "source": section or "estabelecimentos"} for metric, (label, section) in METRICS.items()},
        "rows": sorted(rows, key=lambda row: row["code"]),
    }


def profile_csv(rows: list[dict[str, Any]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def legacy_tables(dashboard: dict[str, Any], profile: dict[str, Any]) -> dict[str, list[dict]]:
    tables = {"perfil_uf": profile["rows"]}
    for section in ("beds", "bed_history", "teams", "services", "professionals"):
        for name, rows in dashboard[section].items():
            if isinstance(rows, list) and rows:
                tables[f"{section}_{name}"] = rows
    for name in ("by_unit_type", "by_management", "checks"):
        tables[name] = dashboard[name]
    return tables


def public_tables(dashboard: dict[str, Any], profile: dict[str, Any]) -> dict[str, list[dict]]:
    return canonical_tables(legacy_tables(dashboard, profile))[0]


def data_dictionary(dashboard: dict[str, Any], profile: dict[str, Any]) -> list[dict]:
    return canonical_tables(legacy_tables(dashboard, profile))[1]


def public_dataset(dashboard: dict, profile: dict, audit: dict) -> dict:
    return {"versao_contrato": "2.0", "id_execucao": profile["run_id"],
            "atualizado_em": profile["generated_at"], "competencias": profile["periods"],
            "ano_populacao": profile["population_reference_year"],
            "tabelas": public_tables(dashboard, profile), "dicionario": data_dictionary(dashboard, profile),
            "fontes": source_catalog(audit), "limitacoes": audit.get("limitations", [])}


def source_catalog(audit: dict[str, Any]) -> list[dict[str, Any]]:
    definitions = [
        ("source", "Estabelecimentos", "Ministério da Saúde / CNES", "UF; tipo de unidade e gestão em tabelas separadas", "Cadastros não representam atendimentos."),
        ("population_source", "População", "IBGE", "UF e ano de referência", "Estimativa anual usada como denominador das taxas."),
        ("beds_source", "Leitos", "Ministério da Saúde / CNES", "UF e competência mensal", "Cadastro não informa ocupação ou disponibilidade em tempo real."),
        ("teams_source", "Equipes", "DATASUS / CNES", "UF e tipo de equipe", "Equipes não equivalem a profissionais ou cobertura efetiva."),
        ("services_source", "Serviços", "DATASUS / CNES", "UF e classificação de serviço", "Um estabelecimento pode ter várias classificações."),
        ("professionals_source", "Profissionais", "DATASUS / CNES", "UF e associação ao SUS", "Não informa jornada, produtividade ou disponibilidade."),
    ]
    return [{"id": key, "name": name, "publisher": publisher, "published_grain": grain,
             "catalog_url": audit[key]["catalog_url"], "resource_url": audit[key]["resource_url"],
             "reference": audit[key].get("competence", audit[key].get("reference_year", "Fotografia do arquivo; competência não informada")),
             "obtained_at": audit[key]["obtained_at"], "sha256": audit[key]["sha256"],
             "limitation": limitation, "license": "Conferir os termos de reutilização no catálogo oficial; a licença do código não substitui a da fonte."}
            for key, name, publisher, grain, limitation in definitions]


def data_package(dashboard: dict[str, Any], profile: dict[str, Any], audit: dict[str, Any]) -> bytes:
    """Export only already-public aggregate tables and their provenance."""
    output = io.BytesIO()
    tables = public_tables(dashboard, profile)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        manifest = {"run_id": profile["run_id"], "generated_at": profile["generated_at"], "schema_version": profile["schema_version"], "files": []}
        for name, rows in tables.items():
            content = profile_csv(rows).encode("utf-8-sig")
            filename = f"tabelas/{name}.csv"
            archive.writestr(filename, content)
            manifest["files"].append({"path": filename, "rows": len(rows), "columns": list(rows[0]), "encoding": "UTF-8 BOM", "delimiter": ",", "null": "empty field", "sha256": hashlib.sha256(content).hexdigest()})
        archive.writestr("manifesto.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        archive.writestr("fontes.json", json.dumps(source_catalog(audit), ensure_ascii=False, indent=2))
        for name, value in (("dados.json", public_dataset(dashboard, profile, audit)), ("dicionario.json", data_dictionary(dashboard, profile)), ("auditoria.json", audit)):
            archive.writestr(name, json.dumps(value, ensure_ascii=False, indent=2))
        archive.writestr("dicionario.csv", profile_csv(data_dictionary(dashboard, profile)).encode("utf-8-sig"))
        ddl, database = relational_snapshot(tables, data_dictionary(dashboard, profile))
        archive.writestr("schema.sql", ddl)
        archive.writestr("cnes.sqlite", database)
        archive.writestr("LEIA-ME.txt", "CNES em Evidência\nDados agregados já publicados pelo projeto.\nCada CSV tem seu próprio grão; não some totais entre tabelas.\nCompetências e ano populacional: perfil.json. Fontes, hashes e limites: auditoria.json.\nCódigos de UF são identificadores: preserve como texto.\nAusências são campos vazios, não zero.\nProfissionais, equipes, serviços e leitos têm unidades diferentes.\nNão contém estabelecimentos individuais nem detalhamento municipal.\nO cadastro não informa acesso, ocupação ou disponibilidade em tempo real.\n")
    return output.getvalue()
