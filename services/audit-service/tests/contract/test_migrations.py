"""Migración `0001` desde cero, reversa y otra vez (puerta de calidad 3; T010)."""

from __future__ import annotations

from sqlalchemy import create_engine, text

from tests.conftest import run_alembic

CONSTRAINTS = {
    "pk_audit_events",
    "uq_audit_events_event_id",
    "ck_audit_events_result",
    "ck_audit_events_action_format",
    "ck_audit_events_entity_type_format",
    "ck_audit_events_branch_requires_company",
    "ck_audit_events_values_are_objects",
    "ck_audit_events_texts_not_blank",
    "ck_audit_events_content_hash_format",
    "ck_audit_events_audit_unchanged",
}
INDEXES = {
    "ix_audit_events_company_occurred",
    "ix_audit_events_company_entity",
    "ix_audit_events_platform_occurred",
    "ix_audit_events_platform_entity",
    "ix_audit_events_company_actor",
    "ix_audit_events_correlation",
    "ix_audit_events_request",
}
TRIGGERS = {"tr_audit_events_no_update", "tr_audit_events_no_delete", "tr_audit_events_no_truncate"}


def _schema(url: str) -> dict[str, set[str]]:
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            tables = set(
                connection.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                ).scalars()
            )
            constraints = set(
                connection.execute(
                    text(
                        "SELECT conname FROM pg_constraint "
                        "WHERE conrelid = 'public.audit_events'::regclass"
                    )
                ).scalars()
            ) if "audit_events" in tables else set()
            indexes = set(
                connection.execute(
                    text("SELECT indexname FROM pg_indexes WHERE tablename = 'audit_events'")
                ).scalars()
            )
            triggers = set(
                connection.execute(
                    text(
                        "SELECT tgname FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
                        "WHERE c.relname = 'audit_events' AND NOT t.tgisinternal"
                    )
                ).scalars()
            )
            functions = set(
                connection.execute(
                    text("SELECT proname FROM pg_proc WHERE proname = 'audit_events_reject_change'")
                ).scalars()
            )
    finally:
        engine.dispose()

    return {
        "tables": tables,
        "constraints": constraints,
        "indexes": indexes,
        "triggers": triggers,
        "functions": functions,
    }


def test_upgrade_downgrade_upgrade(test_database_url: str, migrated_database: None) -> None:
    schema = _schema(test_database_url)
    assert "audit_events" in schema["tables"]
    assert CONSTRAINTS <= schema["constraints"]
    assert INDEXES <= schema["indexes"]
    assert schema["triggers"] == TRIGGERS
    assert schema["functions"] == {"audit_events_reject_change"}

    run_alembic(test_database_url, "downgrade", "base")
    down = _schema(test_database_url)
    assert "audit_events" not in down["tables"]
    assert down["functions"] == set()

    run_alembic(test_database_url, "upgrade", "head")
    again = _schema(test_database_url)
    assert CONSTRAINTS <= again["constraints"]
    assert again["triggers"] == TRIGGERS


def test_no_extension_is_required(test_database_url: str, migrated_database: None) -> None:
    engine = create_engine(test_database_url)
    try:
        with engine.connect() as connection:
            extensions = set(connection.execute(text("SELECT extname FROM pg_extension")).scalars())
    finally:
        engine.dispose()

    assert extensions == {"plpgsql"}
