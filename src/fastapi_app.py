"""
SkyPipe — FastAPI control plane: auth, S3/GCS intake, Spark processing, DuckDB warehouse.
"""

from __future__ import annotations

import logging
import os
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("skypipe.api")

_SRC = os.path.dirname(os.path.abspath(__file__))
if _SRC not in __import__("sys").path:
    __import__("sys").path.insert(0, _SRC)

_SKYPIPE_ROOT = os.path.abspath(os.path.join(_SRC, ".."))
_ENV_FILE = os.path.join(_SKYPIPE_ROOT, ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gcp_project: str = ""
    gcs_bucket: str = ""
    firebase_project_id: str = ""
    jwt_audience: str = ""
    max_upload_mb: int = 500
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost:8080,http://127.0.0.1:5173,http://127.0.0.1:3000,http://127.0.0.1:8080"

    s3_endpoint: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "skypipe-uploads"
    s3_use_ssl: bool = False

    local_data_root: str = ""
    duckdb_path: str = ""

    admin_username: str = "admin"
    admin_password: str = "skypipe"
    jwt_secret: str = "skypipe-dev-change-me-to-long-random-secret"
    jwt_expire_minutes: int = 720


settings = Settings()
# Defaults relative to repo when unset (local uvicorn from src/)
if not settings.local_data_root:
    settings.local_data_root = os.path.join(_SKYPIPE_ROOT, "data")
if not settings.duckdb_path:
    settings.duckdb_path = os.path.join(settings.local_data_root, "warehouse.duckdb")

app = FastAPI(title="SkyPipe API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _init_duckdb_schemas() -> None:
    """
    Guarantee layered warehouse schemas exist whenever API starts.
    This makes DB connectivity visible even before the first new upload.
    """
    try:
        import duckdb
        from warehouse_layers import ensure_schemas

        con = duckdb.connect(settings.duckdb_path)
        try:
            ensure_schemas(con)
        finally:
            con.close()
        logger.info("DuckDB startup init complete at %s", settings.duckdb_path)
    except Exception as ex:
        logger.exception("DuckDB startup init failed: %s", ex)

_jobs_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _create_jwt(subject: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": exp}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def require_user(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1].strip()
    try:
        data = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        sub = data.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Invalid token")
        return str(sub)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired") from None
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail="Invalid token") from e


@app.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest):
    if body.username != settings.admin_username or body.password != settings.admin_password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return TokenResponse(access_token=_create_jwt(body.username))


@app.get("/auth/me")
def me(user: str = Depends(require_user)):
    return {"username": user, "role": "admin", "display_welcome": f"Welcome {user.title()}"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "skypipe-api"}


@app.get("/v1/architecture")
def architecture_overview(_user: str = Depends(require_user)):
    """High-level architecture summary for UI stage cards."""
    return {
        "input_stage": {
            "requirement": "Distributed object storage",
            "implementation": (
                "MinIO with the S3 API in Docker when storage credentials are configured, "
                "or Google Cloud Storage in cloud mode, "
                "or local data folder for offline demos."
            ),
        },
        "processing_stage": {
            "requirement": "Parallel processing engine",
            "implementation": "Apache PySpark (local[*] or Dataproc in cloud).",
        },
        "result_stage": {
            "requirement": "Analytical data warehouse (columnar SQL, marts)",
            "implementation": (
                "DuckDB file (warehouse.duckdb): Spark job summaries plus layered schemas "
                "(raw_data → processed → analytics, optional dim/fact) written on each successful upload."
            ),
        },
    }


@app.get("/v1/capabilities")
def capabilities_overview(_user: str = Depends(require_user)):
    """Operational capabilities for scalability, resilience, and security."""
    return {
        "scalability": {
            "title": "Scalability analysis",
            "summary": "Spark processing scales from local mode to clustered execution as load increases.",
            "details": [
                "Spark uses parallel tasks for profiling and aggregation operations.",
                "SPARK_MASTER can point to local mode or a cluster manager.",
                "Input files are stored in object storage so multiple workers can read in parallel.",
            ],
        },
        "fault_tolerance": {
            "title": "Fault tolerance mechanisms",
            "summary": "Each job is isolated, tracked, and safely marked as completed or failed.",
            "details": [
                "Job state is tracked with progress and status transitions in the API.",
                "Errors are captured and written to job status without crashing the service.",
                "DuckDB persistence stores completed run summaries for recovery and replay.",
            ],
        },
        "security": {
            "title": "Security configuration",
            "summary": "Access control, upload validation, and secure storage controls are enforced by default.",
            "details": [
                "JWT protected endpoints require authenticated users.",
                "Uploads are validated for allowed file extensions and maximum size limits.",
                "Storage credentials are provided through environment variables and not hardcoded.",
            ],
        },
    }


class JobCreateResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress_pct: float
    updated_at: str
    object_uri: str | None = None
    error: str | None = None


def _run_spark_job(job_id: str, local_path: str, filename: str, fmt: str, object_uri: str | None) -> None:
    from pipeline_narrative import processing_stage_cards, results_stage_cards
    from schema_detector import build_schema_profile
    from spark_pipeline import adaptive_analytics, build_spark_session, load_dataframe
    from warehouse_duckdb import persist_run

    input_label = ""
    input_detail = ""
    logical_uri = ""
    with _jobs_lock:
        j = _jobs.get(job_id, {})
        input_label = j.get("input_stage_label", "")
        input_detail = j.get("input_stage_detail", "")
        logical_uri = j.get("input_logical_uri", "")

    warehouse_type = "DuckDB (embedded analytical warehouse)"
    warehouse_detail = (
        f"Aggregated metrics for this job are stored in DuckDB at {settings.duckdb_path}. "
        "The warehouse keeps durable summary data for analytics."
    )

    try:
        with _jobs_lock:
            _jobs[job_id]["status"] = "running"
            _jobs[job_id]["progress_pct"] = 10.0
            _jobs[job_id]["updated_at"] = _utc_now_iso()
            _jobs[job_id]["processing_cards"] = processing_stage_cards(
                None, [], [], []
            )

        spark = build_spark_session(f"SkyPipe-{job_id}")
        try:
            df = load_dataframe(spark, local_path, fmt)
            with _jobs_lock:
                _jobs[job_id]["progress_pct"] = 40.0
            profile = build_schema_profile(df)
            with _jobs_lock:
                _jobs[job_id]["progress_pct"] = 55.0
                _jobs[job_id]["detected_schema"] = {
                    "numeric": profile.numeric_columns,
                    "categorical": profile.categorical_columns,
                    "datetime": profile.datetime_columns,
                    "boolean": profile.boolean_columns,
                }
                _jobs[job_id]["processing_cards"] = processing_stage_cards(
                    None,
                    profile.numeric_columns,
                    profile.categorical_columns,
                    profile.datetime_columns,
                )
            summary = adaptive_analytics(df, profile=profile)
            with _jobs_lock:
                _jobs[job_id]["progress_pct"] = 85.0
                _jobs[job_id]["result"] = summary
                rc = summary.get("row_count")
                _jobs[job_id]["processing_cards"] = processing_stage_cards(
                    rc,
                    profile.numeric_columns,
                    profile.categorical_columns,
                    profile.datetime_columns,
                )
        finally:
            spark.stop()

        logical = logical_uri or object_uri or f"file://{local_path}"
        try:
            persist_run(
                settings.duckdb_path,
                job_id=job_id,
                filename=filename,
                fmt=fmt,
                input_storage_uri=logical,
                input_stage_label=input_label,
                row_count=summary.get("row_count"),
                status=str(summary.get("status", "ok")),
                warehouse_type=warehouse_type,
                warehouse_detail=warehouse_detail,
                bq_table=None,
                result=summary,
            )
        except Exception as wex:
            logger.exception("DuckDB warehouse persist failed: %s", wex)

        from pipeline_narrative import warehouse_layer_cards
        from warehouse_layers import run_pipeline

        layer_result: dict[str, Any] | None = None
        try:
            layer_result = run_pipeline(
                file_path=local_path,
                db_path=settings.duckdb_path,
                fmt=fmt,
                job_id=job_id,
                filename=filename,
            )
        except Exception as lex:
            logger.exception("Layered warehouse failed: %s", lex)
            layer_result = {"ok": False, "error": str(lex)}

        with _jobs_lock:
            _jobs[job_id]["warehouse_type"] = warehouse_type
            _jobs[job_id]["warehouse_detail"] = warehouse_detail
            _jobs[job_id]["warehouse_layers"] = layer_result
            base_cards = results_stage_cards(
                warehouse_detail,
                settings.duckdb_path,
                summary.get("row_count"),
            )
            _jobs[job_id]["results_cards"] = base_cards + warehouse_layer_cards(layer_result)
            _jobs[job_id]["status"] = "completed"
            _jobs[job_id]["progress_pct"] = 100.0
            _jobs[job_id]["updated_at"] = _utc_now_iso()
    except Exception as e:
        logger.exception("Job %s failed", job_id)
        with _jobs_lock:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["error"] = str(e)
            _jobs[job_id]["updated_at"] = _utc_now_iso()


@app.post("/v1/jobs", response_model=JobCreateResponse)
async def create_job(
    file: UploadFile = File(...),
    _user: str = Depends(require_user),
):
    from gcp_utils import detect_format_from_filename, new_job_id, sniff_format_from_bytes, validate_upload_filename
    from storage_pipeline import describe_input_uri, upload_input_bytes

    raw = await file.read()
    max_b = settings.max_upload_mb * 1024 * 1024
    if len(raw) > max_b:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb} MB limit")

    ok, name_or_err = validate_upload_filename(file.filename or "upload")
    if not ok:
        raise HTTPException(status_code=400, detail=name_or_err)
    safe_name = name_or_err

    fmt = sniff_format_from_bytes(safe_name, raw[:4096])
    if fmt == "unknown":
        fmt = detect_format_from_filename(safe_name)
    if fmt == "unknown":
        raise HTTPException(status_code=400, detail="Could not detect file format")

    job_id = new_job_id()
    object_uri, stage_label, stage_detail = upload_input_bytes(
        job_id,
        safe_name,
        raw,
        s3_endpoint=settings.s3_endpoint or None,
        s3_access_key=settings.s3_access_key or None,
        s3_secret_key=settings.s3_secret_key or None,
        s3_bucket=settings.s3_bucket or None,
        s3_use_ssl=settings.s3_use_ssl,
        gcs_bucket=settings.gcs_bucket or None,
        gcp_project=settings.gcp_project or None,
        local_data_root=settings.local_data_root,
    )

    suffix = os.path.splitext(safe_name)[1]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(raw)
    tmp.close()
    local_path = tmp.name
    logical_uri = describe_input_uri(object_uri, local_path)

    from pipeline_narrative import input_stage_cards

    with _jobs_lock:
        _jobs[job_id] = {
            "status": "queued",
            "progress_pct": 0.0,
            "updated_at": _utc_now_iso(),
            "object_uri": object_uri,
            "input_logical_uri": logical_uri,
            "input_stage_label": stage_label,
            "input_stage_detail": stage_detail,
            "input_cards": input_stage_cards(stage_label, stage_detail, logical_uri, safe_name, fmt),
            "local_path": local_path,
            "filename": safe_name,
            "format": fmt,
            "result": None,
            "error": None,
            "detected_schema": None,
            "processing_cards": [],
            "results_cards": [],
            "warehouse_type": "",
            "warehouse_detail": "",
            "warehouse_layers": None,
        }

    worker = threading.Thread(
        target=_run_spark_job,
        args=(job_id, local_path, safe_name, fmt, object_uri),
        daemon=True,
        name=f"skypipe-job-{job_id[:8]}",
    )
    worker.start()

    return JobCreateResponse(job_id=job_id, status="queued", message="Job accepted")


