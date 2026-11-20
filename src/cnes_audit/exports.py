"""Independent formats with a shared typed column contract."""
from __future__ import annotations

import io
import json
import pyarrow as pa
import pyarrow.parquet as pq


def parquet_bytes(rows: list[dict], fields: list[dict]) -> bytes:
    types = {"string": pa.string(), "integer": pa.int64(), "number": pa.float64()}
    schema = pa.schema([pa.field(field["coluna"], types[field["tipo"]], nullable=field["aceita_nulo"]) for field in fields])
    schema = schema.with_metadata({b"cnes_dictionary": json.dumps(fields, ensure_ascii=False).encode("utf-8")})
    table = pa.Table.from_pylist(rows, schema=schema)
    target = io.BytesIO()
    pq.write_table(table, target, compression="snappy")
    return target.getvalue()
