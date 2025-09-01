#!/usr/bin/env bash
set -euo pipefail

echo "[install_nginx_and_conf] Starting..."

REPO_ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../.. && pwd)"
ENV_FILE="${REPO_ROOT_DIR}/.env.deploy"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: Missing ${ENV_FILE}." >&2
  exit 1
fi

# shellcheck source=/dev/null
set -o allexport
source "${ENV_FILE}"
set +o allexport

: "${NGINX_CONF_DEST:?ERROR: NGINX_CONF_DEST is required in .env.deploy}"
: "${NGINX_SSL_DIR:?ERROR: NGINX_SSL_DIR is required in .env.deploy}"

NGINX_CONF_SRC="${REPO_ROOT_DIR}/deploy/nginx/emotionai.conf"

if ! command -v nginx >/dev/null 2>&1; then
  echo "[install_nginx_and_conf] Installing nginx via dnf..."
  sudo dnf -y install nginx
else
  echo "[install_nginx_and_conf] nginx already installed."
fi

sudo systemctl enable nginx
sudo systemctl start nginx || true

# Prepare SSL dir (do not generate certs here)
echo "[install_nginx_and_conf] Ensuring SSL dir exists: ${NGINX_SSL_DIR}"
sudo mkdir -p "${NGINX_SSL_DIR}"

# Copy the configuration
echo "[install_nginx_and_conf] Copying Nginx config to ${NGINX_CONF_DEST}"
sudo install -m 0644 "${NGINX_CONF_SRC}" "${NGINX_CONF_DEST}"

# Validate and reload
echo "[install_nginx_and_conf] Validating nginx configuration..."
sudo nginx -t

echo "[install_nginx_and_conf] Reloading nginx..."
sudo systemctl reload nginx

echo "[install_nginx_and_conf] Done."
