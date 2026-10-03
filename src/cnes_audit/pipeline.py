from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cnes_audit.quality import audit_rows
from cnes_audit.source import iter_csv_rows, zip_entry_metadata

DEFAULT_SOURCE_URL = (
    "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/"
    "CNES/cnes_estabelecimentos_csv.zip"
)


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_source(url: str, destination: Path, attempts: int = 3) -> dict[str, str]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    request = urllib.request.Request(url, headers={"User-Agent": "cnes-em-evidencia/0.1"})
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
                with temporary.open("wb") as target:
                    shutil.copyfileobj(response, target, length=1024 * 1024)
                os.replace(temporary, destination)
                return {
                    "last_modified": response.headers.get("Last-Modified", "não informado"),
                    "etag": response.headers.get("ETag", "não informado").strip('"'),
                }
        except (OSError, urllib.error.URLError) as error:
            last_error = error
            temporary.unlink(missing_ok=True)
            if attempt < attempts:
                time.sleep(2 ** (attempt - 1))

    raise RuntimeError(f"não foi possível obter a fonte após {attempts} tentativas") from last_error


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def build_public_artifacts(
    source_path: Path,
    output_directory: Path,
    source_url: str,
    obtained_at: str,
    source_last_modified: str,
    code_version: str,
    source_etag: str = "não informado",
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_hash = sha256_file(source_path)
    archive = zip_entry_metadata(source_path)
    dashboard = audit_rows(iter_csv_rows(source_path))
    total_rows = dashboard["summary"]["total_records"]
    aggregated_rows = sum(item["records"] for item in dashboard["by_state"])
    if total_rows != aggregated_rows:
        raise RuntimeError(
            f"reconciliação falhou: {total_rows} lidas e {aggregated_rows} agregadas"
        )

    run_id = f"{obtained_at.replace(':', '').replace('-', '')}-{source_hash[:12]}"
    public_metadata = {
        "run_id": run_id,
        "generated_at": obtained_at,
        "source_last_modified": source_last_modified,
        "source_sha256": source_hash,
    }
    dashboard["metadata"] = public_metadata
    audit = {
        "status": "concluído",
        "run_id": run_id,
        "generated_at": obtained_at,
        "process": "cnes-audit",
        "code_version": code_version,
        "source": {
            "catalog_url": (
                "https://dadosabertos.saude.gov.br/dataset/"
                "cnes-cadastro-nacional-de-estabelecimentos-de-saude"
            ),
            "resource_url": source_url,
            "obtained_at": obtained_at,
            "last_modified": source_last_modified,
            "etag": source_etag,
            "sha256": source_hash,
            "archive_bytes": source_path.stat().st_size,
            "entry_name": archive["name"],
            "entry_bytes": archive["uncompressed_bytes"],
        },
        "contract": {
            "version": "1.0",
            "publication_level": "somente contagens agregadas",
            "raw_data_published": False,
        },
        "reconciliation": {
            "rows_read": total_rows,
            "rows_aggregated": aggregated_rows,
            "difference": total_rows - aggregated_rows,
        },
        "checks": dashboard["checks"],
        "limitations": [
            "Os resultados descrevem o arquivo processado e não a qualidade da assistência.",
            "A fonte pode refletir ritmos diferentes de atualização entre gestores locais.",
            "Ausência cadastral não comprova ausência de serviço ou estrutura.",
            "Os tipos de unidade são exibidos por código até a incorporação de tabela oficial versionada.",
        ],
    }
    _write_json(output_directory / "dashboard.json", dashboard)
    _write_json(output_directory / "audit-report.json", audit)
    return dashboard, audit

