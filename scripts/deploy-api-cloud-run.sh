#!/usr/bin/env bash

set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID to your GCP project id.}"
: "${REGION:?Set REGION to your Cloud Run region.}"
: "${SERVICE_NAME:?Set SERVICE_NAME to your Cloud Run service name.}"
: "${POSTGRES_DSN_SECRET:?Set POSTGRES_DSN_SECRET to the Secret Manager secret name for POSTGRES_DSN.}"

AR_REPO="${AR_REPO:-rtd-containers}"
IMAGE_NAME="${IMAGE_NAME:-${SERVICE_NAME}}"
IMAGE_TAG="${IMAGE_TAG:-$(date +%Y%m%d%H%M%S)}"
RUNTIME_SERVICE_ACCOUNT="${RUNTIME_SERVICE_ACCOUNT:-${SERVICE_NAME}-runtime@${PROJECT_ID}.iam.gserviceaccount.com}"
VPC_EGRESS="${VPC_EGRESS:-private-ranges-only}"

SUBSTITUTIONS=(
  "_REGION=${REGION}"
  "_SERVICE_NAME=${SERVICE_NAME}"
  "_AR_REPO=${AR_REPO}"
  "_IMAGE_NAME=${IMAGE_NAME}"
  "_IMAGE_TAG=${IMAGE_TAG}"
  "_POSTGRES_DSN_SECRET=${POSTGRES_DSN_SECRET}"
  "_RUNTIME_SERVICE_ACCOUNT=${RUNTIME_SERVICE_ACCOUNT}"
)

if [[ -n "${REDIS_URL_SECRET:-}" ]]; then
  SUBSTITUTIONS+=("_REDIS_URL_SECRET=${REDIS_URL_SECRET}")
fi

if [[ -n "${ALLOWED_ORIGINS:-}" ]]; then
  SUBSTITUTIONS+=("_ALLOWED_ORIGINS=${ALLOWED_ORIGINS}")
fi

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
  --config cloudbuild.deploy.yaml \
  --substitutions "$(IFS=,; echo "${SUBSTITUTIONS[*]}")" \
  .
