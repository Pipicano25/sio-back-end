"""Repositorio de productos de proveedor contra la base de pruebas (T035; FR-023, FR-024, FR-028)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

from commercial_relationship_service.infrastructure.repositories import SupplierProductRepository

AUDIT = {"created_by": "sub", "updated_by": "sub"}


@pytest.fixture
def world(db_session):
    company, product, supplier = uuid4(), uuid4(), uuid4()
    db_session.execute(
        text(
            "INSERT INTO company_products (id, company_id, global_product_id, internal_code, display_name, "
            "currency_code, created_by, updated_by) VALUES (:id, :company, :global, 'P-1', 'P', 'COP', 's', 's')"
        ),
        {"id": product, "company": company, "global": uuid4()},
    )
    db_session.execute(
        text(
            "INSERT INTO company_suppliers (id, company_id, organization_identity_id, internal_code, display_name, "
            "created_by, updated_by) VALUES (:id, :company, :org, 'S-1', 'S', 's', 's')"
        ),
        {"id": supplier, "company": company, "org": uuid4()},
    )
    db_session.commit()
    return company, product, supplier, SupplierProductRepository(db_session)


def test_search_filters_relation_and_preferred(world):
    company, product, supplier, repository = world
    common = {"company_id": company, "company_supplier_id": supplier, "company_product_id": product,
              "purchase_unit_id": uuid4(), "currency_code": "COP", **AUDIT}
    row = repository.add(repository.build(supplier_product_code="ABC-77", is_preferred=True, **common), duplicates=repository.duplicates)

    def page(**kwargs):
        defaults = {"status": None, "search": None, "filters": {}, "page": 1, "page_size": 20}
        return repository.list_page(company, **{**defaults, **kwargs})

    assert page(search="abc").items[0].id == row.id
    assert page(filters={"is_preferred": True}).total_records == 1
    assert repository.active_relation_exists(
        company_supplier_id=supplier, company_product_id=product, company_product_presentation_id=None
    )
    assert not repository.active_relation_exists(
        company_supplier_id=supplier, company_product_id=product, company_product_presentation_id=None, exclude_id=row.id
    )

    repository.lock_product(product)
    repository.clear_preferred(product, exclude_id=None, actor="sub-2")
    repository.session.commit()
    cleared = repository.get(row.id)
    assert (cleared.is_preferred, cleared.version, cleared.updated_by) == (False, 2, "sub-2")
