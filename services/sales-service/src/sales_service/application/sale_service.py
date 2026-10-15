"""Ventas en borrador (Historia 1; FR-001 a FR-012; research.md R-06, R-07, R-12, R-17).

Flujo de toda escritura: acceso a la sucursal (DS-09) → comprobaciones baratas de
estado y versión → formato de lo que envía el vendedor → validación de referencias y
resolución del precio **fuera de transacción** → transacción corta: bloqueo de la venta,
revalidación de estado, versión y operación en curso, cambio, totales, auditoría y `COMMIT`.

El vendedor nunca envía precio (DS-11), fecha ni condición de pago (DP-01): el precio lo
resuelve Commercial Relationship; la fecha es la del día en la zona de la sucursal (R-12).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sales_service.application import audit_events as audit
from sales_service.application.branch_access import OperatorAccess, require_branch_access
from sales_service.application.exceptions import (
    InvalidStatusError,
    NotFoundError,
    OperationInProgressError,
    ValidationFailedError,
    VersionConflictError,
    field_error,
)
from sales_service.application.ports import AccessDirectory, CompanyInfo
from sales_service.application.reference_validation import (
    HeaderInput,
    LineInput,
    LineSnapshot,
    ReferenceResolver,
    resolve_together,
    today_in,
)
from sales_service.application.snapshots import (
    apply_amounts,
    apply_business_date,
    apply_header,
    apply_line,
    recompute_totals,
    touch,
)
from sales_service.domain.money import DomainRuleError, LineAmounts, LineInputs, check_line_inputs, line_amounts
from sales_service.domain.status import CASH, DRAFT, MAX_LINES
from sales_service.infrastructure.models import Sale, SaleDetail
from sales_service.infrastructure.repository import SaleRepository


@dataclass(frozen=True, slots=True)
class Actor:
    """Usuario humano que actúa: su `sub` (D1) y su acceso operativo (token propio)."""

    subject: str
    access: AccessDirectory


@dataclass(frozen=True, slots=True)
class HeaderData:
    branch_id: UUID
    company_customer_id: UUID
    observations: str | None
    payment_method_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class LineData:
    company_product_id: UUID
    company_product_presentation_id: UUID | None
    price_list_id: UUID | None
    quantity: Decimal
    discount_amount: Decimal
    tax_amount: Decimal


@dataclass(frozen=True, slots=True)
class SaleView:
    sale: Sale
    lines: list[SaleDetail]
    pending_operation_id: UUID | None = None


def check_inputs(lines: Sequence[LineData], *, prefix: Callable[[int], str]) -> list[LineInputs]:
    """Formato de cantidad, descuento e impuesto de todas las líneas; reúne los errores (`422`)."""
    errors: list[dict] = []
    checked: list[LineInputs] = []
    for index, line in enumerate(lines):
        try:
            checked.append(
                check_line_inputs(line.quantity, line.discount_amount, line.tax_amount, prefix=prefix(index))
            )
        except DomainRuleError as error:
            errors.append(field_error(error.field or prefix(index), error.code, error.message))
    if errors:
        raise ValidationFailedError(errors)
    return checked


def compute_amounts(
    inputs: Sequence[LineInputs], snapshots: Sequence[LineSnapshot], *, prefix: Callable[[int], str]
) -> list[LineAmounts]:
    """Montos con el precio resuelto (el descuento se compara con el subtotal ya conocido)."""
    errors: list[dict] = []
    amounts: list[LineAmounts] = []
    for index, (item, snapshot) in enumerate(zip(inputs, snapshots, strict=True)):
        try:
            amounts.append(
                line_amounts(item.quantity, snapshot.unit_price, item.discount_amount, item.tax_amount, prefix=prefix(index))
            )
        except DomainRuleError as error:
            errors.append(field_error(error.field or prefix(index), error.code, error.message))
    if errors:
        raise ValidationFailedError(errors)
    return amounts


def line_inputs(lines: Sequence[LineData], inputs: Sequence[LineInputs], *, first_number: int = 1) -> list[LineInput]:
    return [
        LineInput(
            line.company_product_id,
            line.company_product_presentation_id,
            line.price_list_id,
            item.quantity,
            field_prefix=f"lines[{index}].",
            line_number=first_number + index,
        )
        for index, (line, item) in enumerate(zip(lines, inputs, strict=True))
    ]


def header_values(sale: Sale) -> dict:
    return {
        "status": sale.status,
        "branch_id": sale.branch_id,
        "company_customer_id": sale.company_customer_id,
        "operation_date": sale.operation_date,
        "due_date": sale.due_date,
        "payment_condition_code_snapshot": sale.payment_condition_code_snapshot,
        "payment_method_id": sale.payment_method_id,
        "payment_method_code_snapshot": sale.payment_method_code_snapshot,
        "currency_code": sale.currency_code,
        "subtotal": sale.subtotal,
        "discount_total": sale.discount_total,
        "tax_total": sale.tax_total,
        "total": sale.total,
        "version": sale.version,
    }


def line_values(detail: SaleDetail) -> dict:
    """Datos de auditoría de una línea: sin costo ni margen (DS-12)."""
    return {
        "line_number": detail.line_number,
        "company_product_id": detail.company_product_id,
        "company_product_presentation_id": detail.company_product_presentation_id,
        "price_list_id": detail.price_list_id,
        "price_list_item_id": detail.price_list_item_id,
        "price_list_requested": detail.price_list_requested,
        "quantity": detail.quantity,
        "unit_price": detail.unit_price,
        "discount_amount": detail.discount_amount,
        "tax_amount": detail.tax_amount,
        "subtotal": detail.subtotal,
        "total": detail.total,
    }


class SaleService:
    def __init__(
        self, repository: SaleRepository, resolver: ReferenceResolver, *, clock: Callable[[], datetime]
    ) -> None:
        self._repo = repository
        self._resolver = resolver
        self._clock = clock

    # ------------------------------------------------------------------ apoyo

    def _existing(self, company_id: UUID, sale_id: UUID) -> Sale:
        sale = self._repo.get_sale(company_id, sale_id)
        if sale is None:
            raise NotFoundError()
        self._repo.end_read()
        return sale

    def _precheck(self, sale: Sale, version: int | None) -> None:
        pending = self._repo.pending_operation(sale.id)
        if pending is not None:
            raise OperationInProgressError(pending.id)
        if sale.status != DRAFT:
            raise InvalidStatusError(sale.status)
        if version is not None and sale.version != version:
            raise VersionConflictError()

    def _lock_draft(self, company_id: UUID, sale_id: UUID, version: int) -> Sale:
        self._repo.begin()
        sale = self._repo.lock_sale(company_id, sale_id)
        if sale is None:
            raise NotFoundError()
        self._precheck(sale, version)
        return sale

    def _company_for(self, sale: Sale) -> CompanyInfo:
        company = self._resolver.company(sale.company_id)
        if company.default_currency != sale.currency_code:
            # La moneda de la venta quedó fijada al crearla (FR-010).
            return CompanyInfo(company.id, company.status, sale.currency_code)
        return company

    def view(self, sale: Sale) -> SaleView:
        pending = self._repo.pending_operation(sale.id)
        return SaleView(sale, self._repo.lines(sale.id), pending.id if pending else None)

    # ------------------------------------------------------------------ crear

    def create(self, company_id: UUID, header: HeaderData, lines: Sequence[LineData], actor: Actor) -> SaleView:
        operator = require_branch_access(actor.access, company_id, header.branch_id)
        inputs = check_inputs(lines, prefix=lambda index: f"lines[{index}].")
        company = self._resolver.company(company_id)
        header_snapshot, line_snapshots = resolve_together(
            lambda: self._resolver.resolve_header(
                company, HeaderInput(header.branch_id, header.company_customer_id, header.payment_method_id)
            ),
            lambda: self._resolver.resolve_lines(company_id, company.default_currency, line_inputs(lines, inputs)),
        )
        amounts = compute_amounts(inputs, line_snapshots, prefix=lambda index: f"lines[{index}].")

        now = self._clock()
        sale = Sale(
            id=uuid4(),
            company_id=company_id,
            branch_id=header.branch_id,
            company_customer_id=header.company_customer_id,
            status=DRAFT,
            payment_condition_code_snapshot=CASH,
            payment_terms_days_snapshot=0,
            observations=header.observations,
            currency_code=company.default_currency,
            has_unknown_cost=False,
            created_by_user_id=operator.application_user_id,
            created_at=now,
            updated_at=now,
            created_by=actor.subject,
            updated_by=actor.subject,
        )
        apply_header(sale, header_snapshot)
        apply_business_date(sale, today_in(header_snapshot.branch_timezone, now))
        details = []
        for index, (line, amount, snapshot) in enumerate(zip(lines, amounts, line_snapshots, strict=True)):
            detail = SaleDetail(
                id=uuid4(),
                sale_id=sale.id,
                line_number=index + 1,
                company_product_id=line.company_product_id,
                company_product_presentation_id=line.company_product_presentation_id,
                created_at=now,
                updated_at=now,
                created_by=actor.subject,
                updated_by=actor.subject,
            )
            apply_amounts(detail, amount)
            apply_line(detail, snapshot)
            details.append(detail)
        recompute_totals(sale, details)

        try:
            self._repo.begin()
            self._repo.add(sale)
            self._repo.flush()
            self._repo.add_all(details)
            self._repo.flush()
            audit.record(
                self._repo.session,
                action=audit.CREATE_SALE,
                entity_type=audit.SALE,
                entity_id=sale.id,
                company_id=company_id,
                branch_id=sale.branch_id,
                application_user_id=operator.application_user_id,
                new_values={**header_values(sale), "lines": [line_values(detail) for detail in details]},
            )
            self._repo.commit()
        except Exception:
            self._repo.rollback()
            raise
        return SaleView(sale, details, None)

    # --------------------------------------------------------------- cabecera

    def update_header(self, company_id: UUID, sale_id: UUID, header: HeaderData, version: int, actor: Actor) -> SaleView:
        current = self._existing(company_id, sale_id)
        operator = require_branch_access(actor.access, company_id, current.branch_id)
        if header.branch_id != current.branch_id:
            require_branch_access(actor.access, company_id, header.branch_id)
        self._precheck(current, version)
        header_snapshot = self._resolver.resolve_header(
            self._company_for(current), HeaderInput(header.branch_id, header.company_customer_id, header.payment_method_id)
        )

        try:
            sale = self._lock_draft(company_id, sale_id, version)
            previous = header_values(sale)
            now = self._clock()
            if header.branch_id != sale.branch_id:
                # Otra sucursal: la fecha informativa se recalcula con su zona horaria (R-12).
                apply_business_date(sale, today_in(header_snapshot.branch_timezone, now))
            sale.branch_id = header.branch_id
            sale.company_customer_id = header.company_customer_id
            sale.observations = header.observations
            apply_header(sale, header_snapshot)
            touch(sale, actor.subject, now)
            self._repo.flush()
            audit.record(
                self._repo.session,
                action=audit.UPDATE_SALE,
                entity_type=audit.SALE,
                entity_id=sale.id,
                company_id=company_id,
                branch_id=sale.branch_id,
                application_user_id=operator.application_user_id,
                previous_values=previous,
                new_values=header_values(sale),
            )
            self._repo.commit()
        except Exception:
            self._repo.rollback()
            raise
        return SaleView(sale, self._repo.lines(sale.id), None)

    # ----------------------------------------------------------------- líneas

    def _resolve_line(self, sale: Sale, line: LineData) -> tuple[LineAmounts, LineSnapshot]:
        item = check_inputs([line], prefix=lambda _: "")[0]
        snapshot = self._resolver.resolve_lines(
            sale.company_id,
            sale.currency_code,
            [LineInput(line.company_product_id, line.company_product_presentation_id, line.price_list_id, item.quantity)],
        )[0]
        amount = compute_amounts([item], [snapshot], prefix=lambda _: "")[0]
        return amount, snapshot

    def _finish_line_change(
        self, sale: Sale, operator: OperatorAccess, actor: Actor, action: str, detail_id: UUID, previous, new
    ) -> SaleView:
        lines = self._repo.lines(sale.id)
        recompute_totals(sale, lines)
        touch(sale, actor.subject, self._clock())
        self._repo.flush()
        audit.record(
            self._repo.session,
            action=action,
            entity_type=audit.SALE_DETAIL,
            entity_id=detail_id,
            company_id=sale.company_id,
            branch_id=sale.branch_id,
            application_user_id=operator.application_user_id,
            previous_values=previous,
            new_values={**(new or {}), "sale_id": sale.id, "sale_version": sale.version},
        )
        self._repo.commit()
        return SaleView(sale, lines, None)

    def add_line(self, company_id: UUID, sale_id: UUID, line: LineData, version: int, actor: Actor) -> SaleView:
        current = self._existing(company_id, sale_id)
        operator = require_branch_access(actor.access, company_id, current.branch_id)
        self._precheck(current, version)
        amount, snapshot = self._resolve_line(current, line)

        try:
            sale = self._lock_draft(company_id, sale_id, version)
            existing = self._repo.lines(sale.id)
            if len(existing) >= MAX_LINES:
                raise ValidationFailedError(
                    [field_error("lines", "LINES_LIMIT_EXCEEDED", f"Una venta admite a lo sumo {MAX_LINES} líneas.")]
                )
            used = {item.line_number for item in existing}
            highest = max(used, default=0)
            number = highest + 1 if highest < MAX_LINES else min(n for n in range(1, MAX_LINES + 1) if n not in used)
            now = self._clock()
            detail = SaleDetail(
                id=uuid4(),
                sale_id=sale.id,
                line_number=number,
                company_product_id=line.company_product_id,
                company_product_presentation_id=line.company_product_presentation_id,
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
                sale, operator, actor, audit.ADD_SALE_DETAIL, detail.id, None, line_values(detail)
            )
        except Exception:
            self._repo.rollback()
            raise

    def update_line(
        self, company_id: UUID, sale_id: UUID, detail_id: UUID, line: LineData, version: int, actor: Actor
    ) -> SaleView:
        current = self._existing(company_id, sale_id)
        operator = require_branch_access(actor.access, company_id, current.branch_id)
        self._precheck(current, version)
        if not any(item.id == detail_id for item in self._repo.lines(current.id)):
            raise NotFoundError()
        self._repo.end_read()
        amount, snapshot = self._resolve_line(current, line)

        try:
            sale = self._lock_draft(company_id, sale_id, version)
            detail = next((item for item in self._repo.lines(sale.id) if item.id == detail_id), None)
            if detail is None:
                raise NotFoundError()
            previous = line_values(detail)
            detail.company_product_id = line.company_product_id
            detail.company_product_presentation_id = line.company_product_presentation_id
            apply_amounts(detail, amount)
            apply_line(detail, snapshot)
            touch(detail, actor.subject, self._clock())
            self._repo.flush()
            return self._finish_line_change(
                sale, operator, actor, audit.UPDATE_SALE_DETAIL, detail.id, previous, line_values(detail)
            )
        except Exception:
            self._repo.rollback()
            raise

    def delete_line(self, company_id: UUID, sale_id: UUID, detail_id: UUID, version: int, actor: Actor) -> SaleView:
        current = self._existing(company_id, sale_id)
        operator = require_branch_access(actor.access, company_id, current.branch_id)
        self._precheck(current, version)

        try:
            sale = self._lock_draft(company_id, sale_id, version)
            detail = next((item for item in self._repo.lines(sale.id) if item.id == detail_id), None)
            if detail is None:
                raise NotFoundError()
            previous = line_values(detail)
            self._repo.delete(detail)
            self._repo.flush()
            return self._finish_line_change(sale, operator, actor, audit.DELETE_SALE_DETAIL, detail_id, previous, None)
        except Exception:
            self._repo.rollback()
            raise
