"""Shared exact-read governance and audit orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.audit_events import (
    ExactReadSurface,
    build_exact_read_audit_event,
    build_exact_read_denied_audit_event,
)
from app.core.governance import (
    CallerIdentity,
    GovernancePolicy,
    LifecycleStatus,
    PolicyViolation,
    TrustTier,
)
from app.core.ports import AuditPort


@dataclass(frozen=True, slots=True)
class ExactReadAuditInfo:
    """Minimal audit context shared by exact-read surfaces."""

    slug: str
    version: str
    lifecycle_status: LifecycleStatus
    trust_tier: TrustTier


def enforce_and_audit_exact_read(
    *,
    caller: CallerIdentity,
    governance_policy: GovernancePolicy,
    audit_recorder: AuditPort,
    audit_info: ExactReadAuditInfo,
    surface: ExactReadSurface,
) -> None:
    """Apply exact-read policy and emit the corresponding audit event."""
    try:
        governance_policy.ensure_exact_read_allowed(
            caller=caller,
            lifecycle_status=audit_info.lifecycle_status,
        )
    except PolicyViolation as exc:
        denied_event = build_exact_read_denied_audit_event(
            caller=caller,
            slug=audit_info.slug,
            version=audit_info.version,
            lifecycle_status=audit_info.lifecycle_status,
            trust_tier=audit_info.trust_tier,
            surface=surface,
            policy_profile=governance_policy.profile_name,
            reason_code=exc.code,
        )
        audit_recorder.record_event(
            event_type=denied_event.event_type,
            payload=denied_event.payload,
        )
        raise

    event = build_exact_read_audit_event(
        caller=caller,
        slug=audit_info.slug,
        version=audit_info.version,
        lifecycle_status=audit_info.lifecycle_status,
        trust_tier=audit_info.trust_tier,
        surface=surface,
        policy_profile=governance_policy.profile_name,
    )
    audit_recorder.record_event(event_type=event.event_type, payload=event.payload)
