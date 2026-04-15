"""
Human-readable pipeline story for non-technical UI cards.
"""

from __future__ import annotations

from typing import Any


def warehouse_layer_cards(layer: dict[str, Any] | None) -> list[dict[str, str]]:
    """UI cards linking Spark results to DuckDB medallion schemas (shown on Results)."""
    if not layer:
        return []
    if not layer.get("ok"):
        err = layer.get("error") or "unknown error"
        return [
            {
                "title": "Layered warehouse",
                "icon": "layers",
                "body": f"Layered tables for raw data, processed data, and analytics were not built for this run. Reason: {err}",
            }
        ]
    t = layer.get("tables") or {}
    raw_t = t.get("raw") or "not available"
    proc_t = t.get("processed") or "not available"
    agg_t = t.get("analytics") or "not available"
    body = (
        "The same file Spark analyzed is loaded into warehouse.duckdb in three layers.\n"
        f"Raw layer table: {raw_t}\n"
        f"Processed layer table: {proc_t}\n"
        f"Analytics layer table: {agg_t}"
    )
    dim = t.get("dimension")
    fact = t.get("fact")
    if dim and fact:
        body += (
            f"\nStar schema dimension table: {dim}\n"
            f"Star schema fact table: {fact} with one row per dimension id."
        )
    cards = [
        {
            "title": "UI ↔ DuckDB pipeline",
            "icon": "git-branch",
            "body": (
                "Input upload goes to Spark processing, then results are written to layered DuckDB tables. "
                "Open warehouse.duckdb in the DuckDB CLI to run the example queries."
            ),
        },
        {
            "title": "Where each layer lives",
            "icon": "table",
            "body": body,
        },
    ]
    return cards


def input_stage_cards(
    input_label: str,
    input_detail: str,
    logical_uri: str,
    filename: str,
    file_format: str,
) -> list[dict[str, str]]:
    return [
        {
            "title": "Secure intake",
            "icon": "upload",
            "body": f"Your file {filename} was validated as {file_format.upper()} and scanned for safe extensions.",
        },
        {
            "title": "Distributed storage layer",
            "icon": "database",
            "body": f"{input_detail} Logical location: `{logical_uri}`. This keeps raw uploads in shared object storage so processing workers can access the same dataset consistently.",
        },
        {
            "title": "Why this matters",
            "icon": "layers",
            "body": "Storing raw files in object storage lets many workers read the same dataset in parallel during the next stage.",
        },
    ]


def processing_stage_cards(
    row_count: int | None,
    numeric_cols: list[str],
    categorical_cols: list[str],
    datetime_cols: list[str],
) -> list[dict[str, str]]:
    n = row_count if row_count is not None else 0
    return [
        {
            "title": "Apache Spark cluster engine",
            "icon": "cpu",
            "body": "Data is loaded into a Spark DataFrame. Spark schedules work across parallel tasks for aggregation and profiling.",
        },
        {
            "title": "Automatic schema intelligence",
            "icon": "search",
            "body": f"The engine classified columns without hardcoding your dataset: {len(numeric_cols)} numeric, {len(categorical_cols)} categorical, {len(datetime_cols)} date or time.",
        },
        {
            "title": "Adaptive analytics",
            "icon": "activity",
            "body": "For numbers it computes averages and ranges. For categories it finds top values. For dates it builds daily and monthly trends.",
        },
        {
            "title": "Scale-out processing",
            "icon": "share",
            "body": f"Your dataset contained {n:,} rows in this run. On Dataproc or EMR, the same code can scale across more machines as data grows.",
        },
    ]


def results_stage_cards(
    warehouse_detail: str,
    duckdb_path: str,
    row_count: int | None,
) -> list[dict[str, str]]:
    cards = [
        {
            "title": "What you are seeing",
            "icon": "bar-chart",
            "body": "Charts summarize aggregated results. Raw rows stay in object storage while the warehouse stores analysis ready summaries.",
        },
        {
            "title": "Analytical warehouse",
            "icon": "warehouse",
            "body": warehouse_detail,
        },
        {
            "title": "DuckDB (embedded warehouse)",
            "icon": "disc",
            "body": f"Results are persisted in DuckDB at {duckdb_path}. It is a columnar SQL file for local analytics.",
        },
    ]
    if row_count is not None:
        cards.append(
            {
                "title": "Dataset size",
                "icon": "hash",
                "body": f"{row_count:,} rows were counted during processing.",
            }
        )
    return cards


def chart_insights(result: dict[str, Any]) -> list[dict[str, str]]:
    """Short takeaway lines for each chart section."""
    insights: list[dict[str, str]] = []
    if result.get("status") != "ok":
        return [{"title": "Run status", "body": "The pipeline reported an issue; see the error card above."}]
    for block in result.get("numeric_stats") or []:
        col = block.get("column", "?")
        m = block.get("mean")
        if isinstance(m, (int, float)):
            insights.append(
                {
                    "title": f"Numbers: {col}",
                    "body": f"Typical value (mean) is around {float(m):.2f}. Compare min and max to see spread.",
                }
            )
        else:
            insights.append(
                {
                    "title": f"Numbers: {col}",
                    "body": "Summary statistics were computed for this numeric column.",
                }
            )
    for block in result.get("categorical_top") or []:
        col = block.get("column", "?")
        top = (block.get("top_values") or [{}])[0]
        insights.append(
            {
                "title": f"Categories: {col}",
                "body": f"The most common value is {top.get('value', 'not available')}, appearing {top.get('count', 0)} times in the sample shown.",
            }
        )
    for block in result.get("datetime_trends") or []:
        col = block.get("column", "?")
        insights.append(
            {
                "title": f"Time trend: {col}",
                "body": "The line shows how many rows fall on each day.",
            }
        )
    return insights[:12]
