"""Repositorio de la adopción masiva (spec 027, T011): adopciones existentes y consecutivo `P-NNNNNN`."""

from __future__ import annotations

import threading
from uuid import uuid4

from commercial_relationship_service.application.bulk_adoption_service import ConsecutiveCode
from commercial_relationship_service.infrastructure.bulk_adoption_repository import (
    LOCK_KEY,
    BulkAdoptionRepository,
    SequencedCompanyProductRepository,
    _next_code,
)
from commercial_relationship_service.infrastructure.models import CompanyProductPresentationModel
from commercial_relationship_service.infrastructure.repositories import CompanyProductRepository


def _fields(company_id, code, product_id=None):
    return {
        "company_id": company_id,
        "global_product_id": product_id or uuid4(),
        "internal_code": code,
        "display_name": "Producto",
        "currency_code": "COP",
        "created_by": "sub",
        "updated_by": "sub",
    }


def test_next_code_is_highest_consecutive_plus_one_per_company(db_session):
    products = CompanyProductRepository(db_session)
    company, other = uuid4(), uuid4()
    for code in ("P-000001", "p-000007", "7702001234567", "P-12", "PX-000099"):
        products.create(**_fields(company, code))
    products.create(**_fields(other, "P-000500"))

    repository = BulkAdoptionRepository(db_session)

    assert repository.next_product_code(company) == "P-000008"
    assert repository.next_product_code(uuid4()) == "P-000001"
    assert not db_session.in_transaction()


def test_find_existing_products_and_presentations(db_session):
    company = uuid4()
    product = CompanyProductRepository(db_session).create(**_fields(company, "000045"))
    global_presentation = uuid4()
    db_session.add(
        CompanyProductPresentationModel(
            company_id=company,
            company_product_id=product.id,
            global_product_presentation_id=global_presentation,
            created_by="sub",
            updated_by="sub",
        )
    )
    db_session.commit()

    repository = BulkAdoptionRepository(db_session)

    assert repository.find_products(company, [product.global_product_id, uuid4()]) == {product.global_product_id: product}
    assert list(repository.find_products(uuid4(), [product.global_product_id])) == []
    assert list(repository.find_presentations(company, [global_presentation, uuid4()])) == [global_presentation]
    assert repository.find_products(company, []) == {} and repository.find_presentations(company, []) == {}


def test_consecutive_is_assigned_under_the_company_lock(session_factory):
    """Mientras otra transacción tiene el bloqueo de la empresa, el alta espera y toma el número siguiente."""
    company = uuid4()
    holder = session_factory()
    created: dict[str, str] = {}

    holder_repository = CompanyProductRepository(holder)
    holder_repository.lock_advisory(LOCK_KEY.format(company_id=company))
    first_code = _next_code(holder, company)

    def adopt_in_parallel() -> None:
        with session_factory() as session:
            model = SequencedCompanyProductRepository(session).create(**_fields(company, ConsecutiveCode("P-000001")))
            created["code"] = model.internal_code

    worker = threading.Thread(target=adopt_in_parallel)
    worker.start()
    worker.join(timeout=1)
    assert worker.is_alive(), "el alta debió esperar el bloqueo de la empresa"

    holder_repository.create(**_fields(company, first_code))  # confirma y libera el bloqueo
    worker.join(timeout=10)
    holder.close()

    assert (first_code, created["code"]) == ("P-000001", "P-000002")
