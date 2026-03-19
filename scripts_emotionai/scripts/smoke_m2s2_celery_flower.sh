#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
readonly ROOT_DIR
ARTIFACT_ROOT="${ROOT_DIR}/.tmp/smoke_m2s2_celery_flower"
mkdir -p "${ARTIFACT_ROOT}"

MODE=""
KEEP_STACK="${KEEP_STACK:-0}"
RUN_ID=$(date -u +"%Y%m%dT%H%M%SZ")
RUN_DIR="${ARTIFACT_ROOT}/${RUN_ID}"
mkdir -p "${RUN_DIR}"

readonly FLOWER_URL="http://127.0.0.1:5555"
readonly API_URL="http://127.0.0.1:8000"

cleanup() {
  local exit_code=$?
  if [[ "${KEEP_STACK}" != "1" && "${MODE}" == "e2e" ]]; then
    (
      cd "${ROOT_DIR}"
      docker compose down --remove-orphans >/dev/null 2>&1 || true
    )
  fi
  exit "${exit_code}"
}

trap cleanup EXIT

usage() {
  cat <<'EOF'
Usage: bash scripts_emotionai/scripts/smoke_m2s2_celery_flower.sh [--worker-only | --e2e]

Options:
  --worker-only   Run only the real Celery worker startup smoke using the roadmap command
  --e2e           Run full API -> queue -> worker -> Flower verification
  --help          Show this help message

Environment:
  KEEP_STACK=1    Leave docker compose services running after --e2e
EOF
}

log() {
  printf '[smoke-m2s2] %s\n' "$*"
}

