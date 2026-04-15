#!/usr/bin/env python3
"""
SkyPipe — Standalone CLI for the same layered DuckDB pipeline the API runs after each upload.

Flow: INPUT → raw_data → processed → analytics (+ dim/fact)

The web UI triggers this logic automatically via FastAPI; this script is for demos without the UI.

Usage:
    cd skypipe
    python duckdb_warehouse_pipeline.py
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from warehouse_layers import inspect_database, run_pipeline  # noqa: E402


def get_db_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "warehouse.duckdb"


def prompt_file_path() -> Path:
    raw = input("Enter path to a CSV, Excel, JSON, or Parquet file: ").strip().strip('"').strip("'")
    return Path(raw).expanduser().resolve()


def validate_input_path(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, f"File not found: {path}"
    if not path.is_file():
        return False, f"Not a file: {path}"
    ext = path.suffix.lower()
    fmt_map = {".csv": "csv", ".json": "json", ".xlsx": "excel", ".xls": "excel", ".parquet": "parquet", ".pq": "parquet"}
    fmt = fmt_map.get(ext)
    if not fmt:
        return False, f"Unsupported extension {ext!r}."
    return True, fmt


def main() -> int:
    print("DuckDB layered warehouse (same engine as SkyPipe UI backend)\n")

    path = prompt_file_path()
    ok, msg = validate_input_path(path)
    if not ok:
        print(f"Error: {msg}")
        return 1
    fmt = msg

    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Database: {db_path}\n")

    try:
        import duckdb
    except ImportError:
        print("pip install duckdb pandas openpyxl")
        return 1

    job_id = str(uuid.uuid4())
    out = run_pipeline(
        file_path=path,
        db_path=db_path,
        job_id=job_id,
        filename=path.name,
        fmt=fmt,
    )
    if not out.get("ok"):
        print(f"\nError: {out.get('error')}")
        return 1

    print("\n[Verification] SHOW SCHEMAS / SHOW TABLES")
    verification = out.get("verification") or {}
    print(f"Schemas: {verification.get('schemas')}")
    print(f"raw_data tables: {verification.get('raw_data')}")
    print(f"processed tables: {verification.get('processed')}")
    print(f"analytics tables: {verification.get('analytics')}")

    con = duckdb.connect(str(db_path))
    try:
        print("\n[Inspection]")
        inspect_database(con)
    finally:
        con.close()

    print(f"\nDone. Same file the React app uses: {db_path}")
    print(f'  duckdb "{db_path}"')

    return 0


if __name__ == "__main__":
    sys.exit(main())
