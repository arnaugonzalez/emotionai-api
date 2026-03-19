---
phase: m2s3-opentelemetry-tracing
plan: "02"
subsystem: observability
tags: [opentelemetry, tracing, langchain, tagging, unit-tests, learning-guide]
dependency_graph:
  requires: [m2s3-01]
  provides: [manual-spans-langchain, manual-spans-tagging, span-unit-tests, otel-learning-guide]
  affects: [src/infrastructure/services/langchain_agent_service.py, src/infrastructure/services/openai_tagging_service.py]
tech_stack:
  added: []
  patterns:
    - "Context manager spans (not decorator) for async functions"
    - "InMemorySpanExporter injected directly on service instance for test isolation"
    - "Class-level _tracer = get_tracer(__name__) for per-module instrumentation scope"
key_files:
  created:
    - tests/unit/test_langchain_spans.py
    - tests/unit/test_tagging_spans.py
    - docs/learning/opentelemetry.md
  modified:
    - src/infrastructure/services/langchain_agent_service.py
    - src/infrastructure/services/openai_tagging_service.py
decisions:
  - "Inject test provider tracer directly onto service._tracer instance rather than swapping global TracerProvider — OTEL SDK prevents TracerProvider overrides after first real SDK provider is set"
  - "Span fixtures yield (exporter, provider) tuple instead of just exporter so tests can inject provider.get_tracer() into service instances"
  - "emotionai.chat.llm_generate span wraps entire send_message body including context build, not just the llm_service.generate_therapy_response call — parent span captures total LLM work time"
metrics:
  duration_seconds: 734
  completed_date: "2026-03-19"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 2
---

# Phase m2s3 Plan 02: Manual OTEL Spans and Learning Guide Summary

Manual OpenTelemetry spans added to `LangChainAgentService` (`emotionai.chat.llm_generate`) and `OpenAITaggingService` (`emotionai.tagging.classify`) using context manager form with unit tests via `InMemorySpanExporter` and a 231-line learning guide.

---

## Tasks Completed

| Task | Name | Commit | Key files |
|------|------|--------|-----------|
| 1 | Add manual spans to LangChain and tagging services | `84ca098` | langchain_agent_service.py, openai_tagging_service.py |
| 2 | Write span unit tests and learning guide | `4b129b2` | test_langchain_spans.py, test_tagging_spans.py, docs/learning/opentelemetry.md |

---

## What Was Built

### Task 1: Manual spans in service files

`LangChainAgentService` — `emotionai.chat.llm_generate` span on `send_message`:
- Attributes: `user.id`, `llm.model` ("gpt-4"), `chat.agent_type`, `chat.therapeutic_approach`, `crisis_detected` (only when True)
- Class-level `_tracer = get_tracer(__name__)` — instrumentation scope is the module name

`OpenAITaggingService` — `emotionai.tagging.classify` span on `extract_tags_from_message`:
- Attributes: `input.length`, `llm.model` ("gpt-4o-mini"), `tagging.content_type`, `tagging.has_urgency_keywords` (only when True), `tagging.tag_count`, `llm.total_tokens`
- Same class-level tracer pattern

Both use `with self._tracer.start_as_current_span("...") as span:` — the context manager form required for async functions (decorator form reports 0-second durations).

### Task 2: Unit tests and learning guide

`tests/unit/test_langchain_spans.py` — 6 tests covering:
- Span name presence (`emotionai.chat.llm_generate`)
- `user.id`, `llm.model`, `chat.agent_type` attributes
- Span completion (`end_time` is set)
- `crisis_detected` attribute when crisis response returned

`tests/unit/test_tagging_spans.py` — 4 tests covering:
- Span name presence (`emotionai.tagging.classify`)
- `input.length`, `llm.model` attributes
- Span completion

`docs/learning/opentelemetry.md` — 231 lines covering: three observability pillars, trace/span anatomy, parent-child hierarchy in EmotionAI, context propagation in asyncio, lifespan init rationale, async span pattern (correct vs wrong), `InMemorySpanExporter` test pattern, span attribute conventions, common mistakes.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] InMemorySpanExporter fixture needed provider injection pattern**
- **Found during:** Task 2 (test run)
- **Issue:** OTEL SDK prevents overriding a `TracerProvider` once a real SDK provider has been set. After the first test's fixture restores the "original" provider, subsequent `trace.set_tracer_provider()` calls are silently ignored (with a warning). Tests 2-6 got empty span lists.
- **Fix:** Changed fixture to yield `(exporter, provider)` tuple. Each `_make_service()` function injects the test provider's tracer directly: `service._tracer = provider.get_tracer(__name__)`. This bypasses the global provider restriction entirely.
- **Files modified:** `tests/unit/test_langchain_spans.py`, `tests/unit/test_tagging_spans.py`
- **Commit:** `4b129b2` (included in Task 2 commit, no separate commit needed — fix was discovered during initial test authoring)

---

## Verification Results

- `pytest tests/unit/` — 14 passed (6 langchain + 4 tagging + 4 tracing setup)
- `pytest tests/ -q` — 308 passed, 3 pre-existing XPASS failures in `tests/domain/test_user.py` (documented in STATE.md, not regressions from this plan)
- `grep "start_as_current_span" src/infrastructure/services/langchain_agent_service.py` — context manager form present
- `grep "start_as_current_span" src/infrastructure/services/openai_tagging_service.py` — context manager form present
- `docs/learning/opentelemetry.md` — 231 lines (exceeds 100-line minimum)

---

## Self-Check: PASSED

Files exist:
- `tests/unit/test_langchain_spans.py` — FOUND
- `tests/unit/test_tagging_spans.py` — FOUND
- `docs/learning/opentelemetry.md` — FOUND

Commits exist:
- `84ca098` — FOUND
- `4b129b2` — FOUND
