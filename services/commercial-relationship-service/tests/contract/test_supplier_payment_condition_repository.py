"""Repositorio de condiciones de pago contra la base de pruebas (T044; FR-035, FR-038)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text

from commercial_relationship_service.infrastructure.repositories import (
    SupplierPaymentConditionRepository,
)

AUDIT = {"created_by": "sub", "updated_by": "sub"}


def test_applicable_at_default_scope_and_order(db_session):
    company, supplier = uuid4(), uuid4()
    db_session.execute(
        text(
            "INSERT INTO company_suppliers (id, company_id, organization_identity_id, internal_code, display_name, "
            "created_by, updated_by) VALUES (:id, :company, :org, 'S-1', 'S', 's', 's')"
        ),
        {"id": supplier, "company": company, "org": uuid4()},
    )
    db_session.commit()
    repository = SupplierPaymentConditionRepository(db_session)
    common = {"company_id": company, "company_supplier_id": supplier, "payment_condition_type_id": uuid4(), **AUDIT}

    old = repository.add(repository.build(currency_code="COP", valid_from=datetime(2025, 1, 1, tzinfo=UTC),
                                          valid_to=datetime(2026, 1, 1, tzinfo=UTC), **common), duplicates={})
    current = repository.add(repository.build(currency_code="COP", is_default=True,
                                              valid_from=datetime(2026, 1, 1, tzinfo=UTC), **common), duplicates={})

    page = repository.list_page(
        company, status=None, search=None, filters={}, page=1, page_size=20,
        conditions=repository.applicable_at(datetime(2026, 6, 1, tzinfo=UTC)),
    )
    assert [row.id for row in page.items] == [current.id]
    assert [row.id for row in repository.list_page(company, status=None, search=None, filters={}, page=1, page_size=20).items] == [old.id, current.id]

    repository.lock_supplier(supplier)
    repository.clear_default(supplier, "COP", exclude_id=None, actor="sub-2")
    repository.session.commit()
    assert repository.get(current.id).is_default is False
