variable "project_id" {
  type        = string
  description = "GCP project ID for SkyPipe"
}

variable "region" {
  type        = string
  default     = "us-central1"
  description = "Default region for regional resources"
}

variable "bucket_name" {
  type        = string
  description = "Globally unique GCS bucket name for uploads and checkpoints"
}

variable "bq_dataset" {
  type        = string
  default     = "skypipe"
  description = "BigQuery dataset for analytics outputs and metadata"
}

variable "bq_location" {
  type        = string
  default     = "US"
  description = "BigQuery dataset location"
}

variable "create_dataproc_cluster" {
  type        = bool
  default     = false
  description = "If true, provision a minimal Dataproc cluster (costs apply)"
}

variable "dataproc_zone" {
  type        = string
  default     = "us-central1-a"
  description = "Zone for Dataproc workers"
}
