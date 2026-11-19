"""Adopción masiva de presentaciones globales (spec 027; research R1, R5, R6, R7 y R9).

Cada producto y cada presentación se adoptan con los casos de uso individuales
(`CompanyProductService.adopt` y `CompanyProductPresentationService.adopt`): mismas validaciones, mismo primer uso
en Product Catalog, mismo evento de auditoría y mismo autor. Cada adopción es su propia transacción corta, así un
rechazo no revierte lo adoptado de otros elementos (FR-008).

Este módulo resuelve lo que la adopción individual no tiene:

- los valores automáticos del producto (R5) y de la presentación (R6) cuando no se envían;
- el código interno automático: código de barras principal de la presentación base o, si no tiene, el consecutivo
  `P-000001` de la empresa (el valor definitivo lo asigna el repositorio bajo un bloqueo por empresa);
- la idempotencia (lo que ya existe se informa `ALREADY_ADOPTED`, R7);
- la traducción de las excepciones a la lista cerrada de motivos (R9).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID

from commercial_relationship_service.application.exceptions import (
    CompanyProductInactiveError,
    CompanyProductNotFoundError,
    DependencyUnavailableError,
    DuplicateAdoptionError,
    DuplicateInternalCodeError,
    DuplicatePresentationAdoptionError,
    DuplicateSkuError,
    GlobalPresentationInactiveError,
    GlobalPresentationNotEligibleError,
    GlobalPresentationNotFoundError,
    GlobalPresentationOfOtherProductError,
    GlobalProductInactiveError,
    GlobalProductNotEligibleError,
    GlobalProductNotFoundError,
)
from commercial_relationship_service.application.ports import (
    CatalogProductSummary,
    ProductCatalogBulkDirectory,
)
from commercial_relationship_service.domain.currency import validate_currency
from commercial_relationship_service.domain.rules import validate_inventory_flags, validate_presentation_flags
from commercial_relationship_service.domain.status import ACTIVE

BULK_LIMIT = 100
"""Elementos distintos por solicitud en espera (FR-003)."""

# Resultados por elemento (R9).
ADOPTED = "ADOPTED"
ALREADY_ADOPTED = "ALREADY_ADOPTED"
REJECTED = "REJECTED"

# Motivos de rechazo: lista cerrada de R9.
GLOBAL_NOT_FOUND = "GLOBAL_NOT_FOUND"
GLOBAL_INACTIVE = "GLOBAL_INACTIVE"
NOT_ELIGIBLE = "NOT_ELIGIBLE"
DUPLICATE_INTERNAL_CODE = "DUPLICATE_INTERNAL_CODE"
DUPLICATE_SKU = "DUPLICATE_SKU"
COMPANY_PRODUCT_INACTIVE = "COMPANY_PRODUCT_INACTIVE"
PRODUCT_REJECTED = "PRODUCT_REJECTED"
PRODUCT_MISMATCH = "PRODUCT_MISMATCH"
PRODUCT_DATA_CONFLICT = "PRODUCT_DATA_CONFLICT"
DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"
REASONS = (
    GLOBAL_NOT_FOUND,
    GLOBAL_INACTIVE,
    NOT_ELIGIBLE,
    DUPLICATE_INTERNAL_CODE,
    DUPLICATE_SKU,
    COMPANY_PRODUCT_INACTIVE,
    PRODUCT_REJECTED,
    PRODUCT_MISMATCH,
    PRODUCT_DATA_CONFLICT,
    DEPENDENCY_UNAVAILABLE,
)

DEFAULT_CURRENCY = "COP"
DISPLAY_NAME_MAX = 200
# Mismos valores por defecto de `CompanyProductCreate` y `CompanyProductPresentationCreate` (R5, R6).
PRODUCT_FLAG_DEFAULTS = {
    "inventory_control_enabled": True,
    "lot_tracking_enabled": False,
    "expiration_tracking_enabled": False,
    "is_purchasable": True,
    "is_sellable": True,
}
PRESENTATION_DEFAULTS = {
    "internal_code": None,
    "sku": None,
    "reference_code": None,
    "is_purchasable": True,
    "is_sellable": True,
    "is_default_purchase": False,
    "is_default_sale": False,
}
# Identificadores que cuentan como código de barras (R5, opción A).
BARCODE_TYPES = ("GTIN", "EAN", "UPC", "BARCODE")
CONSECUTIVE_ATTEMPTS = 3
"""Intentos con el consecutivo si una adopción simultánea con otro código lo tomó entre la consulta y el alta."""

_PRODUCT_REASONS: tuple[tuple[type[Exception], str], ...] = (
    (GlobalProductNotFoundError, GLOBAL_NOT_FOUND),
    (GlobalProductInactiveError, GLOBAL_INACTIVE),
    (GlobalProductNotEligibleError, NOT_ELIGIBLE),
    (DuplicateInternalCodeError, DUPLICATE_INTERNAL_CODE),
    (DependencyUnavailableError, DEPENDENCY_UNAVAILABLE),
)
_PRESENTATION_REASONS: tuple[tuple[type[Exception], str], ...] = (
    (GlobalPresentationNotFoundError, GLOBAL_NOT_FOUND),
    (GlobalPresentationInactiveError, GLOBAL_INACTIVE),
    (GlobalPresentationNotEligibleError, NOT_ELIGIBLE),
    (GlobalPresentationOfOtherProductError, PRODUCT_MISMATCH),
    (DuplicateSkuError, DUPLICATE_SKU),
    (DuplicateInternalCodeError, DUPLICATE_INTERNAL_CODE),
    (CompanyProductInactiveError, COMPANY_PRODUCT_INACTIVE),
    (CompanyProductNotFoundError, PRODUCT_REJECTED),
    (DependencyUnavailableError, DEPENDENCY_UNAVAILABLE),
)


class ConsecutiveCode(str):
    """Código interno provisional `P-NNNNNN` (R5).

    La adopción lo recibe como cualquier código; el repositorio de productos lo reconoce por su tipo y, bajo
    `pg_advisory_xact_lock` por empresa y en la misma transacción del alta, lo reemplaza por el siguiente
    consecutivo libre. Así dos adopciones simultáneas nunca toman el mismo número.
    """


class BulkAdoptionRepository(Protocol):
    """Lecturas propias de la adopción masiva (`infrastructure/bulk_adoption_repository.py`)."""

    def find_products(self, company_id: UUID, global_product_ids: list[UUID]) -> dict[UUID, Any]:
        """Productos de la empresa por `global_product_id`, en cualquier estado."""
        ...

    def find_presentations(self, company_id: UUID, global_presentation_ids: list[UUID]) -> dict[UUID, Any]:
        """Presentaciones de la empresa por `global_product_presentation_id`, en cualquier estado."""
        ...

    def next_product_code(self, company_id: UUID) -> str:
        """Siguiente consecutivo libre `P-NNNNNN` de la empresa (lectura sin bloqueo)."""
        ...


@dataclass(frozen=True, slots=True)
class PresentationRequest:
    """Elemento de la solicitud en modo `PRESENTATIONS`: solo los campos enviados (sin `None`)."""

    global_product_presentation_id: UUID
    product_values: dict[str, Any] = field(default_factory=dict)
    presentation_values: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProductOutcome:
    global_product_id: UUID
    result: str
    company_product_id: UUID | None = None
    internal_code: str | None = None
    reason: str | None = None


@dataclass(slots=True)
class PresentationOutcome:
    global_product_presentation_id: UUID
    global_product_id: UUID | None
    result: str
    company_product_presentation_id: UUID | None = None
    reason: str | None = None


@dataclass(slots=True)
class BulkAdoptionResult:
    products: list[ProductOutcome]
    presentations: list[PresentationOutcome]

    def totals(self) -> dict[str, dict[str, int]]:
        def count(outcomes) -> dict[str, int]:
            results = [item.result for item in outcomes]
            return {
                "adopted": results.count(ADOPTED),
                "already_adopted": results.count(ALREADY_ADOPTED),
                "rejected": results.count(REJECTED),
            }

        return {"products": count(self.products), "presentations": count(self.presentations)}


def _reason(error: Exception, table: tuple[tuple[type[Exception], str], ...]) -> str | None:
    return next((reason for kind, reason in table if isinstance(error, kind)), None)


def _product_defaults(defaults: dict[str, Any]) -> dict[str, Any]:
    """Moneda y banderas de `defaults` sobre los valores por defecto de la adopción individual."""
    return {
        "currency_code": defaults.get("currency_code") or DEFAULT_CURRENCY,
        **{name: defaults.get(name, value) for name, value in PRODUCT_FLAG_DEFAULTS.items()},
    }


def _check_values(product: dict[str, Any], presentation: dict[str, Any]) -> None:
    """Validaciones locales de la adopción individual, antes de adoptar nada (FR-012; `422` de la solicitud)."""
    validate_currency(product["currency_code"])
    validate_inventory_flags(
        inventory_control_enabled=product["inventory_control_enabled"],
        lot_tracking_enabled=product["lot_tracking_enabled"],
        expiration_tracking_enabled=product["expiration_tracking_enabled"],
    )
    validate_presentation_flags(
        is_purchasable=presentation["is_purchasable"],
        is_sellable=presentation["is_sellable"],
        is_default_purchase=presentation["is_default_purchase"],
        is_default_sale=presentation["is_default_sale"],
    )


class BulkAdoptionService:
    """Adopta presentaciones en bloque y, por debajo, el producto de cada una (FR-001)."""

    def __init__(
        self,
        *,
        products,
        presentations,
        repository: BulkAdoptionRepository,
        catalog_factory: Callable[[], ProductCatalogBulkDirectory],
    ) -> None:
        self._products = products
        self._presentations = presentations
        self._repository = repository
        # Se resuelve solo cuando hace falta Product Catalog (no pide el token técnico en vano).
        self._catalog_factory = catalog_factory

    # ------------------------------------------------------------ modo PRESENTATIONS

    def adopt_presentations(
        self,
        company_id: UUID,
        items: list[PresentationRequest],
        defaults: dict[str, Any],
        *,
        actor: str,
    ) -> BulkAdoptionResult:
        """Adopta hasta 100 presentaciones distintas; los ids repetidos se procesan una vez (el primero manda).

        Las lecturas por lotes iniciales (presentaciones y resúmenes de producto) se hacen antes de adoptar: si
        Product Catalog no responde ahí, se propaga `DependencyUnavailableError` (`503`) sin haber cambiado nada.

        Raises:
            CurrencyNotSupportedError, InventoryFlagsInvalidError, DefaultFlagInvalidError: datos inválidos en
                `defaults` o en un elemento; no se adopta nada.
            DependencyUnavailableError: Product Catalog no respondió a las lecturas por lotes iniciales.
        """
        first: dict[UUID, PresentationRequest] = {}
        for item in items:
            first.setdefault(item.global_product_presentation_id, item)
        unique = list(first.values())
        base_product = _product_defaults(defaults)

        for item in unique:
            _check_values({**base_product, **item.product_values}, {**PRESENTATION_DEFAULTS, **item.presentation_values})

        catalog = self._catalog_factory()
        lookups = {entry.id: entry.ref for entry in catalog.lookup_presentations([item.global_product_presentation_id for item in unique])}

        groups: dict[UUID, list[PresentationRequest]] = {}
        outcomes: dict[UUID, PresentationOutcome] = {}

        for item in unique:
            ref = lookups.get(item.global_product_presentation_id)
            if ref is None or not ref.found or ref.global_product_id is None:
                outcomes[item.global_product_presentation_id] = PresentationOutcome(
                    item.global_product_presentation_id, None, REJECTED, reason=GLOBAL_NOT_FOUND
                )
            else:
                groups.setdefault(ref.global_product_id, []).append(item)

        existing = self._repository.find_products(company_id, list(groups))
        to_adopt = [product_id for product_id in groups if product_id not in existing]
        summaries = catalog.product_summaries(to_adopt) if to_adopt else {}
        adopted_presentations = self._repository.find_presentations(
            company_id, [item.global_product_presentation_id for members in groups.values() for item in members]
        )

        products: list[ProductOutcome] = []

        for global_product_id, members in groups.items():
            product, presentations = self.adopt_product_group(
                company_id,
                global_product_id,
                members,
                base_product,
                actor=actor,
                catalog=catalog,
                existing_product=existing.get(global_product_id),
                existing_presentations=adopted_presentations,
                summary=summaries.get(global_product_id),
            )
            products.append(product)
            outcomes.update({outcome.global_product_presentation_id: outcome for outcome in presentations})

        return BulkAdoptionResult(
            products=products,
            presentations=[outcomes[item.global_product_presentation_id] for item in unique],
        )

    # ------------------------------------------------------------ núcleo por producto

    def adopt_product_group(
        self,
        company_id: UUID,
        global_product_id: UUID,
        members: list[PresentationRequest],
        product_defaults: dict[str, Any],
        *,
        actor: str,
        catalog: ProductCatalogBulkDirectory,
        existing_product: Any | None,
        existing_presentations: dict[UUID, Any],
        summary: CatalogProductSummary | None,
    ) -> tuple[ProductOutcome, list[PresentationOutcome]]:
        """Adopta (o reconoce) el producto y luego cada presentación pedida, una transacción por elemento."""
        if existing_product is not None:
            model, outcome = existing_product, _already(existing_product)
        else:
            model, outcome = self._adopt_product(
                company_id, global_product_id, members, product_defaults, actor=actor, catalog=catalog, summary=summary
            )

        def rejected(reason: str) -> list[PresentationOutcome]:
            return [
                PresentationOutcome(item.global_product_presentation_id, global_product_id, REJECTED, reason=reason)
                for item in members
            ]

        if model is None:
            return outcome, rejected(PRODUCT_REJECTED)

        if model.status != ACTIVE:
            # No se reactiva en bloque (spec, casos límite).
            return outcome, rejected(COMPANY_PRODUCT_INACTIVE)

        return outcome, [
            self._adopt_presentation(company_id, global_product_id, model, item, existing_presentations, actor=actor)
            for item in members
        ]

    # -------------------------------------------------------------- internos

    def _adopt_product(
        self,
        company_id: UUID,
        global_product_id: UUID,
        members: list[PresentationRequest],
        product_defaults: dict[str, Any],
        *,
        actor: str,
        catalog: ProductCatalogBulkDirectory,
        summary: CatalogProductSummary | None,
    ) -> tuple[Any | None, ProductOutcome]:
        def rejected(reason: str) -> tuple[None, ProductOutcome]:
            return None, ProductOutcome(global_product_id, REJECTED, reason=reason)

        sent = [item.product_values for item in members if item.product_values]
        if any(values != sent[0] for values in sent[1:]):
            return rejected(PRODUCT_DATA_CONFLICT)
        sent_values = sent[0] if sent else {}

        if summary is None or not summary.found:
            return rejected(GLOBAL_NOT_FOUND)

        values = {
            "global_product_id": global_product_id,
            "internal_code": sent_values.get("internal_code"),
            "reference_code": None,
            "display_name": (summary.canonical_name or "").strip()[:DISPLAY_NAME_MAX] or None,
            "short_name": None,
            **product_defaults,
        }
        values.update(sent_values)

        if values["internal_code"] is None:
            try:
                values["internal_code"] = self._automatic_code(company_id, global_product_id, summary, catalog)
            except DependencyUnavailableError:
                return rejected(DEPENDENCY_UNAVAILABLE)

        if values["display_name"] is None:
            # Sin nombre canónico no hay nombre automático: la misma regla que exige `display_name` al adoptar.
            return rejected(NOT_ELIGIBLE)

        for attempt in range(CONSECUTIVE_ATTEMPTS):
            try:
                model = self._products.adopt(company_id, values, actor=actor)
                return model, ProductOutcome(
                    global_product_id, ADOPTED, company_product_id=model.id, internal_code=model.internal_code
                )
            except DuplicateAdoptionError:
                # Otra solicitud lo adoptó entre la consulta y el alta (R7).
                winner = self._repository.find_products(company_id, [global_product_id]).get(global_product_id)
                return (winner, _already(winner)) if winner is not None else rejected(DEPENDENCY_UNAVAILABLE)
            except DuplicateInternalCodeError:
                if not isinstance(values["internal_code"], ConsecutiveCode) or attempt == CONSECUTIVE_ATTEMPTS - 1:
                    return rejected(DUPLICATE_INTERNAL_CODE)
                values["internal_code"] = ConsecutiveCode(self._repository.next_product_code(company_id))
            except tuple(kind for kind, _ in _PRODUCT_REASONS) as error:
                return rejected(_reason(error, _PRODUCT_REASONS))

        return rejected(DUPLICATE_INTERNAL_CODE)  # pragma: no cover (el ciclo siempre retorna)

    def _automatic_code(
        self,
        company_id: UUID,
        global_product_id: UUID,
        summary: CatalogProductSummary,
        catalog: ProductCatalogBulkDirectory,
    ) -> str:
        """Código de barras principal de la presentación base o, si no tiene, el consecutivo (R5, opción A)."""
        candidates = {
            identifier.global_product_presentation_id: identifier
            for identifier in sorted(
                (
                    identifier
                    for identifier in summary.identifiers
                    if identifier.is_primary
                    and identifier.type in BARCODE_TYPES
                    and identifier.global_product_presentation_id is not None
                ),
                key=lambda identifier: BARCODE_TYPES.index(identifier.type),
                reverse=True,
            )
        }

        if candidates:
            # Solo se consulta la presentación base cuando hay algún código de barras principal que elegir.
            base = next((item.id for item in catalog.product_presentations(global_product_id) if item.is_base), None)
            if base in candidates:
                return candidates[base].value

        return ConsecutiveCode(self._repository.next_product_code(company_id))

    def _adopt_presentation(
        self,
        company_id: UUID,
        global_product_id: UUID,
        product: Any,
        item: PresentationRequest,
        existing: dict[UUID, Any],
        *,
        actor: str,
    ) -> PresentationOutcome:
        presentation_id = item.global_product_presentation_id
        current = existing.get(presentation_id)

        if current is not None and current.company_product_id == product.id:
            return PresentationOutcome(
                presentation_id, global_product_id, ALREADY_ADOPTED, company_product_presentation_id=current.id
            )

        values = {
            "company_product_id": product.id,
            "global_product_presentation_id": presentation_id,
            **PRESENTATION_DEFAULTS,
            **item.presentation_values,
        }

        try:
            model = self._presentations.adopt(company_id, values, actor=actor)
        except DuplicatePresentationAdoptionError:
            winner = self._repository.find_presentations(company_id, [presentation_id]).get(presentation_id)
            return PresentationOutcome(
                presentation_id,
                global_product_id,
                ALREADY_ADOPTED,
                company_product_presentation_id=None if winner is None else winner.id,
            )
        except tuple(kind for kind, _ in _PRESENTATION_REASONS) as error:
            return PresentationOutcome(
                presentation_id, global_product_id, REJECTED, reason=_reason(error, _PRESENTATION_REASONS)
            )

        return PresentationOutcome(presentation_id, global_product_id, ADOPTED, company_product_presentation_id=model.id)


def _already(model: Any) -> ProductOutcome:
    return ProductOutcome(
        model.global_product_id, ALREADY_ADOPTED, company_product_id=model.id, internal_code=model.internal_code
    )
