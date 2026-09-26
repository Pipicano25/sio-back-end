"""Crea application_users, user_branches y company_advisor_assignments (Fase B).

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-26

Referencias a Keycloak (`keycloak_user_id`) y a Party Identity
(`person_identity_id`) sin FK física (Principio II). `user_branches` usa FK
compuestas con `company_id` para que usuario y sucursal pertenezcan siempre a la
misma empresa (R-05). Unicidades de membresía y de asesor principal vigente con
índices únicos parciales (R-04). Ver specs/005-operational-context-users/data-model.md.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _uuid(name: str, *, nullable: bool = False) -> sa.Column:
    return sa.Column(name, postgresql.UUID(as_uuid=True), nullable=nullable)


def _version_and_audit_columns() -> list[sa.Column]:
    return [
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("updated_by", sa.String(255), nullable=False),
    ]


def _status_column() -> sa.Column:
    return sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'ACTIVE'"))


def upgrade() -> None:
    op.create_unique_constraint("uq_branches_id_company_id", "branches", ["id", "company_id"])

    op.create_table(
        "application_users",
        _uuid("id"),
        _uuid("company_id"),
        sa.Column("keycloak_user_id", sa.String(255), nullable=False),
        _uuid("person_identity_id"),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("reference_email", sa.String(254), nullable=True),
        _status_column(),
        *_version_and_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_application_users"),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_application_users_company_id_companies",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("id", "company_id", name="uq_application_users_id_company_id"),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name=op.f("ck_application_users_status"),
        ),
        sa.CheckConstraint(
            "keycloak_user_id = btrim(keycloak_user_id) AND keycloak_user_id <> ''",
            name=op.f("ck_application_users_keycloak_user_id_not_blank"),
        ),
        sa.CheckConstraint(
            "btrim(display_name) <> ''",
            name=op.f("ck_application_users_display_name_not_blank"),
        ),
    )
    op.create_index(
        "uq_application_users_company_id_person_identity_id_active",
        "application_users",
        ["company_id", "person_identity_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.create_index(
        "uq_application_users_company_id_keycloak_user_id_active",
        "application_users",
        ["company_id", "keycloak_user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.create_index(
        "ix_application_users_keycloak_user_id_status",
        "application_users",
        ["keycloak_user_id", "status"],
    )
    op.create_index(
        "ix_application_users_company_id_status",
        "application_users",
        ["company_id", "status"],
    )
    op.create_index(
        "ix_application_users_person_identity_id",
        "application_users",
        ["person_identity_id"],
    )

    op.create_table(
        "user_branches",
        _uuid("id"),
        _uuid("application_user_id"),
        _uuid("branch_id"),
        _uuid("company_id"),
        _status_column(),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("assigned_by", sa.String(255), nullable=False),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        *_version_and_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_user_branches"),
        sa.UniqueConstraint(
            "application_user_id",
            "branch_id",
            name="uq_user_branches_application_user_id_branch_id",
        ),
        sa.ForeignKeyConstraint(
            ["application_user_id", "company_id"],
            ["application_users.id", "application_users.company_id"],
            name="fk_user_branches_application_user_company",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id", "company_id"],
            ["branches.id", "branches.company_id"],
            name="fk_user_branches_branch_company",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name=op.f("ck_user_branches_status"),
        ),
        sa.CheckConstraint(
            "(status = 'ACTIVE' AND deactivated_at IS NULL) "
            "OR (status = 'INACTIVE' AND deactivated_at IS NOT NULL)",
            name=op.f("ck_user_branches_deactivation_consistency"),
        ),
        sa.CheckConstraint(
            "btrim(assigned_by) <> ''",
            name=op.f("ck_user_branches_assigned_by_not_blank"),
        ),
    )
    op.create_index(
        "ix_user_branches_branch_id_status",
        "user_branches",
        ["branch_id", "status"],
    )

    op.create_table(
        "company_advisor_assignments",
        _uuid("id"),
        _uuid("company_id"),
        _uuid("person_identity_id"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.true()),
        _status_column(),
        sa.Column(
            "valid_from",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_by", sa.String(255), nullable=False),
        *_version_and_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_company_advisor_assignments"),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_company_advisor_assignments_company_id_companies",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name=op.f("ck_company_advisor_assignments_status"),
        ),
        sa.CheckConstraint(
            "(status = 'ACTIVE' AND valid_to IS NULL) "
            "OR (status = 'INACTIVE' AND valid_to IS NOT NULL AND valid_to > valid_from)",
            name=op.f("ck_company_advisor_assignments_validity"),
        ),
        sa.CheckConstraint(
            "btrim(assigned_by) <> ''",
            name=op.f("ck_company_advisor_assignments_assigned_by_not_blank"),
        ),
    )
    op.create_index(
        "uq_company_advisor_assignments_company_id_primary_active",
        "company_advisor_assignments",
        ["company_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE' AND is_primary"),
    )
    op.create_index(
        "uq_company_advisor_assignments_company_person_active",
        "company_advisor_assignments",
        ["company_id", "person_identity_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.create_index(
        "ix_company_advisor_assignments_company_id_valid_from",
        "company_advisor_assignments",
        ["company_id", sa.text("valid_from DESC")],
    )
    op.create_index(
        "ix_company_advisor_assignments_person_identity_id",
        "company_advisor_assignments",
        ["person_identity_id"],
    )


def downgrade() -> None:
    op.drop_table("company_advisor_assignments")
    op.drop_table("user_branches")
    op.drop_table("application_users")
    op.drop_constraint("uq_branches_id_company_id", "branches", type_="unique")
