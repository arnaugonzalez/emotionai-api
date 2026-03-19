# Deferred Items

## Out-of-scope verification blockers

- Full regression suite currently ends with three pre-existing `XPASS(strict)` results in `tests/domain/test_user.py`:
  - `test_update_profile_replaces_profile`
  - `test_update_profile_emits_event`
  - `test_is_profile_complete_false_for_empty_profile`
  These are Milestone 1 domain bugs already documented in `STATE.md`, not regressions introduced by `m2s1-01`.

- Manual docker smoke test for Prometheus/Grafana could not run in this environment because Docker is not reachable:
  `dial unix /var/run/docker.sock: connect: no such file or directory`
