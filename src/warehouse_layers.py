"""
Layered DuckDB warehouse: raw_data → processed → analytics (+ optional star schema).

Used by the FastAPI job pipeline and by the CLI script `duckdb_warehouse_pipeline.py`.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger("skypipe.warehouse_layers")


def make_job_slug(filename: str, job_id: str) -> str:
    """Unique, safe table prefix per upload (avoids collisions across jobs)."""
    stem = Path(filename).stem.lower()
    stem = re.sub(r"[^a-z0-9_]+", "_", stem)
    stem = re.sub(r"_+", "_", stem).strip("_") or "dataset"
    if stem[0].isdigit():
        stem = "t_" + stem
    stem = stem[:28]
    short = job_id.replace("-", "")[:12]
    return f"{stem}_{short}"


def spark_fmt_to_layer_fmt(fmt: str) -> str | None:
    f = fmt.lower().strip()
    if f in ("csv", "json", "parquet"):
        return f
    if f in ("excel", "xlsx", "xls"):
        return "excel"
    return None


def detect_format_from_path(path: Path) -> str | None:
    ext = path.suffix.lower()
    if ext == ".csv":
        return "csv"
    if ext in (".json",):
        return "json"
    if ext in (".parquet", ".pq"):
        return "parquet"
    if ext in (".xlsx", ".xls"):
        return "excel"
    return None


def ensure_schemas(con) -> None:
    con.execute("CREATE SCHEMA IF NOT EXISTS raw_data")
    con.execute("CREATE SCHEMA IF NOT EXISTS processed")
    con.execute("CREATE SCHEMA IF NOT EXISTS analytics")
    logger.info("Schemas created")


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def load_into_raw(con, path: Path, fmt: str, slug: str) -> str:
    raw_table = f"raw_{slug}"
    fq = f'raw_data."{raw_table}"'
    p = str(path.resolve())

    if fmt == "csv":
        con.execute(f"CREATE OR REPLACE TABLE {fq} AS SELECT * FROM read_csv_auto(?)", [p])
    elif fmt == "json":
        con.execute(f"CREATE OR REPLACE TABLE {fq} AS SELECT * FROM read_json_auto(?)", [p])
    elif fmt == "parquet":
        con.execute(f"CREATE OR REPLACE TABLE {fq} AS SELECT * FROM read_parquet(?)", [p])
    elif fmt == "excel":
        import pandas as pd

        df = pd.read_excel(p, engine="openpyxl")
        if df.empty:
            raise ValueError("Excel sheet has no rows.")
        con.register("_tmp_excel_df", df)
        con.execute(f"CREATE OR REPLACE TABLE {fq} AS SELECT * FROM _tmp_excel_df")
        con.unregister("_tmp_excel_df")
    else:
        raise ValueError(f"Unsupported layered format: {fmt}")

    n = con.execute(f"SELECT COUNT(*) FROM {fq}").fetchone()[0]
    logger.info("Layered raw: %s rows → %s", n, fq)
    return raw_table


def standardize_name(name: str, used: dict[str, int]) -> str:
    s = name.strip().lower().replace(" ", "_")
    s = re.sub(r"[^a-z0-9_]", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        s = "column"
    if s[0].isdigit():
        s = "c_" + s
    base = s
    if base not in used:
        used[base] = 1
        return base
    used[base] += 1
    return f"{base}_{used[base]}"


def get_columns(con, schema: str, table: str) -> list[tuple[str, str]]:
    rows = con.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = ? AND table_name = ?
        ORDER BY ordinal_position
        """,
        [schema, table],
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


NUMERIC_TYPES = frozenset(
    {
        "TINYINT",
        "SMALLINT",
        "INTEGER",
        "BIGINT",
        "HUGEINT",
        "UTINYINT",
        "USMALLINT",
        "UINTEGER",
        "UBIGINT",
        "FLOAT",
        "DOUBLE",
        "REAL",
        "DECIMAL",
    }
)
STRING_TYPES = frozenset({"VARCHAR", "CHAR", "BPCHAR", "TEXT"})


def is_numeric_type(dtype: str) -> bool:
    return dtype.upper().split("(")[0] in NUMERIC_TYPES


def is_string_type(dtype: str) -> bool:
    return dtype.upper().split("(")[0] in STRING_TYPES


