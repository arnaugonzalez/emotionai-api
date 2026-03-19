#!/usr/bin/env bash

if [[ -n "${DEMO_FLOW_LIB_LOADED:-}" ]]; then
  return 0
fi
readonly DEMO_FLOW_LIB_LOADED=1

declare -ag DEMO_STEP_IDS=()
declare -Ag DEMO_STEP_SECTION=()
declare -Ag DEMO_STEP_REQUIRED=()
declare -Ag DEMO_STEP_DESCRIPTION=()
declare -Ag DEMO_STEP_FUNCTION=()
declare -Ag DEMO_RESULT_STATUS=()
declare -Ag DEMO_RESULT_REASON=()
declare -Ag DEMO_RESULT_REMEDIATION=()
declare -Ag DEMO_RESULT_ARTIFACT=()

demo_init_defaults() {
  DEMO_BASE_URL="${DEMO_BASE_URL:-http://127.0.0.1:8000}"
  DEMO_SECTION="${DEMO_SECTION:-all}"
  DEMO_LIST_STEPS="${DEMO_LIST_STEPS:-false}"
  DEMO_HELP="${DEMO_HELP:-false}"
  DEMO_REQUEST_TIMEOUT="${DEMO_REQUEST_TIMEOUT:-10}"
  DEMO_BODY_MAX_LINES="${DEMO_BODY_MAX_LINES:-12}"

  local timestamp
  timestamp=$(date -u +"%Y%m%dT%H%M%SZ")
  DEMO_RUN_ID="${DEMO_RUN_ID:-$timestamp}"
  DEMO_ARTIFACT_ROOT="${DEMO_ARTIFACT_ROOT:-$(pwd)/.tmp/demo_flow/${DEMO_RUN_ID}}"
  mkdir -p "$DEMO_ARTIFACT_ROOT"
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

demo_validate_section() {
  case "$1" in
    all|core|metrics|celery|otel)
      ;;
    *)
      die "Unsupported section '$1'. Expected one of: all, core, metrics, celery, otel"
      ;;
  esac
}

