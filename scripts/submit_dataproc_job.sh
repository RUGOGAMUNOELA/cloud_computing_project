#!/usr/bin/env bash
# Submit SkyPipe PySpark driver to an existing Dataproc cluster.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${GCP_PROJECT:?set GCP_PROJECT}"
REGION="${GCP_REGION:-us-central1}"
CLUSTER="${DATAPROC_CLUSTER_NAME:-skypipe-spark}"
BUCKET="${GCS_BUCKET:?set GCS_BUCKET}"
GCS_PATH="${1:?usage: $0 gs://bucket/path/file.csv csv}"

FMT="${2:-csv}"

cd "$ROOT"
zip -q -j skypipe_modules.zip src/schema_detector.py src/spark_pipeline.py
gsutil cp skypipe_modules.zip "gs://${BUCKET}/jobs/skypipe_modules.zip"
gsutil cp scripts/dataproc_driver.py "gs://${BUCKET}/jobs/dataproc_driver.py"

gcloud dataproc jobs submit pyspark \
  "gs://${BUCKET}/jobs/dataproc_driver.py" \
  --project="${PROJECT}" \
  --region="${REGION}" \
  --cluster="${CLUSTER}" \
  --py-files="gs://${BUCKET}/jobs/skypipe_modules.zip" \
  -- "${GCS_PATH}" "${FMT}"

rm -f skypipe_modules.zip
