#!/usr/bin/env python3
"""
Dataproc entrypoint: run adaptive SkyPipe analytics on gs:// or local paths.
Usage (on cluster via job submit):
  spark-submit dataproc_driver.py gs://bucket/path/file.csv csv
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, ROOT)
os.environ.setdefault("SPARK_MASTER", "yarn")

from schema_detector import build_schema_profile  # noqa: E402
from spark_pipeline import adaptive_analytics, build_spark_session, load_dataframe  # noqa: E402


def main() -> None:
    if len(sys.argv) < 3:
        print(
            "Usage: dataproc_driver.py <path> <csv|json|parquet|excel>",
            file=sys.stderr,
        )
        sys.exit(1)
    path, fmt = sys.argv[1], sys.argv[2].lower()
    spark = build_spark_session("SkyPipe-Dataproc")
    try:
        df = load_dataframe(spark, path, fmt)
        profile = build_schema_profile(df)
        out = adaptive_analytics(df, profile=profile)
        print(json.dumps(out, default=str))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
