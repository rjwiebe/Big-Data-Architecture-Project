#!/usr/bin/env bash

set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID to your GCP project id.}"
: "${REGION:?Set REGION to your Cloud Run region.}"
: "${JOB_NAME:?Set JOB_NAME to your Cloud Run Job name.}"
: "${POSTGRES_DSN_SECRET:?Set POSTGRES_DSN_SECRET to the Secret Manager secret name for POSTGRES_DSN.}"

AR_REPO="${AR_REPO:-rtd-containers}"
IMAGE_NAME="${IMAGE_NAME:-${JOB_NAME}}"
IMAGE_TAG="${IMAGE_TAG:-$(date +%Y%m%d%H%M%S)}"
RUNTIME_SERVICE_ACCOUNT="${RUNTIME_SERVICE_ACCOUNT:-${JOB_NAME}-runtime@${PROJECT_ID}.iam.gserviceaccount.com}"
SCHEDULER_SERVICE_ACCOUNT="${SCHEDULER_SERVICE_ACCOUNT:-${JOB_NAME}-scheduler@${PROJECT_ID}.iam.gserviceaccount.com}"
SCHEDULER_JOB_NAME="${SCHEDULER_JOB_NAME:-${JOB_NAME}-schedule}"
SCHEDULER_LOCATION="${SCHEDULER_LOCATION:-${REGION}}"
SCHEDULE="${SCHEDULE:-0 3 1 * *}"
TIME_ZONE="${TIME_ZONE:-America/Denver}"
TASK_TIMEOUT="${TASK_TIMEOUT:-3600s}"
STATIC_GTFS_URLS="${STATIC_GTFS_URLS:-https://www.rtd-denver.com/files/gtfs/google_transit.zip|https://www.rtd-denver.com/files/gtfs/google_transit_flex.zip|https://www.rtd-denver.com/files/gtfs/bustang-co-us.zip}"
DOWNLOAD_TIMEOUT_SECONDS="${DOWNLOAD_TIMEOUT_SECONDS:-120}"
VPC_EGRESS="${VPC_EGRESS:-private-ranges-only}"

SUBSTITUTIONS=(
  "_REGION=${REGION}"
  "_JOB_NAME=${JOB_NAME}"
  "_AR_REPO=${AR_REPO}"
  "_IMAGE_NAME=${IMAGE_NAME}"
  "_IMAGE_TAG=${IMAGE_TAG}"
  "_POSTGRES_DSN_SECRET=${POSTGRES_DSN_SECRET}"
  "_RUNTIME_SERVICE_ACCOUNT=${RUNTIME_SERVICE_ACCOUNT}"
  "_SCHEDULER_SERVICE_ACCOUNT=${SCHEDULER_SERVICE_ACCOUNT}"
  "_SCHEDULER_JOB_NAME=${SCHEDULER_JOB_NAME}"
  "_SCHEDULER_LOCATION=${SCHEDULER_LOCATION}"
  "_SCHEDULE=${SCHEDULE}"
  "_TIME_ZONE=${TIME_ZONE}"
  "_TASK_TIMEOUT=${TASK_TIMEOUT}"
  "_STATIC_GTFS_URLS=${STATIC_GTFS_URLS}"
  "_DOWNLOAD_TIMEOUT_SECONDS=${DOWNLOAD_TIMEOUT_SECONDS}"
)

if [[ -n "${VPC_NETWORK:-}" ]]; then
  SUBSTITUTIONS+=("_VPC_NETWORK=${VPC_NETWORK}")
fi

if [[ -n "${VPC_SUBNET:-}" ]]; then
  SUBSTITUTIONS+=("_VPC_SUBNET=${VPC_SUBNET}")
fi

if [[ -n "${VPC_NETWORK:-}" || -n "${VPC_SUBNET:-}" ]]; then
  SUBSTITUTIONS+=("_VPC_EGRESS=${VPC_EGRESS}")
fi

gcloud builds submit \
  --project "${PROJECT_ID}" \
  --config cloudbuild.static_gtfs.deploy.yaml \
  --substitutions "$(IFS=,; echo "${SUBSTITUTIONS[*]}")" \
  .