demo_load_step_modules() {
  local step_dir="$1"
  local step_file

  if [[ ! -d "$step_dir" ]]; then
    die "Step directory not found: $step_dir"
  fi

  shopt -s nullglob
  for step_file in "$step_dir"/*.sh; do
    # shellcheck disable=SC1090
    source "$step_file"
  done
  shopt -u nullglob

  if [[ ${#DEMO_STEP_IDS[@]} -eq 0 ]]; then
    die "No demo steps registered from $step_dir"
  fi
}

register_step() {
  local id="$1"
  local section="$2"
  local required="$3"
  local description="$4"
  local function_name="$5"

  # Stable extension contract for all future step modules:
  # register_step <id> <section> <required:true|false> <description> <function_name>
  [[ -n "$id" && -n "$section" && -n "$required" && -n "$description" && -n "$function_name" ]] \
    || die "register_step requires: id section required description function"
  [[ "$id" =~ ^[a-z0-9._-]+$ ]] || die "Step id must match ^[a-z0-9._-]+$: $id"
  [[ "$section" =~ ^[a-z0-9._-]+$ ]] || die "Step section must match ^[a-z0-9._-]+$: $section"
  [[ "$required" == "true" || "$required" == "false" ]] || die "Step required flag must be true or false: $id"
  [[ -z "${DEMO_STEP_FUNCTION[$id]:-}" ]] || die "Duplicate step id: $id"
  declare -F "$function_name" >/dev/null 2>&1 || die "Step function not found for $id: $function_name"

  DEMO_STEP_IDS+=("$id")
  DEMO_STEP_SECTION["$id"]="$section"
  DEMO_STEP_REQUIRED["$id"]="$required"
  DEMO_STEP_DESCRIPTION["$id"]="$description"
  DEMO_STEP_FUNCTION["$id"]="$function_name"
}

demo_should_run_step() {
  local step_id="$1"
  local section="${DEMO_STEP_SECTION[$step_id]}"
  [[ "$DEMO_SECTION" == "all" || "$DEMO_SECTION" == "$section" ]]
}

demo_print_run_header() {
  cat <<EOF
== Demo Flow ==
run_id=${DEMO_RUN_ID}
base_url=${DEMO_BASE_URL}
section=${DEMO_SECTION}
artifacts=${DEMO_ARTIFACT_ROOT}
steps=${#DEMO_STEP_IDS[@]}
EOF
}

demo_print_step_listing() {
  local step_id
  for step_id in "${DEMO_STEP_IDS[@]}"; do
    printf '%s section=%s required=%s function=%s description=%s\n' \
      "$step_id" \
      "${DEMO_STEP_SECTION[$step_id]}" \
      "${DEMO_STEP_REQUIRED[$step_id]}" \
      "${DEMO_STEP_FUNCTION[$step_id]}" \
      "${DEMO_STEP_DESCRIPTION[$step_id]}"
  done
}

demo_run_registered_steps() {
  local step_id status
  local required_failures=0
  local optional_failures=0

  for step_id in "${DEMO_STEP_IDS[@]}"; do
    if demo_should_run_step "$step_id"; then
      demo_run_step "$step_id"
    else
      DEMO_RESULT_STATUS["$step_id"]="SKIP"
      DEMO_RESULT_REASON["$step_id"]="Not selected by --section ${DEMO_SECTION}"
      DEMO_RESULT_REMEDIATION["$step_id"]="Re-run with --section ${DEMO_STEP_SECTION[$step_id]} or --section all."
      DEMO_RESULT_ARTIFACT["$step_id"]="-"
    fi
  done

  status=0
  for step_id in "${DEMO_STEP_IDS[@]}"; do
    if [[ "${DEMO_RESULT_STATUS[$step_id]:-}" == "FAIL" ]]; then
      if [[ "${DEMO_STEP_REQUIRED[$step_id]}" == "true" ]]; then
        status=1
        ((required_failures+=1))
      else
        ((optional_failures+=1))
      fi
    fi
  done
  DEMO_REQUIRED_FAILURES="$required_failures"
  DEMO_OPTIONAL_FAILURES="$optional_failures"
  DEMO_OVERALL_STATUS="$status"
}

demo_run_step() {
  local step_id="$1"
  local artifact_dir="${DEMO_ARTIFACT_ROOT}/${step_id//[^A-Za-z0-9._-]/_}"
  local function_name="${DEMO_STEP_FUNCTION[$step_id]}"
  local step_reason_file="${artifact_dir}/reason.txt"
  local step_remediation_file="${artifact_dir}/remediation.txt"
  local step_artifact_file="${artifact_dir}/artifact.txt"
  local step_status_file="${artifact_dir}/status.txt"
  local step_log_file="${artifact_dir}/step.log"

  mkdir -p "$artifact_dir"
  rm -f "$step_reason_file" "$step_remediation_file" "$step_artifact_file" "$step_status_file" "$step_log_file"

  echo "-- step=${step_id} section=${DEMO_STEP_SECTION[$step_id]} required=${DEMO_STEP_REQUIRED[$step_id]} description=${DEMO_STEP_DESCRIPTION[$step_id]}"

  if "$function_name" "$step_id" "$artifact_dir" >"$step_log_file" 2>&1; then
    if [[ -s "$step_status_file" ]]; then
      DEMO_RESULT_STATUS["$step_id"]="$(<"$step_status_file")"
    else
      DEMO_RESULT_STATUS["$step_id"]="PASS"
    fi
    if [[ -s "$step_reason_file" ]]; then
      DEMO_RESULT_REASON["$step_id"]="$(<"$step_reason_file")"
    else
      DEMO_RESULT_REASON["$step_id"]="OK"
    fi
  else
    DEMO_RESULT_STATUS["$step_id"]="FAIL"
    if [[ -s "$step_reason_file" ]]; then
      DEMO_RESULT_REASON["$step_id"]="$(cat "$step_reason_file")"
    else
      DEMO_RESULT_REASON["$step_id"]="Step failed without reason"
    fi
  fi

  if [[ -s "$step_remediation_file" ]]; then
    DEMO_RESULT_REMEDIATION["$step_id"]="$(<"$step_remediation_file")"
  else
    DEMO_RESULT_REMEDIATION["$step_id"]="-"
  fi

  if [[ -f "$step_artifact_file" ]]; then
    DEMO_RESULT_ARTIFACT["$step_id"]="$(<"$step_artifact_file")"
  else
    DEMO_RESULT_ARTIFACT["$step_id"]="$artifact_dir"
  fi

  cat "$step_log_file"
  demo_print_step_result "$step_id"
}

demo_write_step_result() {
  local artifact_dir="$1"
  local status="$2"
  local reason="$3"
  local remediation="$4"
  local artifact_path="${5:-$artifact_dir}"

  printf '%s\n' "$status" >"${artifact_dir}/status.txt"
  printf '%s\n' "$reason" >"${artifact_dir}/reason.txt"
  printf '%s\n' "$remediation" >"${artifact_dir}/remediation.txt"
  printf '%s\n' "$artifact_path" >"${artifact_dir}/artifact.txt"
}

demo_fail_step() {
  local artifact_dir="$1"
  local reason="$2"
  local remediation="$3"
  local artifact_path="${4:-$artifact_dir}"

  demo_write_step_result "$artifact_dir" "FAIL" "$reason" "$remediation" "$artifact_path"
  return 1
}

demo_pass_step() {
  local artifact_dir="$1"
  local artifact_path="${2:-$artifact_dir}"
  local reason="${3:-OK}"

  demo_write_step_result "$artifact_dir" "PASS" "$reason" "-" "$artifact_path"
}

demo_skip_step() {
  local artifact_dir="$1"
  local reason="$2"
  local remediation="$3"
  local artifact_path="${4:-$artifact_dir}"

  demo_write_step_result "$artifact_dir" "SKIP" "$reason" "$remediation" "$artifact_path"
}

demo_print_step_result() {
  local step_id="$1"

  printf 'result status=%s step=%s section=%s required=%s description=%s\n' \
    "${DEMO_RESULT_STATUS[$step_id]}" \
    "$step_id" \
    "${DEMO_STEP_SECTION[$step_id]}" \
    "${DEMO_STEP_REQUIRED[$step_id]}" \
    "${DEMO_STEP_DESCRIPTION[$step_id]}"
  printf 'reason=%s\n' "${DEMO_RESULT_REASON[$step_id]}"
  printf 'remediation=%s\n' "${DEMO_RESULT_REMEDIATION[$step_id]}"
  printf 'artifact=%s\n' "${DEMO_RESULT_ARTIFACT[$step_id]}"
}

demo_http_get() {
  local path="$1"
  local artifact_dir="$2"
  local label="$3"
  local url="${DEMO_BASE_URL}${path}"

  demo_http_get_url "$url" "$artifact_dir" "$label"
}

demo_http_get_url() {
  local url="$1"
  local artifact_dir="$2"
  local label="$3"

  DEMO_HTTP_STATUS_FILE="${artifact_dir}/${label}.status"
  DEMO_HTTP_HEADERS_FILE="${artifact_dir}/${label}.headers"
  DEMO_HTTP_BODY_FILE="${artifact_dir}/${label}.body"
  DEMO_HTTP_STDERR_FILE="${artifact_dir}/${label}.stderr"

  local curl_exit=0

  if curl --silent --show-error \
    --max-time "$DEMO_REQUEST_TIMEOUT" \
    --dump-header "$DEMO_HTTP_HEADERS_FILE" \
    --output "$DEMO_HTTP_BODY_FILE" \
    --write-out "%{http_code}" \
    "$url" >"$DEMO_HTTP_STATUS_FILE" 2>"$DEMO_HTTP_STDERR_FILE"; then
    curl_exit=0
  else
    curl_exit=$?
  fi

  DEMO_HTTP_STATUS="$(<"$DEMO_HTTP_STATUS_FILE")"
  DEMO_HTTP_CONTENT_TYPE="$(awk 'tolower($1) == "content-type:" {gsub("\r",""); print $2; exit}' "$DEMO_HTTP_HEADERS_FILE" 2>/dev/null || true)"
  DEMO_HTTP_URL="$url"
  DEMO_HTTP_CURL_EXIT="$curl_exit"
}

demo_print_http_failure() {
  local title="$1"
  local remediation="$2"

  echo "FAIL: ${title}"
  echo "url=${DEMO_HTTP_URL}"
  echo "status=${DEMO_HTTP_STATUS}"
  echo "content_type=${DEMO_HTTP_CONTENT_TYPE:-unknown}"
  if [[ -s "$DEMO_HTTP_STDERR_FILE" ]]; then
    echo "curl_stderr:"
    sed -n "1,${DEMO_BODY_MAX_LINES}p" "$DEMO_HTTP_STDERR_FILE"
  fi
  if [[ -s "$DEMO_HTTP_BODY_FILE" ]]; then
    echo "body_snippet:"
    sed -n "1,${DEMO_BODY_MAX_LINES}p" "$DEMO_HTTP_BODY_FILE"
  fi
  echo "remediation=${remediation}"
  echo "artifact=${DEMO_HTTP_BODY_FILE}"
}

demo_assert_http_200() {
  local artifact_dir="$1"
  local path="$2"
  local remediation="$3"

  demo_http_get "$path" "$artifact_dir" "http"
  if [[ "$DEMO_HTTP_CURL_EXIT" -ne 0 ]]; then
    demo_print_http_failure "Request to ${path} did not complete" "$remediation"
    demo_fail_step \
      "$artifact_dir" \
      "curl failed for ${path} with exit ${DEMO_HTTP_CURL_EXIT}; see ${DEMO_HTTP_STDERR_FILE}" \
      "$remediation" \
      "$DEMO_HTTP_BODY_FILE"
    return 1
  fi

  if [[ "$DEMO_HTTP_STATUS" != "200" ]]; then
    demo_print_http_failure "Expected HTTP 200 from ${path}" "$remediation"
    demo_fail_step \
      "$artifact_dir" \
      "Expected HTTP 200 from ${path}, got ${DEMO_HTTP_STATUS}" \
      "$remediation" \
      "$DEMO_HTTP_BODY_FILE"
    return 1
  fi

  demo_pass_step "$artifact_dir" "$DEMO_HTTP_BODY_FILE" "HTTP 200 from ${path}"
}

demo_assert_body_contains() {
  local artifact_dir="$1"
  local needle="$2"
  local description="$3"
  local remediation="$4"

  if ! grep -Fq "$needle" "$DEMO_HTTP_BODY_FILE"; then
    echo "FAIL: missing ${description}"
    echo "needle=${needle}"
    echo "body_snippet:"
    sed -n "1,${DEMO_BODY_MAX_LINES}p" "$DEMO_HTTP_BODY_FILE"
    echo "remediation=${remediation}"
    echo "artifact=${DEMO_HTTP_BODY_FILE}"
    demo_fail_step \
      "$artifact_dir" \
      "Missing ${description}: ${needle}" \
      "$remediation" \
      "$DEMO_HTTP_BODY_FILE"
    return 1
  fi
}

demo_assert_content_type_contains() {
  local artifact_dir="$1"
  local needle="$2"
  local remediation="$3"

  if [[ "${DEMO_HTTP_CONTENT_TYPE:-}" != *"$needle"* ]]; then
    echo "FAIL: unexpected content type"
    echo "expected_substring=${needle}"
    echo "actual=${DEMO_HTTP_CONTENT_TYPE:-unknown}"
    echo "remediation=${remediation}"
    echo "artifact=${DEMO_HTTP_HEADERS_FILE}"
    demo_fail_step \
      "$artifact_dir" \
      "Unexpected content type: ${DEMO_HTTP_CONTENT_TYPE:-unknown}" \
      "$remediation" \
      "$DEMO_HTTP_HEADERS_FILE"
    return 1
  fi
}

demo_file_contains() {
  local file_path="$1"
  local needle="$2"
  grep -Fq "$needle" "$file_path"
}

demo_compose_has_service() {
  local service_name="$1"
  demo_file_contains "$(pwd)/docker-compose.yml" "  ${service_name}:"
}

demo_detect_compose_command() {
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    DEMO_COMPOSE_CMD=(docker compose)
    return 0
  fi

  if command -v docker-compose >/dev/null 2>&1; then
    DEMO_COMPOSE_CMD=(docker-compose)
    return 0
  fi

  return 1
}

demo_compose_service_running() {
  local service_name="$1"
  local services

  if ! demo_detect_compose_command; then
    return 2
  fi

  if ! services=$("${DEMO_COMPOSE_CMD[@]}" ps --status running --services 2>/dev/null); then
    return 3
  fi

  grep -Fxq "$service_name" <<<"$services"
}

demo_print_summary() {
  local step_id pass_count=0 fail_count=0 skip_count=0

  echo
  echo "== Summary =="
  for step_id in "${DEMO_STEP_IDS[@]}"; do
    case "${DEMO_RESULT_STATUS[$step_id]}" in
      PASS) ((pass_count+=1)) ;;
      FAIL) ((fail_count+=1)) ;;
      SKIP) ((skip_count+=1)) ;;
    esac

    printf '%s section=%s required=%s status=%s artifact=%s reason=%s remediation=%s\n' \
      "$step_id" \
      "${DEMO_STEP_SECTION[$step_id]}" \
      "${DEMO_STEP_REQUIRED[$step_id]}" \
      "${DEMO_RESULT_STATUS[$step_id]}" \
      "${DEMO_RESULT_ARTIFACT[$step_id]}" \
      "${DEMO_RESULT_REASON[$step_id]}" \
      "${DEMO_RESULT_REMEDIATION[$step_id]}"
  done

  echo "counts pass=${pass_count} fail=${fail_count} skip=${skip_count}"
  echo "required_failures=${DEMO_REQUIRED_FAILURES:-0} optional_failures=${DEMO_OPTIONAL_FAILURES:-0}"
  echo "artifacts=${DEMO_ARTIFACT_ROOT}"
}

demo_exit_for_results() {
  if [[ "${DEMO_OVERALL_STATUS:-0}" -ne 0 ]]; then
    exit 1
  fi
}
