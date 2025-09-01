#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
ENV_FILE="${REPO_ROOT_DIR}/.env.deploy"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: Missing ${ENV_FILE}. Create it and set required variables (EC2_IP, NGINX_SSL_DIR, FLUTTER_APP_DIR)." >&2
  exit 1
fi

# shellcheck source=/dev/null
set -o allexport
source "${ENV_FILE}"
set +o allexport

: "${EC2_IP:?ERROR: EC2_IP is required in .env.deploy}"
: "${NGINX_SSL_DIR:?ERROR: NGINX_SSL_DIR is required in .env.deploy}"

NGINX_SSL_DIR_ABS="${NGINX_SSL_DIR}"
CRT_PATH="${NGINX_SSL_DIR_ABS}/emotionai.crt"
KEY_PATH="${NGINX_SSL_DIR_ABS}/emotionai.key"
OPENSSL_CNF="${NGINX_SSL_DIR_ABS}/emotionai_ip.cnf"

sudo mkdir -p "${NGINX_SSL_DIR_ABS}"

# Generate OpenSSL config for IP-based SAN
cat >"${OPENSSL_CNF}" <<EOF
[req]
default_bits = 2048
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = ${EC2_IP}

[v3_req]
subjectAltName = @alt_names
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth

[alt_names]
IP.1 = ${EC2_IP}
EOF

# Generate private key and self-signed certificate (~825 days)
if [[ -f "${CRT_PATH}" || -f "${KEY_PATH}" ]]; then
  echo "INFO: Existing cert/key found at ${CRT_PATH} and/or ${KEY_PATH}. They will be overwritten to ensure SAN correctness."
fi

sudo openssl req -x509 -nodes -days 825 -newkey rsa:2048 \
  -keyout "${KEY_PATH}" -out "${CRT_PATH}" \
  -config "${OPENSSL_CNF}"

sudo chmod 600 "${KEY_PATH}"
sudo chmod 644 "${CRT_PATH}"

echo ""
echo "Generated self-signed certificate:"
echo "  Cert: ${CRT_PATH}"
echo "  Key : ${KEY_PATH} (chmod 600)"
echo "  CN  : ${EC2_IP}, SAN IP: ${EC2_IP}"

# Optional Flutter integration
if [[ -n "${FLUTTER_APP_DIR:-}" ]]; then
  FLUTTER_DIR_REL="${FLUTTER_APP_DIR}"
  FLUTTER_DIR_ABS="${REPO_ROOT_DIR}/${FLUTTER_DIR_REL}"
  if [[ -d "${FLUTTER_DIR_ABS}" ]]; then
    CERTS_DIR="${FLUTTER_DIR_ABS}/assets/certs"
    DEST_CERT="${CERTS_DIR}/emotionai_server.crt"
    mkdir -p "${CERTS_DIR}"
    cp -f "${CRT_PATH}" "${DEST_CERT}"
    echo "Copied server cert to Flutter assets: ${DEST_CERT}"

    PUBSPEC_FILE="${FLUTTER_DIR_ABS}/pubspec.yaml"
    if [[ ! -f "${PUBSPEC_FILE}" ]]; then
      echo "flutter:\n  assets:\n    - assets/certs/emotionai_server.crt" > "${PUBSPEC_FILE}"
      echo "Created pubspec.yaml with assets entry."
    else
      # Ensure assets section contains the cert path once
      if ! grep -q "assets:\s*$" "${PUBSPEC_FILE}"; then
        # Add a minimal assets section if none exists
        printf "\nflutter:\n  assets:\n" >> "${PUBSPEC_FILE}"
      fi
      if ! grep -q "-\s*assets/certs/emotionai_server.crt" "${PUBSPEC_FILE}"; then
        # Append the asset entry under assets:, try to place logically
        # If there is an existing 'flutter:' and 'assets:' keep structure
        awk '
          BEGIN {in_flutter=0; in_assets=0; printed=0}
          /^flutter:/ {in_flutter=1}
          {print}
          /^\s*assets:\s*$/ && in_flutter==1 && printed==0 {print "    - assets/certs/emotionai_server.crt"; printed=1}
          END {if (printed==0) print "  assets:\n    - assets/certs/emotionai_server.crt"}
        ' "${PUBSPEC_FILE}" > "${PUBSPEC_FILE}.tmp" && mv "${PUBSPEC_FILE}.tmp" "${PUBSPEC_FILE}"
        echo "Added cert asset to pubspec.yaml."
      else
        echo "Cert asset already present in pubspec.yaml."
      fi
    fi
  else
    echo "INFO: FLUTTER_APP_DIR is set but directory does not exist: ${FLUTTER_DIR_ABS}. Skipping Flutter steps."
  fi
fi

cat <<SUMMARY

Done.
- Nginx cert path : ${CRT_PATH}
- Nginx key path  : ${KEY_PATH}
- OpenSSL config  : ${OPENSSL_CNF}
SUMMARY