@app.get("/v1/jobs/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str, _user: str = Depends(require_user)):
    with _jobs_lock:
        j = _jobs.get(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    return JobStatusResponse(
        job_id=job_id,
        status=j["status"],
        progress_pct=float(j["progress_pct"]),
        updated_at=j["updated_at"],
        object_uri=j.get("object_uri") or j.get("input_logical_uri"),
        error=j.get("error"),
    )


@app.get("/v1/jobs/{job_id}/schema")
def get_job_schema(job_id: str, _user: str = Depends(require_user)):
    with _jobs_lock:
        j = _jobs.get(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    return {"job_id": job_id, "detected_schema": j.get("detected_schema"), "status": j["status"]}


@app.get("/v1/jobs/{job_id}/results")
def get_job_results(job_id: str, _user: str = Depends(require_user)):
    with _jobs_lock:
        j = _jobs.get(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    if j["status"] != "completed":
        raise HTTPException(status_code=409, detail=f"Job not completed: {j['status']}")
    return {
        "job_id": job_id,
        "result": j.get("result"),
        "duckdb_path": settings.duckdb_path,
        "warehouse": {
            "type": j.get("warehouse_type"),
            "detail": j.get("warehouse_detail"),
        },
        "warehouse_layers": j.get("warehouse_layers"),
    }


@app.get("/v1/jobs/{job_id}/story")
def get_job_story(job_id: str, _user: str = Depends(require_user)):
    """Non-technical narrative + exam-oriented storage explanation."""
    from pipeline_narrative import chart_insights

    with _jobs_lock:
        j = _jobs.get(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    out: dict[str, Any] = {
        "job_id": job_id,
        "status": j["status"],
        "input_cards": j.get("input_cards") or [],
        "processing_cards": j.get("processing_cards") or [],
        "results_cards": j.get("results_cards") or [],
        "chart_insights": [],
        "storage_summary": {
            "input_uri": j.get("input_logical_uri"),
            "input_stage": j.get("input_stage_label"),
            "warehouse_file": settings.duckdb_path,
            "layered_warehouse": j.get("warehouse_layers"),
            "note": "DuckDB stores job summaries and layered raw/processed/analytics tables per upload.",
        },
    }
    if j.get("result"):
        out["chart_insights"] = chart_insights(j["result"])
    return out


@app.get("/v1/jobs/{job_id}/download-url")
def get_signed_download(job_id: str, _user: str = Depends(require_user)):
    from gcp_utils import generate_signed_url_read

    with _jobs_lock:
        j = _jobs.get(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    uri = j.get("object_uri")
    if not uri or not uri.startswith("gs://"):
        raise HTTPException(status_code=404, detail="No GCS object for signed URL")
    if not settings.gcs_bucket:
        raise HTTPException(status_code=503, detail="GCS not configured")
    _, rest = uri.split("gs://", 1)
    bucket, obj = rest.split("/", 1)
    url = generate_signed_url_read(bucket, obj, expiration_minutes=30)
    return {"url": url, "expires_in_minutes": 30}
