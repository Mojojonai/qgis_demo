from __future__ import annotations

from pathlib import Path
from typing import Any

import psycopg2


def connection_kwargs(cfg: dict[str, Any], database: str | None = None) -> dict[str, Any]:
    db = cfg["database"]
    return {
        "host": db["host"],
        "port": db["port"],
        "dbname": database or db["database"],
        "user": db["user"],
        "password": db["password"],
    }


def connect(cfg: dict[str, Any], database: str | None = None):
    return psycopg2.connect(**connection_kwargs(cfg, database=database))


def run_sql_file(cfg: dict[str, Any], sql_path: str | Path) -> None:
    path = Path(sql_path)
    if not path.is_absolute():
        path = Path(cfg["_project_root"]) / path
    sql = path.read_text(encoding="utf-8")
    with connect(cfg) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql)
