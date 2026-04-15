# SkyPipe

**Generalized Scalable Distributed Data Processing Pipeline on Google Cloud Platform**

SkyPipe ingests **any structured tabular dataset** (CSV, XLSX, JSON, Parquet), **auto-detects schema and column roles**, runs **adaptive PySpark analytics** (MapReduce-style), stores raw files in **S3-compatible storage (MinIO)** or optional **GCS**, and persists aggregates in **DuckDB** (`warehouse.duckdb`). The **React** UI talks to **FastAPI**. **Terraform** provisions optional GCP resources; **Docker** runs the default stack. For a **standalone layered warehouse demo** (raw / processed / analytics + star schema), run `python duckdb_warehouse_pipeline.py` from the `skypipe/` folder.

> **DSC3219 (UCU, Easter 2026)** — demonstrates MapReduce, distributed Spark, RPC-style APIs, virtualization, fault tolerance, scalability, and GCP security patterns **without hardcoding a specific dataset**.

## Features

| Capability | Implementation |
|------------|----------------|
| Multi-format ingest | Spark readers + Pandas bridge for Excel |
| Schema detection | `schema_detector.py` (numeric / categorical / datetime / boolean) |
| Adaptive analytics | `spark_pipeline.py` — stats match detected types |
| GCS storage | Upload + versioning-friendly object layout |
| DuckDB warehouse | Job summaries in `data/warehouse.duckdb`; optional `duckdb_warehouse_pipeline.py` for layered schemas |
| Security | Optional Firebase token verification, signed URLs, IAM, upload validation |
| IaC | `terraform/` — bucket, dataset, SA, optional Dataproc |

## Repository layout

```
skypipe/
├── README.md
├── requirements.txt
├── docker-compose.yml
├── .env.example
├── terraform/
├── docker/
├── src/
│   ├── fastapi_app.py
│   ├── spark_pipeline.py
│   ├── gcp_utils.py
│   ├── schema_detector.py
│   └── data/
├── docs/           # SRS, system design, concepts
├── report/
├── frontend/          # React (Vite) UI
├── presentation/
└── notebooks/
```

## Quick start (local, no GCP)

1. **Python 3.10+** (3.10–3.12 recommended; Spark wheels may lag newest Python) and **Java 17** (required for Spark).

   **Windows PowerShell** (venv activation is *not* the bare word `activate`):

   ```powershell
   cd skypipe
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

   If `Activate.ps1` is blocked by execution policy:

   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
   ```

   **Command Prompt (cmd.exe):** `.\.venv\Scripts\activate.bat`

   If `pip install` was **cancelled or failed**, run `pip install -r requirements.txt` again until it finishes. Optional GCS uploads need `google-cloud-storage`; you still need PySpark/Java for Spark itself.

### Java 17 (required for PySpark)

PySpark starts a **JVM**. You need a **JDK** (not only a JRE), and on Windows **`JAVA_HOME`** should point at the JDK root (the folder that contains `bin\java.exe`).

- **Install (recommended):** [Eclipse Temurin 17](https://adoptium.net/) or, in PowerShell as admin:

  ```powershell
  winget install EclipseAdoptium.Temurin.17.JDK
  ```

- **Set `JAVA_HOME` permanently:** Windows Search → “Environment Variables” → New user variable `JAVA_HOME` = e.g. `C:\Program Files\Eclipse Adoptium\jdk-17.0.18.8-hotspot` → Edit `Path` → add `%JAVA_HOME%\bin`.

- **Current PowerShell session only:**

  ```powershell
  cd skypipe
  . .\scripts\setup_java_env.ps1
  ```

`spark_pipeline.py` also **auto-detects** Temurin/Microsoft/Oracle JDKs under `Program Files` when `JAVA_HOME` is unset (Windows only). After installing Java, **open a new terminal** (or dot-source `setup_java_env.ps1`) and run the pipeline again.

2. **Run Spark pipeline on sample CSV**

   ```bash
   cd src
   python spark_pipeline.py data/sample_sales.csv
   ```

3. **API + React UI (local)**  
   Leave `GCP_PROJECT` / `GCS_BUCKET` empty unless using real GCP.

   ```bash
   cd src
   uvicorn fastapi_app:app --reload --host 0.0.0.0 --port 8000
   ```

   ```bash
   cd frontend
   npm install && npm run dev
   ```

   Open **http://localhost:5173** — login **admin** / **skypipe** (defaults). Vite proxies API calls to port 8000.

## Docker

From `skypipe/` (create `.env` from `.env.example` first):

```bash
docker compose up --build
```

- API: `http://localhost:8000/docs`  
- React UI (nginx + MinIO + DuckDB volume): `http://localhost:8080`  
- MinIO console: `http://localhost:9001` (`minioadmin` / `minioadmin`)

## Google Cloud setup

1. Copy `terraform/terraform.tfvars.example` → `terraform.tfvars` and fill values.
2. `cd terraform && terraform init && terraform apply`
3. Create a key for the `skypipe-pipeline` service account **only for dev** (prefer Workload Identity Federation in production).
4. Set `GOOGLE_APPLICATION_CREDENTIALS`, `GCP_PROJECT`, `GCS_BUCKET` in `.env`.

**Signed URLs** require the service account to have permission to sign blobs (typically `roles/iam.serviceAccountTokenCreator` on self for user-managed keys, or use impersonation — see [GCS signed URL docs](https://cloud.google.com/storage/docs/access-control/signed-urls)).

## Dataproc (distributed Spark)

1. Set `create_dataproc_cluster = true` in Terraform (mind cost).
2. Submit the same `spark_pipeline` logic packaged as a job, or SSH to cluster and run with:

   ```bash
   export SPARK_MASTER=yarn
   ```

3. Ensure **GCS connector** is on the classpath (preinstalled on Dataproc images).

## Environment variables

See `.env.example`. Highlights:

| Variable | Purpose |
|----------|---------|
| `SPARK_MASTER` | `local[*]`, `yarn`, etc. |
| `SKYPIPE_CHECKPOINT_DIR` | HDFS or `gs://` checkpoint for fault-tolerance demos |
| `SKYPIPE_CHECKPOINT_DF` | `true` to checkpoint the DataFrame mid-DAG |
| `FIREBASE_PROJECT_ID` + `JWT_AUDIENCE` | Enforce Bearer tokens on API |
| `SKYPIPE_UI_PASSWORD` | Simple Streamlit gate |

## Large files & streaming

- **CSV/JSON/Parquet:** Spark reads partitions in parallel; increase partitions for wide clusters.
- **Excel:** Moderate files use Pandas on the driver; for very large spreadsheets convert to **Parquet** or add **spark-excel** on Dataproc.

## Milestones (exam paper)

1. **SRS** → `docs/SRS.md`  
2. **System Design** → `docs/SYSTEM_DESIGN.md` + adaptive engine section  
3. **Secure Implementation** → This repo  
4. **Presentation** → `presentation/PRESENTATION.md`  
5. **Report** → `report/REPORT.md`

## Defense FAQ

See `docs/CONCEPTS.md` for concise answers on *any dataset*, schema detection, Spark on unknown structures, and scalability.

## License

Educational project — retain course attribution when submitting.
