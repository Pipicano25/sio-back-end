"""Núcleo de la adopción masiva (spec 027, T009): valores automáticos, código interno y motivos de rechazo.

Los servicios de adopción individual se sustituyen por dobles que registran los valores recibidos y lanzan las
mismas excepciones que los reales; el catálogo es `FakeProductCatalogBulkDirectory`. Las pruebas de API
(`tests/api/test_bulk_adoption_presentations.py`) cubren el recorrido real contra la base.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from commercial_relationship_service.application.bulk_adoption_service import (
    ADOPTED,
    ALREADY_ADOPTED,
    REJECTED,
    BulkAdoptionService,
    ConsecutiveCode,
    PresentationRequest,
)
from commercial_relationship_service.application.exceptions import (
    CompanyProductInactiveError,
    DependencyUnavailableError,
    DuplicateAdoptionError,
    DuplicateInternalCodeError,
    DuplicateSkuError,
    GlobalPresentationNotEligibleError,
    GlobalPresentationOfOtherProductError,
    GlobalProductInactiveError,
    GlobalProductNotEligibleError,
)
from commercial_relationship_service.domain.errors import CurrencyNotSupportedError
from tests.fakes import FakeProductCatalog, FakeProductCatalogBulkDirectory

COMPANY = uuid4()
ACTOR = "sub-admin.dao"


class ProductsStub:
    """Doble de `CompanyProductService.adopt`: guarda lo adoptado o lanza el error programado por producto."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.errors: dict[UUID, list[Exception]] = {}
        self.adopted: dict[UUID, SimpleNamespace] = {}

    def adopt(self, company_id, values, *, actor):
        self.calls.append(dict(values))
        pending = self.errors.get(values["global_product_id"])
        if pending:
            raise pending.pop(0)
        code = values["internal_code"]
        model = SimpleNamespace(
            id=uuid4(),
            company_id=company_id,
            global_product_id=values["global_product_id"],
            internal_code=f"P-{len(self.adopted) + 1:06d}" if isinstance(code, ConsecutiveCode) else code,
            status="ACTIVE",
            created_by=actor,
        )
        self.adopted[values["global_product_id"]] = model
        return model


class PresentationsStub:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.errors: dict[UUID, Exception] = {}

    def adopt(self, company_id, values, *, actor):
        self.calls.append(dict(values))
        error = self.errors.get(values["global_product_presentation_id"])
        if error is not None:
            raise error
        return SimpleNamespace(id=uuid4(), company_product_id=values["company_product_id"], **{
            "global_product_presentation_id": values["global_product_presentation_id"]
        })


class RepositoryStub:
    def __init__(self, products: ProductsStub) -> None:
        self.products = products
        self.existing_products: dict[UUID, SimpleNamespace] = {}
        self.existing_presentations: dict[UUID, SimpleNamespace] = {}
        self.next_code = "P-000001"

    def find_products(self, company_id, global_product_ids):
        found = {**self.existing_products, **self.products.adopted}
        return {gid: found[gid] for gid in global_product_ids if gid in found}

    def find_presentations(self, company_id, global_presentation_ids):
        return {pid: self.existing_presentations[pid] for pid in global_presentation_ids if pid in self.existing_presentations}

    def next_product_code(self, company_id):
        return self.next_code


@pytest.fixture
def catalog() -> FakeProductCatalogBulkDirectory:
    return FakeProductCatalogBulkDirectory(FakeProductCatalog())


@pytest.fixture
def stubs(catalog):
    products, presentations = ProductsStub(), PresentationsStub()
    repository = RepositoryStub(products)
    service = BulkAdoptionService(
        products=products, presentations=presentations, repository=repository, catalog_factory=lambda: catalog
    )
    return SimpleNamespace(service=service, products=products, presentations=presentations, repository=repository)


def _items(*ids: UUID, product=None, presentation=None) -> list[PresentationRequest]:
    return [
        PresentationRequest(
            global_product_presentation_id=item, product_values=dict(product or {}), presentation_values=dict(presentation or {})
        )
        for item in ids
    ]


def _adopt(stubs, items, defaults=None):
    return stubs.service.adopt_presentations(COMPANY, items, defaults or {}, actor=ACTOR)


# ------------------------------------------------------------ valores automáticos (R5 y R6)


def test_automatic_values_use_barcode_of_base_presentation(stubs, catalog):
    product, (base, other) = catalog.add_product(name="Nivea Sun Protect FPS60", presentations=2, barcode="7702001234567")

    result = _adopt(stubs, _items(other))

    values = stubs.products.calls[0]
    assert values == {
        "global_product_id": product,
        "internal_code": "7702001234567",
        "reference_code": None,
        "display_name": "Nivea Sun Protect FPS60",
        "short_name": None,
        "currency_code": "COP",
        "inventory_control_enabled": True,
        "lot_tracking_enabled": False,
        "expiration_tracking_enabled": False,
        "is_purchasable": True,
        "is_sellable": True,
    }
    presentation_values = stubs.presentations.calls[0]
    assert presentation_values == {
        "company_product_id": stubs.products.adopted[product].id,
        "global_product_presentation_id": other,
        "internal_code": None,
        "sku": None,
        "reference_code": None,
        "is_purchasable": True,
        "is_sellable": True,
        "is_default_purchase": False,
        "is_default_sale": False,
    }
    assert [(item.result, item.internal_code) for item in result.products] == [(ADOPTED, "7702001234567")]
    assert [item.result for item in result.presentations] == [ADOPTED]


