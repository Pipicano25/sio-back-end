"""Unicidad cruzada entre unidades de medida y tipos de empaque (FR-017, R-09)."""

from __future__ import annotations

from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from product_catalog_service.application.exceptions import (
    CodeUsedByPackagingTypeError,
    CodeUsedByUnitOfMeasureError,
)
from product_catalog_service.infrastructure.locks import advisory_lock
from product_catalog_service.infrastructure.models import (
    GlobalPackagingTypeModel,
    GlobalUnitOfMeasureModel,
)


def ensure_base_code_available(
    session: Session,
    code: str,
    target: Literal["unit", "packaging"],
) -> None:
    """Serializa por código y rechaza si la otra tabla ya lo usa."""
    advisory_lock(session, f"product-catalog:base-code:{code}")

    if target == "unit":
        taken = session.execute(
            select(GlobalPackagingTypeModel.id).where(GlobalPackagingTypeModel.code == code)
        ).first()
        if taken is not None:
            raise CodeUsedByPackagingTypeError(
                f"El código {code} ya pertenece a un tipo de empaque."
            )
        return

    taken = session.execute(
        select(GlobalUnitOfMeasureModel.id).where(GlobalUnitOfMeasureModel.code == code)
    ).first()
    if taken is not None:
        raise CodeUsedByUnitOfMeasureError(
            f"El código {code} ya pertenece a una unidad de medida."
        )
