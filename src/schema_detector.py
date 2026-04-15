"""
SkyPipe — Smart Adaptive Processing: automatic schema and column-type detection.

Classifies columns as numeric, categorical, or temporal for dynamic PySpark analytics.
Works for any structured tabular dataset loaded into a Spark DataFrame.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    BooleanType,
    ByteType,
    DateType,
    DecimalType,
    DoubleType,
    FloatType,
    IntegerType,
    LongType,
    ShortType,
    StringType,
    StructType,
    TimestampNTZType,
    TimestampType,
)


NUMERIC_TYPES = (
    ByteType,
    ShortType,
    IntegerType,
    LongType,
    FloatType,
    DoubleType,
    DecimalType,
)
DATE_TYPES = (DateType, TimestampType, TimestampNTZType)


@dataclass
class SchemaProfile:
    """Detected schema profile for adaptive pipeline configuration."""

    all_columns: list[str]
    numeric_columns: list[str]
    categorical_columns: list[str]
    datetime_columns: list[str]
    boolean_columns: list[str]
    row_count_estimate: int | None = None
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "all_columns": self.all_columns,
            "numeric_columns": self.numeric_columns,
            "categorical_columns": self.categorical_columns,
            "datetime_columns": self.datetime_columns,
            "boolean_columns": self.boolean_columns,
            "row_count_estimate": self.row_count_estimate,
            "issues": self.issues,
        }


def _is_numeric_type(dt) -> bool:
    return isinstance(dt, NUMERIC_TYPES)


def _is_date_type(dt) -> bool:
    return isinstance(dt, DATE_TYPES)


def _is_boolean_type(dt) -> bool:
    return isinstance(dt, BooleanType)


def detect_column_types_from_schema(schema: StructType) -> dict[str, str]:
    """
    Map column name -> coarse type: 'numeric' | 'categorical' | 'datetime' | 'boolean'.
    """
    mapping: dict[str, str] = {}
    for fld in schema.fields:
        name = fld.name
        dt = fld.dataType
        if _is_boolean_type(dt):
            mapping[name] = "boolean"
        elif _is_numeric_type(dt):
            mapping[name] = "numeric"
        elif _is_date_type(dt):
            mapping[name] = "datetime"
        elif isinstance(dt, StringType):
            mapping[name] = "categorical"
        else:
            mapping[name] = "categorical"
    return mapping


def infer_datetime_columns(df: DataFrame, sample_rows: int = 500) -> set[str]:
    """
    Heuristic: string columns that parse as timestamps become datetime for analytics.
    """
    string_cols = [f.name for f in df.schema.fields if isinstance(f.dataType, StringType)]
    if not string_cols:
        return set()
    sample = df.limit(sample_rows)
    detected: set[str] = set()
    for col in string_cols:
        try:
            parsed = F.to_timestamp(F.col(col))
            non_null = sample.select(parsed.alias("_ts")).filter(F.col("_ts").isNotNull()).limit(1).count()
            if non_null > 0:
                detected.add(col)
        except Exception:
            continue
    return detected


def build_schema_profile(df: DataFrame, categorical_max_distinct: int = 200) -> SchemaProfile:
    """
    Build a full profile: numeric / categorical / datetime / boolean.

    Categorical heuristic: non-numeric, non-datetime columns with moderate cardinality
    (or explicit strings). High-cardinality strings stay as categorical for top-N freq.
    """
    schema = df.schema
    col_types = detect_column_types_from_schema(schema)
    datetime_from_strings = infer_datetime_columns(df)
    issues: list[str] = []

    numeric: list[str] = []
    categorical: list[str] = []
    datetime_cols: list[str] = []
    boolean_cols: list[str] = []

    for name, kind in col_types.items():
        if kind == "boolean":
            boolean_cols.append(name)
        elif kind == "numeric":
            numeric.append(name)
        elif kind == "datetime" or name in datetime_from_strings:
            datetime_cols.append(name)
        else:
            categorical.append(name)

    # Reclassify: strings promoted to datetime should not remain only in categorical
    for c in datetime_from_strings:
        if c in categorical:
            categorical.remove(c)
        if c not in datetime_cols:
            datetime_cols.append(c)

    # Optional: treat low-cardinality numerics as categorical for frequency (exam flexibility)
    for n in list(numeric):
        try:
            d = df.select(n).distinct().count()
            if d <= categorical_max_distinct and d > 0:
                numeric.remove(n)
                if n not in categorical:
                    categorical.append(n)
        except Exception as e:
            issues.append(f"distinct check failed for {n}: {e}")

    all_cols = [f.name for f in schema.fields]
    return SchemaProfile(
        all_columns=all_cols,
        numeric_columns=numeric,
        categorical_columns=categorical,
        datetime_columns=datetime_cols,
        boolean_columns=boolean_cols,
        issues=issues,
    )


def validate_minimum_schema(profile: SchemaProfile) -> tuple[bool, list[str]]:
    """Ensure there is at least one analyzable column."""
    errors: list[str] = []
    if not profile.all_columns:
        errors.append("Dataset has no columns.")
    return len(errors) == 0, errors