def clean_data(con, raw_table: str, slug: str) -> str:
    src_schema = "raw_data"
    dst_schema = "processed"
    proc_table = f"processed_{slug}"
    fq_src = f'{src_schema}."{raw_table}"'
    fq_dst = f'{dst_schema}."{proc_table}"'

    cols = get_columns(con, src_schema, raw_table)
    if not cols:
        raise RuntimeError("Raw table has no columns.")

    used: dict[str, int] = {}
    select_parts: list[str] = []
    for col_name, dtype in cols:
        std = standardize_name(col_name, used)
        q = _quote_ident(col_name)
        if is_string_type(dtype):
            select_parts.append(f"COALESCE(CAST({q} AS VARCHAR), '(missing)') AS {_quote_ident(std)}")
        elif is_numeric_type(dtype):
            select_parts.append(f"COALESCE(CAST({q} AS DOUBLE), 0) AS {_quote_ident(std)}")
        else:
            select_parts.append(f"COALESCE(CAST({q} AS VARCHAR), '(missing)') AS {_quote_ident(std)}")

    select_sql = ",\n            ".join(select_parts)
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {fq_dst} AS
        SELECT DISTINCT
            {select_sql}
        FROM {fq_src}
        """
    )
    n = con.execute(f"SELECT COUNT(*) FROM {fq_dst}").fetchone()[0]
    logger.info("Layered processed: %s rows → %s", n, fq_dst)
    return proc_table


def create_aggregations(con, proc_table: str, slug: str) -> tuple[str, str | None, str | None]:
    schema = "processed"
    cols = get_columns(con, schema, proc_table)
    numeric = [c for c, t in cols if is_numeric_type(t)]
    categorical = [c for c, t in cols if is_string_type(t)]

    fq_proc = f'{schema}."{proc_table}"'
    agg_name = f"analytics_{slug}"
    fq_agg = f'analytics."{agg_name}"'

    group_col = categorical[0] if categorical else None
    gq = _quote_ident(group_col) if group_col else None

    if group_col and numeric:
        sum_exprs = ", ".join(f"SUM({_quote_ident(c)}) AS sum_{c}" for c in numeric)
        avg_exprs = ", ".join(f"AVG({_quote_ident(c)}) AS avg_{c}" for c in numeric)
        con.execute(
            f"""
            CREATE OR REPLACE TABLE {fq_agg} AS
            SELECT
                {gq} AS slice_key,
                COUNT(*) AS row_count,
                {sum_exprs},
                {avg_exprs}
            FROM {fq_proc}
            GROUP BY {gq}
            """
        )
    elif numeric:
        sum_exprs = ", ".join(f"SUM({_quote_ident(c)}) AS sum_{c}" for c in numeric)
        avg_exprs = ", ".join(f"AVG({_quote_ident(c)}) AS avg_{c}" for c in numeric)
        con.execute(
            f"""
            CREATE OR REPLACE TABLE {fq_agg} AS
            SELECT
                COUNT(*) AS row_count,
                {sum_exprs},
                {avg_exprs}
            FROM {fq_proc}
            """
        )
    else:
        con.execute(
            f"""
            CREATE OR REPLACE TABLE {fq_agg} AS
            SELECT COUNT(*) AS row_count FROM {fq_proc}
            """
        )

    dim_name: str | None = None
    fact_name: str | None = None

    if group_col:
        dim_name = f"dim_{slug}"
        fact_name = f"fact_{slug}"
        fq_dim = f'analytics."{dim_name}"'
        fq_fact = f'analytics."{fact_name}"'
        con.execute(
            f"""
            CREATE OR REPLACE TABLE {fq_dim} AS
            SELECT
                ROW_NUMBER() OVER (ORDER BY {gq}) AS dim_id,
                {gq} AS category_value
            FROM (SELECT DISTINCT {gq} FROM {fq_proc}) AS d
            """
        )
        sum_for_fact = ", ".join(f"SUM(p.{_quote_ident(c)}) AS sum_{c}" for c in numeric) if numeric else ""
        avg_for_fact = ", ".join(f"AVG(p.{_quote_ident(c)}) AS avg_{c}" for c in numeric) if numeric else ""
        extra = ", ".join(x for x in [sum_for_fact, avg_for_fact] if x)
        if extra:
            metrics = f"COUNT(*) AS row_count, {extra}"
        else:
            metrics = "COUNT(*) AS row_count"
        con.execute(
            f"""
            CREATE OR REPLACE TABLE {fq_fact} AS
            SELECT
                d.dim_id,
                {metrics}
            FROM {fq_proc} p
            INNER JOIN {fq_dim} d ON p.{gq} = d.category_value
            GROUP BY d.dim_id
            """
        )
        logger.info("Layered star schema: %s, %s", fq_dim, fq_fact)

    logger.info("Layered analytics mart ready: %s", fq_agg)
    return agg_name, dim_name, fact_name


def run_layered_warehouse(
    db_path: str,
    file_path: str | Path,
    spark_fmt: str,
    job_id: str,
    filename: str,
) -> dict[str, Any]:
    """
    Load the same local file Spark used into medallion schemas in warehouse.duckdb.
    Returns a dict for API/UI (never raises — failures are soft).
    """
    return run_pipeline(
        file_path=file_path,
        db_path=db_path,
        job_id=job_id,
        filename=filename,
        fmt=spark_fmt,
    )


def _show_pipeline_structure(con) -> dict[str, list[str]]:
    """Debug visibility: schemas + tables in each schema."""
    schema_rows = con.execute(
        """
        SELECT schema_name
        FROM information_schema.schemata
        ORDER BY schema_name
        """
    ).fetchall()
    all_schemas = [r[0] for r in schema_rows]
    logger.info("SHOW SCHEMAS -> %s", all_schemas)
    out: dict[str, list[str]] = {"schemas": all_schemas}
    for sch in ("raw_data", "processed", "analytics"):
        table_rows = con.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = ?
            ORDER BY table_name
            """,
            [sch],
        ).fetchall()
        tables = [r[0] for r in table_rows]
        logger.info("SHOW TABLES FROM %s -> %s", sch, tables)
        out[sch] = tables
    return out


