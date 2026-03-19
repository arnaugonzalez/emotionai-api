---
phase: m2s2
slug: celery-redis-task-queue
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase m2s2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest -q` |
| **Full suite command** | `pytest --cov=src --cov-report=term-missing` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest -q tests/infrastructure/tasks -q`
- **After every plan wave:** Run `pytest --cov=src --cov-report=term-missing`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| m2s2-01-01 | 01 | 1 | m2s2-01 | unit | `pytest tests/infrastructure/tasks/test_notification_tasks.py -q` | ❌ W0 | ⬜ pending |
| m2s2-01-02 | 01 | 1 | m2s2-02 | integration | `pytest tests/infrastructure/tasks/test_task_dispatch.py -q` | ❌ W0 | ⬜ pending |
| m2s2-01-03 | 01 | 1 | m2s2-03 | smoke | `celery -A src.infrastructure.tasks.worker.celery_app inspect ping` | ❌ W0 | ⬜ pending |
| m2s2-01-04 | 01 | 2 | m2s2-04 | manual | `docker compose up -d flower && open http://localhost:5555` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠ flaky*

---

## Wave 0 Requirements

- [ ] `tests/infrastructure/tasks/test_notification_tasks.py` — stubs for m2s2-01
- [ ] `tests/infrastructure/tasks/test_task_dispatch.py` — integration harness for m2s2-02
- [ ] `src/infrastructure/tasks/worker.py` import smoke test — verifies Celery app boot for m2s2-03

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Flower UI displays completed task execution | m2s2-04 | UI behavior is operational/visual and not part of test suite | `docker compose up -d redis celery_worker flower`, trigger record endpoint, verify task in `http://localhost:5555` |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
