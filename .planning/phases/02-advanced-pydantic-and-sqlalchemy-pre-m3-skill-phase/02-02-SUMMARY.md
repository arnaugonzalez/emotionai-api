---
phase: 02-advanced-pydantic-and-sqlalchemy-pre-m3-skill-phase
plan: "02"
subsystem: api
tags: [pydantic-v2, model_validator, field_validator, pydantic-settings, SettingsConfigDict, profile-dtos, settings, testing]

requires:
  - phase: 02-advanced-pydantic-and-sqlalchemy-pre-m3-skill-phase
    provides: "Plan 01 established Pydantic v2 basics and test infrastructure"

provides:
  - "UserProfileRequest @model_validator enforcing at-least-one-field constraint"
  - "TherapyPreferences @field_validator for allowed communication styles"
  - "ProfileStatusResponse @field_validator for 0-100 completeness range"
  - "UserProfileResponse with from_attributes=True for ORM compatibility"
  - "Settings migrated from inner class Config to model_config = SettingsConfigDict(...)"
  - "trusted_hosts field accepts comma-separated env var (Union[List[str], str] type)"
  - "31 unit tests covering all validator and config behavior"

affects:
  - "profile endpoints (routers/profile.py uses .model_dump() directly)"
  - "all services importing Settings (model_config is fully backward-compatible)"
  - "future ORM-to-DTO mapping (from_attributes=True enables direct ORM construction)"

tech-stack:
  added: []
  patterns:
    - "@model_validator(mode='after') for cross-field constraints on request DTOs"
    - "@field_validator with allowed-values whitelist for enum-like string fields"
    - "model_config = SettingsConfigDict(...) instead of inner class Config for Pydantic v2"
    - "Union[List[str], str] field type to bypass pydantic-settings JSON-decode for comma-separated env vars"

key-files:
  created:
    - tests/infrastructure/test_settings.py
  modified:
    - src/application/dtos/profile_dtos.py
    - src/presentation/api/routers/profile.py
    - src/infrastructure/config/settings.py
    - tests/application/dtos/test_profile_dtos.py

key-decisions:
  - "Union[List[str], str] used for trusted_hosts field — pydantic-settings v2 EnvSettingsSource JSON-decodes List[str] fields before validators run; Union bypasses that path"
  - "ALLOWED_COMMUNICATION_STYLES defined inline inside field_validator (not as ClassVar) to avoid Pydantic model field conflict"
  - "_safe_model_to_dict shim replaced by direct .model_dump() — all callers are fully Pydantic v2, shim is dead code"
  - "existing test using communication_style='calm' updated to 'supportive' to match new validated allowed-values list"

patterns-established:
  - "TDD: write failing tests first, verify RED, implement GREEN, verify GREEN"
  - "Test classes grouped by model: TestUserProfileRequest, TestTherapyPreferences, TestProfileStatusResponse, TestUserProfileResponse, TestSettingsModelConfig"
  - "monkeypatch.setenv pattern for Settings instantiation in unit tests"

requirements-completed: [PYD-02, PYD-03]

duration: 7min
completed: 2026-03-21
---

# Phase 02 Plan 02: Pydantic v2 Validators and Settings Migration Summary

**Pydantic v2 validators added to profile DTOs (cross-field, field-level, ORM config) and Settings migrated from inner class Config to SettingsConfigDict with comma-separated env var fix**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-21T17:25:34Z
- **Completed:** 2026-03-21T17:32:13Z
- **Tasks:** 2
- **Files modified:** 4 modified, 1 created

## Accomplishments

- Added `@model_validator(mode='after')` to `UserProfileRequest` — all-None request body now raises `ValidationError`
- Added `@field_validator` to `TherapyPreferences` enforcing allowed communication styles (`["supportive", "direct", "analytical", "casual", "formal"]`)
- Added `@field_validator` to `ProfileStatusResponse` enforcing `profile_completeness` in `[0, 100]`
- Added `model_config = ConfigDict(from_attributes=True)` to `UserProfileResponse` for SQLAlchemy ORM compatibility
- Removed `_safe_model_to_dict` v1/v2 compatibility shim from `profile.py`; replaced 3 call sites with `.model_dump()`
- Migrated `Settings.class Config` to `model_config = SettingsConfigDict(...)` in pydantic-settings v2 style
- Fixed pre-existing `trusted_hosts` parsing bug: `Union[List[str], str]` bypasses pydantic-settings JSON-decode path
- 31 tests total (22 profile DTO + 9 settings) all pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Add validators to profile DTOs and write tests** - `dc82240` (feat)
2. **Task 2: Migrate Settings.Config to model_config and write tests** - `d7dd952` (feat)

_Note: TDD tasks — tests written before implementation in both cases_

## Files Created/Modified

- `src/application/dtos/profile_dtos.py` — added `@model_validator`, two `@field_validator`s, `ConfigDict(from_attributes=True)`, `Union` import
- `src/presentation/api/routers/profile.py` — removed `_safe_model_to_dict`, replaced 3 call sites with `.model_dump()`
- `src/infrastructure/config/settings.py` — replaced `class Config` with `model_config = SettingsConfigDict(...)`, fixed `trusted_hosts` type
- `tests/application/dtos/test_profile_dtos.py` — 22 tests across 4 test classes (updated "calm" to "supportive")
- `tests/infrastructure/test_settings.py` — 9 tests covering model_config, comma-parse, env detection (new file)

## Decisions Made

- `Union[List[str], str]` for `trusted_hosts`: pydantic-settings v2 `EnvSettingsSource` tries to `json.loads()` all `List[str]` fields, failing on comma-separated strings. Using `Union` makes the field non-complex, bypassing JSON-decode, letting the `@field_validator(mode='before')` handle splitting.
- Communication styles defined inline in the validator (not as `ClassVar`) to avoid Pydantic treating them as model fields.
- `_safe_model_to_dict` was dead code — all three callers were already Pydantic v2; `.model_dump()` is the direct replacement.
- Updated existing test using `communication_style="calm"` to `"supportive"` since `"calm"` is now rejected by the new validator.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed trusted_hosts comma-separated env var parsing**
- **Found during:** Task 2 (Settings migration)
- **Issue:** The `@field_validator("trusted_hosts", mode="before")` in the original code was silently broken — pydantic-settings v2 `EnvSettingsSource` calls `json.loads()` on `List[str]` fields before validators run, raising `JSONDecodeError` for comma-separated strings like `"a.com,b.com"`
- **Fix:** Changed field type from `List[str]` to `Union[List[str], str]` — non-complex union prevents JSON-decode path; existing field_validator then splits on comma
- **Files modified:** `src/infrastructure/config/settings.py`
- **Verification:** `test_trusted_hosts_comma_parse` and `test_trusted_hosts_single_value` both pass
- **Committed in:** `d7dd952` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fix corrects a pre-existing bug that made `TRUSTED_HOSTS=a.com,b.com` crash in production. No scope creep.

## Issues Encountered

- pydantic-settings v2 `EnvSettingsSource` JSON-decodes `List[str]` fields before field validators execute — `mode='before'` validators are not called early enough for list-type env vars. Resolved by using `Union[List[str], str]` as documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Profile DTOs are fully Pydantic v2 with validators — ready for M3 feature work
- Settings config is idiomatic pydantic-settings v2 — `model_config` pattern established for future settings expansion
- All 360 tests pass (3 pre-existing XPASS failures in `tests/domain/test_user.py` are unchanged pre-existing issues)

---
*Phase: 02-advanced-pydantic-and-sqlalchemy-pre-m3-skill-phase*
*Completed: 2026-03-21*
