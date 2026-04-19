#!/usr/bin/env bash

set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID to your GCP project id.}"

REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-rtd-api}"
AR_REPO="${AR_REPO:-rtd-containers}"
RUNTIME_SERVICE_ACCOUNT_NAME="${RUNTIME_SERVICE_ACCOUNT_NAME:-${SERVICE_NAME}-runtime}"
POSTGRES_DSN_SECRET="${POSTGRES_DSN_SECRET:-postgres-dsn}"
REDIS_URL_SECRET="${REDIS_URL_SECRET:-}"
BUILD_SERVICE_ACCOUNT="${BUILD_SERVICE_ACCOUNT:-}"
VPC_NETWORK="${VPC_NETWORK:-}"
VPC_SUBNET="${VPC_SUBNET:-}"

gcloud config set project "${PROJECT_ID}" >/dev/null

PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
if [[ -z "${BUILD_SERVICE_ACCOUNT}" ]]; then
  BUILD_SERVICE_ACCOUNT="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
fi

RUNTIME_SERVICE_ACCOUNT_EMAIL="${RUNTIME_SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
SERVERLESS_SERVICE_AGENT="service-${PROJECT_NUMBER}@serverless-robot-prod.iam.gserviceaccount.com"

ensure_secret() {
  local secret_name="$1"
  local secret_value="${2:-}"

  if ! gcloud secrets describe "${secret_name}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud secrets create "${secret_name}" \
      --project "${PROJECT_ID}" \
      --replication-policy=automatic >/dev/null
    echo "Created secret ${secret_name}"
  fi

  if [[ -n "${secret_value}" ]]; then
    printf '%s' "${secret_value}" | gcloud secrets versions add "${secret_name}" \
      --project "${PROJECT_ID}" \
      --data-file=- >/dev/null
    echo "Added a secret version to ${secret_name}"
  fi

  gcloud secrets add-iam-policy-binding "${secret_name}" \
    --project "${PROJECT_ID}" \
    --member="serviceAccount:${RUNTIME_SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/secretmanager.secretAccessor" >/dev/null
}

echo "Enabling required services..."
gcloud services enable \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  compute.googleapis.com \
  run.googleapis.com \
  secretmanager.googleapis.com \
  iam.googleapis.com \
  --project "${PROJECT_ID}" >/dev/null

if ! gcloud artifacts repositories describe "${AR_REPO}" \
  --project "${PROJECT_ID}" \
  --location "${REGION}" >/dev/null 2>&1; then
  gcloud artifacts repositories create "${AR_REPO}" \
    --project "${PROJECT_ID}" \
    --repository-format=docker \
    --location "${REGION}" \
    --description="Containers for ${SERVICE_NAME}" >/dev/null
  echo "Created Artifact Registry repository ${AR_REPO}"
fi

if ! gcloud iam service-accounts describe "${RUNTIME_SERVICE_ACCOUNT_EMAIL}" \
  --project "${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${RUNTIME_SERVICE_ACCOUNT_NAME}" \
    --project "${PROJECT_ID}" \
    --display-name="${SERVICE_NAME} Cloud Run runtime" >/dev/null
  echo "Created runtime service account ${RUNTIME_SERVICE_ACCOUNT_EMAIL}"
fi

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${BUILD_SERVICE_ACCOUNT}" \
  --role="roles/run.admin" >/dev/null

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${BUILD_SERVICE_ACCOUNT}" \
  --role="roles/artifactregistry.writer" >/dev/null

gcloud iam service-accounts add-iam-policy-binding "${RUNTIME_SERVICE_ACCOUNT_EMAIL}" \
  --project "${PROJECT_ID}" \
  --member="serviceAccount:${BUILD_SERVICE_ACCOUNT}" \
  --role="roles/iam.serviceAccountUser" >/dev/null

if [[ -n "${VPC_NETWORK}" || -n "${VPC_SUBNET}" ]]; then
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SERVERLESS_SERVICE_AGENT}" \
    --role="roles/compute.networkUser" >/dev/null
fi

ensure_secret "${POSTGRES_DSN_SECRET}" "${POSTGRES_DSN_VALUE:-}"

if [[ -n "${REDIS_URL_SECRET}" ]]; then
  ensure_secret "${REDIS_URL_SECRET}" "${REDIS_URL_VALUE:-}"
fi

cat <<EOF

Bootstrap complete.

Project: ${PROJECT_ID}
Region: ${REGION}
Cloud Run service: ${SERVICE_NAME}
Artifact Registry repo: ${AR_REPO}
Runtime service account: ${RUNTIME_SERVICE_ACCOUNT_EMAIL}
Cloud Build service account: ${BUILD_SERVICE_ACCOUNT}
Direct VPC egress network: ${VPC_NETWORK:-not configured}
Direct VPC egress subnet: ${VPC_SUBNET:-not configured}
Required secret: ${POSTGRES_DSN_SECRET}
Optional Redis secret: ${REDIS_URL_SECRET:-not configured}

Next steps:
1. Preload the GTFS tables in your production PostgreSQL database before enabling auto-deploy.
2. Connect the GitHub repository to Cloud Build and create:
   - a pull request trigger using cloudbuild.pr.yaml
   - a main branch trigger using cloudbuild.deploy.yaml
3. Set trigger substitutions for:
   - _REGION=${REGION}
   - _SERVICE_NAME=${SERVICE_NAME}
   - _AR_REPO=${AR_REPO}
   - _IMAGE_NAME=${SERVICE_NAME}
   - _POSTGRES_DSN_SECRET=${POSTGRES_DSN_SECRET}
   - _RUNTIME_SERVICE_ACCOUNT=${RUNTIME_SERVICE_ACCOUNT_EMAIL}
4. Set _REDIS_URL_SECRET and _ALLOWED_ORIGINS on the deploy trigger if needed.
5. If you are using Cloud SQL private IP, also set:
   - _VPC_NETWORK=${VPC_NETWORK:-default}
   - _VPC_SUBNET=${VPC_SUBNET:-your-regional-subnet}
   - _VPC_EGRESS=private-ranges-only

EOF