def run_pipeline(
    file_path: str | Path,
    db_path: str | Path = "warehouse.duckdb",
    job_id: str = "manual",
    filename: str | None = None,
    fmt: str | None = None,
) -> dict[str, Any]:
    """
    End-to-end integrated warehouse flow:
    INPUT -> RAW -> PROCESSED -> ANALYTICS.
    """
    path = Path(file_path)
    if not path.is_file():
        return {"ok": False, "error": f"Input file not found: {path}"}

    if fmt:
        layer_fmt = spark_fmt_to_layer_fmt(fmt) or fmt.lower().strip()
    else:
        layer_fmt = detect_format_from_path(path)
    if not layer_fmt:
        return {"ok": False, "error": f"Unsupported dataset format: {path.suffix}"}

    final_filename = filename or path.name
    slug = make_job_slug(final_filename, job_id)
    db = Path(db_path)
    db.parent.mkdir(parents=True, exist_ok=True)

    try:
        import duckdb
    except ImportError:
        return {"ok": False, "error": "duckdb package not installed."}

    try:
        con = duckdb.connect(str(db))
        try:
            # Step 1 + 2: always done first.
            ensure_schemas(con)
            print("Schemas created")

            # Step 3: raw layer.
            raw_table = load_into_raw(con, path, layer_fmt, slug)
            print("Raw data loaded")

            # Step 4: processed layer.
            proc_table = clean_data(con, raw_table, slug)
            print("Processing complete")

            # Step 5: analytics layer.
            agg_name, dim_name, fact_name = create_aggregations(con, proc_table, slug)
            print("Analytics table created")

            # Step 6: verify and print structure.
            structure = _show_pipeline_structure(con)
        finally:
            con.close()
    except Exception as e:
        logger.exception("Integrated pipeline failed for job %s", job_id)
        return {"ok": False, "error": str(e)}

    tables: dict[str, str | None] = {
        "raw": f'raw_data."{raw_table}"',
        "processed": f'processed."{proc_table}"',
        "analytics": f'analytics."{agg_name}"',
        "dimension": f'analytics."{dim_name}"' if dim_name else None,
        "fact": f'analytics."{fact_name}"' if fact_name else None,
    }
    return {
        "ok": True,
        "job_id": job_id,
        "slug": slug,
        "schemas": ["raw_data", "processed", "analytics"],
        "tables": tables,
        "verification": structure,
        "flow": "Input file -> raw_data.raw_<id> -> processed.processed_<id> -> analytics.analytics_<id>",
        "example_cli": f'duckdb "{db}"',
        "example_queries": [
            f"SELECT * FROM {tables['raw']} LIMIT 10;",
            f"SELECT * FROM {tables['processed']} LIMIT 10;",
            f"SELECT * FROM {tables['analytics']} LIMIT 20;",
        ]
        + (
            [
                f"SELECT * FROM {tables['dimension']} LIMIT 50;",
                f"SELECT * FROM {tables['fact']} LIMIT 50;",
            ]
            if tables.get("dimension") and tables.get("fact")
            else []
        ),
    }


def inspect_database(con) -> None:
    """CLI helper: print schemas, columns, samples."""
    schemas = ["raw_data", "processed", "analytics"]
    for sch in schemas:
        print(f"\n--- SCHEMA: {sch} ---")
        tables = con.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = ? ORDER BY table_name
            """,
            [sch],
        ).fetchall()
        if not tables:
            print("  (no tables)")
            continue
        for (tname,) in tables:
            print(f"\n  TABLE: {sch}.{tname}")
            desc = con.execute(
                """
                SELECT column_name, data_type FROM information_schema.columns
                WHERE table_schema = ? AND table_name = ?
                ORDER BY ordinal_position
                """,
                [sch, tname],
            ).fetchall()
            for col, dt in desc:
                print(f"    - {col}: {dt}")
            try:
                sample = con.execute(
                    f"SELECT * FROM {_quote_ident(sch)}.{_quote_ident(tname)} LIMIT 5"
                ).fetchdf()
                print("    Sample:")
                print(sample.to_string(index=False, max_colwidth=20) if not sample.empty else "      (empty)")
            except Exception as e:
                print(f"    (sample error: {e})")
