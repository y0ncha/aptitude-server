# Repo Meta Memory

- Product: Aptitude skill repository.
- Runtime: Go service (primary).
- Core principles: immutability, determinism, explicit relationships, governance, auditability.
- Architecture source of truth: `docs/overview.md`.
- Planning location: `.agents/plans/`.
- Layering rule: `interface -> core` and persistence access only via core ports, wired in `app/main.py`.
