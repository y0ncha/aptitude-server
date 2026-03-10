"""Integration tests for immutable skill registry endpoints."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from alembic import command
from app.main import create_app


@pytest.fixture
def migrated_registry_database(require_integration_database: str) -> str:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", require_integration_database)
    command.upgrade(config, "head")
    return require_integration_database


def _manifest(
    skill_id: str,
    version: str,
    *,
    depends_on: list[dict[str, object]] | None = None,
    extends: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "skill_id": skill_id,
        "version": version,
        "name": "Python Lint",
        "description": "Linting skill",
        "tags": ["python", "lint"],
        "depends_on": depends_on or [],
        "extends": extends or [],
        "conflicts_with": [],
        "overlaps_with": [],
    }


def _publish(
    *,
    client: TestClient,
    skill_id: str,
    version: str,
    artifact_bytes: bytes,
    depends_on: list[dict[str, object]] | None = None,
    extends: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    response = client.post(
        "/skills/publish",
        data={
            "manifest": json.dumps(
                _manifest(
                    skill_id=skill_id,
                    version=version,
                    depends_on=depends_on,
                    extends=extends,
                )
            )
        },
        files={"artifact": ("artifact.bin", artifact_bytes, "application/octet-stream")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _search(client: TestClient, **params: object) -> object:
    response = client.get("/skills/search", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def _discovery_search(client: TestClient, **params: object) -> object:
    response = client.get("/discovery/skills/search", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def _batch_fetch(
    client: TestClient,
    *,
    coordinates: list[dict[str, str]],
) -> object:
    response = client.post("/fetch/skill-versions:batch", json={"coordinates": coordinates})
    assert response.status_code == 200, response.text
    return response.json()


def _relationships(
    client: TestClient,
    *,
    coordinates: list[dict[str, str]],
    edge_types: list[str] | None = None,
) -> object:
    payload: dict[str, object] = {"coordinates": coordinates}
    if edge_types is not None:
        payload["edge_types"] = edge_types
    response = client.post("/resolution/relationships:batch", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _publish_manifest(
    *,
    client: TestClient,
    manifest: dict[str, object],
    artifact_bytes: bytes,
) -> dict[str, object]:
    response = client.post(
        "/skills/publish",
        data={"manifest": json.dumps(manifest)},
        files={"artifact": ("artifact.bin", artifact_bytes, "application/octet-stream")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _assert_invalid_request(response: object, *, location: list[str] | None = None) -> None:
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "INVALID_REQUEST"
    assert body["error"]["message"] == "Request validation failed."
    assert isinstance(body["error"]["details"]["errors"], list)
    if location is not None:
        assert body["error"]["details"]["errors"][0]["loc"] == location


@pytest.mark.integration
def test_publish_fetch_and_list_skill_versions(
    monkeypatch: pytest.MonkeyPatch,
    migrated_registry_database: str,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DATABASE_URL", migrated_registry_database)
    monkeypatch.setenv("ARTIFACT_ROOT_DIR", str(tmp_path / "artifacts"))
    skill_id = f"python.lint.{uuid4().hex}"

    with TestClient(create_app()) as client:
        _publish(client=client, skill_id=skill_id, version="1.0.0", artifact_bytes=b"v1")
        _publish(client=client, skill_id=skill_id, version="1.1.0", artifact_bytes=b"v11")
        _publish(client=client, skill_id=skill_id, version="2.0.0", artifact_bytes=b"v2")

        for expected in ["1.0.0", "1.1.0", "2.0.0"]:
            response = client.get(f"/skills/{skill_id}/{expected}")
            assert response.status_code == 200
            body = response.json()
            assert body["skill_id"] == skill_id
            assert body["version"] == expected
            assert body["checksum"]["algorithm"] == "sha256"
            assert base64.b64decode(body["artifact_base64"]) in {b"v1", b"v11", b"v2"}

        list_first = client.get(f"/skills/{skill_id}")
        list_second = client.get(f"/skills/{skill_id}")

    assert list_first.status_code == 200
    assert list_second.status_code == 200
    assert list_first.json() == list_second.json()
    assert [item["version"] for item in list_first.json()["versions"]] == [
        "2.0.0",
        "1.1.0",
        "1.0.0",
    ]


@pytest.mark.integration
def test_duplicate_publish_returns_409(
    monkeypatch: pytest.MonkeyPatch,
    migrated_registry_database: str,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DATABASE_URL", migrated_registry_database)
    monkeypatch.setenv("ARTIFACT_ROOT_DIR", str(tmp_path / "artifacts"))
    skill_id = f"python.lint.{uuid4().hex}"

    with TestClient(create_app()) as client:
        _publish(
            client=client,
            skill_id=skill_id,
            version="1.0.0",
            artifact_bytes=b"v1",
        )
        duplicate = client.post(
            "/skills/publish",
            data={"manifest": json.dumps(_manifest(skill_id=skill_id, version="1.0.0"))},
            files={"artifact": ("artifact.bin", b"v1", "application/octet-stream")},
        )

    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DUPLICATE_SKILL_VERSION"


@pytest.mark.integration
def test_fetch_detects_corrupted_artifact_checksum(
    monkeypatch: pytest.MonkeyPatch,
    migrated_registry_database: str,
    tmp_path: Path,
) -> None:
    artifact_root = tmp_path / "artifacts"
    monkeypatch.setenv("DATABASE_URL", migrated_registry_database)
    monkeypatch.setenv("ARTIFACT_ROOT_DIR", str(artifact_root))
    skill_id = f"python.lint.{uuid4().hex}"

    with TestClient(create_app()) as client:
        publish = _publish(
            client=client, skill_id=skill_id, version="1.0.0", artifact_bytes=b"trusted"
        )
        relative_path = publish["artifact_metadata"]["relative_path"]
        artifact_path = artifact_root / relative_path
        artifact_path.write_bytes(b"tampered")
        corrupted = client.get(f"/skills/{skill_id}/1.0.0")

    assert corrupted.status_code == 500
    assert corrupted.json()["error"]["code"] == "INTEGRITY_CHECK_FAILED"


@pytest.mark.integration
def test_fetch_returns_dependency_metadata_in_stable_order(
    monkeypatch: pytest.MonkeyPatch,
    migrated_registry_database: str,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DATABASE_URL", migrated_registry_database)
    monkeypatch.setenv("ARTIFACT_ROOT_DIR", str(tmp_path / "artifacts"))
    suffix = uuid4().hex
    skill_id = f"python.dep.{suffix}"
    dependency_a = f"shared.a.{suffix}"
    dependency_b = f"shared.b.{suffix}"
    extension_a = f"base.a.{suffix}"
    extension_b = f"base.b.{suffix}"

    with TestClient(create_app()) as client:
        _publish(
            client=client,
            skill_id=skill_id,
            version="1.0.0",
            artifact_bytes=b"v1",
            depends_on=[
                {
                    "skill_id": dependency_b,
                    "version_constraint": ">=2.0.0,<3.0.0",
                    "optional": True,
                    "markers": ["linux", "gpu"],
                },
                {"skill_id": dependency_a, "version": "1.0.0"},
            ],
            extends=[
                {"skill_id": extension_b, "version": "3.0.0"},
                {"skill_id": extension_a, "version": "2.1.0"},
            ],
        )
        first = client.get(f"/skills/{skill_id}/1.0.0")
        second = client.get(f"/skills/{skill_id}/1.0.0")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["manifest"]["depends_on"] == [
        {
            "skill_id": dependency_b,
            "version_constraint": ">=2.0.0,<3.0.0",
            "optional": True,
            "markers": ["linux", "gpu"],
        },
        {"skill_id": dependency_a, "version": "1.0.0"},
    ]
    assert first.json()["manifest"]["extends"] == [
        {"skill_id": extension_b, "version": "3.0.0"},
        {"skill_id": extension_a, "version": "2.1.0"},
    ]


@pytest.mark.integration
def test_new_fetch_endpoints_return_metadata_and_stream_artifact(
    monkeypatch: pytest.MonkeyPatch,
    migrated_registry_database: str,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DATABASE_URL", migrated_registry_database)
    monkeypatch.setenv("ARTIFACT_ROOT_DIR", str(tmp_path / "artifacts"))
    skill_id = f"python.fetch.{uuid4().hex}"

    with TestClient(create_app()) as client:
        _publish(client=client, skill_id=skill_id, version="1.2.3", artifact_bytes=b"fetch-me")

        metadata = client.get(f"/fetch/skills/{skill_id}/1.2.3")
        artifact = client.get(f"/fetch/skills/{skill_id}/1.2.3/artifact")

    assert metadata.status_code == 200
    metadata_body = metadata.json()
    assert metadata_body["skill_id"] == skill_id
    assert metadata_body["version"] == "1.2.3"
    assert metadata_body["artifact_ref"]["download_path"] == (
        f"/fetch/skills/{skill_id}/1.2.3/artifact"
    )
    assert "artifact_base64" not in metadata_body

    assert artifact.status_code == 200
    assert artifact.content == b"fetch-me"
    assert artifact.headers["etag"] == metadata_body["checksum"]["digest"]
    assert artifact.headers["cache-control"] == "public, immutable"


@pytest.mark.integration
def test_batch_fetch_preserves_request_order_and_not_found_results(
    monkeypatch: pytest.MonkeyPatch,
    migrated_registry_database: str,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DATABASE_URL", migrated_registry_database)
    monkeypatch.setenv("ARTIFACT_ROOT_DIR", str(tmp_path / "artifacts"))
    suffix = uuid4().hex
    first_skill_id = f"python.batch.first.{suffix}"
    second_skill_id = f"python.batch.second.{suffix}"

    with TestClient(create_app()) as client:
        _publish(client=client, skill_id=first_skill_id, version="1.0.0", artifact_bytes=b"first")
        _publish(client=client, skill_id=second_skill_id, version="2.0.0", artifact_bytes=b"second")

        response = _batch_fetch(
            client,
            coordinates=[
                {"skill_id": second_skill_id, "version": "2.0.0"},
                {"skill_id": f"python.batch.missing.{suffix}", "version": "9.9.9"},
                {"skill_id": first_skill_id, "version": "1.0.0"},
            ],
        )

    assert [item["status"] for item in response["results"]] == ["found", "not_found", "found"]
    assert response["results"][0]["coordinate"] == {
        "skill_id": second_skill_id,
        "version": "2.0.0",
    }
    assert response["results"][0]["version"]["artifact_ref"]["download_path"] == (
        f"/fetch/skills/{second_skill_id}/2.0.0/artifact"
    )
    assert response["results"][1]["version"] is None
    assert response["results"][2]["coordinate"] == {
        "skill_id": first_skill_id,
        "version": "1.0.0",
    }


@pytest.mark.integration
def test_relationship_batch_returns_direct_authored_edges_in_manifest_order(
    monkeypatch: pytest.MonkeyPatch,
    migrated_registry_database: str,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DATABASE_URL", migrated_registry_database)
    monkeypatch.setenv("ARTIFACT_ROOT_DIR", str(tmp_path / "artifacts"))
    suffix = uuid4().hex
    source_skill_id = f"python.relationship.source.{suffix}"
    direct_dependency = f"python.relationship.dependency.{suffix}"
    direct_extension = f"python.relationship.extension.{suffix}"
    transitive_dependency = f"python.relationship.transitive.{suffix}"

    with TestClient(create_app()) as client:
        _publish(
            client=client,
            skill_id=direct_dependency,
            version="2.0.0",
            artifact_bytes=b"dep",
            depends_on=[{"skill_id": transitive_dependency, "version": "3.0.0"}],
        )
        _publish(
            client=client,
            skill_id=direct_extension,
            version="1.5.0",
            artifact_bytes=b"ext",
        )
        _publish(
            client=client,
            skill_id=source_skill_id,
            version="1.0.0",
            artifact_bytes=b"source",
            depends_on=[
                {
                    "skill_id": f"python.relationship.constraint.{suffix}",
                    "version_constraint": ">=4.0.0,<5.0.0",
                    "optional": True,
                    "markers": ["linux"],
                },
                {"skill_id": direct_dependency, "version": "2.0.0"},
            ],
            extends=[{"skill_id": direct_extension, "version": "1.5.0"}],
        )

        response = _relationships(
            client,
            coordinates=[{"skill_id": source_skill_id, "version": "1.0.0"}],
        )

    assert response["results"][0]["status"] == "found"
    relationships = response["results"][0]["relationships"]
    assert [item["edge_type"] for item in relationships] == [
        "depends_on",
        "depends_on",
        "extends",
    ]
    assert relationships[0]["selector"] == {
        "skill_id": f"python.relationship.constraint.{suffix}",
        "version_constraint": ">=4.0.0,<5.0.0",
        "optional": True,
        "markers": ["linux"],
    }
    assert relationships[0]["target_version"] is None
    assert relationships[1]["selector"] == {
        "skill_id": direct_dependency,
        "version": "2.0.0",
    }
    assert relationships[1]["target_version"]["skill_id"] == direct_dependency
    assert relationships[1]["target_version"]["version"] == "2.0.0"
    assert relationships[2]["selector"] == {
        "skill_id": direct_extension,
        "version": "1.5.0",
    }
    assert relationships[2]["target_version"]["skill_id"] == direct_extension
    assert all(
        item["target_version"] is None
        or item["target_version"]["skill_id"] != transitive_dependency
        for item in relationships
    )


@pytest.mark.integration
def test_publish_rejects_malformed_dependency_declarations(
    monkeypatch: pytest.MonkeyPatch,
    migrated_registry_database: str,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DATABASE_URL", migrated_registry_database)
    monkeypatch.setenv("ARTIFACT_ROOT_DIR", str(tmp_path / "artifacts"))
    skill_id = f"python.invalid.{uuid4().hex}"

    invalid_manifest = {
        "schema_version": "1.0",
        "skill_id": skill_id,
        "version": "1.0.0",
        "name": "Python Lint",
        "depends_on": [{"skill_id": "missing.version"}],
    }

    with TestClient(create_app()) as client:
        response = client.post(
            "/skills/publish",
            data={"manifest": json.dumps(invalid_manifest)},
            files={"artifact": ("artifact.bin", b"v1", "application/octet-stream")},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_MANIFEST"


@pytest.mark.integration
def test_publish_rejects_invalid_dependency_constraint_syntax(
    monkeypatch: pytest.MonkeyPatch,
    migrated_registry_database: str,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DATABASE_URL", migrated_registry_database)
    monkeypatch.setenv("ARTIFACT_ROOT_DIR", str(tmp_path / "artifacts"))
    skill_id = f"python.invalid.constraint.{uuid4().hex}"

    invalid_manifest = {
        "schema_version": "1.0",
        "skill_id": skill_id,
        "version": "1.0.0",
        "name": "Python Lint",
        "depends_on": [{"skill_id": "shared.base", "version_constraint": "latest"}],
    }

    with TestClient(create_app()) as client:
        response = client.post(
            "/skills/publish",
            data={"manifest": json.dumps(invalid_manifest)},
            files={"artifact": ("artifact.bin", b"v1", "application/octet-stream")},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_MANIFEST"


@pytest.mark.integration
def test_search_returns_compact_candidates_and_best_version_per_skill(
    monkeypatch: pytest.MonkeyPatch,
    migrated_registry_database: str,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DATABASE_URL", migrated_registry_database)
    monkeypatch.setenv("ARTIFACT_ROOT_DIR", str(tmp_path / "artifacts"))
    skill_id = f"python.search.{uuid4().hex}"

    with TestClient(create_app()) as client:
        _publish(client=client, skill_id=skill_id, version="1.0.0", artifact_bytes=b"older")
        _publish(client=client, skill_id=skill_id, version="2.0.0", artifact_bytes=b"newer")

        first = _search(client, q=skill_id)
        second = _search(client, q=skill_id)

    assert first == second
    assert len(first["results"]) == 1
    result = first["results"][0]
    assert result["skill_id"] == skill_id
    assert result["version"] == "2.0.0"
    assert result["name"] == "Python Lint"
    assert result["tags"] == ["python", "lint"]
    assert result["usage_count"] == 0
    assert "exact_skill_id_match" in result["reasons"]
    assert "manifest" not in result
    assert "checksum" not in result
    assert "artifact_base64" not in result


@pytest.mark.integration
def test_discovery_endpoint_matches_legacy_search_output(
    monkeypatch: pytest.MonkeyPatch,
    migrated_registry_database: str,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DATABASE_URL", migrated_registry_database)
    monkeypatch.setenv("ARTIFACT_ROOT_DIR", str(tmp_path / "artifacts"))
    skill_id = f"python.discovery.{uuid4().hex}"

    with TestClient(create_app()) as client:
        _publish(client=client, skill_id=skill_id, version="1.0.0", artifact_bytes=b"v1")
        _publish(client=client, skill_id=skill_id, version="2.0.0", artifact_bytes=b"v2")

        legacy = _search(client, q=skill_id)
        discovery = _discovery_search(client, q=skill_id)

    assert discovery == legacy


@pytest.mark.integration
def test_search_supports_repeated_tag_and_language_filters(
    monkeypatch: pytest.MonkeyPatch,
    migrated_registry_database: str,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DATABASE_URL", migrated_registry_database)
    monkeypatch.setenv("ARTIFACT_ROOT_DIR", str(tmp_path / "artifacts"))
    suffix = uuid4().hex
    language_tag = f"lang-{suffix}"
    lint_tag = f"lint-{suffix}"
    other_tag = f"other-{suffix}"

    with TestClient(create_app()) as client:
        _publish_manifest(
            client=client,
            manifest={
                **_manifest(skill_id=f"python.lint.{suffix}", version="1.0.0"),
                "tags": [language_tag, lint_tag],
            },
            artifact_bytes=b"lint",
        )
        _publish_manifest(
            client=client,
            manifest={
                **_manifest(skill_id=f"python.test.{suffix}", version="1.0.0"),
                "tags": [language_tag],
            },
            artifact_bytes=b"test",
        )
        _publish_manifest(
            client=client,
            manifest={
                **_manifest(skill_id=f"go.lint.{suffix}", version="1.0.0"),
                "tags": [other_tag, lint_tag],
            },
            artifact_bytes=b"go",
        )

        tag_filtered = _search(client, tag=[language_tag, lint_tag])
        language_filtered = _search(client, language=language_tag)

    assert [item["skill_id"] for item in tag_filtered["results"]] == [f"python.lint.{suffix}"]
    assert sorted(item["skill_id"] for item in language_filtered["results"]) == sorted(
        [f"python.lint.{suffix}", f"python.test.{suffix}"]
    )
    assert tag_filtered["results"][0]["matched_tags"] == sorted([language_tag, lint_tag])


@pytest.mark.integration
def test_search_supports_freshness_and_footprint_filters(
    monkeypatch: pytest.MonkeyPatch,
    migrated_registry_database: str,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DATABASE_URL", migrated_registry_database)
    monkeypatch.setenv("ARTIFACT_ROOT_DIR", str(tmp_path / "artifacts"))
    suffix = uuid4().hex
    filter_tag = f"footprint-{suffix}"
    old_skill_id = f"python.old.{suffix}"
    small_skill_id = f"python.small.{suffix}"
    large_skill_id = f"python.large.{suffix}"

    with TestClient(create_app()) as client:
        _publish_manifest(
            client=client,
            manifest={**_manifest(skill_id=old_skill_id, version="1.0.0"), "tags": [filter_tag]},
            artifact_bytes=b"old",
        )
        _publish_manifest(
            client=client,
            manifest={**_manifest(skill_id=small_skill_id, version="1.0.0"), "tags": [filter_tag]},
            artifact_bytes=b"1234",
        )
        _publish_manifest(
            client=client,
            manifest={**_manifest(skill_id=large_skill_id, version="1.0.0"), "tags": [filter_tag]},
            artifact_bytes=b"x" * 32,
        )

        engine = create_engine(migrated_registry_database)
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        UPDATE skill_versions
                        SET published_at = CURRENT_TIMESTAMP - INTERVAL '10 days'
                        WHERE manifest_json ->> 'skill_id' = :skill_id
                        """
                    ),
                    {"skill_id": old_skill_id},
                )
                connection.execute(
                    text(
                        """
                        UPDATE skill_search_documents
                        SET published_at = CURRENT_TIMESTAMP - INTERVAL '10 days'
                        WHERE skill_id = :skill_id
                        """
                    ),
                    {"skill_id": old_skill_id},
                )
        finally:
            engine.dispose()

        fresh = _search(client, tag=filter_tag, fresh_within_days=1)
        footprint = _search(client, tag=filter_tag, max_footprint_bytes=8)

    assert old_skill_id not in [item["skill_id"] for item in fresh["results"]]
    assert [item["skill_id"] for item in footprint["results"]] == [
        small_skill_id,
        old_skill_id,
    ]


