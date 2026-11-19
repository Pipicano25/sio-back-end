"""Persistencia de la adopción masiva (spec 027, T011; research R5 y R7).

Historia 1: búsqueda de adopciones existentes y consecutivo `P-NNNNNN` del código interno automático. Las
operaciones de procesos en segundo plano (`bulk_adoption_jobs`) llegan con la Historia 3.

El consecutivo se asigna en `SequencedCompanyProductRepository.create`, dentro de la misma transacción del alta y
bajo `pg_advisory_xact_lock` por empresa: el bloqueo se libera con el `commit` del alta, así dos adopciones
simultáneas nunca toman el mismo número.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, cast, func, select
from sqlalchemy.orm import Session

from commercial_relationship_service.application.bulk_adoption_service import ConsecutiveCode
from commercial_relationship_service.infrastructure.models import (
    CompanyProductModel,
    CompanyProductPresentationModel,
)
from commercial_relationship_service.infrastructure.persistence import end_read
from commercial_relationship_service.infrastructure.repositories import CompanyProductRepository

CONSECUTIVE_PREFIX = "P-"
CONSECUTIVE_PATTERN = r"^[Pp]-[0-9]{6,18}$"
"""Códigos que cuentan para el consecutivo (sin distinguir mayúsculas, como la unicidad de `internal_code`)."""
CONSECUTIVE_DIGITS = 6
LOCK_KEY = "commercial-relationship:company-product-consecutive:{company_id}"


def _next_code(session: Session, company_id: UUID) -> str:
    """Siguiente consecutivo libre de la empresa: el mayor `P-NNNNNN` usado más uno. No cierra la transacción."""
    model = CompanyProductModel
    highest = session.scalar(
        select(func.max(cast(func.substr(model.internal_code, 3), BigInteger))).where(
            model.company_id == company_id,
            model.internal_code.op("~")(CONSECUTIVE_PATTERN),
        )
    )
    return f"{CONSECUTIVE_PREFIX}{(highest or 0) + 1:0{CONSECUTIVE_DIGITS}d}"


class BulkAdoptionRepository:
    """Lecturas de la adopción masiva; cada una cierra su transacción implícita (no retiene conexiones)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def find_products(self, company_id: UUID, global_product_ids: list[UUID]) -> dict[UUID, CompanyProductModel]:
        if not global_product_ids:
            return {}
        model = CompanyProductModel
        rows = self.session.scalars(
            select(model).where(model.company_id == company_id, model.global_product_id.in_(global_product_ids))
        )
        found = {row.global_product_id: row for row in rows}
        end_read(self.session)
        return found

    def find_presentations(
        self, company_id: UUID, global_presentation_ids: list[UUID]
    ) -> dict[UUID, CompanyProductPresentationModel]:
        if not global_presentation_ids:
            return {}
        model = CompanyProductPresentationModel
        rows = self.session.scalars(
            select(model).where(
                model.company_id == company_id, model.global_product_presentation_id.in_(global_presentation_ids)
            )
        )
        found = {row.global_product_presentation_id: row for row in rows}
        end_read(self.session)
        return found

    def next_product_code(self, company_id: UUID) -> str:
        """Consecutivo provisional (sin bloqueo); el definitivo lo fija `SequencedCompanyProductRepository`."""
        code = _next_code(self.session, company_id)
        end_read(self.session)
        return code


class SequencedCompanyProductRepository(CompanyProductRepository):
    """`CompanyProductRepository` que asigna el consecutivo definitivo al dar de alta un `ConsecutiveCode`."""

    def create(self, *, audit: dict[str, Any] | None = None, **fields: Any) -> CompanyProductModel:
        if isinstance(fields.get("internal_code"), ConsecutiveCode):
            company_id = fields["company_id"]
            self.lock_advisory(LOCK_KEY.format(company_id=company_id))
            fields["internal_code"] = _next_code(self.session, company_id)
        return super().create(audit=audit, **fields)
