# Aptitude Resolver PRD

## 1. Executive Summary

- **Problem Statement**: Agent runtimes need a dedicated runtime-facing service that converts prompt/tool requests into executable skill bundles with deterministic planning and policy checks.
- **Proposed Solution**: Define `aptitude-resolver` as the MCP/CLI orchestration layer that normalizes requests, calls `aptitude-server` APIs, applies pluggable policy/scanner/selection components, and returns execution plans.
- **Success Criteria**:
  - End-to-end `tool_call -> execution_plan` p95 <= 800 ms with warm cache and bundles <= 100 skills.
  - CLI and MCP produce identical selected bundle hash for equivalent input >= 99.9% of runs.
  - Plugin chain failure isolation: >= 99% of plugin failures do not crash resolver process.
  - 0 direct writes from resolver to server persistence layers (API-only interaction).
  - Security scanner plugin blocks 100% of known-deny signatures in validation test set.
- **In Scope**: Runtime request normalization, server API consumption, plugin orchestration, execution-plan assembly, and resolver-local caching/observability.
- **Out of Scope**: Artifact publication/storage, canonical dependency graph persistence, and server governance policy authoring.
- **Related PRD**: Server ownership and API contracts are defined in [`repository-prd.md`](./repository-prd.md).

## 2. User Experience & Functionality

- **User Personas**:
  - Agent/application developer invoking skill resolution through CLI or MCP.
  - Security engineer enforcing pre-execution checks.
  - Platform engineer extending resolver behavior with plugins.

- **User Stories**:
  - As an agent developer, I want to send a prompt/tool call and receive the best executable skill bundle so that I can run tasks without manual dependency assembly.
  - As a security engineer, I want to plug in scanners and policy checks so that unsafe or non-compliant bundles are blocked before execution.
  - As a platform engineer, I want overlap scoring against currently loaded skills so that redundant capabilities are avoided.
  - As an operator, I want full trace output from request to selected bundle so that failures are diagnosable.

- **Acceptance Criteria**:
  - Resolver exposes both MCP tool and CLI command with consistent request/response schema.
  - Resolver calls server resolve endpoints and never bypasses server policy gates.
  - Plugin interface supports pre-resolve, post-resolve, and pre-execution hooks.
  - Overlap scorer plugin can compare candidate bundles with active runtime skill set and return deterministic exclusion recommendations.
  - On plugin failure, resolver returns structured degradation/failure reason without corrupting state.
  - Resolver output includes `ResolvedBundle`, plugin decisions, and execution plan trace ID.

- **Non-Goals**:
  - Acting as authoritative skill artifact source of truth.
  - Maintaining long-term graph metadata or artifact persistence.
  - Replacing server governance, trust, or versioning rules.

## 3. AI System Requirements (If Applicable)

- **Tool Requirements**:
  - Input adapters: MCP server and CLI command surface.
  - Server client SDK/API for resolve/download/report operations.
  - Plugin runtime interface for scanners, overlap scorers, policy extensions, and execution adapters.
  - Local cache for resolved bundles/artifacts with TTL and hash validation.
  - Observability hooks for traces, metrics, and structured logs.

- **Evaluation Strategy**:
  - Request quality benchmark: percentage of prompts mapped to expected skill families on labeled dataset.
  - Latency/load tests for MCP and CLI paths independently and combined.
  - Plugin reliability tests: fail-open/fail-closed behavior by plugin policy class.
  - Regression suite ensuring identical resolution outcome for same input/context and server snapshot.

## 4. Technical Specifications

- **Architecture Overview**:
  - `MCP/CLI Interface` -> `Request Normalizer` -> `Server Client` -> `Plugin Orchestrator` -> `Execution Planner` -> `Runtime Adapter`.
  - Resolver is a coordination layer and plugin machine that consumes server contracts and does not persist authoritative artifact metadata.

```mermaid
flowchart LR
  Client["MCP Host / CLI Caller"] --> Resolver["aptitude-resolver"]
  Resolver --> Repo["aptitude-server API"]
  Resolver --> Plugins["Policy + Scanner + Overlap Plugins"]
  Resolver --> Runtime["Execution Adapter"]
```

- **Integration Points**:
  - Server APIs: resolve, fetch bundle/artifacts, metadata/report retrieval.
  - Authentication: service token for resolver-to-server calls; optional user identity passthrough for audit context.
  - Plugin integrations: local process plugins in MVP; remote plugin transport optional in later versions.
  - Runtime integrations: MCP host applications, CI pipelines, local developer terminals.

- **Security & Privacy**:
  - Scoped credentials and least-privilege API access.
  - Configurable plugin isolation level (subprocess boundary in MVP for untrusted plugins).
  - Prompt and execution trace retention policy with redaction support for sensitive fields.
  - Signed plugin manifests for trusted plugin loading in enterprise mode.

## 5. Risks & Roadmap

- **Phased Rollout**:
  - **MVP**: CLI + MCP interface, server resolve integration, core plugin hooks, basic trace logging.
  - **v1.1**: security scanner plugin pack, overlap scoring plugin, cache controls, richer policy modes.
  - **v2.0**: distributed plugin execution, multi-repo federation support, policy marketplace.

- **Technical Risks**:
  - Plugin-chain latency can dominate end-to-end SLA without strict hook budgets.
  - Resolver/server schema drift can break deterministic behavior across versions.
  - Overlap-scoring heuristics may suppress needed capabilities if benchmark coverage is weak.
  - Excessive local caching can serve stale decisions without robust invalidation.

## 6. Boundary Contract & Exit Criteria

- **Server Dependency Contract (Input to Resolver)**:
  - Resolver integrates through server versioned APIs/SDK contracts only, as defined in [`repository-prd.md`](./repository-prd.md).
  - Resolver treats `ResolvedBundle`, `ResolutionReport`, error taxonomy, and `repo_state_id` as source-of-truth inputs.
  - Resolver must not read or write server DB tables, artifact storage, or internal services directly.

- **Resolver Exit Criteria (After Server Gate)**:
  - Server exit criteria from [`repository-prd.md`](./repository-prd.md) are fully met before resolver MVP build starts.
  - Contract compatibility tests pass against server `v1` fixtures in CI.
  - Resolver failure handling is proven: server/API/plugin errors return structured degradation output with trace IDs.
  - End-to-end SLA is met (`tool_call -> execution_plan` p95 <= 800 ms under target bundle size).
  - Architecture guardrails are enforced (lint/tests preventing server persistence-layer coupling).

```mermaid
sequenceDiagram
  participant Team as Platform Team
  participant Repo as aptitude-server
  participant Resolver as aptitude-resolver
  Team->>Repo: Implement and validate contract v1
  Repo-->>Team: Server exit criteria passed
  Team->>Resolver: Start resolver MVP implementation
  Resolver->>Repo: Resolve/fetch via server APIs only
```

## Assumptions to Confirm

- Resolver is stateless by default except for bounded local cache.
- Initial plugin model is in-process/subprocess Python interface before remote plugin protocol.
