"""Download a verified immutable SQLite snapshot, then query it locally read-only."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import urllib.request

BASE_URL = "https://lucastastrofe.github.io/cnes-em-evidencia/api/v1"


def _download(url: str, limit: int) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as response:
        content = response.read(limit + 1)
    if len(content) > limit:
        raise ValueError("Download excede o limite esperado")
    return content


def obter_snapshot(cache_directory: Path) -> tuple[Path, dict]:
    metadata = json.loads(_download(f"{BASE_URL}/sqlite.json", 100_000))
    digest = metadata.get("sha256", "")
    relative = metadata.get("arquivo", "")
    size = metadata.get("bytes")
    if not re.fullmatch(r"[0-9a-f]{64}", digest) or relative != f"snapshots/{digest}.sqlite":
        raise ValueError("Manifesto SQLite inválido")
    if not isinstance(size, int) or not 0 < size <= 50_000_000:
        raise ValueError("Tamanho SQLite inválido")
    cache_directory = Path(cache_directory)
    cache_directory.mkdir(parents=True, exist_ok=True)
    target = cache_directory / f"{digest}.sqlite"
    if target.exists():
        content = target.read_bytes()
    else:
        content = _download(f"{BASE_URL}/{relative}", size)
    if len(content) != size or hashlib.sha256(content).hexdigest() != digest:
        raise ValueError("A integridade do arquivo não confere; download rejeitado")
    if not target.exists():
        with tempfile.NamedTemporaryFile(dir=cache_directory, suffix=".sqlite.tmp", delete=False) as stream:
            stream.write(content)
            temporary = Path(stream.name)
        try:
            if not target.exists():
                temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    return target, metadata


def conectar_somente_leitura(path: Path) -> sqlite3.Connection:
    # Immutable is safe because each published filename identifies its exact content.
    connection = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.execute("PRAGMA query_only=ON")
    return connection
