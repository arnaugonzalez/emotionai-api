# Deferred Items — m1s4-router-integration-tests

## passlib + bcrypt version incompatibility

**Found during:** m1s4-01 Task 2 (auth integration tests)
**Severity:** P1 — production cannot hash passwords

**Issue:** The installed `bcrypt` library version (>=4.0) removed `__about__` attribute.
`passlib`'s bcrypt backend calls `_bcrypt.__about__.__version__` during
initialization, which raises `AttributeError`. This triggers `detect_wrap_bug()`
to fail with `ValueError: password cannot be longer than 72 bytes`.

**Impact:** In production, any call to `pwd_context.hash()` or `pwd_context.verify()`
will raise a `ValueError`, making login and registration impossible.

**Workaround in tests:** Patched `pwd_context.hash` and `pwd_context.verify` in
`src.presentation.api.routers.auth` module namespace.

**Fix options:**
1. Pin `bcrypt<4.0` in `requirements.txt` (quickest fix)
2. Replace `passlib` with `bcrypt` directly: `bcrypt.hashpw()` / `bcrypt.checkpw()`
3. Upgrade to a maintained passlib fork (e.g., `passlib2`)

**Files to change:** `requirements.txt`, `src/presentation/api/routers/auth.py`
