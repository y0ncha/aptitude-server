"""Integration coverage for Alembic migration lifecycle."""

from __future__ import annotations

import json

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command


@pytest.mark.integration
def test_migrations_upgrade_and_downgrade(require_integration_database: str) -> None:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", require_integration_database)

    command.downgrade(config, "base")
    command.upgrade(config, "head")

    upgraded_engine = create_engine(require_integration_database)
    try:
        inspector = inspect(upgraded_engine)
        assert "audit_events" in inspector.get_table_names()
        assert "skills" in inspector.get_table_names()
        assert "skill_versions" in inspector.get_table_names()
        assert "skill_version_checksums" in inspector.get_table_names()
        assert "skill_relationship_edges" in inspector.get_table_names()
        assert "skill_search_documents" in inspector.get_table_names()

        index_rows = upgraded_engine.connect().execute(
            text(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = current_schema()
                  AND tablename = 'skill_search_documents'
                ORDER BY indexname
                """
            )
        ).scalars().all()
        assert "ix_skill_search_documents_normalized_skill_id" in index_rows
        assert "ix_skill_search_documents_normalized_name" in index_rows
        assert "ix_skill_search_documents_published_at" in index_rows
        assert "ix_skill_search_documents_artifact_size_bytes" in index_rows
        assert "ix_skill_search_documents_normalized_tags_gin" in index_rows
        assert "ix_skill_search_documents_search_vector_gin" in index_rows
    finally:
        upgraded_engine.dispose()

    command.downgrade(config, "base")

    downgraded_engine = create_engine(require_integration_database)
    try:
        inspector = inspect(downgraded_engine)
        assert "audit_events" not in inspector.get_table_names()
        assert "skills" not in inspector.get_table_names()
        assert "skill_versions" not in inspector.get_table_names()
        assert "skill_version_checksums" not in inspector.get_table_names()
        assert "skill_relationship_edges" not in inspector.get_table_names()
        assert "skill_search_documents" not in inspector.get_table_names()
    finally:
        downgraded_engine.dispose()


@pytest.mark.integration
def test_0003_backfills_relationship_edges_from_manifest(require_integration_database: str) -> None:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", require_integration_database)

    command.downgrade(config, "base")
    command.upgrade(config, "0002_immutable_skill_registry")

    engine = create_engine(require_integration_database)
    try:
        with engine.begin() as connection:
            source_skill_id = "migration.source"
            target_skill_id = "migration.target"
            extends_skill_id = "migration.extended"
            source_fk = connection.execute(
                text("INSERT INTO skills (skill_id) VALUES (:skill_id) RETURNING id"),
                {"skill_id": source_skill_id},
            ).scalar_one()
            connection.execute(
                text("INSERT INTO skills (skill_id) VALUES (:skill_id)"),
                {"skill_id": target_skill_id},
            )
            connection.execute(
                text("INSERT INTO skills (skill_id) VALUES (:skill_id)"),
                {"skill_id": extends_skill_id},
            )

            manifest = json.dumps(
                {
                    "skill_id": source_skill_id,
                    "version": "1.0.0",
                    "name": "Migration Source",
                    "depends_on": [
                        {
                            "skill_id": target_skill_id,
                            "version_constraint": ">=2.0.0,<3.0.0",
                        }
                    ],
                    "extends": [{"skill_id": extends_skill_id, "version": "3.0.0"}],
                }
            )
            connection.execute(
                text(
                    """
                    INSERT INTO skill_versions
                        (skill_fk, version, manifest_json, artifact_rel_path, artifact_size_bytes)
                    VALUES
                        (:skill_fk, '1.0.0', CAST(:manifest_json AS jsonb), 'artifact.bin', 4)
                    """
                ),
                {"skill_fk": source_fk, "manifest_json": manifest},
            )
    finally:
        engine.dispose()

    command.upgrade(config, "head")

    upgraded_engine = create_engine(require_integration_database)
    try:
        with upgraded_engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT edge_type, target_skill_id, target_version_selector
                    FROM skill_relationship_edges
                    ORDER BY edge_type, target_skill_id, target_version_selector
                    """
                )
            ).all()
            assert rows == [
                ("depends_on", "migration.target", ">=2.0.0,<3.0.0"),
                ("extends", "migration.extended", "3.0.0"),
            ]
    finally:
        upgraded_engine.dispose()


@pytest.mark.integration
def test_0004_backfills_search_documents_from_manifest(require_integration_database: str) -> None:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", require_integration_database)

    command.downgrade(config, "base")
    command.upgrade(config, "0003_deterministic_dependency_resolution")

    engine = create_engine(require_integration_database)
    try:
        with engine.begin() as connection:
            skill_id = "migration.search"
            skill_fk = connection.execute(
                text("INSERT INTO skills (skill_id) VALUES (:skill_id) RETURNING id"),
                {"skill_id": skill_id},
            ).scalar_one()
            manifest = json.dumps(
                {
                    "skill_id": skill_id,
                    "version": "1.2.3",
                    "name": "Migration Search",
                    "description": "Searchable migration skill",
                    "tags": ["Python", "Lint"],
                }
            )
            connection.execute(
                text(
                    """
                    INSERT INTO skill_versions
                        (skill_fk, version, manifest_json, artifact_rel_path, artifact_size_bytes)
                    VALUES
                        (:skill_fk, '1.2.3', CAST(:manifest_json AS jsonb), 'artifact.bin', 512)
                    """
                ),
                {"skill_fk": skill_fk, "manifest_json": manifest},
            )
    finally:
        engine.dispose()

    command.upgrade(config, "head")

    upgraded_engine = create_engine(require_integration_database)
    try:
        with upgraded_engine.connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT
                        skill_id,
                        normalized_skill_id,
                        version,
                        name,
                        description,
                        tags,
                        normalized_tags,
                        artifact_size_bytes,
                        usage_count
                    FROM skill_search_documents
                    WHERE skill_id = 'migration.search'
                    """
                )
            ).mappings().one()
            assert row["skill_id"] == "migration.search"
            assert row["normalized_skill_id"] == "migration.search"
            assert row["version"] == "1.2.3"
            assert row["name"] == "Migration Search"
            assert row["description"] == "Searchable migration skill"
            assert row["tags"] == ["Python", "Lint"]
            assert row["normalized_tags"] == ["python", "lint"]
            assert row["artifact_size_bytes"] == 512
            assert row["usage_count"] == 0
    finally:
        upgraded_engine.dispose()
