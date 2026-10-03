from __future__ import annotations

import argparse
import os
from pathlib import Path

from cnes_audit.pipeline import (
    DEFAULT_SOURCE_URL,
    build_public_artifacts,
    download_source,
    utc_now,
)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Baixa, audita e agrega os dados abertos de estabelecimentos do CNES."
    )
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
    parser.add_argument("--input", type=Path, help="usa um ZIP local e não faz download")
    parser.add_argument("--work-directory", type=Path, default=Path("data/work"))
    parser.add_argument("--output", type=Path, default=Path("site/data"))
    parser.add_argument("--code-version", default=os.getenv("GITHUB_SHA", "working-tree"))
    return parser


def main() -> int:
    args = make_parser().parse_args()
    obtained_at = utc_now()
    source_path = args.input or args.work_directory / "cnes_estabelecimentos_csv.zip"
    headers = {"last_modified": "arquivo local", "etag": "não informado"}

    if args.input is None:
        headers = download_source(args.source_url, source_path)

    dashboard, audit = build_public_artifacts(
        source_path=source_path,
        output_directory=args.output,
        source_url=args.source_url,
        obtained_at=obtained_at,
        source_last_modified=headers["last_modified"],
        source_etag=headers["etag"],
        code_version=args.code_version,
    )
    print(
        f"{audit['run_id']}: {dashboard['summary']['total_records']} registros, "
        f"{dashboard['summary']['checks_with_findings']} controles com achados"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

