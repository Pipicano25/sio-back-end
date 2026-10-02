"""Modelos SQLAlchemy de la Fase B (migraciones 0013–0017).

Se separan de `models.py` (Fase A) para no alterar ese módulo; comparten la
misma `Base` y se registran al importar `models`.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    false,
    func,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from party_identity_service.infrastructure.database import Base


class _AuditMixin:
    """Auditoría (Principio VI, D1) y `version` (Principio VII)."""

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)
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

    @declared_attr.directive
    def __mapper_args__(cls) -> dict:
        return {"version_id_col": cls.version}


class GlobalBusinessSectorModel(_AuditMixin, Base):
    """Modelo de la tabla global_business_sectors."""

    __tablename__ = "global_business_sectors"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    parent_sector_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "global_business_sectors.id",
            name="fk_global_business_sectors_parent_sector_id",
        ),
        nullable=True,
    )
    classification_system: Mapped[str] = mapped_column(String(30), nullable=False)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ACTIVE",
        server_default=text("'ACTIVE'"),
    )


class _ContactProfileColumns(_AuditMixin):
    """Columnas comunes de los perfiles de contacto versionados."""

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    address_line: Mapped[str | None] = mapped_column(Text, nullable=True)
    country_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    administrative_division_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=True,
    )
    city_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by_user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    confirmed_by_company_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)


class PersonContactProfileModel(_ContactProfileColumns, Base):
    """Modelo de la tabla person_contact_profiles."""

    __tablename__ = "person_contact_profiles"

    person_identity_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "person_identities.id",
            name="fk_person_contact_profiles_person_identity_id",
        ),
        nullable=False,
    )


class OrganizationContactProfileModel(_ContactProfileColumns, Base):
    """Modelo de la tabla organization_contact_profiles."""

    __tablename__ = "organization_contact_profiles"

    organization_identity_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "organization_identities.id",
            name="fk_organization_contact_profiles_organization_identity_id",
        ),
        nullable=False,
    )


class OrganizationContactPersonModel(_AuditMixin, Base):
    """Modelo de la tabla organization_contact_persons."""

    __tablename__ = "organization_contact_persons"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_identity_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "organization_identities.id",
            name="fk_organization_contact_persons_organization_identity_id",
        ),
        nullable=False,
    )
    person_identity_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "person_identities.id",
            name="fk_organization_contact_persons_person_identity_id",
        ),
        nullable=True,
    )
    position: Mapped[str | None] = mapped_column(String(120), nullable=True)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())


class OrganizationBusinessSectorModel(_AuditMixin, Base):
    """Modelo de la tabla organization_business_sectors."""

    __tablename__ = "organization_business_sectors"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_identity_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "organization_identities.id",
            name="fk_organization_business_sectors_organization_identity_id",
        ),
        nullable=False,
    )
    global_business_sector_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "global_business_sectors.id",
            name="fk_organization_business_sectors_global_business_sector_id",
        ),
        nullable=False,
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OrganizationLegalRepresentativeModel(_AuditMixin, Base):
    """Modelo de la tabla organization_legal_representatives."""

    __tablename__ = "organization_legal_representatives"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_identity_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "organization_identities.id",
            name="fk_organization_legal_representatives_organization_identity_id",
        ),
        nullable=False,
    )
    person_identity_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "person_identities.id",
            name="fk_organization_legal_representatives_person_identity_id",
        ),
        nullable=False,
    )
    representative_type: Mapped[str] = mapped_column(String(30), nullable=False)
    position: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_document_reference: Mapped[str | None] = mapped_column(String(1000), nullable=True)
