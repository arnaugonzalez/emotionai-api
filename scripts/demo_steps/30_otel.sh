#!/usr/bin/env bash

demo_step_otel_compose_service() {
  local _step_id="$1"
  local artifact_dir="$2"

  if ! demo_compose_has_service "jaeger"; then
    demo_skip_step \
      "$artifact_dir" \
      "Jaeger service is not defined in docker-compose.yml" \
      "Add a jaeger service before expecting --section otel to probe trace infrastructure." \
      "$(pwd)/docker-compose.yml"
    echo "SKIP: Jaeger service is not configured yet"
    return 0
  fi

  echo "PASS: docker-compose.yml defines the jaeger service"
  demo_pass_step "$artifact_dir" "$(pwd)/docker-compose.yml" "Compose service present for otel section"
}

demo_step_otel_jaeger_reachable() {
  local _step_id="$1"
  local artifact_dir="$2"
  local jaeger_url="http://127.0.0.1:16686/"
  local compose_rc=0

  if ! demo_compose_has_service "jaeger"; then
    demo_skip_step \
      "$artifact_dir" \
      "Jaeger service is not defined in docker-compose.yml" \
      "Add a jaeger service exposing port 16686 before expecting reachability checks to run." \
      "$(pwd)/docker-compose.yml"
    echo "SKIP: Jaeger service is not configured yet"
    return 0
  fi

  if demo_compose_service_running "jaeger"; then
    compose_rc=0
  else
    compose_rc=$?
  fi

  if [[ "$compose_rc" -ne 0 ]]; then
    demo_skip_step \
      "$artifact_dir" \
      "Jaeger service is not running" \
      "Start the jaeger service with docker compose up jaeger before running --section otel." \
      "$(pwd)/docker-compose.yml"
    echo "SKIP: Jaeger service is not running"
    return 0
  fi

  demo_http_get_url "$jaeger_url" "$artifact_dir" "jaeger"
  if [[ "$DEMO_HTTP_CURL_EXIT" -ne 0 || "$DEMO_HTTP_STATUS" != "200" ]]; then
    demo_print_http_failure "Expected Jaeger UI at ${jaeger_url}" \
      "Verify the jaeger container logs and confirm port 16686 is reachable on localhost."
    demo_fail_step \
      "$artifact_dir" \
      "Expected Jaeger UI at ${jaeger_url}, got HTTP ${DEMO_HTTP_STATUS}" \
      "Verify the jaeger container logs and confirm port 16686 is reachable on localhost." \
      "$DEMO_HTTP_BODY_FILE"
    return 1
  fi

  echo "PASS: Jaeger UI responded on ${jaeger_url}"
  demo_pass_step "$artifact_dir" "$DEMO_HTTP_BODY_FILE" "Jaeger UI reachable"
}

demo_step_otel_otlp_ready() {
  local _step_id="$1"
  local artifact_dir="$2"
  local otlp_url="http://127.0.0.1:4318/"
  local compose_rc=0

  if ! demo_compose_has_service "jaeger"; then
    demo_skip_step \
      "$artifact_dir" \
      "No OTLP-capable tracing stack is declared yet" \
      "Add Jaeger or another OTLP receiver exposing port 4318 before expecting endpoint readiness checks." \
      "$(pwd)/docker-compose.yml"
    echo "SKIP: OTLP receiver is not configured yet"
    return 0
  fi

  if demo_compose_service_running "jaeger"; then
    compose_rc=0
  else
    compose_rc=$?
  fi

  if [[ "$compose_rc" -ne 0 ]]; then
    demo_skip_step \
      "$artifact_dir" \
      "Tracing stack is not running" \
      "Start the tracing services with docker compose up jaeger before running --section otel." \
      "$(pwd)/docker-compose.yml"
    echo "SKIP: Tracing stack is not running"
    return 0
  fi

  demo_http_get_url "$otlp_url" "$artifact_dir" "otlp"
  if [[ "$DEMO_HTTP_CURL_EXIT" -ne 0 ]]; then
    demo_print_http_failure "OTLP HTTP endpoint not reachable at ${otlp_url}" \
      "Confirm the collector exposes port 4318 and accepts OTLP/HTTP traffic."
    demo_fail_step \
      "$artifact_dir" \
      "OTLP HTTP endpoint not reachable at ${otlp_url}" \
      "Confirm the collector exposes port 4318 and accepts OTLP/HTTP traffic." \
      "$DEMO_HTTP_STDERR_FILE"
    return 1
  fi

  echo "PASS: OTLP HTTP endpoint is reachable on ${otlp_url}"
  demo_pass_step "$artifact_dir" "$DEMO_HTTP_BODY_FILE" "OTLP HTTP endpoint reachable"
}

register_step \
  "otel.compose_service" \
  "otel" \
  "false" \
  "OTEL section prerequisites are declared in docker-compose.yml" \
  "demo_step_otel_compose_service"

register_step \
  "otel.jaeger_reachable" \
  "otel" \
  "false" \
  "Jaeger UI responds when the optional tracing stack is running" \
  "demo_step_otel_jaeger_reachable"

register_step \
  "otel.otlp_ready" \
  "otel" \
  "false" \
  "OTLP HTTP endpoint is reachable when the tracing stack is running" \
  "demo_step_otel_otlp_ready"
