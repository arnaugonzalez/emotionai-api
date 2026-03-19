#!/usr/bin/env bash

demo_step_metrics_endpoint() {
  local _step_id="$1"
  local artifact_dir="$2"

  demo_assert_http_200 "$artifact_dir" "/metrics" \
    "Start the API with Prometheus instrumentation enabled before running the metrics section."
}

demo_step_metrics_format() {
  local _step_id="$1"
  local artifact_dir="$2"

  demo_assert_http_200 "$artifact_dir" "/metrics" \
    "Start the API with Prometheus instrumentation enabled before running the metrics section." || return 1
  demo_assert_content_type_contains "$artifact_dir" "text/plain" \
    "Check the /metrics route content type and ensure Prometheus text exposition is being served." || return 1

  demo_assert_body_contains "$artifact_dir" "# HELP" "Prometheus HELP headers" \
    "Check the /metrics handler output and confirm Prometheus text exposition is enabled." || return 1
  demo_assert_body_contains "$artifact_dir" "# TYPE" "Prometheus TYPE headers" \
    "Check the /metrics handler output and confirm Prometheus text exposition is enabled." || return 1

  demo_pass_step "$artifact_dir" "$DEMO_HTTP_BODY_FILE"
}

demo_step_metrics_required_families() {
  local _step_id="$1"
  local artifact_dir="$2"

  demo_assert_http_200 "$artifact_dir" "/metrics" \
    "Start the API with Prometheus instrumentation enabled before running the metrics section." || return 1

  demo_assert_body_contains "$artifact_dir" "emotionai_chat_requests_total" "metric family emotionai_chat_requests_total" \
    "Verify custom Prometheus counters are registered during FastAPI startup." || return 1
  demo_assert_body_contains "$artifact_dir" "emotionai_active_users_gauge" "metric family emotionai_active_users_gauge" \
    "Verify the active-user in-progress gauge is initialized during startup." || return 1
  demo_assert_body_contains "$artifact_dir" "emotionai_openai_latency_seconds" "metric family emotionai_openai_latency_seconds" \
    "Verify the OpenAI latency histogram is initialized during startup." || return 1

  demo_pass_step "$artifact_dir" "$DEMO_HTTP_BODY_FILE"
}

register_step \
  "metrics.endpoint" \
  "metrics" \
  "true" \
  "Metrics endpoint returns HTTP 200" \
  "demo_step_metrics_endpoint"

register_step \
  "metrics.format" \
  "metrics" \
  "true" \
  "Metrics body includes Prometheus HELP and TYPE headers" \
  "demo_step_metrics_format"

register_step \
  "metrics.required_families" \
  "metrics" \
  "true" \
  "Metrics body exposes required EmotionAI metric families" \
  "demo_step_metrics_required_families"
