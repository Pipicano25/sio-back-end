"""Repositorios de listas y precios contra la base de pruebas (T054; FR-042, FR-057; R-04, R-06)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text

from commercial_relationship_service.infrastructure.repositories import (
    PriceListItemRepository,
    PriceListRepository,
)

AUDIT = {"created_by": "sub", "updated_by": "sub"}


def test_price_list_search_code_and_default_scope(db_session):
    company = uuid4()
    lists = PriceListRepository(db_session)
    marked = lists.add(lists.build(company_id=company, code="MINORISTA", name="Minorista", currency_code="COP",
                                   is_default=True, **AUDIT), duplicates=lists.duplicates)
    lists.add(lists.build(company_id=company, code="EXPORT", name="Exportación", currency_code="USD", **AUDIT),
              duplicates=lists.duplicates)

    page = lists.list_page(company, status=None, search="minor", filters={}, page=1, page_size=20)
    assert [row.id for row in page.items] == [marked.id]
    assert lists.list_code_taken(company, "minorista")
    assert not lists.list_code_taken(company, "minorista", exclude_id=marked.id)

    lists.lock_default_scope(company, "COP")
    lists.clear_default(company, "COP", exclude_id=None, actor="sub-2")
    lists.session.commit()
    assert lists.get(marked.id).is_default is False


def test_price_items_applicable_at_and_database_now(db_session):
    company, product = uuid4(), uuid4()
    db_session.execute(
        text(
            "INSERT INTO company_products (id, company_id, global_product_id, internal_code, display_name, "
            "currency_code, created_by, updated_by) VALUES (:id, :company, :global, 'P-1', 'P', 'COP', 's', 's')"
        ),
        {"id": product, "company": company, "global": uuid4()},
    )
    db_session.commit()
    lists, items = PriceListRepository(db_session), PriceListItemRepository(db_session)
    price_list = lists.add(lists.build(company_id=company, code="L", name="L", currency_code="COP", **AUDIT), duplicates={})
    common = {"company_id": company, "price_list_id": price_list.id, "company_product_id": product, **AUDIT}
    old = items.add(items.build(unit_price=1, valid_from=datetime(2025, 1, 1, tzinfo=UTC),
                                valid_to=datetime(2026, 1, 1, tzinfo=UTC), **common), duplicates=items.duplicates)
    new = items.add(items.build(unit_price=2, valid_from=datetime(2026, 1, 1, tzinfo=UTC), **common), duplicates=items.duplicates)

    def applicable(at):
        page = items.list_page(company, status=None, search=None, filters={}, page=1, page_size=20,
                               conditions=items.applicable_at(at))
        return [row.id for row in page.items]

    assert applicable(datetime(2025, 6, 1, tzinfo=UTC)) == [old.id]
    assert applicable(datetime(2026, 1, 1, tzinfo=UTC)) == [new.id]  # [) en el límite
    now = items.database_now()
    items.release()
    assert now.tzinfo is not None