@pytest.mark.integration
def test_search_uses_deterministic_tie_breaks(
    monkeypatch: pytest.MonkeyPatch,
    migrated_registry_database: str,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DATABASE_URL", migrated_registry_database)
    monkeypatch.setenv("ARTIFACT_ROOT_DIR", str(tmp_path / "artifacts"))
    alpha = f"alpha.tie.{uuid4().hex}"
    beta = f"beta.tie.{uuid4().hex}"
    versioned = f"version.tie.{uuid4().hex}"
    tie_tag = f"tie-{uuid4().hex}"

    with TestClient(create_app()) as client:
        for skill_id in (beta, alpha):
            response = client.post(
                "/skills/publish",
                data={
                    "manifest": json.dumps(
                        {
                                **_manifest(skill_id=skill_id, version="1.0.0"),
                                "name": "Shared Search Name",
                                "description": "Shared deterministic search text",
                                "tags": [tie_tag],
                            }
                        )
                    },
                files={"artifact": ("artifact.bin", b"same", "application/octet-stream")},
            )
            assert response.status_code == 201, response.text

        for version in ("1.0.0", "1.1.0"):
            response = client.post(
                "/skills/publish",
                data={
                    "manifest": json.dumps(
                        {
                                **_manifest(skill_id=versioned, version=version),
                                "name": "Shared Search Name",
                                "description": "Shared deterministic search text",
                                "tags": [tie_tag],
                            }
                        )
                    },
                files={"artifact": ("artifact.bin", b"same", "application/octet-stream")},
            )
            assert response.status_code == 201, response.text

        engine = create_engine(migrated_registry_database)
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        UPDATE skill_search_documents
                        SET published_at = TIMESTAMPTZ '2026-03-10T08:30:00Z'
                        WHERE skill_id IN (:alpha, :beta, :versioned)
                        """
                    ),
                    {"alpha": alpha, "beta": beta, "versioned": versioned},
                )
        finally:
            engine.dispose()

        ordered = _search(client, q="shared search", tag=tie_tag)

    assert [item["skill_id"] for item in ordered["results"][:2]] == [alpha, beta]
    assert [
        item["version"] for item in ordered["results"] if item["skill_id"] == versioned
    ] == ["1.1.0"]


@pytest.mark.integration
def test_search_rejects_requests_without_selectors(
    monkeypatch: pytest.MonkeyPatch,
    migrated_registry_database: str,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DATABASE_URL", migrated_registry_database)
    monkeypatch.setenv("ARTIFACT_ROOT_DIR", str(tmp_path / "artifacts"))

    with TestClient(create_app()) as client:
        response = client.get("/skills/search")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


@pytest.mark.integration
def test_fetch_rejects_invalid_skill_id_path(
    monkeypatch: pytest.MonkeyPatch,
    migrated_registry_database: str,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DATABASE_URL", migrated_registry_database)
    monkeypatch.setenv("ARTIFACT_ROOT_DIR", str(tmp_path / "artifacts"))

    with TestClient(create_app()) as client:
        response = client.get("/skills/invalid%20skill/1.0.0")

    _assert_invalid_request(response, location=["path", "skill_id"])


@pytest.mark.integration
def test_fetch_rejects_invalid_version_path(
    monkeypatch: pytest.MonkeyPatch,
    migrated_registry_database: str,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DATABASE_URL", migrated_registry_database)
    monkeypatch.setenv("ARTIFACT_ROOT_DIR", str(tmp_path / "artifacts"))

    with TestClient(create_app()) as client:
        response = client.get("/skills/python.lint/latest")

    _assert_invalid_request(response, location=["path", "version"])


@pytest.mark.integration
def test_publish_rejects_missing_manifest_form_field(
    monkeypatch: pytest.MonkeyPatch,
    migrated_registry_database: str,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DATABASE_URL", migrated_registry_database)
    monkeypatch.setenv("ARTIFACT_ROOT_DIR", str(tmp_path / "artifacts"))

    with TestClient(create_app()) as client:
        response = client.post(
            "/skills/publish",
            files={"artifact": ("artifact.bin", b"v1", "application/octet-stream")},
        )

    _assert_invalid_request(response, location=["body", "manifest"])


@pytest.mark.integration
def test_publish_rejects_missing_artifact_upload(
    monkeypatch: pytest.MonkeyPatch,
    migrated_registry_database: str,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DATABASE_URL", migrated_registry_database)
    monkeypatch.setenv("ARTIFACT_ROOT_DIR", str(tmp_path / "artifacts"))

    with TestClient(create_app()) as client:
        response = client.post(
            "/skills/publish",
            data={"manifest": json.dumps(_manifest(skill_id="python.lint", version="1.0.0"))},
        )

    _assert_invalid_request(response, location=["body", "artifact"])


@pytest.mark.integration
def test_publish_rejects_malformed_manifest_json(
    monkeypatch: pytest.MonkeyPatch,
    migrated_registry_database: str,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DATABASE_URL", migrated_registry_database)
    monkeypatch.setenv("ARTIFACT_ROOT_DIR", str(tmp_path / "artifacts"))

    with TestClient(create_app()) as client:
        response = client.post(
            "/skills/publish",
            data={"manifest": "not-json"},
            files={"artifact": ("artifact.bin", b"v1", "application/octet-stream")},
        )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "INVALID_MANIFEST"
    assert body["error"]["message"] == "Manifest validation failed."
    assert body["error"]["details"]["errors"][0]["type"] == "json_invalid"
