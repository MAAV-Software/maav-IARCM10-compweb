#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEBAPP_DIR="${ROOT_DIR}/webapp"
VENV_DIR="${WEBAPP_DIR}/.venv"
VENDOR_DIR="${WEBAPP_DIR}/vendor"
MODEL_DIR="${WEBAPP_DIR}/models"
MODEL_NAME="vosk-model-small-en-us-0.15"
MODEL_ZIP_URL="https://alphacephei.com/vosk/models/${MODEL_NAME}.zip"

if python3 -m venv "${VENV_DIR}" >/dev/null 2>&1; then
  source "${VENV_DIR}/bin/activate"
  python -m pip install --upgrade pip
  python -m pip install -r "${WEBAPP_DIR}/requirements.txt"
else
  echo "python3-venv unavailable, installing Python deps into ${VENDOR_DIR} instead."
  mkdir -p "${VENDOR_DIR}"
  python3 -m pip install --upgrade pip
  python3 -m pip install --target "${VENDOR_DIR}" -r "${WEBAPP_DIR}/requirements.txt"
fi

mkdir -p "${MODEL_DIR}"
if [[ ! -d "${MODEL_DIR}/${MODEL_NAME}" ]]; then
  TMP_ZIP="$(mktemp --suffix=.zip)"
  echo "Downloading offline Vosk model ${MODEL_NAME}..."
  curl -L "${MODEL_ZIP_URL}" -o "${TMP_ZIP}"
  unzip -q "${TMP_ZIP}" -d "${MODEL_DIR}"
  rm -f "${TMP_ZIP}"
fi

echo "Bootstrap complete."
if [[ -f "${VENV_DIR}/bin/activate" ]]; then
  echo "Activate with: source ${VENV_DIR}/bin/activate"
else
  echo "Dependencies installed into ${VENDOR_DIR}"
fi