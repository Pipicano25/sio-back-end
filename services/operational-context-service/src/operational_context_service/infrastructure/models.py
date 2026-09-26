"""Modelos SQLAlchemy de Operational Context Service (data-model.md).

Las referencias a Party Identity y Geography son `UUID REF` sin FK física
(Principio II). La única FK es interna: `branches.company_id → companies.id`.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
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
