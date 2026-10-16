"""Repositorios de la spec 021: políticas de precios de lista y su historial (`data-model.md`).

La pertenencia de una presentación a una sola política de la lista en cada instante la garantiza la exclusión GiST
`ex_price_list_pricing_policy_presentations_no_overlap` (RC-021-1), también ante operaciones concurrentes; su
violación se traduce a `409 PRESENTATION_ALREADY_IN_POLICY`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from commercial_relationship_service.application import audit_events
from commercial_relationship_service.application.exceptions import (
    CommercialRelationshipError,
    PolicyNameDuplicateError,
    PresentationAlreadyInPolicyError,
    SequenceConflictError,
)
from commercial_relationship_service.application.pagination import PageResult
from commercial_relationship_service.infrastructure.models import (
    AUTOMATIC_FINAL_STATUSES,
    AutomaticPriceApplicationModel,
    AutomaticPriceUpdateRequestModel,
    PriceListItemModel,
    PriceListModel,
    PricingPolicyModel,
    PricingPolicyPresentationModel,
    PricingPolicyTermModel,
)
from commercial_relationship_service.infrastructure.persistence import (
    commit_or_translate,
    end_read,
    flush_or_translate,
)
from commercial_relationship_service.infrastructure.repository_base import SQLAlchemyRepositoryBase

POLICY_DUPLICATES = {
    "uq_price_list_pricing_policies_name_ci": lambda: PolicyNameDuplicateError(field="name"),
    "ex_price_list_pricing_policy_presentations_no_overlap": lambda: PresentationAlreadyInPolicyError(
        field="company_product_presentation_ids"
    ),
}


class PricingPolicyRepository(SQLAlchemyRepositoryBase[PricingPolicyModel]):
    """`price_list_pricing_policies` con sus términos y asignaciones (FR-021-01..06)."""

    model = PricingPolicyModel
    search_columns = ("name",)
    order_columns = ("name", "id")
    duplicates = POLICY_DUPLICATES

    # -------------------------------------------------------------- lecturas

    def list_for_price_list(
        self, company_id: UUID, price_list_id: UUID, *, status: str | None, search: str | None, page: int, page_size: int
    ) -> PageResult[PricingPolicyModel]:
        return self.list_page(
            company_id,
            status=status,
            search=search,
            filters={},
            page=page,
            page_size=page_size,
            conditions=(PricingPolicyModel.price_list_id == price_list_id,),
        )

    def current_markups(self, policy_ids: list[UUID]) -> dict[UUID, Any]:
        """Porcentaje del término abierto de cada política (las inactivas no tienen)."""
        if not policy_ids:
            return {}
        rows = self.session.execute(
            select(PricingPolicyTermModel.policy_id, PricingPolicyTermModel.markup_percentage).where(
                PricingPolicyTermModel.policy_id.in_(policy_ids), PricingPolicyTermModel.valid_to.is_(None)
            )
        ).all()
        end_read(self.session)
        return dict(rows)

    def last_markups(self, policy_ids: list[UUID]) -> dict[UUID, Any]:
        """Porcentaje vigente o, en una política inactiva, el último que tuvo."""
        if not policy_ids:
            return {}
        rows = self.session.execute(
            select(PricingPolicyTermModel.policy_id, PricingPolicyTermModel.markup_percentage)
            .where(PricingPolicyTermModel.policy_id.in_(policy_ids))
            .order_by(PricingPolicyTermModel.policy_id, PricingPolicyTermModel.valid_from)
        ).all()
        end_read(self.session)
        return {policy_id: markup for policy_id, markup in rows}

    def presentation_counts(self, policy_ids: list[UUID]) -> dict[UUID, int]:
        if not policy_ids:
            return {}
        rows = self.session.execute(
            select(PricingPolicyPresentationModel.policy_id, func.count())
            .where(
                PricingPolicyPresentationModel.policy_id.in_(policy_ids),
                PricingPolicyPresentationModel.valid_to.is_(None),
            )
            .group_by(PricingPolicyPresentationModel.policy_id)
        ).all()
        end_read(self.session)
        return dict(rows)

    def terms(self, policy_id: UUID) -> list[PricingPolicyTermModel]:
        rows = list(
            self.session.scalars(
                select(PricingPolicyTermModel)
                .where(PricingPolicyTermModel.policy_id == policy_id)
                .order_by(PricingPolicyTermModel.valid_from, PricingPolicyTermModel.id)
            )
        )
        end_read(self.session)
        return rows

    def assignments_page(
        self, policy_id: UUID, *, include_closed: bool, page: int, page_size: int
    ) -> PageResult[PricingPolicyPresentationModel]:
        statement = select(PricingPolicyPresentationModel).where(PricingPolicyPresentationModel.policy_id == policy_id)
        if not include_closed:
            statement = statement.where(PricingPolicyPresentationModel.valid_to.is_(None))
        total = self.session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        rows = list(
            self.session.scalars(
                statement.order_by(PricingPolicyPresentationModel.valid_from, PricingPolicyPresentationModel.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        end_read(self.session)
        return PageResult(items=rows, page=page, page_size=page_size, total_records=total)

    # ------------------------------------------- lecturas dentro de una escritura

    def open_term(self, policy_id: UUID) -> PricingPolicyTermModel | None:
        return self.session.scalar(
            select(PricingPolicyTermModel)
            .where(PricingPolicyTermModel.policy_id == policy_id, PricingPolicyTermModel.valid_to.is_(None))
            .with_for_update()
        )

    def open_assignments(self, policy_id: UUID) -> dict[UUID, PricingPolicyPresentationModel]:
        rows = self.session.scalars(
            select(PricingPolicyPresentationModel)
            .where(PricingPolicyPresentationModel.policy_id == policy_id, PricingPolicyPresentationModel.valid_to.is_(None))
            .with_for_update()
        )
        return {row.company_product_presentation_id: row for row in rows}

    # ------------------------------------------------------------- escrituras

    def insert(
        self,
        policy: PricingPolicyModel,
        rows: list[Any],
        *,
        audit: dict[str, Any],
    ) -> PricingPolicyModel:
        """Inserta la política con su primer término y sus asignaciones en una transacción."""
        self.session.add(policy)
        flush_or_translate(self.session, duplicates=self.duplicates)
        self.session.add_all(rows)
        audit_events.track_create(self.session, policy, **audit)
        commit_or_translate(self.session, duplicates=self.duplicates)
        self.session.refresh(policy)
        end_read(self.session)
        return policy

    def save_with(self, policy: PricingPolicyModel, rows: list[Any], *, audit: dict[str, Any]) -> PricingPolicyModel:
        """Guarda la política (versión y auditoría) con los cierres y altas de su historial."""
        self.session.add_all(rows)
        return self.save(policy, duplicates=self.duplicates, audit=audit)

    def abort(self) -> None:
        """Descarta la transacción en curso (y sus bloqueos) ante un error detectado tras bloquear."""
        self.session.rollback()

    @staticmethod
    def close(row: PricingPolicyTermModel | PricingPolicyPresentationModel, at: datetime, actor: str) -> None:
        row.valid_to = at
        row.closed_at = at
        row.closed_by = actor


# --------------------------------------------------------------------------
# Solicitudes y aplicaciones automáticas (FR-021-19..28)
# --------------------------------------------------------------------------

class DetailAlreadyReceived(CommercialRelationshipError):
    """Otra transacción guardó la misma línea de compra a la vez: el servicio vuelve a leerla (idempotencia)."""


REQUEST_DUPLICATES = {
    "uq_automatic_price_update_requests_sequence": lambda: SequenceConflictError(field="sequence"),
    "uq_automatic_price_update_requests_purchase_detail_id": DetailAlreadyReceived,
}

FINAL = AUTOMATIC_FINAL_STATUSES


class AutomaticPricingRepository:
    """Inbox de solicitudes y cola de aplicaciones por (lista, presentación)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------ inbox (A1)

    def request_by_detail(self, purchase_detail_id: UUID) -> AutomaticPriceUpdateRequestModel | None:
        row = self.session.scalar(
            select(AutomaticPriceUpdateRequestModel).where(
                AutomaticPriceUpdateRequestModel.purchase_detail_id == purchase_detail_id
            )
        )
        end_read(self.session)
        return row

    def applications_of(self, request_id: UUID) -> list[AutomaticPriceApplicationModel]:
        rows = list(
            self.session.scalars(
                select(AutomaticPriceApplicationModel)
                .where(AutomaticPriceApplicationModel.request_id == request_id)
                .order_by(AutomaticPriceApplicationModel.price_list_id)
            )
        )
        end_read(self.session)
        return rows

    def lists_in_policy_mode(self, company_id: UUID, at: datetime) -> list[UUID]:
        """Listas con al menos una política `ACTIVE` en el instante (DS-06): `[created_at, deactivated_at)`."""
        return list(
            self.session.scalars(
                select(PricingPolicyModel.price_list_id)
                .where(
                    PricingPolicyModel.company_id == company_id,
                    PricingPolicyModel.created_at <= at,
                    or_(PricingPolicyModel.deactivated_at.is_(None), PricingPolicyModel.deactivated_at > at),
                )
                .distinct()
                .order_by(PricingPolicyModel.price_list_id)
            )
        )

    def capture(self, price_list_id: UUID, presentation_id: UUID, at: datetime) -> tuple[UUID, UUID, Any] | None:
        """Política y término vigentes en el instante para la presentación en la lista (RC-021-5)."""
        row = self.session.execute(
            select(
                PricingPolicyPresentationModel.policy_id,
                PricingPolicyTermModel.id,
                PricingPolicyTermModel.markup_percentage,
            )
            .join(PricingPolicyTermModel, PricingPolicyTermModel.policy_id == PricingPolicyPresentationModel.policy_id)
            .where(
                PricingPolicyPresentationModel.price_list_id == price_list_id,
                PricingPolicyPresentationModel.company_product_presentation_id == presentation_id,
                PricingPolicyPresentationModel.valid_from <= at,
                or_(PricingPolicyPresentationModel.valid_to.is_(None), PricingPolicyPresentationModel.valid_to > at),
                PricingPolicyTermModel.valid_from <= at,
                or_(PricingPolicyTermModel.valid_to.is_(None), PricingPolicyTermModel.valid_to > at),
            )
        ).first()
        return None if row is None else (row[0], row[1], row[2])

    def insert_request(self, request, applications: list, *, audit: dict[str, Any]):
        self.session.add(request)
        flush_or_translate(self.session, duplicates=REQUEST_DUPLICATES)
        self.session.add_all(applications)
        audit_events.track_create(self.session, request, **audit)
        commit_or_translate(self.session, duplicates=REQUEST_DUPLICATES)
        end_read(self.session)
        return request

    def rollback(self) -> None:
        self.session.rollback()

    # ------------------------------------------------------- cola del worker

    def processable_ids(self, limit: int) -> list[UUID]:
        """Aplicaciones listas para procesar en orden de secuencia (FR-021-22); se revalidan bajo bloqueo."""
        rows = self.session.execute(
            text(PROCESSABLE_SQL + " ORDER BY a.sequence, a.created_at LIMIT :limit"), {"limit": limit}
        ).scalars().all()
        end_read(self.session)
        return list(rows)

    def lock_queue(self, price_list_id: UUID, presentation_id: UUID) -> None:
        self.session.execute(
            select(func.pg_advisory_xact_lock(func.hashtextextended(f"cr:automatic-price:{price_list_id}:{presentation_id}", 0)))
        )

    def application_for_update(self, application_id: UUID) -> AutomaticPriceApplicationModel | None:
        return self.session.scalar(
            select(AutomaticPriceApplicationModel)
            .where(AutomaticPriceApplicationModel.id == application_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def still_processable(self, application_id: UUID) -> bool:
        return self.session.execute(
            text(PROCESSABLE_SQL + " AND a.id = :id"), {"id": application_id}
        ).first() is not None

    def now(self) -> datetime:
        return self.session.scalar(select(func.now()))

    def get(self, model, entity_id: UUID):
        return self.session.get(model, entity_id, populate_existing=True)

    def prices_of(self, price_list_id: UUID, presentation_id: UUID) -> list[PriceListItemModel]:
        """Precios `ACTIVE` de la lista y presentación, bloqueados para la transacción en curso."""
        return list(
            self.session.scalars(
                select(PriceListItemModel)
                .where(
                    PriceListItemModel.price_list_id == price_list_id,
                    PriceListItemModel.company_product_presentation_id == presentation_id,
                    PriceListItemModel.status == "ACTIVE",
                )
                .order_by(PriceListItemModel.valid_from)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        )

    def add(self, model) -> None:
        self.session.add(model)

    def flush(self) -> None:
        self.session.flush()

    def commit(self) -> None:
        self.session.commit()


class AutomaticPriceApplicationRepository(SQLAlchemyRepositoryBase[AutomaticPriceApplicationModel]):
    """Consulta (A2, A3) y resolución administrativa (A4) de las aplicaciones automáticas (FR-021-27, FR-021-32a)."""

    model = AutomaticPriceApplicationModel
    order_columns = ("created_at", "id")

    def list_for_company(
        self,
        company_id: UUID,
        *,
        status: str | None,
        price_list_id: UUID | None,
        presentation_id: UUID | None,
        purchase_id: UUID | None,
        page: int,
        page_size: int,
    ) -> PageResult[AutomaticPriceApplicationModel]:
        conditions: tuple[Any, ...] = ()
        if purchase_id is not None:
            conditions = (
                AutomaticPriceApplicationModel.request_id.in_(
                    select(AutomaticPriceUpdateRequestModel.id).where(
                        AutomaticPriceUpdateRequestModel.company_id == company_id,
                        AutomaticPriceUpdateRequestModel.purchase_id == purchase_id,
                    )
                ),
            )
        return self.list_page(
            company_id,
            status=status or "ALL",
            search=None,
            filters={"price_list_id": price_list_id, "company_product_presentation_id": presentation_id},
            page=page,
            page_size=page_size,
            conditions=conditions,
        )

    def requests_of(self, applications: list[AutomaticPriceApplicationModel]) -> dict[UUID, AutomaticPriceUpdateRequestModel]:
        ids = {application.request_id for application in applications}
        if not ids:
            return {}
        rows = self.session.scalars(
            select(AutomaticPriceUpdateRequestModel).where(AutomaticPriceUpdateRequestModel.id.in_(ids))
        )
        found = {row.id: row for row in rows}
        end_read(self.session)
        return found

    def currencies_of(self, applications: list[AutomaticPriceApplicationModel]) -> dict[UUID, str]:
        ids = {application.price_list_id for application in applications}
        if not ids:
            return {}
        rows = self.session.execute(select(PriceListModel.id, PriceListModel.currency_code).where(PriceListModel.id.in_(ids)))
        found = {row[0]: row[1] for row in rows}
        end_read(self.session)
        return found

    def lock_queue(self, price_list_id: UUID, presentation_id: UUID) -> None:
        """El mismo bloqueo consultivo del worker: la resolución no se cruza con un procesamiento en curso."""
        AutomaticPricingRepository(self.session).lock_queue(price_list_id, presentation_id)


# Una aplicación se procesa si no está en estado final, ya tocaba su intento, no hay otra anterior pendiente de la
# misma lista y presentación y ya llegaron todas las solicitudes anteriores de su serie (secuencia contigua desde 1).
PROCESSABLE_SQL = f"""
SELECT a.id FROM automatic_price_applications a
JOIN automatic_price_update_requests r ON r.id = a.request_id
WHERE a.status IN ('PENDING', 'FAILED')
  AND a.next_attempt_at <= now()
  AND NOT EXISTS (
      SELECT 1 FROM automatic_price_applications b
       WHERE b.price_list_id = a.price_list_id
         AND b.company_product_presentation_id = a.company_product_presentation_id
         AND b.sequence < a.sequence
         AND b.status NOT IN ({", ".join(f"'{status}'" for status in AUTOMATIC_FINAL_STATUSES)}))
  AND (SELECT count(*) FROM automatic_price_update_requests p
        WHERE p.company_id = r.company_id
          AND p.company_product_presentation_id = r.company_product_presentation_id
          AND p.sequence < r.sequence) = r.sequence - 1
"""
