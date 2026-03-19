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
    all|core|metrics)
      ;;
    *)
      die "Unsupported section '$1'. Expected one of: all, core, metrics"
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

  [[ -n "$id" && -n "$section" && -n "$required" && -n "$description" && -n "$function_name" ]] \
    || die "register_step requires: id section required description function"
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

  for step_id in "${DEMO_STEP_IDS[@]}"; do
    if demo_should_run_step "$step_id"; then
      demo_run_step "$step_id"
    else
      DEMO_RESULT_STATUS["$step_id"]="SKIP"
      DEMO_RESULT_REASON["$step_id"]="Not selected by --section ${DEMO_SECTION}"
      DEMO_RESULT_ARTIFACT["$step_id"]="-"
    fi
  done

  status=0
  for step_id in "${DEMO_STEP_IDS[@]}"; do
    if [[ "${DEMO_RESULT_STATUS[$step_id]:-}" == "FAIL" && "${DEMO_STEP_REQUIRED[$step_id]}" == "true" ]]; then
      status=1
      break
    fi
  done
  DEMO_OVERALL_STATUS="$status"
}

demo_run_step() {
  local step_id="$1"
  local artifact_dir="${DEMO_ARTIFACT_ROOT}/${step_id//[^A-Za-z0-9._-]/_}"
  local function_name="${DEMO_STEP_FUNCTION[$step_id]}"
  local step_reason_file="${artifact_dir}/reason.txt"
  local step_artifact_file="${artifact_dir}/artifact.txt"
  local step_log_file="${artifact_dir}/step.log"

  mkdir -p "$artifact_dir"
  rm -f "$step_reason_file" "$step_artifact_file" "$step_log_file"

  echo "-- step=${step_id} section=${DEMO_STEP_SECTION[$step_id]} required=${DEMO_STEP_REQUIRED[$step_id]} description=${DEMO_STEP_DESCRIPTION[$step_id]}"

  if "$function_name" "$step_id" "$artifact_dir" >"$step_log_file" 2>&1; then
    DEMO_RESULT_STATUS["$step_id"]="PASS"
    DEMO_RESULT_REASON["$step_id"]="OK"
  else
    DEMO_RESULT_STATUS["$step_id"]="FAIL"
    DEMO_RESULT_REASON["$step_id"]="$(<"$step_reason_file" 2>/dev/null || echo "Step failed without reason")"
  fi

  if [[ -f "$step_artifact_file" ]]; then
    DEMO_RESULT_ARTIFACT["$step_id"]="$(<"$step_artifact_file")"
  else
    DEMO_RESULT_ARTIFACT["$step_id"]="$artifact_dir"
  fi

  cat "$step_log_file"
}

demo_fail_step() {
  local artifact_dir="$1"
  local reason="$2"
  local artifact_path="${3:-$artifact_dir}"

  printf '%s\n' "$reason" >"${artifact_dir}/reason.txt"
  printf '%s\n' "$artifact_path" >"${artifact_dir}/artifact.txt"
  return 1
}

demo_pass_step() {
  local artifact_dir="$1"
  local artifact_path="${2:-$artifact_dir}"

  printf '%s\n' "$artifact_path" >"${artifact_dir}/artifact.txt"
}

demo_http_get() {
  local path="$1"
  local artifact_dir="$2"
  local label="$3"

  DEMO_HTTP_STATUS_FILE="${artifact_dir}/${label}.status"
  DEMO_HTTP_HEADERS_FILE="${artifact_dir}/${label}.headers"
  DEMO_HTTP_BODY_FILE="${artifact_dir}/${label}.body"
  DEMO_HTTP_STDERR_FILE="${artifact_dir}/${label}.stderr"

  local url="${DEMO_BASE_URL}${path}"
  local curl_exit=0

  if ! curl --silent --show-error \
    --max-time "$DEMO_REQUEST_TIMEOUT" \
    --dump-header "$DEMO_HTTP_HEADERS_FILE" \
    --output "$DEMO_HTTP_BODY_FILE" \
    --write-out "%{http_code}" \
    "$url" >"$DEMO_HTTP_STATUS_FILE" 2>"$DEMO_HTTP_STDERR_FILE"; then
    curl_exit=$?
  fi

  DEMO_HTTP_STATUS="$(<"$DEMO_HTTP_STATUS_FILE")"
  DEMO_HTTP_CONTENT_TYPE="$(awk 'BEGIN{IGNORECASE=1} /^Content-Type:/ {gsub("\r",""); print $2; exit}' "$DEMO_HTTP_HEADERS_FILE" 2>/dev/null || true)"
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
    demo_fail_step "$artifact_dir" "curl failed for ${path}; see ${DEMO_HTTP_STDERR_FILE}" "$DEMO_HTTP_BODY_FILE"
    return 1
  fi

  if [[ "$DEMO_HTTP_STATUS" != "200" ]]; then
    demo_print_http_failure "Expected HTTP 200 from ${path}" "$remediation"
    demo_fail_step "$artifact_dir" "Expected HTTP 200 from ${path}, got ${DEMO_HTTP_STATUS}" "$DEMO_HTTP_BODY_FILE"
    return 1
  fi

  demo_pass_step "$artifact_dir" "$DEMO_HTTP_BODY_FILE"
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
    demo_fail_step "$artifact_dir" "Missing ${description}: ${needle}" "$DEMO_HTTP_BODY_FILE"
    return 1
  fi
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

    printf '%s section=%s required=%s status=%s artifact=%s reason=%s\n' \
      "$step_id" \
      "${DEMO_STEP_SECTION[$step_id]}" \
      "${DEMO_STEP_REQUIRED[$step_id]}" \
      "${DEMO_RESULT_STATUS[$step_id]}" \
      "${DEMO_RESULT_ARTIFACT[$step_id]}" \
      "${DEMO_RESULT_REASON[$step_id]}"
  done

  echo "counts pass=${pass_count} fail=${fail_count} skip=${skip_count}"
}

demo_exit_for_results() {
  if [[ "${DEMO_OVERALL_STATUS:-0}" -ne 0 ]]; then
    exit 1
  fi
}
