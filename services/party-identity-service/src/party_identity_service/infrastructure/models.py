"""Modelos SQLAlchemy de Party Identity Service."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
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
            "identification_type IN "
            "('NATIONAL_ID', 'FOREIGN_ID', 'PASSPORT', 'TAX_ID', 'OTHER')",
            name="ck_person_identities_identification_type",
        ),
        CheckConstraint(
            "verification_status IN "
            "('UNVERIFIED', 'VERIFIED', 'SUSPENDED')",
            name="ck_person_identities_verification_status",
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
        String(20),
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

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )

    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )

    updated_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
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
