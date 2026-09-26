"""Servicio de producto con `ManufacturerDirectory` falso (RC-09, RC-13, FR-026 a FR-028, FR-006)."""

from uuid import uuid4

import pytest

from product_catalog_service.application.exceptions import (
    BaseUnitLockedByFirstUseError,
    DependencyUnavailableError,
    ManufacturerAccessDeniedError,
    ManufacturerNotFoundError,
    ReferenceInactiveError,
)
from product_catalog_service.application.product_service import ProductService
from product_catalog_service.infrastructure.models import GlobalProductModel
from tests import factories


_OPEN_SESSIONS: list = []


@pytest.fixture(autouse=True)
def _close_sessions(session_factory):
    yield
    while _OPEN_SESSIONS:
        _OPEN_SESSIONS.pop().close()


def _service(session_factory, directory):
    session = session_factory()
    _OPEN_SESSIONS.append(session)
    return ProductService(session, directory)


def _create(session_factory, directory, **overrides):
    unit = overrides.pop("unit", None) or factories.unit(session_factory, "UND")
    data = {
        "product_type": "GOOD",
        "canonical_name": "Arroz blanco",
        "description": None,
        "global_brand_id": None,
        "manufacturer_organization_id": None,
        "base_unit_id": unit.id,
        "actor": "tester",
        **overrides,
    }
    return _service(session_factory, directory).create(**data).product


def _update_kwargs(product: GlobalProductModel, **changes):
    return {
        "version": product.version,
        "canonical_name": product.canonical_name,
        "description": product.description,
        "global_brand_id": product.global_brand_id,
        "manufacturer_organization_id": product.manufacturer_organization_id,
        "base_unit_id": product.base_unit_id,
        "actor": "tester",
        **changes,
    }


def test_unknown_manufacturer_rejected(session_factory, fake_manufacturer_directory) -> None:
    with pytest.raises(ManufacturerNotFoundError):
        _create(session_factory, fake_manufacturer_directory, manufacturer_organization_id=uuid4())


def test_unavailable_directory_rejects_without_persisting(session_factory, fake_manufacturer_directory) -> None:
    fake_manufacturer_directory.mode = "unavailable"
    with pytest.raises(DependencyUnavailableError):
        _create(session_factory, fake_manufacturer_directory, manufacturer_organization_id=uuid4())

    with session_factory() as session:
        assert session.query(GlobalProductModel).count() == 0


def test_access_denied_is_distinct(session_factory, fake_manufacturer_directory) -> None:
    fake_manufacturer_directory.mode = "denied"
    with pytest.raises(ManufacturerAccessDeniedError):
        _create(session_factory, fake_manufacturer_directory, manufacturer_organization_id=uuid4())


def test_unchanged_same_or_removed_manufacturer_is_not_revalidated(
    session_factory, fake_manufacturer_directory
) -> None:
    manufacturer = uuid4()
    fake_manufacturer_directory.existing.add(manufacturer)
    product = _create(session_factory, fake_manufacturer_directory, manufacturer_organization_id=manufacturer)
    assert fake_manufacturer_directory.calls == [manufacturer]

    fake_manufacturer_directory.mode = "unavailable"
    service = _service(session_factory, fake_manufacturer_directory)
    product = service.update(product.id, **_update_kwargs(product, description="Nueva")).product
    product = service.update(product.id, **_update_kwargs(product, manufacturer_organization_id=manufacturer)).product
    product = service.update(product.id, **_update_kwargs(product, manufacturer_organization_id=None)).product

    assert product.manufacturer_organization_id is None
    assert fake_manufacturer_directory.calls == [manufacturer]


def test_base_unit_change_allowed_without_first_use(session_factory, fake_manufacturer_directory) -> None:
    product = _create(session_factory, fake_manufacturer_directory)
    other = factories.unit(session_factory, "KG")

    updated = _service(session_factory, fake_manufacturer_directory).update(
        product.id, **_update_kwargs(product, base_unit_id=other.id)
    ).product

    assert updated.base_unit_id == other.id


def test_base_unit_change_rejected_with_first_use(session_factory, fake_manufacturer_directory) -> None:
    unit = factories.unit(session_factory, "UND")
    other = factories.unit(session_factory, "KG")
    product = factories.product(session_factory, unit.id, first_used=True)

    with pytest.raises(BaseUnitLockedByFirstUseError):
        _service(session_factory, fake_manufacturer_directory).update(
            product.id, **_update_kwargs(product, base_unit_id=other.id)
        )


def test_inactive_brand_or_unit_rejected(session_factory, fake_manufacturer_directory) -> None:
    inactive_brand = factories.brand(session_factory, "OLD", status="INACTIVE")
    inactive_unit = factories.unit(session_factory, "LB", status="INACTIVE")

    with pytest.raises(ReferenceInactiveError):
        _create(session_factory, fake_manufacturer_directory, global_brand_id=inactive_brand.id)
    with pytest.raises(ReferenceInactiveError):
        _create(session_factory, fake_manufacturer_directory, unit=inactive_unit)


def test_reactivate_with_inactive_brand_and_unit_is_allowed(session_factory, fake_manufacturer_directory) -> None:
    unit = factories.unit(session_factory, "UND", status="INACTIVE")
    brand = factories.brand(session_factory, "OLD", status="INACTIVE")
    product = factories.product(session_factory, unit.id, brand_id=brand.id, status="INACTIVE")

    reactivated = _service(session_factory, fake_manufacturer_directory).reactivate(
        product.id, version=product.version, actor="tester"
    )

    assert reactivated.status == "ACTIVE"
