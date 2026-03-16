#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="rtd-collector.service"
SRC_SERVICE_FILE="deploy/systemd/${SERVICE_NAME}"
DEST_SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}"

if [[ ! -f "${SRC_SERVICE_FILE}" ]]; then
  echo "Missing ${SRC_SERVICE_FILE}" >&2
  exit 1
fi

sudo cp "${SRC_SERVICE_FILE}" "${DEST_SERVICE_FILE}"
sudo systemctl daemon-reload
sudo systemctl enable --now "${SERVICE_NAME}"

sudo systemctl status "${SERVICE_NAME}" --no-pager
