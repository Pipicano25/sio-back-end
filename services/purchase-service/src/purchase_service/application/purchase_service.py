"""Compras en borrador (Historia 1; FR-001 a FR-011; research.md R-06, R-11).

Flujo de toda escritura: acceso a la sucursal (DS-09) → comprobaciones baratas de
estado y versión → validación de referencias **fuera de transacción** → transacción
corta: bloqueo de la compra, revalidación de estado, versión y operación en curso,
cambio, totales, evento de auditoría y `COMMIT`.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from purchase_service.application import audit_events as audit
from purchase_service.application.branch_access import OperatorAccess, require_branch_access
from purchase_service.application.exceptions import (
    InvalidStatusError,
    NotFoundError,
    OperationInProgressError,
    ValidationFailedError,
    VersionConflictError,
    field_error,
)
from purchase_service.application.ports import AccessDirectory, CompanyInfo
from purchase_service.application.reference_validation import HeaderInput, LineInput, ReferenceResolver, resolve_together
from purchase_service.application.snapshots import apply_amounts, apply_header, apply_line, recompute_totals, touch
from purchase_service.domain.money import DomainRuleError, LineAmounts, line_amounts
from purchase_service.domain.status import DRAFT, MAX_LINES
from purchase_service.infrastructure.models import Purchase, PurchaseDetail
from purchase_service.infrastructure.repository import PurchaseRepository


@dataclass(frozen=True, slots=True)
class Actor:
    """Usuario humano que actúa: su `sub` (D1) y su acceso operativo (token propio)."""

    subject: str
    access: AccessDirectory


@dataclass(frozen=True, slots=True)
class HeaderData:
    branch_id: UUID
    company_supplier_id: UUID
    operation_date: date
    supplier_payment_condition_id: UUID | None
    promised_delivery_at: datetime | None
    supplier_document_number: str | None
    observations: str | None


@dataclass(frozen=True, slots=True)
class LineData:
    company_product_id: UUID
    company_product_presentation_id: UUID | None
    supplier_product_id: UUID | None
    quantity: Decimal
    unit_cost: Decimal
    discount_amount: Decimal
    tax_amount: Decimal


@dataclass(frozen=True, slots=True)
class PurchaseView:
    purchase: Purchase
    lines: list[PurchaseDetail]
    pending_operation_id: UUID | None = None


def compute_amounts(lines: Sequence[LineData], *, prefix: Callable[[int], str]) -> list[LineAmounts]:
    """Valida y calcula todas las líneas; reúne los errores de formato (`422`)."""
    errors: list[dict] = []
    amounts: list[LineAmounts] = []
    for index, line in enumerate(lines):
        try:
            amounts.append(
                line_amounts(line.quantity, line.unit_cost, line.discount_amount, line.tax_amount, prefix=prefix(index))
            )
        except DomainRuleError as error:
            errors.append(field_error(error.field or prefix(index), error.code, error.message))
    if errors:
        raise ValidationFailedError(errors)
    return amounts


def header_values(purchase: Purchase) -> dict:
    return {
        "status": purchase.status,
        "branch_id": purchase.branch_id,
        "company_supplier_id": purchase.company_supplier_id,
        "supplier_payment_condition_id": purchase.supplier_payment_condition_id,
        "operation_date": purchase.operation_date,
        "due_date": purchase.due_date,
        "payment_condition_code_snapshot": purchase.payment_condition_code_snapshot,
        "currency_code": purchase.currency_code,
        "subtotal": purchase.subtotal,
        "discount_total": purchase.discount_total,
        "tax_total": purchase.tax_total,
        "total": purchase.total,
        "version": purchase.version,
    }


def line_values(detail: PurchaseDetail) -> dict:
    return {
        "line_number": detail.line_number,
        "company_product_id": detail.company_product_id,
        "company_product_presentation_id": detail.company_product_presentation_id,
        "supplier_product_id": detail.supplier_product_id,
        "quantity": detail.quantity,
        "unit_cost": detail.unit_cost,
        "discount_amount": detail.discount_amount,
        "tax_amount": detail.tax_amount,
        "subtotal": detail.subtotal,
        "total": detail.total,
    }


class PurchaseService:
    def __init__(
        self, repository: PurchaseRepository, resolver: ReferenceResolver, *, clock: Callable[[], datetime]
    ) -> None:
        self._repo = repository
        self._resolver = resolver
        self._clock = clock

    # ------------------------------------------------------------------ apoyo

    def _existing(self, company_id: UUID, purchase_id: UUID) -> Purchase:
        purchase = self._repo.get_purchase(company_id, purchase_id)
        if purchase is None:
            raise NotFoundError()
        self._repo.end_read()
        return purchase

    def _precheck(self, purchase: Purchase, version: int | None) -> None:
        pending = self._repo.pending_operation(purchase.id)
        if pending is not None:
            raise OperationInProgressError(pending.id)
        if purchase.status != DRAFT:
            raise InvalidStatusError(purchase.status)
        if version is not None and purchase.version != version:
            raise VersionConflictError()

    def _lock_draft(self, company_id: UUID, purchase_id: UUID, version: int) -> Purchase:
        self._repo.begin()
        purchase = self._repo.lock_purchase(company_id, purchase_id)
        if purchase is None:
            raise NotFoundError()
        pending = self._repo.pending_operation(purchase.id)
        if pending is not None:
            raise OperationInProgressError(pending.id)
        self._precheck(purchase, version)
        return purchase

    def _company_for(self, purchase: Purchase) -> CompanyInfo:
        company = self._resolver.company(purchase.company_id)
        # La moneda de la compra queda fijada al crearla (FR-010).
        return replace(company, default_currency=purchase.currency_code)

    def view(self, purchase: Purchase) -> PurchaseView:
        pending = self._repo.pending_operation(purchase.id)
        return PurchaseView(purchase, self._repo.lines(purchase.id), pending.id if pending else None)

    # ------------------------------------------------------------------ crear

    def create(self, company_id: UUID, header: HeaderData, lines: Sequence[LineData], actor: Actor) -> PurchaseView:
        operator = require_branch_access(actor.access, company_id, header.branch_id)
        amounts = compute_amounts(lines, prefix=lambda index: f"lines[{index}].")
        company = self._resolver.company(company_id)
        header_snapshot, line_snapshots = resolve_together(
            lambda: self._resolver.resolve_header(company, _header_input(header)),
            lambda: self._resolver.resolve_lines(
                company_id,
                header.company_supplier_id,
                [
                    LineInput(
                        line.company_product_id,
                        line.company_product_presentation_id,
                        line.supplier_product_id,
                        amount.quantity,
                        field_prefix=f"lines[{index}].",
                        line_number=index + 1,
                    )
                    for index, (line, amount) in enumerate(zip(lines, amounts, strict=True))
                ],
            ),
        )

        now = self._clock()
        purchase = Purchase(
            id=uuid4(),
            company_id=company_id,
            branch_id=header.branch_id,
            company_supplier_id=header.company_supplier_id,
            supplier_payment_condition_id=header.supplier_payment_condition_id,
            status=DRAFT,
            operation_date=header.operation_date,
            promised_delivery_at=header.promised_delivery_at,
            supplier_document_number=header.supplier_document_number,
            observations=header.observations,
            currency_code=company.default_currency,
            created_by_user_id=operator.application_user_id,
            created_at=now,
            updated_at=now,
            created_by=actor.subject,
            updated_by=actor.subject,
        )
        apply_header(purchase, header_snapshot)
        details = []
        for index, (line, amount, snapshot) in enumerate(zip(lines, amounts, line_snapshots, strict=True)):
            detail = PurchaseDetail(
                id=uuid4(),
                purchase_id=purchase.id,
                line_number=index + 1,
                company_product_id=line.company_product_id,
                company_product_presentation_id=line.company_product_presentation_id,
                supplier_product_id=line.supplier_product_id,
                created_at=now,
                updated_at=now,
                created_by=actor.subject,
                updated_by=actor.subject,
            )
            apply_amounts(detail, amount)
            apply_line(detail, snapshot)
            details.append(detail)
        recompute_totals(purchase, details)

        try:
            self._repo.begin()
            self._repo.add(purchase)
            self._repo.flush()
            self._repo.add_all(details)
            self._repo.flush()
            audit.record(
                self._repo.session,
                action=audit.CREATE_PURCHASE,
                entity_type=audit.PURCHASE,
                entity_id=purchase.id,
                company_id=company_id,
                branch_id=purchase.branch_id,
                application_user_id=operator.application_user_id,
                new_values={**header_values(purchase), "lines": [line_values(detail) for detail in details]},
            )
            self._repo.commit()
        except Exception:
            self._repo.rollback()
            raise
        return PurchaseView(purchase, details, None)

    # --------------------------------------------------------------- cabecera

    def update_header(
        self, company_id: UUID, purchase_id: UUID, header: HeaderData, version: int, actor: Actor
    ) -> PurchaseView:
        current = self._existing(company_id, purchase_id)
        operator = require_branch_access(actor.access, company_id, current.branch_id)
        if header.branch_id != current.branch_id:
            require_branch_access(actor.access, company_id, header.branch_id)
        self._precheck(current, version)
        header_snapshot = self._resolver.resolve_header(self._company_for(current), _header_input(header))

        try:
            purchase = self._lock_draft(company_id, purchase_id, version)
            previous = header_values(purchase)
            purchase.branch_id = header.branch_id
            purchase.company_supplier_id = header.company_supplier_id
            purchase.supplier_payment_condition_id = header.supplier_payment_condition_id
            purchase.operation_date = header.operation_date
            purchase.promised_delivery_at = header.promised_delivery_at
            purchase.supplier_document_number = header.supplier_document_number
            purchase.observations = header.observations
            apply_header(purchase, header_snapshot)
            touch(purchase, actor.subject, self._clock())
            self._repo.flush()
            audit.record(
                self._repo.session,
                action=audit.UPDATE_PURCHASE,
                entity_type=audit.PURCHASE,
                entity_id=purchase.id,
                company_id=company_id,
                branch_id=purchase.branch_id,
                application_user_id=operator.application_user_id,
                previous_values=previous,
                new_values=header_values(purchase),
            )
            self._repo.commit()
        except Exception:
            self._repo.rollback()
            raise
        return PurchaseView(purchase, self._repo.lines(purchase.id), None)

    # ----------------------------------------------------------------- líneas

    def _resolve_line(self, purchase: Purchase, line: LineData) -> tuple[LineAmounts, object]:
        amount = compute_amounts([line], prefix=lambda _: "")[0]
        snapshot = self._resolver.resolve_lines(
            purchase.company_id,
            purchase.company_supplier_id,
            [
                LineInput(
                    line.company_product_id,
                    line.company_product_presentation_id,
                    line.supplier_product_id,
                    amount.quantity,
                )
            ],
        )[0]
        return amount, snapshot

    def _finish_line_change(
        self, purchase: Purchase, operator: OperatorAccess, actor: Actor, action: str, detail_id: UUID, previous, new
    ) -> PurchaseView:
        lines = self._repo.lines(purchase.id)
        recompute_totals(purchase, lines)
        touch(purchase, actor.subject, self._clock())
        self._repo.flush()
        audit.record(
            self._repo.session,
            action=action,
            entity_type=audit.PURCHASE_DETAIL,
            entity_id=detail_id,
            company_id=purchase.company_id,
            branch_id=purchase.branch_id,
            application_user_id=operator.application_user_id,
            previous_values=previous,
            new_values={**(new or {}), "purchase_id": purchase.id, "purchase_version": purchase.version},
        )
        self._repo.commit()
        return PurchaseView(purchase, lines, None)

    def add_line(self, company_id: UUID, purchase_id: UUID, line: LineData, version: int, actor: Actor) -> PurchaseView:
        current = self._existing(company_id, purchase_id)
        operator = require_branch_access(actor.access, company_id, current.branch_id)
        self._precheck(current, version)
        amount, snapshot = self._resolve_line(current, line)

        try:
            purchase = self._lock_draft(company_id, purchase_id, version)
            existing = self._repo.lines(purchase.id)
            if len(existing) >= MAX_LINES:
                raise ValidationFailedError(
                    [field_error("lines", "LINES_LIMIT_EXCEEDED", f"Una compra admite a lo sumo {MAX_LINES} líneas.")]
                )
            used = {item.line_number for item in existing}
            highest = max(used, default=0)
            number = highest + 1 if highest < MAX_LINES else min(n for n in range(1, MAX_LINES + 1) if n not in used)
            now = self._clock()
            detail = PurchaseDetail(
                id=uuid4(),
                purchase_id=purchase.id,
                line_number=number,
                company_product_id=line.company_product_id,
                company_product_presentation_id=line.company_product_presentation_id,
                supplier_product_id=line.supplier_product_id,
                created_at=now,
                updated_at=now,
                created_by=actor.subject,
                updated_by=actor.subject,
            )
            apply_amounts(detail, amount)
            apply_line(detail, snapshot)
            self._repo.add(detail)
            self._repo.flush()
            return self._finish_line_change(
                purchase, operator, actor, audit.ADD_PURCHASE_DETAIL, detail.id, None, line_values(detail)
            )
        except Exception:
            self._repo.rollback()
            raise

    def update_line(
        self, company_id: UUID, purchase_id: UUID, detail_id: UUID, line: LineData, version: int, actor: Actor
    ) -> PurchaseView:
        current = self._existing(company_id, purchase_id)
        operator = require_branch_access(actor.access, company_id, current.branch_id)
        self._precheck(current, version)
        if not any(item.id == detail_id for item in self._repo.lines(current.id)):
            raise NotFoundError()
        self._repo.end_read()
        amount, snapshot = self._resolve_line(current, line)

        try:
            purchase = self._lock_draft(company_id, purchase_id, version)
            detail = next((item for item in self._repo.lines(purchase.id) if item.id == detail_id), None)
            if detail is None:
                raise NotFoundError()
            previous = line_values(detail)
            detail.company_product_id = line.company_product_id
            detail.company_product_presentation_id = line.company_product_presentation_id
            detail.supplier_product_id = line.supplier_product_id
            apply_amounts(detail, amount)
            apply_line(detail, snapshot)
            touch(detail, actor.subject, self._clock())
            self._repo.flush()
            return self._finish_line_change(
                purchase, operator, actor, audit.UPDATE_PURCHASE_DETAIL, detail.id, previous, line_values(detail)
            )
        except Exception:
            self._repo.rollback()
            raise

    def delete_line(self, company_id: UUID, purchase_id: UUID, detail_id: UUID, version: int, actor: Actor) -> PurchaseView:
        current = self._existing(company_id, purchase_id)
        operator = require_branch_access(actor.access, company_id, current.branch_id)
        self._precheck(current, version)

        try:
            purchase = self._lock_draft(company_id, purchase_id, version)
            detail = next((item for item in self._repo.lines(purchase.id) if item.id == detail_id), None)
            if detail is None:
                raise NotFoundError()
            previous = line_values(detail)
            self._repo.delete(detail)
            self._repo.flush()
            return self._finish_line_change(
                purchase, operator, actor, audit.DELETE_PURCHASE_DETAIL, detail_id, previous, None
            )
        except Exception:
            self._repo.rollback()
            raise


def _header_input(header: HeaderData) -> HeaderInput:
    return HeaderInput(
        branch_id=header.branch_id,
        company_supplier_id=header.company_supplier_id,
        operation_date=header.operation_date,
        supplier_payment_condition_id=header.supplier_payment_condition_id,
    )
