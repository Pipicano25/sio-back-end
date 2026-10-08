"""Modelos SQLAlchemy de Operational Context Service (data-model.md).

Las referencias a Party Identity, Geography y Keycloak son `UUID REF` o `sub`
sin FK física (Principio II). Las FK son internas: `branches.company_id`,
`application_users.company_id`, las FK compuestas de `user_branches` (misma
empresa, R-05) y `company_advisor_assignments.company_id`.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CHAR,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from operational_context_service.infrastructure.database import Base


def _uuid_ref(nullable: bool = True) -> Mapped[UUID | None]:
    return mapped_column(PostgreSQLUUID(as_uuid=True), nullable=nullable)


class _LocationAndAuditMixin:
    """Columnas comunes de contacto, ubicación, estado y auditoría."""

    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    address_line: Mapped[str | None] = mapped_column(Text, nullable=True)
    country_id: Mapped[UUID | None] = _uuid_ref()
    administrative_division_id: Mapped[UUID | None] = _uuid_ref()
    city_id: Mapped[UUID | None] = _uuid_ref()
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'ACTIVE'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)


def _common_checks(table: str) -> tuple:
    return (
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="status"),
        CheckConstraint("(latitude IS NULL) = (longitude IS NULL)", name="coordinates_pair"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude_range"),
        CheckConstraint(
            "(administrative_division_id IS NULL AND city_id IS NULL) "
            "OR country_id IS NOT NULL",
            name="geography_parent",
        ),
        Index(f"ix_{table}_city_id", "city_id"),
    )


class CompanyModel(_LocationAndAuditMixin, Base):
    """Tabla `companies`."""

    __tablename__ = "companies"
    __table_args__ = (
        UniqueConstraint(
            "organization_identity_id",
            name="uq_companies_organization_identity_id",
        ),
        *_common_checks("companies"),
        CheckConstraint("default_currency ~ '^[A-Z]{3}$'", name="default_currency_format"),
        CheckConstraint("btrim(timezone) <> ''", name="timezone_not_blank"),
        Index("ix_companies_status", "status"),
        Index("ix_companies_country_id", "country_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    organization_identity_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )
    timezone: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
        server_default=text("'America/Bogota'"),
    )
    default_currency: Mapped[str] = mapped_column(
        CHAR(3),
        nullable=False,
        server_default=text("'COP'"),
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    __mapper_args__ = {"version_id_col": version}


class BranchModel(_LocationAndAuditMixin, Base):
    """Tabla `branches`."""

    __tablename__ = "branches"
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_branches_company_id_code"),
        # Destino de la FK compuesta de user_branches (R-05, Fase B).
        UniqueConstraint("id", "company_id", name="uq_branches_id_company_id"),
        *_common_checks("branches"),
        CheckConstraint("code = upper(btrim(code)) AND code <> ''", name="code_normalized"),
        CheckConstraint(
            "timezone IS NULL OR btrim(timezone) <> ''",
            name="timezone_not_blank",
        ),
        Index("ix_branches_company_id_status", "company_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    company_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "companies.id",
            name="fk_branches_company_id_companies",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    timezone: Mapped[str | None] = mapped_column(String(60), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    __mapper_args__ = {"version_id_col": version}


class _VersionAndAuditMixin:
    """Estado y auditoría de las tablas de la Fase B (Principios VI y VII)."""

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'ACTIVE'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)


class ApplicationUserModel(_VersionAndAuditMixin, Base):
    """Tabla `application_users`: membresía de una persona humana en una empresa."""

    __tablename__ = "application_users"
    __table_args__ = (
        UniqueConstraint("id", "company_id", name="uq_application_users_id_company_id"),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="status"),
        CheckConstraint(
            "keycloak_user_id = btrim(keycloak_user_id) AND keycloak_user_id <> ''",
            name="keycloak_user_id_not_blank",
        ),
        CheckConstraint("btrim(display_name) <> ''", name="display_name_not_blank"),
        Index(
            "uq_application_users_company_id_person_identity_id_active",
            "company_id",
            "person_identity_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        Index(
            "uq_application_users_company_id_keycloak_user_id_active",
            "company_id",
            "keycloak_user_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        Index("ix_application_users_keycloak_user_id_status", "keycloak_user_id", "status"),
        Index("ix_application_users_company_id_status", "company_id", "status"),
        Index("ix_application_users_person_identity_id", "person_identity_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    company_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "companies.id",
            name="fk_application_users_company_id_companies",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    keycloak_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    person_identity_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    reference_email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))

    __mapper_args__ = {"version_id_col": version}


class UserBranchModel(_VersionAndAuditMixin, Base):
    """Tabla `user_branches`: asignación usuario–sucursal de la misma empresa (R-05)."""

    __tablename__ = "user_branches"
    __table_args__ = (
        UniqueConstraint(
            "application_user_id",
            "branch_id",
            name="uq_user_branches_application_user_id_branch_id",
        ),
        ForeignKeyConstraint(
            ["application_user_id", "company_id"],
            ["application_users.id", "application_users.company_id"],
            name="fk_user_branches_application_user_company",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["branch_id", "company_id"],
            ["branches.id", "branches.company_id"],
            name="fk_user_branches_branch_company",
            ondelete="RESTRICT",
        ),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="status"),
        CheckConstraint(
            "(status = 'ACTIVE' AND deactivated_at IS NULL) "
            "OR (status = 'INACTIVE' AND deactivated_at IS NOT NULL)",
            name="deactivation_consistency",
        ),
        CheckConstraint("btrim(assigned_by) <> ''", name="assigned_by_not_blank"),
        Index("ix_user_branches_branch_id_status", "branch_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    application_user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    branch_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    company_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    assigned_by: Mapped[str] = mapped_column(String(255), nullable=False)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))

    __mapper_args__ = {"version_id_col": version}


class CompanyAdvisorAssignmentModel(_VersionAndAuditMixin, Base):
    """Tabla `company_advisor_assignments`: asesores con vigencia e historial."""

    __tablename__ = "company_advisor_assignments"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="status"),
        CheckConstraint(
            "(status = 'ACTIVE' AND valid_to IS NULL) "
            "OR (status = 'INACTIVE' AND valid_to IS NOT NULL AND valid_to > valid_from)",
            name="validity",
        ),
        CheckConstraint("btrim(assigned_by) <> ''", name="assigned_by_not_blank"),
        Index(
            "uq_company_advisor_assignments_company_id_primary_active",
            "company_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE' AND is_primary"),
        ),
        Index(
            "uq_company_advisor_assignments_company_person_active",
            "company_id",
            "person_identity_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        Index(
            "ix_company_advisor_assignments_company_id_valid_from",
            "company_id",
            text("valid_from DESC"),
        ),
        Index("ix_company_advisor_assignments_person_identity_id", "person_identity_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    company_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "companies.id",
            name="fk_company_advisor_assignments_company_id_companies",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    person_identity_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_by: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))

    __mapper_args__ = {"version_id_col": version}


# Outbox de auditoría (feature 016, D26): estructura de `libs/sio-audit`, registrada en el
# `metadata` para que `alembic check` coincida con la migración.
from sio_audit.outbox import audit_outbox_table  # noqa: E402

audit_outbox = audit_outbox_table(Base.metadata)
