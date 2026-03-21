"""Publish-surface API mappers."""

from __future__ import annotations

from app.core.skill_models import (
    CreateSkillVersionCommand,
    ProvenanceMetadata,
    SkillContentInput,
    SkillGovernanceInput,
    SkillMetadataInput,
    SkillRelationshipSelector,
    SkillRelationshipsInput,
)
from app.interface.dto.skills_publish import (
    DependencySelectorRequest,
    ExactRelationshipSelectorRequest,
    SkillGovernanceRequest,
    SkillVersionCreateRequest,
)


def to_create_command(slug: str, request: SkillVersionCreateRequest) -> CreateSkillVersionCommand:
    """Translate validated API models into immutable core publish commands."""
    return CreateSkillVersionCommand(
        slug=slug,
        intent=request.intent,
        version=request.version,
        content=SkillContentInput(raw_markdown=request.content.raw_markdown),
        metadata=SkillMetadataInput(
            name=request.metadata.name,
            description=request.metadata.description,
            tags=tuple(request.metadata.tags),
            headers=request.metadata.headers,
            inputs_schema=request.metadata.inputs_schema,
            outputs_schema=request.metadata.outputs_schema,
            token_estimate=request.metadata.token_estimate,
            maturity_score=request.metadata.maturity_score,
            security_score=request.metadata.security_score,
        ),
        governance=_governance_input(request.governance),
        relationships=SkillRelationshipsInput(
            depends_on=tuple(
                _dependency_selector(item) for item in request.relationships.depends_on
            ),
            extends=tuple(_exact_selector(item) for item in request.relationships.extends),
            conflicts_with=tuple(
                _exact_selector(item) for item in request.relationships.conflicts_with
            ),
            overlaps_with=tuple(
                _exact_selector(item) for item in request.relationships.overlaps_with
            ),
        ),
    )


def _dependency_selector(item: DependencySelectorRequest) -> SkillRelationshipSelector:
    return SkillRelationshipSelector(
        slug=item.slug,
        version=item.version,
        version_constraint=item.version_constraint,
        optional=item.optional,
        markers=tuple(item.markers),
    )


def _exact_selector(item: ExactRelationshipSelectorRequest) -> SkillRelationshipSelector:
    return SkillRelationshipSelector(slug=item.slug, version=item.version)


def _governance_input(item: SkillGovernanceRequest) -> SkillGovernanceInput:
    return SkillGovernanceInput(
        trust_tier=item.trust_tier,
        provenance=(
            None
            if item.provenance is None
            else ProvenanceMetadata(
                repo_url=item.provenance.repo_url,
                commit_sha=item.provenance.commit_sha,
                tree_path=item.provenance.tree_path,
                publisher_identity=item.provenance.publisher_identity,
            )
        ),
    )
