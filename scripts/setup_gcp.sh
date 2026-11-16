#!/usr/bin/env bash
# Phase 0 GCP setup: APIs, GCS staging bucket, BigQuery datasets, daily query cap.
#
# Usage:
#   scripts/setup_gcp.sh            # print the commands only (default, changes nothing)
#   scripts/setup_gcp.sh --apply    # run them; safe to re-run (existing resources are skipped)
#
# Config comes from .env at the repo root (copy .env.example). Required: GCP_PROJECT.
# The $5 budget alert was created by hand in the console, so this script does not manage it.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "${repo_root}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${repo_root}/.env"
  set +a
fi

apply=false
case "${1:-}" in
  --apply) apply=true ;;
  "") ;;
  *) echo "usage: $0 [--apply]" >&2; exit 2 ;;
esac

project="${GCP_PROJECT:?set GCP_PROJECT in .env}"
location="${GCP_LOCATION:-US}"
bucket="${GCS_BUCKET:-${project}-kuairand}"
label="project:feed-exploration"
staging_file_ttl_days=14          # Parquet staging files are only needed until the load is verified
dev_table_ttl_seconds=5184000     # 60 days
# Project-wide cap on on-demand query bytes per day: 200 GiB, in MiB (the quota's unit, checked below).
query_cap_mib=204800

# GCP project IDs: 6-30 chars, lowercase letters, digits, hyphens, starting with a letter.
if [[ ! "${project}" =~ ^[a-z][a-z0-9-]{4,28}[a-z0-9]$ ]]; then
  if [[ "${apply}" == true ]]; then
    echo "error: GCP_PROJECT='${project}' is not a valid project ID (placeholder?). Nothing was changed." >&2
    exit 1
  fi
  echo "# warning: GCP_PROJECT='${project}' is not a valid project ID; printing commands only." >&2
fi

run() {
  printf '+'; printf ' %q' "$@"; printf '\n'   # shell-quoted, so printed commands can be pasted
  if [[ "${apply}" == true ]]; then
    "$@"
  fi
}

# Returns success if the resource exists. Always false in print mode, so every command is shown.
exists() {
  [[ "${apply}" == true ]] && "$@" >/dev/null 2>&1
}

echo "# project=${project} location=${location} bucket=gs://${bucket} apply=${apply}"

echo "# 1. APIs"
run gcloud services enable \
  bigquery.googleapis.com storage.googleapis.com cloudquotas.googleapis.com \
  --project="${project}"

echo "# 2. GCS staging bucket (US multi-region, private, files auto-deleted after ${staging_file_ttl_days} days)"
if exists gcloud storage buckets describe "gs://${bucket}" --project="${project}"; then
  echo "# bucket gs://${bucket} exists, skipping create"
else
  run gcloud storage buckets create "gs://${bucket}" \
    --project="${project}" \
    --location="${location}" \
    --default-storage-class=STANDARD \
    --uniform-bucket-level-access \
    --public-access-prevention
fi
lifecycle_file="$(mktemp)"
trap 'rm -f "${lifecycle_file}"' EXIT
printf '{"rule":[{"action":{"type":"Delete"},"condition":{"age":%d}}]}\n' \
  "${staging_file_ttl_days}" > "${lifecycle_file}"
run gcloud storage buckets update "gs://${bucket}" \
  --project="${project}" --lifecycle-file="${lifecycle_file}" --update-labels="project=feed-exploration"

echo "# 3. BigQuery datasets (${location})"
make_dataset() {
  local name="$1" description="$2"
  shift 2
  if exists bq show --dataset "${project}:${name}"; then
    echo "# dataset ${project}:${name} exists, skipping"
  else
    run bq --location="${location}" mk --dataset \
      --description="${description}" --label="${label}" "$@" "${project}:${name}"
  fi
}
make_dataset raw     "KuaiRand-27K as loaded from source files, plus 5% user-sample copies (*_dev5)"
make_dataset staging "dbt prod: stg_ and int_ models"
make_dataset marts   "dbt prod: fct_, dim_ and mart_ models"
make_dataset dev     "dbt dev target (5% hashed user sample); tables expire after 60 days" \
  --default_table_expiration="${dev_table_ttl_seconds}"

echo "# 4. Daily query cap: QueryUsagePerDay = ${query_cap_mib} MiB (200 GiB) for the whole project"
if [[ "${apply}" == true ]]; then
  # Refuse to set the value unless the quota is really measured in MiB.
  unit="$(gcloud quotas info describe QueryUsagePerDay \
    --service=bigquery.googleapis.com --project="${project}" --format='value(metricUnit)')"
  echo "# QueryUsagePerDay unit: ${unit}"
  if [[ "${unit}" != MiBy* ]]; then
    echo "error: unexpected unit '${unit}' for QueryUsagePerDay; not setting the cap." >&2
    exit 1
  fi
fi
run gcloud quotas preferences update bq-query-usage-per-day \
  --allow-missing \
  --service=bigquery.googleapis.com \
  --project="${project}" \
  --quota-id=QueryUsagePerDay \
  --preferred-value="${query_cap_mib}" \
  --allow-high-percentage-quota-decrease \
  --justification="Cost guard for a personal analysis project" \
  --quiet

echo "# done"
