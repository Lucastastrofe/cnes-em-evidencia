"""Validated read-only client for this project's published API."""
from __future__ import annotations

import json
import re
import urllib.request
from cnes_audit.catalog import API_BASE


def fetch_json(path: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_/]+\.json", path) or ".." in path:
        raise ValueError("Caminho fora do contrato da API")
    request = urllib.request.Request(f"{API_BASE}/{path}", headers={"Accept": "application/json", "User-Agent": "cnes-em-evidencia"})
    with urllib.request.urlopen(request, timeout=15) as response:
        content = response.read(8_000_001)
        if len(content) > 8_000_000:
            raise ValueError("Resposta excede o limite esperado")
    payload = json.loads(content)
    if not isinstance(payload, dict) or not isinstance(payload.get("metadados"), dict):
        raise ValueError("Resposta fora do contrato")
    if not isinstance(payload["metadados"].get("id_execucao"), str) or not payload["metadados"]["id_execucao"]:
        raise ValueError("Resposta sem identificação de execução")
    return payload


def fetch_catalog() -> dict:
    payload = fetch_json("catalogo.json")
    tables = payload.get("tabelas")
    if not isinstance(tables, list) or not tables:
        raise ValueError("Catálogo sem tabelas")
    for table in tables:
        if not isinstance(table, dict) or not re.fullmatch(r"[a-z][a-z0-9_]*", str(table.get("tabela", ""))):
            raise ValueError("Identificador de tabela inválido")
        if not isinstance(table.get("linhas"), int) or not isinstance(table.get("colunas"), int):
            raise ValueError("Contagens inválidas no catálogo")
        if not isinstance(table.get("camada"), str) or not isinstance(table.get("grao"), str) or table["linhas"] < 0 or table["colunas"] < 1:
            raise ValueError("Metadados da tabela incompletos")
    return payload


def fetch_table(table: str, uf: str | None = None) -> dict:
    if not re.fullmatch(r"[a-z][a-z0-9_]*", table):
        raise ValueError("Tabela inválida")
    if uf is not None and not re.fullmatch(r"\d{2}|[A-Z]{2}", uf):
        raise ValueError("UF inválida")
    path = f"tabelas/{table}/ufs/{uf}.json" if uf else f"tabelas/{table}.json"
    payload = fetch_json(path)
    if not isinstance(payload.get("dados"), list) or any(not isinstance(row, dict) for row in payload["dados"]):
        raise ValueError("Dados da tabela fora do contrato")
    if payload.get("total") != len(payload["dados"]):
        raise ValueError("Total da API não reconcilia com os dados")
    return payload