def test_barcode_of_non_base_presentation_is_not_used(stubs, catalog):
    product, (base, other) = catalog.add_product(presentations=2)
    catalog.identifiers[product] = [
        # Identificador principal de una presentación que no es la base: no cuenta (opción A).
        catalog_identifier("7700000000017", other),
    ]

    _adopt(stubs, _items(base))

    code = stubs.products.calls[0]["internal_code"]
    assert isinstance(code, ConsecutiveCode) and code == "P-000001"


def test_without_barcode_uses_company_consecutive(stubs, catalog):
    _, (presentation,) = catalog.add_product()
    stubs.repository.next_code = "P-000042"

    result = _adopt(stubs, _items(presentation))

    code = stubs.products.calls[0]["internal_code"]
    assert isinstance(code, ConsecutiveCode) and code == "P-000042"
    # El valor definitivo lo asigna el repositorio bajo el bloqueo de la empresa; el resultado trae el guardado.
    assert result.products[0].internal_code == "P-000001"
    # Sin identificadores principales no hace falta consultar las presentaciones del producto.
    assert not [call for call in catalog.calls if call[0] == "products_presentations_list"]


def test_long_canonical_name_is_trimmed_to_display_name_limit(stubs, catalog):
    _, (presentation,) = catalog.add_product(name="N" * 250)
    _adopt(stubs, _items(presentation))
    assert stubs.products.calls[0]["display_name"] == "N" * 200


def test_defaults_apply_to_products_without_own_values(stubs, catalog):
    _, (presentation,) = catalog.add_product()
    _adopt(stubs, _items(presentation), defaults={"currency_code": "USD", "is_sellable": False})
    values = stubs.products.calls[0]
    assert values["currency_code"] == "USD" and values["is_sellable"] is False and values["is_purchasable"] is True


# ------------------------------------------------------------ datos enviados por elemento (FR-012)


def test_sent_values_replace_automatic_ones(stubs, catalog):
    _, (presentation,) = catalog.add_product(barcode="7702001234567")

    _adopt(
        stubs,
        _items(
            presentation,
            product={"internal_code": "007664", "display_name": "Protector solar", "currency_code": "USD"},
            presentation={"sku": "SKU-1", "is_default_sale": True},
        ),
        defaults={"currency_code": "EUR"},
    )

    values = stubs.products.calls[0]
    assert (values["internal_code"], values["display_name"], values["currency_code"]) == ("007664", "Protector solar", "USD")
    presentation_values = stubs.presentations.calls[0]
    assert presentation_values["sku"] == "SKU-1" and presentation_values["is_default_sale"] is True
    # Con el código enviado no se consulta la presentación base.
    assert not [call for call in catalog.calls if call[0] == "products_presentations_list"]


def test_invalid_values_reject_the_whole_request_before_adopting(stubs, catalog):
    _, (presentation,) = catalog.add_product()
    with pytest.raises(CurrencyNotSupportedError):
        _adopt(stubs, _items(presentation, product={"currency_code": "XXX"}))
    assert stubs.products.calls == []


# ------------------------------------------------------------ motivos de rechazo (R9)


@pytest.mark.parametrize(
    "error,reason",
    [
        (GlobalProductInactiveError(field="global_product_id"), "GLOBAL_INACTIVE"),
        (GlobalProductNotEligibleError(field="global_product_id"), "NOT_ELIGIBLE"),
        (DuplicateInternalCodeError(field="internal_code"), "DUPLICATE_INTERNAL_CODE"),
        (DependencyUnavailableError(provider="product-catalog", cause="x", operation="products_first_use"), "DEPENDENCY_UNAVAILABLE"),
    ],
)
def test_product_errors_become_reasons_and_reject_its_presentations(stubs, catalog, error, reason):
    product, (first, second) = catalog.add_product(presentations=2, barcode="7702001234567")
    stubs.products.errors[product] = [error]

    result = _adopt(stubs, _items(first, second))

    assert [(item.result, item.reason) for item in result.products] == [(REJECTED, reason)]
    assert [(item.result, item.reason) for item in result.presentations] == [(REJECTED, "PRODUCT_REJECTED")] * 2
    assert stubs.presentations.calls == []


@pytest.mark.parametrize(
    "error,reason",
    [
        (GlobalPresentationNotEligibleError(field="global_product_presentation_id"), "NOT_ELIGIBLE"),
        (GlobalPresentationOfOtherProductError(field="global_product_presentation_id"), "PRODUCT_MISMATCH"),
        (DuplicateSkuError(field="sku"), "DUPLICATE_SKU"),
        (DuplicateInternalCodeError(field="internal_code"), "DUPLICATE_INTERNAL_CODE"),
        (CompanyProductInactiveError(field="company_product_id"), "COMPANY_PRODUCT_INACTIVE"),
    ],
)
def test_presentation_errors_become_reasons_without_stopping_the_rest(stubs, catalog, error, reason):
    _, (first, second) = catalog.add_product(presentations=2)
    stubs.presentations.errors[first] = error

    result = _adopt(stubs, _items(first, second))

    assert [(item.result, item.reason) for item in result.presentations] == [(REJECTED, reason), (ADOPTED, None)]


