"""Registro del primer uso (RC-17, FR-076 a FR-079, FR-028)."""

from tests import factories


def _url(product_id, manual: bool = False) -> str:
    return f"/api/v1/products/{product_id}/first-use" + ("/manual" if manual else "")


def test_adoption_marks_presentation_and_product(api_as, session_factory) -> None:
    consumer = api_as("first-use:register", sub="service-account-commercial")
    product, _, _ = factories.complete_product(session_factory)
    box = factories.presentation(session_factory, product.id, "CAJA", base_quantity=20)

    response = consumer.post(_url(product.id), json={"global_product_presentation_id": str(box.id)})

    assert response.status_code == 200
    body = response.json()
    assert body["product_first_use_source"] == "ADOPTION"
    assert body["presentation_first_use_source"] == "ADOPTION"
    assert set(body) == {
        "global_product_id",
        "product_first_used_at",
        "product_first_use_source",
        "global_product_presentation_id",
        "presentation_first_used_at",
        "presentation_first_use_source",
    }

    with session_factory() as session:
        from product_catalog_service.infrastructure.models import GlobalProductModel

        stored = session.get(GlobalProductModel, product.id)
        assert stored.first_used_by == "service-account-commercial"


def test_repeated_registration_is_idempotent(api_as, session_factory) -> None:
    consumer = api_as("first-use:register")
    product, _, _ = factories.complete_product(session_factory)

    first = consumer.post(_url(product.id)).json()
    second = consumer.post(_url(product.id))

    assert second.status_code == 200
    assert second.json()["product_first_used_at"] == first["product_first_used_at"]


def test_presentation_of_other_product_rejected(api, session_factory) -> None:
    product, _, _ = factories.complete_product(session_factory, "Uno")
    other, _, _ = factories.complete_product(session_factory, "Otro")
    foreign = factories.presentation(session_factory, other.id, "CAJA")

    response = api.post(_url(product.id), json={"global_product_presentation_id": str(foreign.id)})

    assert response.status_code == 422
    assert response.json()["code"] == "PRODUCT_CATALOG.PRESENTATION_OF_OTHER_PRODUCT"


def test_not_eligible_without_mark_is_rejected(api, session_factory) -> None:
    unit = factories.unit(session_factory)
    incomplete = factories.product(session_factory, unit.id, "Incompleto")
    inactive, _, _ = factories.complete_product(session_factory, "Inactivo", status="INACTIVE")

    for product in (incomplete, inactive):
        response = api.post(_url(product.id))
        assert response.status_code == 422
        assert response.json()["code"] == "PRODUCT_CATALOG.NOT_ELIGIBLE_FOR_FIRST_USE"
        assert api.get(f"/api/v1/products/{product.id}").json()["first_used_at"] is None


def test_already_marked_but_now_ineligible_returns_success(api, session_factory) -> None:
    unit = factories.unit(session_factory)
    product = factories.product(session_factory, unit.id, "Marcado", first_used=True)

    response = api.post(_url(product.id))

    assert response.status_code == 200
    assert response.json()["product_first_use_source"] == "MANUAL"


def test_manual_registration_skips_eligibility(api_as, session_factory) -> None:
    admin = api_as("first-use:register-manual", sub="catalog-admin")
    unit = factories.unit(session_factory)
    product = factories.product(session_factory, unit.id, "Migrado")

    response = admin.post(_url(product.id, manual=True))

    assert response.status_code == 200
    assert response.json()["product_first_use_source"] == "MANUAL"


def test_permissions_are_separate(api_as, session_factory) -> None:
    product, _, _ = factories.complete_product(session_factory)

    assert api_as("first-use:register").post(_url(product.id, manual=True)).status_code == 403
    assert api_as("first-use:register-manual").post(_url(product.id)).status_code == 403
    assert api_as("products:update").post(_url(product.id)).status_code == 403


def test_mark_locks_base_unit_and_cannot_be_removed(api, session_factory) -> None:
    product, _, _ = factories.complete_product(session_factory)
    other = factories.unit(session_factory, "KG")
    api.post(_url(product.id))
    current = api.get(f"/api/v1/products/{product.id}").json()
    body = {
        "canonical_name": current["canonical_name"],
        "base_unit_id": str(other.id),
        "version": current["version"],
    }

    locked = api.put(f"/api/v1/products/{product.id}", json=body)
    assert locked.json()["code"] == "PRODUCT_CATALOG.BASE_UNIT_LOCKED_BY_FIRST_USE"

    cleared = api.put(
        f"/api/v1/products/{product.id}",
        json={**body, "base_unit_id": current["base_unit_id"], "first_used_at": None},
    )
    assert cleared.json()["code"] == "PRODUCT_CATALOG.IMMUTABLE_FIELD"
    assert api.delete(_url(product.id)).status_code in {404, 405}