fail() {
  printf '[smoke-m2s2] ERROR: %s\n' "$*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

wait_for_http() {
  local url="$1"
  local expected="${2:-200}"
  local timeout_seconds="${3:-90}"
  local start_epoch
  start_epoch=$(date +%s)

  while true; do
    local status
    status=$(curl -sS -o /dev/null -w '%{http_code}' "${url}" || true)
    if [[ "${status}" == "${expected}" ]]; then
      return 0
    fi

    if (( $(date +%s) - start_epoch >= timeout_seconds )); then
      fail "Timed out waiting for ${url} to return ${expected}; last status=${status}"
    fi

    sleep 2
  done
}

run_worker_only() {
  local worker_log="${RUN_DIR}/worker-only.log"
  log "Starting Redis for worker smoke"
  (
    cd "${ROOT_DIR}"
    docker compose up -d redis
  )

  log "Prebuilding celery_worker image so timeout measures worker startup, not image build"
  (
    cd "${ROOT_DIR}"
    docker compose build celery_worker
  ) >"${RUN_DIR}/worker-build.log" 2>&1 || {
    sed -n '1,220p' "${RUN_DIR}/worker-build.log" >&2 || true
    fail "Failed to build celery_worker image"
  }

  log "Running roadmap worker command as a real process"
  set +e
  (
    cd "${ROOT_DIR}"
    timeout 25s docker compose run --rm -e REDIS_URL=redis://redis:6379/0 celery_worker \
      celery -A src.infrastructure.tasks.worker worker --loglevel=info
  ) >"${worker_log}" 2>&1
  local rc=$?
  set -e

  if [[ "${rc}" -ne 0 && "${rc}" -ne 124 ]]; then
    sed -n '1,220p' "${worker_log}" >&2 || true
    fail "Worker startup command failed with exit code ${rc}"
  fi

  if ! grep -Eiq 'ready|mingle: all alone|celery@.*ready' "${worker_log}"; then
    sed -n '1,220p' "${worker_log}" >&2 || true
    fail "Worker did not emit a ready signal"
  fi

  log "Worker startup smoke passed"
  log "Artifact: ${worker_log}"
}

run_migrations() {
  log "Running database migrations"
  (
    cd "${ROOT_DIR}"
    docker compose run --rm api alembic upgrade head
  ) >"${RUN_DIR}/migrations.log" 2>&1 || {
    sed -n '1,220p' "${RUN_DIR}/migrations.log" >&2 || true
    fail "Database migrations failed"
  }
}

register_user() {
  local email="m2s2-${RUN_ID}@example.com"
  local register_body="${RUN_DIR}/register-response.json"
  local register_status

  register_status=$(curl -sS \
    -o "${register_body}" \
    -w '%{http_code}' \
    -X POST "${API_URL}/v1/api/auth/register" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"${email}\",\"password\":\"SmokePass123!\",\"first_name\":\"Smoke\",\"last_name\":\"Test\"}")

  if [[ "${register_status}" != "200" ]]; then
    sed -n '1,160p' "${register_body}" >&2 || true
    fail "User registration failed with HTTP ${register_status}"
  fi

  ACCESS_TOKEN=$(
    python3 - "${register_body}" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as fh:
    payload = json.load(fh)
print(payload["access_token"])
PY
  )

  if [[ -z "${ACCESS_TOKEN}" ]]; then
    fail "Registration response did not contain an access token"
  fi
}

post_record() {
  local record_body="${RUN_DIR}/record-response.json"
  local record_status

  record_status=$(curl -sS \
    -o "${record_body}" \
    -w '%{http_code}' \
    -X POST "${API_URL}/v1/api/emotional_records/" \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -d '{"emotion":"calm","intensity":6,"description":"Smoke test record for celery flower verification","source":"smoke_m2s2"}')

  if [[ "${record_status}" != "200" ]]; then
    sed -n '1,200p' "${record_body}" >&2 || true
    fail "Emotional record creation failed with HTTP ${record_status}"
  fi
}

wait_for_flower_task() {
  local task_file="${RUN_DIR}/flower-tasks.json"
  local timeout_seconds="${1:-90}"
  local start_epoch
  start_epoch=$(date +%s)

  while true; do
    local status
    status=$(curl -sS -o "${task_file}" -w '%{http_code}' "${FLOWER_URL}/api/tasks" || true)

    if [[ "${status}" == "200" ]]; then
      if python3 - "${task_file}" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as fh:
    payload = json.load(fh)

def entries(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                yield value
    elif isinstance(data, list):
        for value in data:
            if isinstance(value, dict):
                yield value

for task in entries(payload):
    name = task.get("name") or task.get("task") or ""
    state = task.get("state") or task.get("status") or ""
    if name == "emotionai.notify_new_record" and state == "SUCCESS":
        raise SystemExit(0)

raise SystemExit(1)
PY
      then
        return 0
      fi
    fi

    if (( $(date +%s) - start_epoch >= timeout_seconds )); then
      sed -n '1,200p' "${task_file}" >&2 || true
      fail "Timed out waiting for emotionai.notify_new_record to reach SUCCESS in Flower"
    fi

    sleep 2
  done
}

run_e2e() {
  log "Booting db, redis, api, celery_worker, and flower"
  (
    cd "${ROOT_DIR}"
    docker compose up -d db redis api celery_worker flower
  ) >"${RUN_DIR}/compose-up.log" 2>&1 || {
    sed -n '1,220p' "${RUN_DIR}/compose-up.log" >&2 || true
    fail "docker compose up failed"
  }

  run_migrations

  log "Waiting for API and Flower"
  wait_for_http "${API_URL}/health/" 200 120
  wait_for_http "${FLOWER_URL}/api/workers" 200 120

  register_user
  post_record

  log "Polling Flower for emotionai.notify_new_record SUCCESS"
  wait_for_flower_task 90

  log "End-to-end smoke passed"
  log "Artifacts: ${RUN_DIR}"
}

main() {
  require_cmd docker
  require_cmd curl
  require_cmd python3

  if [[ $# -ne 1 ]]; then
    usage
    exit 1
  fi

  case "$1" in
    --worker-only)
      MODE="worker-only"
      run_worker_only
      ;;
    --e2e)
      MODE="e2e"
      run_e2e
      ;;
    --help)
      usage
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
