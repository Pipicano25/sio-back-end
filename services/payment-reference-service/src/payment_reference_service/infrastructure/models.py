"""Modelos SQLAlchemy de Payment Reference Service."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Boolean, CheckConstraint, DateTime, String, Text, UniqueConstraint, false
from payment_reference_service.infrastructure.database import Base


class GlobalPaymentConditionTypeModel(Base):
    """Modelo persistente de una condición global de pago."""

    __tablename__ = "global_payment_condition_types"

    __table_args__ = (
        UniqueConstraint(
            "code",
            name="uq_global_payment_condition_types_code",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_global_payment_condition_types_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        nullable=False,
    )

    code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
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
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class GlobalPaymentMethodModel(Base):
    """Modelo persistente de un método global de pago."""

    __tablename__ = "global_payment_methods"

    __table_args__ = (
        UniqueConstraint(
            "code",
            name="uq_global_payment_methods_code",
        ),
        CheckConstraint(
            "method_type IN ('CASH', 'BANK', 'CARD', 'WALLET', 'CHECK', 'OTHER')",
            name="ck_global_payment_methods_method_type",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_global_payment_methods_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        nullable=False,
    )

    code: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    method_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    requires_reference: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
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
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
