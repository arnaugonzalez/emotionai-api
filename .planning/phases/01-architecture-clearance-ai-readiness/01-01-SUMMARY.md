---
phase: 01-architecture-clearance-ai-readiness
plan: "01"
subsystem: infrastructure/application
tags: [cleanup, imports, tagging, auth, otel]
dependency_graph:
  requires: [m2s3]
  provides: [clean-import-graph, canonical-tagging-interface, canonical-auth-dep]
  affects:
    - src/infrastructure/container.py
    - src/application/tagging/services/tagging_service.py
    - src/infrastructure/tagging/services/openai_tagging_service.py
    - src/presentation/api/routers/deps.py
    - main.py
tech_stack:
  added: []
  patterns:
    - Feature-scoped canonical interface replaces root-level service file
    - Direct auth dependency import removes indirection wrapper
key_files:
  created: []
  modified:
    - src/application/tagging/services/tagging_service.py
    - src/infrastructure/tagging/services/openai_tagging_service.py
    - src/infrastructure/container.py
    - src/presentation/api/routers/deps.py
    - main.py
    - src/presentation/dependencies.py
    - src/application/chat/use_cases/agent_chat_use_case.py
    - src/presentation/api/routers/auth.py
    - src/presentation/api/routers/breathing.py
    - src/presentation/api/routers/chat.py
    - src/presentation/api/routers/data.py
    - src/presentation/api/routers/dev_seed.py
    - src/presentation/api/routers/records.py
    - src/presentation/api/routers/usage.py
    - tests/unit/test_tagging_spans.py
  deleted:
    - src/application/services/tagging_service.py
    - src/infrastructure/services/openai_tagging_service.py
decisions:
  - feature-scoped tagging_service.py is now canonical ITaggingService interface; root-level file deleted
  - OTEL span (emotionai.tagging.classify) ported to new canonical OpenAITaggingService location
  - get_current_user_id imported directly from src.presentation.dependencies in all routers and main.py; deps.py wrapper removed
metrics:
  duration: "~15 minutes"
  completed: "2026-03-20"
  tasks_completed: 2
  files_changed: 17
---

# Phase 01 Plan 01: Code Cleanup and Import Consolidation Summary

**One-liner:** Eliminated duplicate tagging service files and auth wrapper by promoting feature-scoped ITaggingService to canonical, porting OTEL spans, and wiring all routers directly to dependencies.py.

---

## Tasks Completed

### Task 1: Promote feature-scoped tagging_service.py to canonical, port OTEL, and consolidate imports

- Expanded `src/application/tagging/services/tagging_service.py` from a 3-line re-export shim to the full 130-line `ITaggingService` ABC + `TagExtractionResult` class definitions
- Deleted root-level `src/application/services/tagging_service.py`
- Updated 3 importers of the root-level path: `container.py`, `dependencies.py`, `agent_chat_use_case.py`
- Added `from ....infrastructure.telemetry.tracing import get_tracer` and `_tracer = get_tracer(__name__)` to `src/infrastructure/tagging/services/openai_tagging_service.py`
- Ported `emotionai.tagging.classify` OTEL span (with all attributes: `input.length`, `llm.model`, `tagging.content_type`, `tagging.has_urgency_keywords`, `llm.total_tokens`, `tagging.tag_count`) to the feature-scoped file
- Deleted `src/infrastructure/services/openai_tagging_service.py` (old location)
- Updated `container.py` to import `OpenAITaggingService` from `.tagging.services.openai_tagging_service`

### Task 2: Consolidate auth get_current_user_id and update router imports

- Updated 7 routers (auth, breathing, chat, data, dev_seed, records, usage) to import `get_current_user_id` from `...dependencies` directly instead of `deps`
- Removed the 4-line `get_current_user_id` wrapper function and its `_jwt_get_current_user_id` import from `deps.py`
- Updated `main.py` to import `get_current_user_id` from `src.presentation.dependencies`

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated test_tagging_spans.py import path**
- **Found during:** Task 2 verification (pytest run)
- **Issue:** `tests/unit/test_tagging_spans.py` imported `OpenAITaggingService` from the old `src.infrastructure.services.openai_tagging_service` path, causing collection error after Task 1 deleted that file
- **Fix:** Updated import to `src.infrastructure.tagging.services.openai_tagging_service`
- **Files modified:** `tests/unit/test_tagging_spans.py`
- **Commit:** 6773d95

**2. [Rule 3 - Blocking] Updated main.py import path for get_current_user_id**
- **Found during:** Task 2 verification (pytest run)
- **Issue:** `main.py` imported `get_current_user_id` from `src.presentation.api.routers.deps` — not listed in the plan's 8-router list, but must be fixed for tests to pass
- **Fix:** Changed import to `from src.presentation.dependencies import get_current_user_id`
- **Files modified:** `main.py`
- **Commit:** 6773d95

---

## Verification Results

```
python -c "from src.infrastructure.container import ApplicationContainer"  # OK
grep -rn "from.*application\.services\.tagging_service" src/              # 0 results
grep -rn "from.*infrastructure.services.openai_tagging" src/              # 0 results
grep -rn "from .deps import.*get_current_user_id" src/presentation/       # 0 results
pytest tests/ -q                                                           # 308 passed, 3 pre-existing XPASS(strict) failures
```

Pre-existing test failures (carried forward from milestone 1, not caused by this plan):
- `tests/domain/test_user.py::test_update_profile_replaces_profile` — XPASS(strict)
- `tests/domain/test_user.py::test_update_profile_emits_event` — XPASS(strict)
- `tests/domain/test_user.py::test_is_profile_complete_false_for_empty_profile` — XPASS(strict)

---

## Self-Check: PASSED

Files verified to exist:
- `src/application/tagging/services/tagging_service.py` — contains `class ITaggingService(ABC)` and `class TagExtractionResult`
- `src/infrastructure/tagging/services/openai_tagging_service.py` — contains `_tracer = get_tracer(__name__)`
- `src/infrastructure/container.py` — contains `from .tagging.services.openai_tagging_service import OpenAITaggingService`

Files verified deleted:
- `src/application/services/tagging_service.py` — does not exist
- `src/infrastructure/services/openai_tagging_service.py` — does not exist

Commit verified: `6773d95` exists in `git log --oneline`
