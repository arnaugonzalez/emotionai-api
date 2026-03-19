#!/usr/bin/env bash

demo_step_core_health() {
  local _step_id="$1"
  local artifact_dir="$2"

  demo_assert_http_200 "$artifact_dir" "/health/" \
    "Start the API on ${DEMO_BASE_URL} and verify the canonical trailing-slash health route responds."
}

register_step \
  "core.health" \
  "core" \
  "true" \
  "Health endpoint responds on the canonical /health/ route" \
  "demo_step_core_health"
