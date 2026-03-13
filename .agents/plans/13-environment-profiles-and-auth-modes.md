# Plan 13 - Environment Profiles and Auth Modes

## Summary
Add a new append-only milestone `13-environment-profiles-and-auth-modes.md` and update `roadmap.md` to list it after Plan 12. This plan standardizes `dev`, `test`, and `prod` as explicit runtime profiles, keeps a single FastAPI application and a single settings model, and introduces one controlled auth switch so local development can run without tokens while `test` and `prod` continue to exercise real auth behavior.

## Key Changes
- Add explicit environment/profile settings in `app/core/settings.py`:
  - `APP_ENV`: `dev | test | prod`
  - `AUTH_MODE`: `bypass | opaque_tokens`
  - Keep the existing env-driven settings pattern; do not introduce separate settings classes or a second app entrypoint.
  - Default `APP_ENV` remains `dev`.
  - Default `AUTH_MODE` remains `opaque_tokens`; runner commands, not implicit settings defaults, decide when local dev bypass is enabled.
  - Add validation that `AUTH_MODE=bypass` is only valid when `APP_ENV=dev`. Reject bypass in `test` and `prod` at startup.
- Refactor auth resolution in `app/core/dependencies.py` into two paths behind one interface:
  - `opaque_tokens`: preserve current Bearer-token behavior and existing error semantics.
  - `bypass`: return a synthetic `CallerIdentity(token="dev-bypass", scopes=frozenset({"read","publish","admin"}))` without requiring an `Authorization` header.
  - Keep scope enforcement unchanged after caller resolution so route logic and governance rules still use the same `CallerIdentity` flow.
- Keep `test` auth-enabled:
  - Pytest continues to set `AUTH_TOKENS_JSON` and exercises real auth behavior by default.
  - Add targeted tests that explicitly enable `APP_ENV=dev` and `AUTH_MODE=bypass` to verify the local-dev shortcut works, but do not make bypass the default test profile.
- Add explicit local runner profiles in `Makefile` and docs:
  - `make run`: `APP_ENV=dev AUTH_MODE=bypass`
  - `make run-auth`: `APP_ENV=dev AUTH_MODE=opaque_tokens`
  - `make debug`: `APP_ENV=dev AUTH_MODE=bypass`
  - `make test`: `APP_ENV=test AUTH_MODE=opaque_tokens`
  - Production docs specify `APP_ENV=prod AUTH_MODE=opaque_tokens` and secret-managed `AUTH_TOKENS_JSON`
- Document profile intent in README and the new plan:
  - `dev`: fast local iteration, optional auth bypass
  - `test`: realistic auth and policy behavior
  - `prod`: auth required, HTTPS required, no bypass
  - Clarify that local bypass is a developer convenience only and not a deployment mode.

## Public Interfaces and Configuration
- New/standardized environment variables:
  - `APP_ENV=dev|test|prod`
  - `AUTH_MODE=bypass|opaque_tokens`
- Behavioral contract:
  - No HTTP API shape changes
  - No new auth mechanism beyond opaque bearer tokens in non-dev environments
  - In `dev` bypass mode, protected routes remain protected by scope checks, but the caller is injected automatically with full scopes
- Command interface changes:
  - Add `make run-auth` as the explicit local command for exercising token-based auth
  - Preserve existing `make run` as the frictionless local default

## Test Plan
- Unit tests for settings validation:
  - `APP_ENV=dev AUTH_MODE=bypass` is accepted
  - `APP_ENV=test AUTH_MODE=bypass` fails
  - `APP_ENV=prod AUTH_MODE=bypass` fails
  - `AUTH_MODE=opaque_tokens` is accepted in all three environments
- Unit tests for caller resolution:
  - bypass mode returns the synthetic dev caller without credentials
  - opaque token mode preserves current 401/403 behavior for missing token, wrong scheme, invalid token, and insufficient scope
- Interface/API tests:
  - one protected route succeeds in `dev+bypass` without `Authorization`
  - the same route still fails without `Authorization` in `test+opaque_tokens`
  - a route requiring `admin` succeeds in `dev+bypass` to confirm the injected caller carries all scopes
- Regression tests:
  - existing integration tests remain auth-enabled and continue to pass with explicit test env settings
  - no changes to governance/policy decisions once a `CallerIdentity` exists

## Assumptions and Defaults
- Roadmap numbering is append-only, so this is a new Plan 13; existing plans are not renumbered.
- There is no separate `staging` profile in this milestone; staging should use `APP_ENV=prod` semantics unless a later plan introduces a fourth profile.
- The repo keeps one FastAPI app and one settings model; environment behavior is controlled by validated settings and runner commands, not separate codebases.
- Dev bypass injects full scopes intentionally to keep manual local development frictionless; realistic auth testing remains available through `make run-auth`.
- HTTPS remains required for non-local environments and is handled at the edge, not by FastAPI/Uvicorn certificate management.
