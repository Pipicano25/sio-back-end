"""Repositorio de presentaciones empresariales contra la base de pruebas (T026; FR-016, R-04)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

from commercial_relationship_service.infrastructure.repositories import (
    CompanyProductPresentationRepository,
)

AUDIT = {"created_by": "sub", "updated_by": "sub"}


@pytest.fixture
def repository(db_session):
    return CompanyProductPresentationRepository(db_session)


@pytest.fixture
def product(db_session):
    company, product_id = uuid4(), uuid4()
    db_session.execute(
        text(
            "INSERT INTO company_products (id, company_id, global_product_id, internal_code, display_name, "
            "currency_code, created_by, updated_by) VALUES (:id, :company, :global, 'P-1', 'Producto', 'COP', 's', 's')"
        ),
        {"id": product_id, "company": company, "global": uuid4()},
    )
    db_session.commit()
    return company, product_id


def _add(repository, company, product_id, **fields):
    return repository.add(
        repository.build(company_id=company, company_product_id=product_id,
                         global_product_presentation_id=uuid4(), **AUDIT, **fields),
        duplicates=repository.duplicates,
    )


def test_create_search_filters_and_pagination(repository, product):
    company, product_id = product
    first = _add(repository, company, product_id, sku="CAJA-12", reference_code="REF-A")
    _add(repository, company, product_id, internal_code="UND-1", is_sellable=False)
    third = _add(repository, company, product_id, sku="BLISTER")
    repository.load_for_update(third.id, expected_version=1).status = "INACTIVE"
    repository.save(third, duplicates={})

    def page(**kwargs):
        defaults = {"status": None, "search": None, "filters": {}, "page": 1, "page_size": 20}
        return repository.list_page(company, **{**defaults, **kwargs})

    assert page().total_records == 2
    assert page(status="ALL").total_records == 3
    assert [row.id for row in page(search="caja").items] == [first.id]
    assert page(search="ref-a").items[0].id == first.id
    assert page(search="und").total_records == 1
    assert page(filters={"is_sellable": False}).total_records == 1
    assert page(status="ALL", page_size=2, page=2).items != []
    assert repository.adoption_exists(product_id, first.global_product_presentation_id)
    assert repository.code_in_use(company, "sku", "caja-12")
    assert not repository.code_in_use(company, "sku", "caja-12", exclude_id=first.id)
    assert not repository.code_in_use(company, "sku", None)


def test_clear_marks_increments_version_and_audits(repository, product):
    company, product_id = product
    marked = _add(repository, company, product_id, is_default_purchase=True)

    repository.lock_product(product_id)
    repository.clear_product_marks("is_default_purchase", product_id, exclude_id=None, actor="sub-new")
    repository.session.commit()

    cleared = repository.get(marked.id)
    assert cleared.is_default_purchase is False
    assert cleared.version == 2
    assert cleared.updated_by == "sub-new"
