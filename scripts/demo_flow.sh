#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
readonly SCRIPT_DIR

# shellcheck source=scripts/demo_flow_lib.sh
source "${SCRIPT_DIR}/demo_flow_lib.sh"

print_help() {
  cat <<'EOF'
Usage: bash scripts/demo_flow.sh [options]

Options:
  --section all|core|metrics|celery|otel
                              Run one section or all sections (default: all)
  --list-steps                Print all discovered registered steps
  --base-url URL              Override the API base URL (default: http://127.0.0.1:8000)
  --help                      Show this help message
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --section)
        [[ $# -ge 2 ]] || die "Missing value for --section"
        DEMO_SECTION="$2"
        shift 2
        ;;
      --list-steps)
        DEMO_LIST_STEPS=true
        shift
        ;;
      --base-url)
        [[ $# -ge 2 ]] || die "Missing value for --base-url"
        DEMO_BASE_URL="$2"
        shift 2
        ;;
      --help)
        DEMO_HELP=true
        shift
        ;;
      *)
        die "Unknown argument: $1"
        ;;
    esac
  done
}

main() {
  demo_init_defaults
  parse_args "$@"

  if [[ "$DEMO_HELP" == "true" ]]; then
    print_help
    return 0
  fi

  demo_validate_section "$DEMO_SECTION"
  demo_load_step_modules "${SCRIPT_DIR}/demo_steps"

  if [[ "$DEMO_LIST_STEPS" == "true" ]]; then
    demo_print_step_listing
    return 0
  fi

  demo_print_run_header
  demo_run_registered_steps
  demo_print_summary
  demo_exit_for_results
}

main "$@"
