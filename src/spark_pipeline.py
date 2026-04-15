"""
SkyPipe — PySpark Smart Adaptive Processing Engine.

MapReduce mapping:
  - Map: per-column operations (stats, parses, groupBy keys) implemented as Spark transformations.
  - Reduce: global aggregations (sum, avg, count, collect top-k) as actions / grouped reductions.

Works for arbitrary structured datasets after format-specific load + schema inference.
"""

from __future__ import annotations

import glob
import json
import logging
import os
import sys
from dataclasses import asdict
from typing import Any

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType

from schema_detector import SchemaProfile, build_schema_profile, validate_minimum_schema


def _dtype(df: DataFrame, col: str):
    for f in df.schema.fields:
        if f.name == col:
            return f.dataType
    return None

logger = logging.getLogger("skypipe.spark")


def _bootstrap_java_home() -> None:
    """
    If JAVA_HOME is missing, try common Windows JDK locations (Eclipse Temurin, Oracle, Microsoft).
    PySpark starts a JVM; without JAVA_HOME many fresh installs fail until the user sets it.
    """
    if os.environ.get("JAVA_HOME"):
        return
    if sys.platform != "win32":
        return
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    patterns = [
        os.path.join(program_files, "Eclipse Adoptium", "jdk-*"),
        os.path.join(program_files, "Java", "jdk-*"),
        os.path.join(program_files, "Microsoft", "jdk-*"),
        os.path.join(program_files_x86, "Eclipse Adoptium", "jdk-*"),
        os.path.join(program_files_x86, "Java", "jdk-*"),
    ]
    for pattern in patterns:
        matches = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
        for home in matches:
            java_exe = os.path.join(home, "bin", "java.exe")
            if os.path.isfile(java_exe):
                os.environ["JAVA_HOME"] = home
                bin_dir = os.path.join(home, "bin")
                path = os.environ.get("PATH", "")
                if bin_dir not in path:
                    os.environ["PATH"] = bin_dir + os.pathsep + path
                logger.info("Using JAVA_HOME=%s (auto-detected)", home)
                return


def build_spark_session(app_name: str = "SkyPipe") -> SparkSession:
    """
    Local or cluster master from SPARK_MASTER (e.g. local[*], yarn, spark://...).
    Fault-tolerance oriented defaults: speculation, shuffle retry, optional checkpoint.
    """
    _bootstrap_java_home()
    master = os.environ.get("SPARK_MASTER", "local[*]")
    checkpoint_dir = os.environ.get("SKYPIPE_CHECKPOINT_DIR", "").strip()
    builder = (
        SparkSession.builder.appName(app_name)
        .master(master)
        .config("spark.sql.shuffle.partitions", os.environ.get("SPARK_SHUFFLE_PARTITIONS", "200"))
        .config("spark.sql.execution.arrow.pyspark.enabled", "true")
        .config("spark.speculation", "true")
        .config("spark.task.maxFailures", "4")
    )
    # GCS: requires gcs-connector JAR on classpath for gs:// paths (Dataproc includes it).
    if os.environ.get("GCP_PROJECT"):
        builder = builder.config("spark.hadoop.fs.gs.impl", "com.google.cloud.hadoop.fs.gcs.GoogleHadoopFileSystem")
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel(os.environ.get("SPARK_LOG_LEVEL", "WARN"))
    if checkpoint_dir:
        spark.sparkContext.setCheckpointDir(checkpoint_dir)
    return spark


def load_dataframe(spark: SparkSession, path: str, fmt: str, options: dict[str, str] | None = None) -> DataFrame:
    """
    Load structured data. fmt: csv | json | parquet | excel
    Excel uses Pandas on the driver (suitable for moderate files); for very large XLSX use CSV/Parquet or
    add crealytics spark-excel on the cluster.
    """
    opts = options or {}
    fmt_l = fmt.lower().strip()
    if fmt_l == "parquet":
        return spark.read.parquet(path)
    if fmt_l == "csv":
        return (
            spark.read.option("header", opts.get("header", "true"))
            .option("inferSchema", opts.get("inferSchema", "true"))
            .option("multiLine", opts.get("multiLine", "false"))
            .csv(path)
        )
    if fmt_l == "json":
        return spark.read.option("multiLine", opts.get("multiLine", "true")).json(path)
    if fmt_l in ("excel", "xlsx", "xls"):
        return _load_excel_via_pandas(spark, path)
    raise ValueError(f"Unsupported format: {fmt}")


def _load_excel_via_pandas(spark: SparkSession, path: str) -> DataFrame:
    import pandas as pd

    pdf = pd.read_excel(path, engine="openpyxl")
    return spark.createDataFrame(pdf)


