# Course Concepts — SkyPipe Mapping (Defense Cheatsheet)

## How does SkyPipe handle **any** dataset?
- Data is loaded into a Spark `DataFrame` with **schema inference** (CSV/JSON) or native types (Parquet).
- `schema_detector` builds a **profile** of column roles without using domain-specific names.
- `adaptive_analytics` only runs operations that match the profile, so the same code path supports sales, health, IoT, or exam sample CSVs.

## How is schema detected automatically?
- **Structural:** Spark `StructField` types map to numeric, string, boolean, date/timestamp.
- **Heuristic:** String columns are sampled; if many values parse as timestamps, they are treated as temporal for trend analytics.
- **Cardinality:** Low-distinct numerics may be analyzed as categorical top-N (configurable).

## How does Spark process unknown structures?
- Spark’s **lazy** DAG applies operations after analysis planning; unknown columns are just names in the schema.
- Aggregations reference columns **by name lists** produced at runtime, not compile-time constants.

## Scalability regardless of dataset size
- **Partitioned reads** for CSV/JSON/Parquet across executors.
- **Shuffle partitions** tunable via `spark.sql.shuffle.partitions`.
- **Horizontal scaling:** add Dataproc workers → more CPU/memory for map and reduce stages.
- **Storage:** GCS holds arbitrarily large objects; Spark streams/chunks reads without loading full file on driver (except moderate Excel via Pandas — documented trade-off).

## MapReduce → PySpark
- **Map:** column expressions (`F.col`, `to_timestamp`, projections).
- **Reduce:** `groupBy`, `agg`, `count`, ordering, `limit` for top-K.

## RPC / RMI analogy
- FastAPI endpoints act as **remote procedures**: `create_job`, `get_job`, `get_results` with JSON contracts — same conceptual model as RPC (without Java RMI wire protocol).

## Fault tolerance
- `spark.task.maxFailures`, `spark.speculation=true`.
- Optional `DataFrame.checkpoint()` for lineage truncation and recovery.

## Load balancing
- On cluster: **cluster manager** distributes Spark tasks across executors (parallelism analogous to load balancing layers distributing HTTP requests).

## Virtualization
- **Containers:** Docker images for reproducible environments.
- **VMs:** Dataproc nodes run isolated guest OS instances.

## Security (exam checklist)
- Firebase (optional) + **signed URLs** + **upload validation** + **IAM least privilege** + **encryption at rest** (GCS/BQ defaults).
