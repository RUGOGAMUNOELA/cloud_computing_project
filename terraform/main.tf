locals {
  sa_id = "skypipe-pipeline"
}

resource "google_service_account" "skypipe" {
  account_id   = local.sa_id
  display_name = "SkyPipe pipeline (least privilege)"
}

resource "google_storage_bucket" "skypipe_data" {
  name                        = var.bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false

  # Default Google-managed encryption at rest (no CMEK). Add google_kms_crypto_key for CMEK.

  versioning {
    enabled = true
  }
}

resource "google_storage_bucket_iam_member" "skypipe_object_admin" {
  bucket = google_storage_bucket.skypipe_data.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.skypipe.email}"
}

resource "google_bigquery_dataset" "skypipe" {
  dataset_id                 = var.bq_dataset
  location                   = var.bq_location
  description                = "SkyPipe adaptive analytics outputs"
  delete_contents_on_destroy = false
}

resource "google_project_iam_member" "skypipe_bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.skypipe.email}"
}

resource "google_project_iam_member" "skypipe_bq_data_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.skypipe.email}"
}

resource "google_dataproc_cluster" "skypipe" {
  count  = var.create_dataproc_cluster ? 1 : 0
  name   = "skypipe-spark"
  region = var.region

  cluster_config {
    staging_bucket = google_storage_bucket.skypipe_data.name

    gce_cluster_config {
      zone = var.dataproc_zone

      service_account = google_service_account.skypipe.email
      # Shielded VMs and internal IP hardening can be enabled per org policy
    }

    master_config {
      num_instances = 1
      machine_type  = "n1-standard-2"
      disk_config {
        boot_disk_size_gb = 50
      }
    }

    worker_config {
      num_instances = 2
      machine_type  = "n1-standard-2"
      disk_config {
        boot_disk_size_gb = 50
      }
    }

    software_config {
      image_version = "2.2-debian12"
      optional_components = [
        "JUPYTER",
        "ZEPPELIN"
      ]
    }
  }
}
