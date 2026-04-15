output "bucket_name" {
  value       = google_storage_bucket.skypipe_data.name
  description = "Upload and checkpoint bucket"
}

output "service_account_email" {
  value       = google_service_account.skypipe.email
  description = "Attach this SA to Dataproc / GKE workers or use key for local dev (prefer WIF)"
}

output "bigquery_dataset" {
  value       = google_bigquery_dataset.skypipe.dataset_id
  description = "Dataset for flattened analytics tables"
}

output "dataproc_cluster_name" {
  value       = try(google_dataproc_cluster.skypipe[0].name, null)
  description = "Dataproc cluster name if created"
}
