"""Build a static, read-only API from the validated published snapshot."""
from __future__ import annotations

import argparse
import json
import hashlib
import re
from pathlib import Path

from cnes_audit.integrated import build_profile, data_package, profile_csv, public_dataset
from cnes_audit.contracts import decode_dashboard, encode_dashboard, encode_profile, relational_snapshot
from cnes_audit.catalog import table_catalog, dcat_catalog
from cnes_audit.exports import parquet_bytes


def build_api(data_directory: Path, destination: Path) -> dict:
    dashboard = decode_dashboard(json.loads((data_directory / "dashboard.json").read_text(encoding="utf-8")))
    audit = json.loads((data_directory / "audit-report.json").read_text(encoding="utf-8"))
    if dashboard["metadata"]["run_id"] != audit["run_id"]:
        raise ValueError("Dashboard e auditoria de execuções diferentes")
    profile = build_profile(dashboard)
    dataset = public_dataset(dashboard, profile, audit)
    # Persist the same canonical snapshot used by the app, API and downloads.
    for filename, value in (("dados.json", dataset), ("dicionario.json", dataset["dicionario"]), ("dashboard.json", encode_dashboard(dashboard)), ("uf-profile.json", encode_profile(profile))):
        (data_directory / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (data_directory / "uf-profile.csv").write_text(profile_csv(dataset["tabelas"]["perfil_uf"]), encoding="utf-8-sig")
    api = destination / "api" / "v1"
    api.mkdir(parents=True, exist_ok=True)

    def write(relative: str, payload) -> None:
        path = api / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n", encoding="utf-8")

    meta = {key: value for key, value in dataset.items() if key not in ("tabelas", "dicionario", "fontes")}
    catalog = table_catalog(dataset)
    endpoints = ["metadados.json", "catalogo.json", "dicionario.json", "fontes.json", "ufs.json"]
    for name, rows in dataset["tabelas"].items():
        endpoint = f"tabelas/{name}.json"
        write(endpoint, {"metadados": meta, "total": len(rows), "dados": rows})
        csv_path = api / "csv" / f"{name}.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        csv_path.write_text(profile_csv(rows), encoding="utf-8-sig")
        parquet_path = api / "parquet" / f"{name}.parquet"
        parquet_path.parent.mkdir(parents=True, exist_ok=True)
        parquet_path.write_bytes(parquet_bytes(rows, [field for field in dataset["dicionario"] if field["tabela"] == name]))
        endpoints.append(endpoint)
        field = next(item["campo_uf"] for item in catalog if item["tabela"] == name)
        if field:
            for code in sorted({row[field] for row in rows}):
                selected = [row for row in rows if row[field] == code]
                write(f"tabelas/{name}/ufs/{code}.json", {"metadados": meta, "total": len(selected), "dados": selected})
    write("metadados.json", meta)
    write("dicionario.json", dataset["dicionario"])
    write("fontes.json", dataset["fontes"])
    write("ufs.json", {"metadados": meta, "dados": dataset["tabelas"]["perfil_uf"]})
    for row in dataset["tabelas"]["perfil_uf"]:
        write(f"ufs/{row['co_uf']}.json", {"metadados": meta, "dados": row})
    write("catalogo.json", {"metadados": meta, "tabelas": catalog})
    write("catalogo-dcat.json", dcat_catalog(dataset))
    write("index.json", {"contrato": "3.0", "transporte": "API estática GET", "endpoints": endpoints,
                         "filtro_uf": "tabelas/{tabela}/ufs/{co_uf}.json", "parametros_query": False})
    (api / "dicionario.csv").write_text(profile_csv(dataset["dicionario"]), encoding="utf-8-sig")
    (api / "dados.zip").write_bytes(data_package(dashboard, profile, audit))
    ddl, database = relational_snapshot(dataset["tabelas"], dataset["dicionario"])
    (api / "schema.sql").write_text(ddl, encoding="utf-8")
    (api / "cnes.sqlite").write_bytes(database)
    digest = hashlib.sha256(database).hexdigest()
    snapshot = api / "snapshots" / f"{digest}.sqlite"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_bytes(database)
    # Retain seven generated versions, enough to outlive the provider's short cache TTL.
    candidates = sorted((path for path in snapshot.parent.iterdir() if re.fullmatch(r"[0-9a-f]{64}\.sqlite", path.name) and path.is_file()), key=lambda path: path.stat().st_mtime, reverse=True)
    for obsolete in candidates[7:]:
        if obsolete.parent.resolve() != snapshot.parent.resolve():
            raise ValueError("Snapshot fora do diretório de publicação")
        obsolete.unlink()
    write("sqlite.json", {"arquivo": f"snapshots/{digest}.sqlite", "sha256": digest, "bytes": len(database), "id_execucao": dataset["id_execucao"], "atualizado_em": dataset["atualizado_em"], "versao_contrato": dataset["versao_contrato"], "modo": "snapshot_somente_leitura", "atualizacao": "Verificação diária pelo pipeline; não é streaming"})
    (destination / ".nojekyll").touch()
    return dataset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data/published"))
    parser.add_argument("--output", type=Path, default=Path("docs"))
    args = parser.parse_args()
    dataset = build_api(args.data, args.output)
    print(f"Contrato {dataset['versao_contrato']}: {len(dataset['tabelas'])} tabelas")


if __name__ == "__main__":
    main()
