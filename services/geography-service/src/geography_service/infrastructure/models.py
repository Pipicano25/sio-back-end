from datetime import datetime
from uuid import UUID, uuid4
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey
from sqlalchemy import Numeric

from geography_service.infrastructure.database import Base


class GlobalCountryModel(Base):
    __tablename__ = "global_countries"

    __table_args__ = (
        UniqueConstraint(
            "iso2_code",
            name="uq_global_countries_iso2_code",
        ),
        UniqueConstraint(
            "iso3_code",
            name="uq_global_countries_iso3_code",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_global_countries_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        default=uuid4,
    )

    iso2_code: Mapped[str] = mapped_column(
        CHAR(2),
        nullable=False,
    )

    iso3_code: Mapped[str] = mapped_column(
        CHAR(3),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    phone_prefix: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
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


class GlobalAdministrativeDivisionModel(Base):
    __tablename__ = "global_administrative_divisions"

    __table_args__ = (
        CheckConstraint(
            "division_type IN "
            "('DEPARTMENT', 'STATE', 'PROVINCE', "
            "'REGION', 'DISTRICT', 'OTHER')",
            name="ck_global_administrative_divisions_type",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_global_administrative_divisions_status",
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
        ForeignKey(
            "global_countries.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    parent_division_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "global_administrative_divisions.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    code: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
    )

    division_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
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


class GlobalCityModel(Base):
    """Modelo SQLAlchemy de la tabla global_cities."""

    __tablename__ = "global_cities"

    __table_args__ = (
        CheckConstraint(
            "latitude IS NULL OR "
            "(latitude >= -90 AND latitude <= 90)",
            name="ck_global_cities_latitude",
        ),
        CheckConstraint(
            "longitude IS NULL OR "
            "(longitude >= -180 AND longitude <= 180)",
            name="ck_global_cities_longitude",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_global_cities_status",
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
        ForeignKey(
            "global_countries.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    administrative_division_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "global_administrative_divisions.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    code: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
    )

    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(
            precision=9,
            scale=6,
        ),
        nullable=True,
    )

    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(
            precision=9,
            scale=6,
        ),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
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
