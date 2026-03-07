# Aptitude Scope: Server vs Resolver

## Purpose

This document defines the hard boundary between `aptitude-server` and `aptitude-resolver` so responsibilities do not overlap.

## Maven Analogy

- `aptitude-server` = Maven Artifactory (authoritative package/metadata/graph source).
- `aptitude-resolver` = Maven Builder (client-facing orchestrator that consumes packages and builds execution plans).

## Ownership Matrix

| Capability | Server Owner | Resolver Owner | Notes |
| --- | --- | --- | --- |
| Skill artifact storage (immutable versions) | Yes | No | Resolver consumes only |
| Upload / publish workflow | Yes | No | Includes validation and provenance |
| Download artifact / bundle APIs | Yes | No | Resolver calls these APIs |
| Dependency/conflict/overlap graph source of truth | Yes | No | Resolver may post-process but not persist authority |
| Metadata index and evaluation signals | Yes | No | Resolver reads signals |
| Optional RAG index for retrieval hints | Yes (optional) | No | Advisory signal only |
| Deterministic dependency resolution contract | Yes | Partial | Resolver can request, not redefine |
| Prompt/tool-call interface (MCP/CLI) | No | Yes | Primary user entrypoint |
| Plugin machine (security scanner, overlap scorer, policy hooks) | No | Yes | Extensible runtime behavior |
| Runtime execution planning | No | Yes | Builds executable plan from resolved bundle |
| Governance policy enforcement at source | Yes | Partial | Resolver can add stricter local gates |
| Audit of server lifecycle events | Yes | No | Publish/deprecate/archive/resolve in server |
| Request trace across plugins/runtime | No | Yes | Resolver trace and diagnostics |

## System Contract (Request Flow)

1. Client sends tool call + prompt to resolver (`MCP` or `CLI`).
2. Resolver normalizes request and asks server for deterministic resolution.
3. Server returns `ResolvedBundle` + `ResolutionReport` (+ optional retrieval hints).
4. Resolver executes plugin chain (security scan, overlap scoring, policy checks).
5. Resolver builds execution plan and returns output/trace to client.
6. Resolver never writes directly to server DB; all interaction is API-based.

## API and Data Contract

- Server must expose:
  - `POST /skills/publish`
  - `GET /skills/{id}/{version}`
  - `POST /resolve`
  - `GET /bundles/{bundle_id}` (or equivalent artifact download)
  - `GET /reports/{resolution_id}`
- Resolver must expose:
  - MCP tool endpoint: `resolve_and_plan`
  - CLI command: `aptitude resolve "<prompt>"`
  - Structured output: `bundle_hash`, selected skills, plugin decisions, execution plan, trace ID

## Boundary Rules (Hard)

- Resolver cannot mutate skill artifacts, metadata authority, or dependency graph source-of-truth.
- Server cannot execute runtime plugin chains or user prompt orchestration.
- Any overlap-scoring logic that changes final runtime selection must be recorded in resolver trace output.
- Deterministic package selection rules live in server policy; resolver-specific filtering must be additive and explicit.

## Non-Goals

- Building a monolith that combines server persistence and resolver runtime in one deployable.
- Letting plugin behavior silently override server governance decisions.
- Making optional RAG retrieval a mandatory dependency for MVP resolution.

## Assumptions to Validate

- Initial target scale: 10k skills, 100-200 skill bundle upper bound.
- Resolver plugin budget target: <= 150 ms median overhead per plugin.
- RAG remains disabled by default and enabled only after benchmark validation.
