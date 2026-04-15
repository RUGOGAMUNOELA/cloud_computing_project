# System Design Document
**SkyPipe - Distributed Data Processing Pipeline**

## 1. Architectural Overview

```
                         Browser
                            |
                            v
                 React UI served by Nginx
                            |
             +--------------+--------------+
             |                             |
             v                             v
       /auth and /v1                  Static frontend
     reverse-proxied to API              assets
             |
             v
      FastAPI Control Plane
   (auth, upload, jobs, results)
             |
             +------------------------------+
             |                              |
             v                              v
   Distributed Input Storage          Spark Processing Engine
 (MinIO S3 API or optional GCS)    (schema detection + analytics)
             |                              |
             +--------------+---------------+
                            |
                            v
                 DuckDB Warehouse File
             warehouse.duckdb persistent store
        schemas: raw_data, processed, analytics
```

This architecture satisfies the exam requirement for:
- distributed input storage
- parallel processing stage
- warehouse result store

## 2. Stage by Stage Design

### 2.1 Input Stage
- Uploads are received by FastAPI.
- Objects are written to MinIO by default through S3 API.
- Optional cloud mode writes to Google Cloud Storage.
- Local fallback exists for offline development.

### 2.2 Processing Stage
- Spark loads datasets in CSV, JSON, Excel, or Parquet format.
- `schema_detector.py` classifies column types.
- `spark_pipeline.py` computes adaptive statistics:
  - numeric summaries
  - categorical top values
  - datetime trends

### 2.3 Result Store Stage
- Results are persisted in DuckDB:
  - `main.skypipe_analytics_runs` for run summary history
  - layered warehouse tables in:
    - `raw_data`
    - `processed`
    - `analytics`
- Optional star schema style dimension and fact tables are generated per run where applicable.

## 3. MapReduce and Distributed Concepts
| Concept | SkyPipe realization |
|--------|----------------------|
| Map | Column projections, type parsing, row transformations |
| Reduce | `groupBy`, `count`, `avg`, `min`, `max`, frequency aggregations |
| Shuffle | Spark repartition and grouped computation exchange |
| Parallelism | Spark executor tasks operate on partitions concurrently |

## 4. Scalability Analysis
- Object storage enables shared reads by multiple workers.
- Spark runtime can scale from local mode to cluster mode.
- Containerized service separation isolates concerns and supports horizontal expansion.
- Analytics are pre-aggregated into DuckDB warehouse tables to reduce repeated compute cost.

## 5. Fault Tolerance Mechanisms
- Job lifecycle tracked per `job_id` with explicit statuses.
- Failures are captured and surfaced without crashing the API service.
- Processing runs in background worker threads so request handling stays responsive.
- Completed job summaries remain persisted in DuckDB for recovery and audit.

## 6. Security Configuration
- JWT authentication protects private API routes.
- Upload validation enforces safe filename and file size constraints.
- Credentials for storage access are provided from environment variables.
- Nginx acts as gateway boundary for UI and API route exposure.

## 7. Component Responsibilities

### `fastapi_app.py`
- Auth endpoints
- Upload endpoint and job orchestration
- Job status, story, and results APIs
- Startup initialization for DuckDB schemas

### `storage_pipeline.py`
- Upload routing to MinIO, GCS, or local fallback
- Logical URI description returned to API

### `schema_detector.py`
- Automatic schema profiling for adaptive analytics

### `spark_pipeline.py`
- Spark session creation
- Dataframe loading per format
- Adaptive aggregation engine

### `warehouse_layers.py`
- End to end warehouse flow:
  - ensure schemas
  - raw load
  - processing cleanup
  - analytics aggregation
  - verification output

### `warehouse_duckdb.py`
- Persist and retrieve summary records from run history table

## 8. Deployment and Virtualization
- Docker Compose services:
  - `skypipe-web` (Nginx + React)
  - `skypipe-api` (FastAPI + Spark runtime)
  - `minio` (object store)
- Shared volume persists DuckDB and uploaded artifacts.

## 9. Exam Evidence Checklist
- System architecture diagram: included above with frontend, gateway, server, storage.
- Scalability analysis: section 4.
- Fault tolerance mechanisms: section 5.
- Security configuration: section 6.

---
*End of System Design*
