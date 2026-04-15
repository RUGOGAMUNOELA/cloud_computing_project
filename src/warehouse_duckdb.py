"""
Result store: analytical warehouse in embedded DuckDB (columnar SQL, local file).
Persists job summaries for fast reads and offline inspection (CLI or API).
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("skypipe.warehouse")

DDL = """
CREATE TABLE IF NOT EXISTS skypipe_analytics_runs (
    job_id VARCHAR PRIMARY KEY,
    created_at TIMESTAMP,
    filename VARCHAR,
    format VARCHAR,
    input_storage_uri VARCHAR,
    input_stage_label VARCHAR,
    row_count INTEGER,
    status VARCHAR,
    warehouse_type VARCHAR,
    warehouse_detail VARCHAR,
    bq_table VARCHAR,
    result_json VARCHAR
);
"""


def _connect(path: str):
    import duckdb

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    con = duckdb.connect(path)
    con.execute(DDL)
    return con


def persist_run(
    duckdb_path: str,
    job_id: str,
    filename: str,
    fmt: str,
    input_storage_uri: str,
    input_stage_label: str,
    row_count: int | None,
    status: str,
    warehouse_type: str,
    warehouse_detail: str,
    bq_table: str | None,
    result: dict[str, Any],
) -> None:
    con = _connect(duckdb_path)
    try:
        con.execute("DELETE FROM skypipe_analytics_runs WHERE job_id = ?", [job_id])
        con.execute(
            """
            INSERT INTO skypipe_analytics_runs
            (job_id, created_at, filename, format, input_storage_uri, input_stage_label,
             row_count, status, warehouse_type, warehouse_detail, bq_table, result_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                job_id,
                datetime.now(timezone.utc),
                filename,
                fmt,
                input_storage_uri,
                input_stage_label,
                row_count,
                status,
                warehouse_type,
                warehouse_detail,
                bq_table,
                json.dumps(result, default=str),
            ],
        )
    finally:
        con.close()
    logger.info("Persisted job %s to DuckDB warehouse %s", job_id, duckdb_path)


def fetch_run(duckdb_path: str, job_id: str) -> dict[str, Any] | None:
    if not os.path.isfile(duckdb_path):
        return None
    con = _connect(duckdb_path)
    try:
        cur = con.execute("SELECT * FROM skypipe_analytics_runs WHERE job_id = ?", [job_id])
        row = cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
    finally:
        con.close()
