"""Modelos SQLAlchemy de Party Identity Service."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from party_identity_service.infrastructure.database import Base


class PersonIdentityModel(Base):
    """Modelo SQLAlchemy de la tabla person_identities."""

    __tablename__ = "person_identities"

    __table_args__ = (
        UniqueConstraint(
            "identification_country_id",
            "identification_type",
            "identification_number",
            name="uq_person_identities_identification",
        ),
        CheckConstraint(
            "verification_status IN "
            "('UNVERIFIED', 'VERIFIED', 'SUSPENDED')",
            name="ck_person_identities_verification_status",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_person_identities_status",
        ),
        Index(
            "ix_person_identities_status",
            "status",
        ),
        Index(
            "ix_person_identities_identification_country_id",
            "identification_country_id",
        ),
        Index(
            "ix_person_identities_identification_type",
            "identification_type",
        ),
        Index(
            "ix_person_identities_verification_status",
            "verification_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        default=uuid4,
    )

    identification_country_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )

    identification_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    identification_number: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    middle_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    second_last_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    birth_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    verification_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ACTIVE",
        server_default=text("'ACTIVE'"),
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )

    created_by: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    updated_by: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
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

    __mapper_args__ = {
        "version_id_col": version,
    }


class OrganizationIdentityModel(Base):
    """Modelo SQLAlchemy de la tabla organization_identities."""

    __tablename__ = "organization_identities"

    __table_args__ = (
        UniqueConstraint(
            "country_id",
            "identification_type",
            "identification_number",
            name="uq_organization_identities_identification",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_organization_identities_status",
        ),
        Index(
            "ix_organization_identities_status",
            "status",
        ),
        Index(
            "ix_organization_identities_country_id",
            "country_id",
        ),
        Index(
            "ix_organization_identities_identification_type",
            "identification_type",
        ),
        Index(
            "ix_organization_identities_registration_status",
            "registration_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        default=uuid4,
    )

    country_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )

    identification_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    identification_number: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    legal_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    trade_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    organization_type: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    registration_status: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    website: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ACTIVE",
        server_default=text("'ACTIVE'"),
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )

    created_by: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    updated_by: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
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

    __mapper_args__ = {
        "version_id_col": version,
    }


class IdentificationTypeRuleModel(Base):
    """Modelo SQLAlchemy de la tabla identification_type_rules."""

    __tablename__ = "identification_type_rules"

    __table_args__ = (
        CheckConstraint(
            "party_kind IN ('PERSON', 'ORGANIZATION')",
            name="ck_identification_type_rules_party_kind",
        ),
        CheckConstraint(
            "length(trim(number_pattern)) > 0",
            name="ck_identification_type_rules_number_pattern_not_empty",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from",
            name="ck_identification_type_rules_valid_range",
        ),
        CheckConstraint(
            "min_age_years IS NULL OR min_age_years >= 0",
            name="ck_identification_type_rules_min_age_non_negative",
        ),
        CheckConstraint(
            "max_age_years IS NULL OR max_age_years >= 0",
            name="ck_identification_type_rules_max_age_non_negative",
        ),
        CheckConstraint(
            "min_age_years IS NULL OR max_age_years IS NULL "
            "OR max_age_years >= min_age_years",
            name="ck_identification_type_rules_age_range",
        ),
        Index(
            "uq_identification_type_rules_active",
            "party_kind",
            "country_id",
            "identification_type",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
        Index(
            "ix_identification_type_rules_country_id",
            "country_id",
        ),
        Index(
            "ix_identification_type_rules_sigla",
            "sigla",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        default=uuid4,
    )

    party_kind: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    country_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )

    identification_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    sigla: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    number_pattern: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    number_pattern_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    example_value: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    min_age_years: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    max_age_years: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )

    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    valid_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )

    created_by: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    updated_by: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
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

    __mapper_args__ = {
        "version_id_col": version,
    }


class IdentificationTypeRuleCountryCorrectionModel(Base):
    """Registro de la migración 0020 (G-017-01): estado anterior de cada regla corregida.

    `COUNTRY_CORRECTED`: regla histórica de 0006/0010 cuyo `country_id` pasó del UUID histórico
    al de Colombia del entorno. `DUPLICATE_RETIRED`: copia equivalente del `seed` retirada. La
    aplicación no lo escribe; el `downgrade` de 0020 restaura las reglas desde aquí.
    """

    __tablename__ = "identification_type_rule_country_corrections"

    __table_args__ = (
        CheckConstraint(
            "correction IN ('COUNTRY_CORRECTED', 'DUPLICATE_RETIRED')",
            name="ck_identification_type_rule_country_corrections_correction",
        ),
    )

    rule_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    correction: Mapped[str] = mapped_column(String(30), nullable=False)
    previous_country_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    new_country_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    previous_is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    previous_valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    previous_version: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_updated_by: Mapped[str] = mapped_column(String(255), nullable=False)
    previous_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


# Modelos de la Fase B: se definen en un módulo propio y se reexportan aquí para
# que `models` siga siendo el punto único de registro de la metadata.
from party_identity_service.infrastructure.phase_b_models import (  # noqa: E402,F401
    GlobalBusinessSectorModel,
    OrganizationBusinessSectorModel,
    OrganizationContactPersonModel,
    OrganizationContactProfileModel,
    OrganizationLegalRepresentativeModel,
    PersonContactProfileModel,
)


# Outbox de auditoría (feature 016, D26): estructura de `libs/sio-audit`, registrada en el
# `metadata` para que `alembic check` coincida con la migración.
from sio_audit.outbox import audit_outbox_table  # noqa: E402

audit_outbox = audit_outbox_table(Base.metadata)
