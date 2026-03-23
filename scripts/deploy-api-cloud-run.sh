#!/usr/bin/env bash

set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID to your GCP project id.}"
: "${REGION:?Set REGION to your Cloud Run region.}"
: "${SERVICE_NAME:?Set SERVICE_NAME to your Cloud Run service name.}"
: "${POSTGRES_DSN_SECRET:?Set POSTGRES_DSN_SECRET to the Secret Manager secret name for POSTGRES_DSN.}"

IMAGE_TAG="${IMAGE_TAG:-$(date +%Y%m%d%H%M%S)}"
IMAGE_URI="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:${IMAGE_TAG}"

gcloud builds submit --project "${PROJECT_ID}" --tag "${IMAGE_URI}" .

DEPLOY_CMD=(
  gcloud run deploy "${SERVICE_NAME}"
  --project "${PROJECT_ID}"
  --region "${REGION}"
  --platform managed
  --image "${IMAGE_URI}"
  --allow-unauthenticated
  --set-secrets "POSTGRES_DSN=${POSTGRES_DSN_SECRET}:latest"
)

if [[ -n "${REDIS_URL_SECRET:-}" ]]; then
  DEPLOY_CMD+=(--set-secrets "REDIS_URL=${REDIS_URL_SECRET}:latest")
fi

if [[ -n "${ALLOWED_ORIGINS:-}" ]]; then
  DEPLOY_CMD+=(--set-env-vars "ALLOWED_ORIGINS=${ALLOWED_ORIGINS}")
fi

"${DEPLOY_CMD[@]}"
