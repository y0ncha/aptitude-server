"""Unit tests guarding the frozen public contract documentation."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

REMOVED_PUBLIC_READ_ROUTE_MARKERS = (
    "/discovery/skills/search",
    "/resolution/relationships:batch",
    "/fetch/metadata:batch",
    "/fetch/content:batch",
)

CURRENT_CONTRACT_DOCS = (
    REPO_ROOT / "docs/project/api-contract.md",
    REPO_ROOT / "docs/project/scope.md",
    REPO_ROOT / "docs/prd.md",
    REPO_ROOT / ".agents/plans/roadmap.md",
)

FROZEN_FUTURE_PLAN_DOCS = tuple(sorted((REPO_ROOT / ".agents/plans").glob("1[0-5]-*.md")))
DOC_PORTABILITY_ROOTS = (REPO_ROOT / "README.md", REPO_ROOT / "docs", REPO_ROOT / ".agents")
FORBIDDEN_INTERNAL_ROOT_LINK = re.compile(r"\]\(/(?:docs|\.agents)/")
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
DOCS_HUB_PATH = REPO_ROOT / "docs/README.md"
STABLE_FACTS_PATH = REPO_ROOT / ".agents/memory/meta.md"
HISTORY_MANIFEST_PATH = REPO_ROOT / ".agents/history-append-only-manifest.json"
IN_SCOPE_DOC_ROOTS = (
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs",
    REPO_ROOT / ".agents/agent.md",
    REPO_ROOT / ".agents/plans",
)
PROTECTED_HISTORY_DOCS = tuple(
    sorted((REPO_ROOT / ".agents/plans").glob("0[1-9]-*.md"))
    + sorted((REPO_ROOT / ".agents/plans").glob("1[01]-*.md"))
    + sorted((REPO_ROOT / "docs/changelog").glob("0[1-9]-*.md"))
    + sorted((REPO_ROOT / "docs/changelog").glob("1[01]-*.md"))
)


def _iter_in_scope_doc_paths() -> tuple[Path, ...]:
    app_readmes = sorted((REPO_ROOT / "app").rglob("README.md"))
    scoped_paths: list[Path] = []
    for root in IN_SCOPE_DOC_ROOTS:
        scoped_paths.extend((root,) if root.is_file() else sorted(root.rglob("*.md")))
    scoped_paths.extend(app_readmes)
    return tuple(dict.fromkeys(scoped_paths))


def _iter_markdown_links(path: Path) -> list[str]:
    return MARKDOWN_LINK_PATTERN.findall(path.read_text(encoding="utf-8"))


def _resolve_markdown_link(source_path: Path, raw_target: str) -> Path | None:
    target = raw_target.strip()
    if not target or target.startswith(("http://", "https://", "mailto:", "#")):
        return None
    if target.startswith(("discussion://", "collection://", "view://")):
        return None
    clean_target = target.split("#", 1)[0].split("?", 1)[0]
    if not clean_target or clean_target.startswith("{{"):
        return None
    if clean_target.startswith("/"):
        return (REPO_ROOT / clean_target.lstrip("/")).resolve()
    return (source_path.parent / clean_target).resolve()


def _history_prefix_matches(
    *, expected_prefix_length: int, expected_prefix_sha256: str, content: str
) -> bool:
    if len(content) < expected_prefix_length:
        return False
    actual_prefix = content[:expected_prefix_length]
    actual_prefix_sha256 = hashlib.sha256(actual_prefix.encode("utf-8")).hexdigest()
    return actual_prefix_sha256 == expected_prefix_sha256


@pytest.mark.unit
@pytest.mark.parametrize(
    "path",
    CURRENT_CONTRACT_DOCS + FROZEN_FUTURE_PLAN_DOCS,
    ids=lambda path: path.name,
)
def test_current_contract_docs_do_not_reintroduce_removed_public_read_routes(
    path: Path,
) -> None:
    document = path.read_text()

    for route_marker in REMOVED_PUBLIC_READ_ROUTE_MARKERS:
        assert route_marker not in document


@pytest.mark.unit
def test_api_contract_documents_the_frozen_public_read_surface() -> None:
    document = (REPO_ROOT / "docs/project/api-contract.md").read_text()

    assert "GET /metrics" in document
    assert "POST /skills/{slug}/versions" in document
    assert "POST /skill-versions" not in document
    assert "create_skill" in document
    assert "publish_version" in document
    assert "GET /resolution/{slug}/{version}" in document
    assert "GET /skills/{slug}/versions/{version}" in document
    assert "GET /skills/{slug}/versions/{version}/content" in document
    assert "Resolution remains a first-class public exact-read surface." in document
    assert "they do not add sibling public read route families or compatibility aliases" in document
    assert "X-Request-ID" in document


@pytest.mark.unit
def test_readme_documents_operability_stack_and_metrics_contract() -> None:
    document = (REPO_ROOT / "README.md").read_text()

    assert "/metrics" in document
    assert "X-Request-ID" in document
    assert "Grafana" in document
    assert "Prometheus" in document
    assert "GET /skills/{slug}/versions/{version}" in document
    assert "GET /skills/{slug}/versions/{version}/content" in document
    assert "/fetch/metadata:batch" not in document
    assert "/fetch/content:batch" not in document
    assert "docs/guides/setup-dev.md" in document


@pytest.mark.unit
def test_docs_hub_exists_and_classifies_document_sets() -> None:
    document = DOCS_HUB_PATH.read_text(encoding="utf-8")

    assert "Canonical / Current Docs" in document
    assert "Operational Guides and Runbooks" in document
    assert "Historical Milestones" in document
    assert "Drafts and Context" in document
    assert ".agents/plans/roadmap.md" in document
    assert "docs/changelog/" in document


@pytest.mark.unit
def test_stable_facts_file_exists_and_is_referenced_from_agent_contract() -> None:
    agent_contract = (REPO_ROOT / ".agents/agent.md").read_text(encoding="utf-8")
    stable_facts = STABLE_FACTS_PATH.read_text(encoding="utf-8")

    assert "memory/meta.md" in agent_contract
    assert "# Stable Repo Facts" in stable_facts


@pytest.mark.unit
def test_roadmap_freezes_the_public_read_route_families_for_later_plans() -> None:
    document = (REPO_ROOT / ".agents/plans/roadmap.md").read_text()

    assert "Plans 09-15 keep the public route families fixed" in document
    assert "publish, discovery, resolution, exact metadata fetch, exact content fetch" in document


@pytest.mark.unit
def test_agent_contract_points_to_the_real_plan_directory() -> None:
    document = (REPO_ROOT / ".agents/agent.md").read_text()

    assert "`.agents/plans/roadmap.md`" in document
    assert "`.agents/plans/XX-*.md`" in document
    assert "under `.agents/plans/XX-*.md`" in document
    assert "`plans/XX-*.md`" not in document


@pytest.mark.unit
def test_docs_and_agent_materials_use_portable_internal_links() -> None:
    offending_paths: list[str] = []

    for root in DOC_PORTABILITY_ROOTS:
        paths = (root,) if root.is_file() else sorted(root.rglob("*.md"))
        for path in paths:
            document = path.read_text()
            if "/Users/" in document or FORBIDDEN_INTERNAL_ROOT_LINK.search(document):
                offending_paths.append(str(path.relative_to(REPO_ROOT)))

    assert not offending_paths, "Non-portable internal documentation paths found:\n" + "\n".join(
        offending_paths
    )


@pytest.mark.unit
def test_user_facing_docs_have_resolvable_internal_markdown_links() -> None:
    missing_links: list[str] = []

    for path in _iter_in_scope_doc_paths():
        for raw_target in _iter_markdown_links(path):
            resolved_target = _resolve_markdown_link(path, raw_target)
            if resolved_target is not None and not resolved_target.exists():
                missing_links.append(f"{path.relative_to(REPO_ROOT)} -> {raw_target}")

    assert not missing_links, "Broken internal markdown links found:\n" + "\n".join(missing_links)


@pytest.mark.unit
def test_append_only_history_manifest_covers_the_expected_protected_docs() -> None:
    manifest = json.loads(HISTORY_MANIFEST_PATH.read_text(encoding="utf-8"))
    protected_paths = sorted(str(path.relative_to(REPO_ROOT)) for path in PROTECTED_HISTORY_DOCS)

    assert sorted(manifest) == protected_paths


@pytest.mark.unit
def test_protected_history_docs_preserve_the_manifested_prefix() -> None:
    manifest = json.loads(HISTORY_MANIFEST_PATH.read_text(encoding="utf-8"))

    for relative_path, metadata in manifest.items():
        content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert _history_prefix_matches(
            expected_prefix_length=metadata["prefix_length"],
            expected_prefix_sha256=metadata["prefix_sha256"],
            content=content,
        ), relative_path


@pytest.mark.unit
def test_append_only_guard_rejects_in_place_edits_inside_the_protected_prefix() -> None:
    manifest = json.loads(HISTORY_MANIFEST_PATH.read_text(encoding="utf-8"))
    relative_path = sorted(manifest)[0]
    metadata = manifest[relative_path]
    content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    prefix = content[: metadata["prefix_length"]]
    replacement_char = "X" if prefix[0] != "X" else "Y"
    mutated_content = replacement_char + content[1:]

    assert _history_prefix_matches(
        expected_prefix_length=metadata["prefix_length"],
        expected_prefix_sha256=metadata["prefix_sha256"],
        content=content,
    )
    assert not _history_prefix_matches(
        expected_prefix_length=metadata["prefix_length"],
        expected_prefix_sha256=metadata["prefix_sha256"],
        content=mutated_content,
    )


@pytest.mark.unit
def test_append_only_guard_allows_new_content_to_be_appended_after_the_protected_prefix() -> None:
    manifest = json.loads(HISTORY_MANIFEST_PATH.read_text(encoding="utf-8"))
    relative_path = sorted(manifest)[0]
    metadata = manifest[relative_path]
    content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    appended_content = content + "\n\n## Addendum (2099-01-01)\n- Example follow-on note.\n"

    assert _history_prefix_matches(
        expected_prefix_length=metadata["prefix_length"],
        expected_prefix_sha256=metadata["prefix_sha256"],
        content=appended_content,
    )
