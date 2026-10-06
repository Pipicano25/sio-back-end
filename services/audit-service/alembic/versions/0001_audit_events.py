"""Tabla audit_events, índices por alcance e inmutabilidad (feature 011, R-06, R-10).

`gen_random_uuid()` pertenece al núcleo de PostgreSQL 17: no se agrega ninguna
extensión. La inmutabilidad se garantiza con triggers que rechazan `UPDATE`,
`DELETE` y `TRUNCATE` también en sesiones manuales; el rol de la aplicación es
dueño de la tabla, por lo que `REVOKE` no la protegería.

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("application_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("keycloak_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("username_snapshot", sa.String(160), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(60), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("previous_values", postgresql.JSONB(), nullable=True),
        sa.Column("new_values", postgresql.JSONB(), nullable=True),
        sa.Column(
            "redacted_paths",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("result", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_service", sa.String(80), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_hash", sa.CHAR(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("updated_by", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_audit_events"),
        sa.UniqueConstraint("event_id", name="uq_audit_events_event_id"),
        sa.CheckConstraint("result IN ('SUCCESS','FAILURE')", name=op.f("ck_audit_events_result")),
        sa.CheckConstraint(
            "action ~ '^[A-Z][A-Z0-9_]{0,49}$'", name=op.f("ck_audit_events_action_format")
        ),
        sa.CheckConstraint(
            "entity_type ~ '^[A-Z][A-Za-z0-9]{0,59}$'", name=op.f("ck_audit_events_entity_type_format")
        ),
        sa.CheckConstraint(
            "branch_id IS NULL OR company_id IS NOT NULL",
            name=op.f("ck_audit_events_branch_requires_company"),
        ),
        sa.CheckConstraint(
            "(previous_values IS NULL OR jsonb_typeof(previous_values) = 'object') "
            "AND (new_values IS NULL OR jsonb_typeof(new_values) = 'object')",
            name=op.f("ck_audit_events_values_are_objects"),
        ),
        sa.CheckConstraint(
            "(username_snapshot IS NULL OR (btrim(username_snapshot) <> '' "
            "AND username_snapshot = btrim(username_snapshot))) "
            "AND (reason IS NULL OR (btrim(reason) <> '' AND reason = btrim(reason) "
            "AND char_length(reason) <= 2000)) "
            "AND btrim(source_service) <> ''",
            name=op.f("ck_audit_events_texts_not_blank"),
        ),
        sa.CheckConstraint(
            "content_hash ~ '^[0-9a-f]{64}$'", name=op.f("ck_audit_events_content_hash_format")
        ),
        sa.CheckConstraint(
            "updated_at = created_at AND updated_by = created_by",
            name=op.f("ck_audit_events_audit_unchanged"),
        ),
    )

    op.create_index(
        "ix_audit_events_company_occurred",
        "audit_events",
        ["company_id", sa.text("occurred_at DESC"), sa.text("id DESC")],
        postgresql_where=sa.text("company_id IS NOT NULL"),
    )
    op.create_index(
        "ix_audit_events_company_entity",
        "audit_events",
        ["company_id", "entity_type", "entity_id", "occurred_at", "id"],
        postgresql_where=sa.text("company_id IS NOT NULL"),
    )
    op.create_index(
        "ix_audit_events_platform_occurred",
        "audit_events",
        [sa.text("occurred_at DESC"), sa.text("id DESC")],
        postgresql_where=sa.text("company_id IS NULL"),
    )
    op.create_index(
        "ix_audit_events_platform_entity",
        "audit_events",
        ["entity_type", "entity_id", "occurred_at", "id"],
        postgresql_where=sa.text("company_id IS NULL"),
    )
    op.create_index(
        "ix_audit_events_company_actor",
        "audit_events",
        ["company_id", "keycloak_user_id", sa.text("occurred_at DESC")],
    )
    op.create_index(
        "ix_audit_events_correlation",
        "audit_events",
        ["correlation_id"],
        postgresql_where=sa.text("correlation_id IS NOT NULL"),
    )
    op.create_index(
        "ix_audit_events_request",
        "audit_events",
        ["request_id"],
        postgresql_where=sa.text("request_id IS NOT NULL"),
    )

    op.execute(
        """
        CREATE FUNCTION audit_events_reject_change() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events es inmutable: % no permitido', TG_OP
                USING ERRCODE = 'restrict_violation';
        END;
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER tr_audit_events_no_update BEFORE UPDATE ON audit_events "
        "FOR EACH ROW EXECUTE FUNCTION audit_events_reject_change()"
    )
    op.execute(
        "CREATE TRIGGER tr_audit_events_no_delete BEFORE DELETE ON audit_events "
        "FOR EACH ROW EXECUTE FUNCTION audit_events_reject_change()"
    )
    op.execute(
        "CREATE TRIGGER tr_audit_events_no_truncate BEFORE TRUNCATE ON audit_events "
        "FOR EACH STATEMENT EXECUTE FUNCTION audit_events_reject_change()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS tr_audit_events_no_truncate ON audit_events")
    op.execute("DROP TRIGGER IF EXISTS tr_audit_events_no_delete ON audit_events")
    op.execute("DROP TRIGGER IF EXISTS tr_audit_events_no_update ON audit_events")
    op.execute("DROP FUNCTION IF EXISTS audit_events_reject_change()")
    op.drop_table("audit_events")
