# Software Requirements Specification (SRS)  
**Project:** SkyPipe — Generalized Scalable Distributed Data Processing Pipeline on GCP  
**Course:** DSC3219 — Cloud and Distributed Computing (Easter 2026)  
**Institution:** Uganda Christian University  

## 1. Introduction

### 1.1 Purpose
This document specifies functional and non-functional requirements for SkyPipe, a cloud-native system that ingests **arbitrary structured datasets**, performs **schema-aware adaptive analytics** using PySpark, persists results to **BigQuery**, and exposes control and reporting through **FastAPI** and **Streamlit**.

### 1.2 Scope
SkyPipe supports CSV, XLSX, JSON, and Parquet. It **must not** depend on a fixed domain schema (e.g., taxi trips). Processing logic is selected dynamically from **automatically detected column types**.

### 1.3 Definitions
- **Adaptive engine:** Component that classifies columns (numeric, categorical, datetime, boolean) and schedules Spark transformations accordingly.
- **Job:** One end-to-end execution from uploaded file to stored analytics summary.

## 2. Overall Description

### 2.1 Product Perspective
SkyPipe integrates:
- **Streamlit (SaaS-style UI)** for upload and visualization.
- **FastAPI (RPC-style API)** for job orchestration.
- **Apache Spark** for distributed MapReduce-style analytics.
- **GCS** for durable object storage.
- **BigQuery** for analytical warehouse storage.
- **Terraform** for infrastructure as code.
- **Docker** for portable deployment.

### 2.2 User Classes
- **Analyst / student:** Uploads data, runs analysis, views charts.
- **Operator:** Manages GCP projects, IAM, Dataproc clusters.

### 2.3 Operating Environment
- Python 3.10+, Java 17 for Spark.
- GCP project with billing enabled (for cloud path).
- Optional Dataproc cluster for distributed Spark.

## 3. Functional Requirements

### FR-1 — Multi-format ingest
The system shall accept CSV, XLSX/XLS, JSON, and Parquet uploads via the UI and API.

### FR-2 — **Dataset flexibility (core requirement)**
The system shall treat **any tabular structured dataset** as input. No hardcoded column names or fixed business rules shall be required for core analytics.

### FR-3 — Automatic schema and type detection
The system shall infer Spark types on load (where applicable) and refine classification into numeric, categorical, datetime (including parseable strings), and boolean columns.

### FR-4 — Adaptive analytics
- Numeric columns: count, mean, min, max, population standard deviation.
- Categorical columns: top-N frequency counts.
- Datetime columns: counts grouped by day, month, and year.

### FR-5 — MapReduce-style processing
Analytics shall be implemented as Spark **transformations** (map-like column operations) and **actions / aggregations** (reduce-like global and grouped summaries).

### FR-6 — Result persistence
Structured results shall be written to BigQuery with **dynamically created tables** per job (hash-based table id).

### FR-7 — Metadata tracking
Each job shall record filename, format, row counts, BigQuery table id, and timestamps in a metadata table.

### FR-8 — RPC API
Clients shall trigger processing and retrieve status and results via HTTP JSON endpoints.

### FR-9 — Security
- Optional **Firebase ID token** verification on API routes.
- **Signed URLs** for time-limited raw file access in GCS.
- **Input validation** on filenames, extensions, and maximum upload size.
- **Least-privilege IAM** for pipeline service accounts.

### FR-10 — Observability
Structured logging shall support debugging distributed jobs (Spark log level configurable).

## 4. Non-Functional Requirements

### NFR-1 — Scalability
Increasing dataset size shall be addressed by horizontal worker scaling on Dataproc and Spark partitioning; API remains stateless aside from in-memory job tracking (replaceable with Redis/DB).

### NFR-2 — Fault tolerance
Spark shall run with speculation and configurable task retries; optional RDD/DataFrame checkpointing for long DAGs.

### NFR-3 — Performance
Large CSV/JSON shall use Spark’s distributed readers; Excel shall use driver-side Pandas for moderate files with documented cluster alternative (spark-excel).

### NFR-4 — Security & compliance
Encryption at rest: default GCS and BigQuery encryption; optional CMEK via Terraform extension.

## 5. External Interface Requirements
- REST JSON API (`/v1/jobs`, `/health`).
- Streamlit browser UI.
- GCP APIs: Storage, BigQuery, optional Dataproc.

## 6. Milestone Traceability (Exam)
| Milestone | This SRS section |
|-----------|------------------|
| 1. SRS | §1–6 (flexibility in FR-2, FR-3) |
| 2. System Design | Informs components in companion design doc |
| 3. Secure Implementation | FR-9, NFR-4 |
| 4. Presentation | FR-2–FR-5 narrative |
| 5. Report | NFR-1–NFR-3 |

---
*End of SRS*