def test_consecutive_is_retried_when_taken_by_a_simultaneous_adoption(stubs, catalog):
    product, (presentation,) = catalog.add_product()
    stubs.products.errors[product] = [DuplicateInternalCodeError(field="internal_code")]

    result = _adopt(stubs, _items(presentation))

    assert len(stubs.products.calls) == 2
    assert result.products[0].result == ADOPTED


def test_missing_presentation_is_rejected_as_not_found(stubs, catalog):
    _, (presentation,) = catalog.add_product()
    missing = uuid4()

    result = _adopt(stubs, _items(missing, presentation))

    assert [(item.global_product_presentation_id, item.result, item.reason) for item in result.presentations] == [
        (missing, REJECTED, "GLOBAL_NOT_FOUND"),
        (presentation, ADOPTED, None),
    ]
    assert result.presentations[0].global_product_id is None


def test_product_data_conflict_rejects_the_product_group(stubs, catalog):
    _, (first, second) = catalog.add_product(presentations=2)
    items = [
        PresentationRequest(first, {"internal_code": "A-1"}, {}),
        PresentationRequest(second, {"internal_code": "B-2"}, {}),
    ]

    result = _adopt(stubs, items)

    assert [(item.result, item.reason) for item in result.products] == [(REJECTED, "PRODUCT_DATA_CONFLICT")]
    assert [item.reason for item in result.presentations] == ["PRODUCT_REJECTED", "PRODUCT_REJECTED"]
    assert stubs.products.calls == []


def test_same_values_on_several_items_are_not_a_conflict(stubs, catalog):
    _, (first, second) = catalog.add_product(presentations=2)
    items = [PresentationRequest(first, {"internal_code": "A-1"}, {}), PresentationRequest(second, {}, {})]
    result = _adopt(stubs, items)
    assert result.products[0].result == ADOPTED and stubs.products.calls[0]["internal_code"] == "A-1"


# ------------------------------------------------------------ ya adoptado (idempotencia, R7)


def test_already_adopted_product_and_presentation_report_existing_ids(stubs, catalog):
    product, (first, second) = catalog.add_product(presentations=2)
    existing_product = SimpleNamespace(id=uuid4(), global_product_id=product, internal_code="000045", status="ACTIVE")
    existing_presentation = SimpleNamespace(id=uuid4(), company_product_id=existing_product.id)
    stubs.repository.existing_products[product] = existing_product
    stubs.repository.existing_presentations[first] = existing_presentation

    result = _adopt(stubs, _items(first, second))

    assert [(item.result, item.company_product_id, item.internal_code) for item in result.products] == [
        (ALREADY_ADOPTED, existing_product.id, "000045")
    ]
    assert [(item.result, item.company_product_presentation_id) for item in result.presentations][0] == (
        ALREADY_ADOPTED,
        existing_presentation.id,
    )
    assert result.presentations[1].result == ADOPTED
    assert stubs.products.calls == []
    assert [call["global_product_presentation_id"] for call in stubs.presentations.calls] == [second]


def test_inactive_company_product_rejects_its_presentations(stubs, catalog):
    product, (presentation,) = catalog.add_product()
    stubs.repository.existing_products[product] = SimpleNamespace(
        id=uuid4(), global_product_id=product, internal_code="000045", status="INACTIVE"
    )

    result = _adopt(stubs, _items(presentation))

    assert result.products[0].result == ALREADY_ADOPTED
    assert [(item.result, item.reason) for item in result.presentations] == [(REJECTED, "COMPANY_PRODUCT_INACTIVE")]


def test_simultaneous_product_adoption_is_reported_as_already_adopted(stubs, catalog):
    product, (presentation,) = catalog.add_product(barcode="7702001234567")
    winner = SimpleNamespace(id=uuid4(), global_product_id=product, internal_code="X-9", status="ACTIVE")

    def lose_the_race(*args, **kwargs):
        stubs.repository.existing_products[product] = winner
        raise DuplicateAdoptionError(field="global_product_id")

    stubs.products.adopt = lose_the_race

    result = _adopt(stubs, _items(presentation))

    assert [(item.result, item.company_product_id) for item in result.products] == [(ALREADY_ADOPTED, winner.id)]
    assert result.presentations[0].result == ADOPTED


def test_repeated_ids_are_processed_once(stubs, catalog):
    _, (presentation,) = catalog.add_product()
    result = _adopt(stubs, _items(presentation, presentation))
    assert len(result.presentations) == 1 and len(stubs.presentations.calls) == 1


def catalog_identifier(value: str, presentation_id: UUID):
    from commercial_relationship_service.application.ports import CatalogIdentifier

    return CatalogIdentifier(type="GTIN", value=value, is_primary=True, global_product_presentation_id=presentation_id)
