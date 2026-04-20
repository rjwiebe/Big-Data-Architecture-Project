#!/usr/bin/env bash

set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID to your GCP project id.}"

REGION="${REGION:-us-central1}"
SCHEDULER_LOCATION="${SCHEDULER_LOCATION:-${REGION}}"
JOB_NAME="${JOB_NAME:-rtd-static-gtfs}"
AR_REPO="${AR_REPO:-rtd-containers}"
RUNTIME_SERVICE_ACCOUNT_NAME="${RUNTIME_SERVICE_ACCOUNT_NAME:-${JOB_NAME}-runtime}"
SCHEDULER_SERVICE_ACCOUNT_NAME="${SCHEDULER_SERVICE_ACCOUNT_NAME:-${JOB_NAME}-scheduler}"
POSTGRES_DSN_SECRET="${POSTGRES_DSN_SECRET:-static-gtfs-postgres-dsn}"
BUILD_SERVICE_ACCOUNT="${BUILD_SERVICE_ACCOUNT:-}"
VPC_NETWORK="${VPC_NETWORK:-}"
VPC_SUBNET="${VPC_SUBNET:-}"

gcloud config set project "${PROJECT_ID}" >/dev/null

PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
if [[ -z "${BUILD_SERVICE_ACCOUNT}" ]]; then
  BUILD_SERVICE_ACCOUNT="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
fi

RUNTIME_SERVICE_ACCOUNT_EMAIL="${RUNTIME_SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
SCHEDULER_SERVICE_ACCOUNT_EMAIL="${SCHEDULER_SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
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

ensure_service_account() {
  local service_account_name="$1"
  local service_account_email="$2"
  local display_name="$3"

  if ! gcloud iam service-accounts describe "${service_account_email}" \
    --project "${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud iam service-accounts create "${service_account_name}" \
      --project "${PROJECT_ID}" \
      --display-name="${display_name}" >/dev/null
    echo "Created service account ${service_account_email}"
  fi
}

echo "Enabling required services..."
gcloud services enable \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  cloudscheduler.googleapis.com \
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
    --description="Containers for ${JOB_NAME}" >/dev/null
  echo "Created Artifact Registry repository ${AR_REPO}"
fi

ensure_service_account \
  "${RUNTIME_SERVICE_ACCOUNT_NAME}" \
  "${RUNTIME_SERVICE_ACCOUNT_EMAIL}" \
  "${JOB_NAME} Cloud Run Job runtime"

ensure_service_account \
  "${SCHEDULER_SERVICE_ACCOUNT_NAME}" \
  "${SCHEDULER_SERVICE_ACCOUNT_EMAIL}" \
  "${JOB_NAME} Cloud Scheduler invoker"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${BUILD_SERVICE_ACCOUNT}" \
  --role="roles/run.admin" >/dev/null

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${BUILD_SERVICE_ACCOUNT}" \
  --role="roles/artifactregistry.writer" >/dev/null

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${BUILD_SERVICE_ACCOUNT}" \
  --role="roles/cloudscheduler.admin" >/dev/null

gcloud iam service-accounts add-iam-policy-binding "${RUNTIME_SERVICE_ACCOUNT_EMAIL}" \
  --project "${PROJECT_ID}" \
  --member="serviceAccount:${BUILD_SERVICE_ACCOUNT}" \
  --role="roles/iam.serviceAccountUser" >/dev/null

gcloud iam service-accounts add-iam-policy-binding "${SCHEDULER_SERVICE_ACCOUNT_EMAIL}" \
  --project "${PROJECT_ID}" \
  --member="serviceAccount:${BUILD_SERVICE_ACCOUNT}" \
  --role="roles/iam.serviceAccountUser" >/dev/null

if [[ -n "${VPC_NETWORK}" || -n "${VPC_SUBNET}" ]]; then
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SERVERLESS_SERVICE_AGENT}" \
    --role="roles/compute.networkUser" >/dev/null
fi

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SCHEDULER_SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/run.invoker" >/dev/null

ensure_secret "${POSTGRES_DSN_SECRET}" "${POSTGRES_DSN_VALUE:-}"

cat <<EOF

Bootstrap complete.

Project: ${PROJECT_ID}
Region: ${REGION}
Scheduler location: ${SCHEDULER_LOCATION}
Cloud Run Job: ${JOB_NAME}
Artifact Registry repo: ${AR_REPO}
Runtime service account: ${RUNTIME_SERVICE_ACCOUNT_EMAIL}
Scheduler service account: ${SCHEDULER_SERVICE_ACCOUNT_EMAIL}
Cloud Build service account: ${BUILD_SERVICE_ACCOUNT}
Direct VPC egress network: ${VPC_NETWORK:-not configured}
Direct VPC egress subnet: ${VPC_SUBNET:-not configured}
Required secret: ${POSTGRES_DSN_SECRET}

Next steps:
1. Create a pull request trigger using cloudbuild.static_gtfs.pr.yaml.
2. Create a main branch trigger using cloudbuild.static_gtfs.deploy.yaml.
3. Set trigger substitutions for:
   - _REGION=${REGION}
   - _JOB_NAME=${JOB_NAME}
   - _AR_REPO=${AR_REPO}
   - _IMAGE_NAME=${JOB_NAME}
   - _POSTGRES_DSN_SECRET=${POSTGRES_DSN_SECRET}
   - _RUNTIME_SERVICE_ACCOUNT=${RUNTIME_SERVICE_ACCOUNT_EMAIL}
   - _SCHEDULER_SERVICE_ACCOUNT=${SCHEDULER_SERVICE_ACCOUNT_EMAIL}
   - _SCHEDULER_LOCATION=${SCHEDULER_LOCATION}
4. Set _STATIC_GTFS_URLS, _SCHEDULE, and _TIME_ZONE if you want non-default feeds or timing.
5. If you are using private-IP PostgreSQL, also set:
   - _VPC_NETWORK=${VPC_NETWORK:-default}
   - _VPC_SUBNET=${VPC_SUBNET:-your-regional-subnet}
   - _VPC_EGRESS=private-ranges-only

EOF
