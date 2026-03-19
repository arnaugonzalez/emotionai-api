#!/usr/bin/env bash

demo_step_celery_compose_service() {
  local _step_id="$1"
  local artifact_dir="$2"
  local missing_services=()
  local service_name

  for service_name in celery_worker flower; do
    if ! demo_compose_has_service "$service_name"; then
      missing_services+=("$service_name")
    fi
  done

  if [[ ${#missing_services[@]} -gt 0 ]]; then
    demo_skip_step \
      "$artifact_dir" \
      "Missing docker-compose services: ${missing_services[*]}" \
      "Add celery_worker and flower services in docker-compose.yml before running --section celery." \
      "$(pwd)/docker-compose.yml"
    echo "SKIP: Celery demo services are not defined in docker-compose.yml"
    return 0
  fi

  echo "PASS: docker-compose.yml defines celery_worker and flower services"
  demo_pass_step "$artifact_dir" "$(pwd)/docker-compose.yml" "Compose services present for celery section"
}

demo_step_celery_flower_reachable() {
  local _step_id="$1"
  local artifact_dir="$2"
  local flower_url="http://127.0.0.1:5555/"
  local compose_rc=0

  if ! demo_compose_has_service "flower"; then
    demo_skip_step \
      "$artifact_dir" \
      "Flower service is not defined in docker-compose.yml" \
      "Add a flower service exposing port 5555 before expecting reachability checks to run." \
      "$(pwd)/docker-compose.yml"
    echo "SKIP: Flower service is not configured yet"
    return 0
  fi

  if demo_compose_service_running "flower"; then
    compose_rc=0
  else
    compose_rc=$?
  fi

  if [[ "$compose_rc" -ne 0 ]]; then
    demo_skip_step \
      "$artifact_dir" \
      "Flower service is not running" \
      "Start the flower service with docker compose up flower before running --section celery." \
      "$(pwd)/docker-compose.yml"
    echo "SKIP: Flower service is not running"
    return 0
  fi

  demo_http_get_url "$flower_url" "$artifact_dir" "flower"
  if [[ "$DEMO_HTTP_CURL_EXIT" -ne 0 || "$DEMO_HTTP_STATUS" != "200" ]]; then
    demo_print_http_failure "Expected Flower UI at ${flower_url}" \
      "Verify the flower container logs and confirm port 5555 is reachable on localhost."
    demo_fail_step \
      "$artifact_dir" \
      "Expected Flower UI at ${flower_url}, got HTTP ${DEMO_HTTP_STATUS}" \
      "Verify the flower container logs and confirm port 5555 is reachable on localhost." \
      "$DEMO_HTTP_BODY_FILE"
    return 1
  fi

  echo "PASS: Flower UI responded on ${flower_url}"
  demo_pass_step "$artifact_dir" "$DEMO_HTTP_BODY_FILE" "Flower UI reachable"
}

register_step \
  "celery.compose_services" \
  "celery" \
  "false" \
  "Celery section prerequisites are declared in docker-compose.yml" \
  "demo_step_celery_compose_service"

register_step \
  "celery.flower_reachable" \
  "celery" \
  "false" \
  "Flower UI responds when the optional celery stack is running" \
  "demo_step_celery_flower_reachable"