def adaptive_analytics(
    df: DataFrame,
    profile: SchemaProfile | None = None,
    top_k: int = 10,
) -> dict[str, Any]:
    """
    Run adaptive MapReduce-style analytics from detected schema.
    Returns a JSON-serializable summary for API / UI.
    """
    if profile is None:
        profile = build_schema_profile(df)
    ok, errs = validate_minimum_schema(profile)
    if not ok:
        return {"status": "error", "errors": errs, "profile": asdict(profile)}

    results: dict[str, Any] = {
        "status": "ok",
        "profile": {
            "all_columns": profile.all_columns,
            "numeric_columns": profile.numeric_columns,
            "categorical_columns": profile.categorical_columns,
            "datetime_columns": profile.datetime_columns,
            "boolean_columns": profile.boolean_columns,
            "issues": profile.issues,
        },
        "numeric_stats": [],
        "categorical_top": [],
        "datetime_trends": [],
        "row_count": 0,
    }

    # Optional checkpoint for long DAGs (fault tolerance demo)
    if os.environ.get("SKYPIPE_CHECKPOINT_DF", "").lower() in ("1", "true", "yes"):
        df = df.checkpoint()

    results["row_count"] = df.count()

    # --- Numeric: map (identity columns) -> reduce (aggregations) ---
    for col in profile.numeric_columns:
        agg = df.select(
            F.count(F.col(col)).alias("count"),
            F.avg(F.col(col)).alias("mean"),
            F.min(F.col(col)).alias("min"),
            F.max(F.col(col)).alias("max"),
            F.stddev_pop(F.col(col)).alias("stddev_pop"),
        ).collect()[0]
        results["numeric_stats"].append(
            {
                "column": col,
                "count": int(agg["count"] or 0),
                "mean": float(agg["mean"]) if agg["mean"] is not None else None,
                "min": float(agg["min"]) if agg["min"] is not None else None,
                "max": float(agg["max"]) if agg["max"] is not None else None,
                "stddev_pop": float(agg["stddev_pop"]) if agg["stddev_pop"] is not None else None,
            }
        )

    # --- Categorical: map (column) -> reduce (groupBy count, order, limit) ---
    for col in profile.categorical_columns:
        freq = (
            df.groupBy(F.col(col).alias("value"))
            .count()
            .orderBy(F.desc("count"))
            .limit(top_k)
            .collect()
        )
        results["categorical_top"].append(
            {
                "column": col,
                "top_values": [{"value": str(r["value"]), "count": int(r["count"])} for r in freq],
            }
        )

    # --- Date/time: trends by day / month / year (map parse -> reduce groupBy) ---
    for col in profile.datetime_columns:
        c = F.col(col)
        if isinstance(_dtype(df, col), StringType):
            c = F.to_timestamp(F.col(col))
        day_df = df.withColumn("_d", F.to_date(c)).groupBy("_d").count().orderBy("_d")
        month_df = df.withColumn("_m", F.date_trunc("month", c)).groupBy("_m").count().orderBy("_m")
        year_df = df.withColumn("_y", F.year(c)).groupBy("_y").count().orderBy("_y")
        results["datetime_trends"].append(
            {
                "column": col,
                "by_day": [{"date": str(r["_d"]), "count": int(r["count"])} for r in day_df.collect()],
                "by_month": [{"month": str(r["_m"]), "count": int(r["count"])} for r in month_df.collect()],
                "by_year": [{"year": int(r["_y"]), "count": int(r["count"])} for r in year_df.collect()],
            }
        )

    return results


def run_pipeline_local(
    local_path: str,
    filename: str,
    fmt: str | None = None,
    top_k: int = 10,
) -> dict[str, Any]:
    """End-to-end run for CLI / tests: SparkSession, load, profile, analytics."""
    from gcp_utils import detect_format_from_filename, sniff_format_from_bytes

    if fmt is None:
        with open(local_path, "rb") as f:
            head = f.read(4096)
        fmt = sniff_format_from_bytes(filename, head)
        if fmt == "unknown":
            fmt = detect_format_from_filename(filename)
    spark = build_spark_session()
    try:
        df = load_dataframe(spark, local_path, fmt)
        return adaptive_analytics(df, top_k=top_k)
    finally:
        spark.stop()


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 2:
        print("Usage: python spark_pipeline.py <path-to-file>")
        sys.exit(1)
    out = run_pipeline_local(sys.argv[1], os.path.basename(sys.argv[1]))
    print(json.dumps(out, indent=2, default=str))
