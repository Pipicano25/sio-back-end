"""Historia 1 de la spec 027: adoptar una lista de presentaciones en una sola solicitud (T012).

`POST /api/v1/companies/{company_id}/bulk-adoptions` con `mode=PRESENTATIONS`, contra la base de pruebas y con
Product Catalog simulado (`FakeProductCatalog` para la adopción individual y `FakeProductCatalogBulkDirectory`
para las lecturas por lotes, sobre el mismo catálogo en memoria).
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import text

from tests.api.helpers import adopt, code_of
from tests.conftest import user_sub

URL = "/api/v1/companies/{company}/bulk-adoptions"


def _post(client, company, ids, **extra):
    items = [{"global_product_presentation_id": str(item)} for item in ids]
    return client.post(URL.format(company=company), json={"mode": "PRESENTATIONS", "items": items, **extra})


def _counts(test_engine, company):
    with test_engine.connect() as connection:
        products = connection.execute(
            text("SELECT count(*) FROM company_products WHERE company_id = :c"), {"c": company}
        ).scalar_one()
        presentations = connection.execute(
            text("SELECT count(*) FROM company_product_presentations WHERE company_id = :c"), {"c": company}
        ).scalar_one()
    return products, presentations


def _results(body, key):
    return [(item["result"], item["reason"]) for item in body[key]]


def _four_products(fake_bulk_catalog):
    """4 productos con 10 presentaciones (4, 3, 2 y 1); el primero con código de barras en su base."""
    groups = [
        fake_bulk_catalog.add_product(name="Acetaminofén 500 mg", presentations=4, barcode="7702001234567"),
        fake_bulk_catalog.add_product(name="Ibuprofeno 400 mg", presentations=3),
        fake_bulk_catalog.add_product(name="Loratadina 10 mg", presentations=2),
        fake_bulk_catalog.add_product(name="Omeprazol 20 mg", presentations=1),
    ]
    return groups, [presentation for _, presentations in groups for presentation in presentations]


def test_adopts_ten_presentations_of_four_new_products(as_user, company, fake_bulk_catalog, fake_catalog, test_engine):
    groups, ids = _four_products(fake_bulk_catalog)

    response = _post(as_user("admin.dao"), company, ids)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["company_id"] == str(company) and body["mode"] == "PRESENTATIONS"
    assert body["totals"] == {
        "products": {"adopted": 4, "already_adopted": 0, "rejected": 0},
        "presentations": {"adopted": 10, "already_adopted": 0, "rejected": 0},
    }
    assert [item["global_product_id"] for item in body["products"]] == [str(product) for product, _ in groups]
    assert [item["internal_code"] for item in body["products"]] == ["7702001234567", "P-000001", "P-000002", "P-000003"]
    assert [item["global_product_presentation_id"] for item in body["presentations"]] == [str(item) for item in ids]
    assert all(item["company_product_presentation_id"] for item in body["presentations"])
    assert _counts(test_engine, company) == (4, 10)
    # Primer uso igual que en la adopción individual: una vez por producto y por presentación.
    assert sorted(fake_catalog.first_use_calls, key=str) == sorted((product for product, _ in groups), key=str)
    assert len(fake_catalog.presentation_first_use_calls) == 10

    # Lo adoptado queda disponible como en la adopción individual, con el autor de la solicitud.
    product = as_user("operario.dao").get(f"/api/v1/company-products/{body['products'][1]['company_product_id']}")
    assert product.status_code == 200
    assert product.json()["display_name"] == "Ibuprofeno 400 mg" and product.json()["currency_code"] == "COP"
    assert product.json()["created_by"] == user_sub("admin.dao")


def test_repeating_the_request_reports_already_adopted_without_duplicates(as_user, company, fake_bulk_catalog, test_engine):
    _, ids = _four_products(fake_bulk_catalog)
    client = as_user("admin.dao")
    assert _post(client, company, ids[:3]).status_code == 200

    response = _post(client, company, ids)

    body = response.json()
    assert response.status_code == 200, response.text
    assert body["totals"]["products"] == {"adopted": 3, "already_adopted": 1, "rejected": 0}
    assert body["totals"]["presentations"] == {"adopted": 7, "already_adopted": 3, "rejected": 0}
    assert _results(body, "presentations")[:3] == [("ALREADY_ADOPTED", None)] * 3
    assert _counts(test_engine, company) == (4, 10)


def test_missing_presentation_and_inactive_product_are_rejected_and_the_rest_adopted(
    as_user, company, fake_bulk_catalog, test_engine
):
    _, (active,) = fake_bulk_catalog.add_product()
    inactive_product, (of_inactive,) = fake_bulk_catalog.add_product(status="INACTIVE")
    missing = uuid4()

    response = _post(as_user("admin.dao"), company, [missing, of_inactive, active])

    body = response.json()
    assert response.status_code == 200, response.text
    assert _results(body, "presentations") == [
        ("REJECTED", "GLOBAL_NOT_FOUND"),
        ("REJECTED", "PRODUCT_REJECTED"),
        ("ADOPTED", None),
    ]
    rejected = next(item for item in body["products"] if item["global_product_id"] == str(inactive_product))
    assert (rejected["result"], rejected["reason"], rejected["company_product_id"]) == ("REJECTED", "GLOBAL_INACTIVE", None)
    assert _counts(test_engine, company) == (1, 1)


def test_more_than_one_hundred_or_empty_list_is_rejected_without_adopting(as_user, company, fake_bulk_catalog, test_engine):
    client = as_user("admin.dao")
    _, ids = fake_bulk_catalog.add_product(presentations=1)

    too_many = _post(client, company, ids + [uuid4() for _ in range(100)])
    empty = _post(client, company, [])

    assert too_many.status_code == 422 and code_of(too_many) == "VALIDATION_ERROR"
    assert "100" in too_many.text
    assert empty.status_code == 422 and code_of(empty) == "VALIDATION_ERROR"
    assert _counts(test_engine, company) == (0, 0)
    assert fake_bulk_catalog.calls == []


def test_repeated_ids_are_processed_once(as_user, company, fake_bulk_catalog, test_engine):
    _, (presentation,) = fake_bulk_catalog.add_product()
    response = _post(as_user("admin.dao"), company, [presentation] * 3)
    assert response.status_code == 200, response.text
    assert len(response.json()["presentations"]) == 1
    assert _counts(test_engine, company) == (1, 1)


def test_sent_product_and_presentation_values_are_used(as_user, company, fake_bulk_catalog):
    _, (presentation,) = fake_bulk_catalog.add_product(barcode="7702001234567")
    body = {
        "mode": "PRESENTATIONS",
        "items": [
            {
                "global_product_presentation_id": str(presentation),
                "product": {"internal_code": "007664", "display_name": "Nivea Sun Protect Solar FPS60"},
                "presentation": {"internal_code": "007664-1", "sku": "SKU-007664", "is_default_sale": True},
            }
        ],
    }
    client = as_user("admin.dao")

    response = client.post(URL.format(company=company), json=body)

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["products"][0]["internal_code"] == "007664"
    product = client.get(f"/api/v1/company-products/{result['products'][0]['company_product_id']}").json()
    assert product["display_name"] == "Nivea Sun Protect Solar FPS60"
    adopted = client.get(
        f"/api/v1/company-product-presentations/{result['presentations'][0]['company_product_presentation_id']}"
    ).json()
    assert (adopted["internal_code"], adopted["sku"], adopted["is_default_sale"]) == ("007664-1", "SKU-007664", True)


def test_barcode_already_used_rejects_the_product_as_duplicate_code(as_user, company, fake_bulk_catalog, fake_catalog, test_engine):
    client = as_user("admin.dao")
    adopt(client, company, fake_catalog, internal_code="7702001234567")
    _, (presentation,) = fake_bulk_catalog.add_product(barcode="7702001234567")

    response = _post(client, company, [presentation])

    body = response.json()
    assert _results(body, "products") == [("REJECTED", "DUPLICATE_INTERNAL_CODE")]
    assert _results(body, "presentations") == [("REJECTED", "PRODUCT_REJECTED")]
    assert _counts(test_engine, company) == (1, 0)

    # Con un código propio, el mismo producto se adopta.
    retry = client.post(
        URL.format(company=company),
        json={
            "mode": "PRESENTATIONS",
            "items": [{"global_product_presentation_id": str(presentation), "product": {"internal_code": "OTRO-1"}}],
        },
    )
    assert _results(retry.json(), "products") == [("ADOPTED", None)]


def test_inactive_company_product_rejects_its_presentations(as_user, company, fake_bulk_catalog):
    client = as_user("admin.dao")
    _, (first, second) = fake_bulk_catalog.add_product(presentations=2)
    adopted = _post(client, company, [first]).json()["products"][0]
    deactivated = client.post(f"/api/v1/company-products/{adopted['company_product_id']}/deactivate", json={})
    assert deactivated.status_code == 200, deactivated.text

    body = _post(client, company, [second]).json()

    assert _results(body, "products") == [("ALREADY_ADOPTED", None)]
    assert _results(body, "presentations") == [("REJECTED", "COMPANY_PRODUCT_INACTIVE")]


def test_catalog_unavailable_for_one_product_does_not_stop_the_rest(
    as_user, company, fake_bulk_catalog, fake_catalog, test_engine
):
    failing, (of_failing,) = fake_bulk_catalog.add_product()
    _, (healthy,) = fake_bulk_catalog.add_product()
    fake_catalog.first_use_unavailable_for.add(failing)

    response = _post(as_user("admin.dao"), company, [of_failing, healthy])

    body = response.json()
    assert response.status_code == 200, response.text
    assert _results(body, "products") == [("REJECTED", "DEPENDENCY_UNAVAILABLE"), ("ADOPTED", None)]
    assert _results(body, "presentations") == [("REJECTED", "PRODUCT_REJECTED"), ("ADOPTED", None)]
    assert _counts(test_engine, company) == (1, 1)


def test_catalog_unavailable_before_adopting_answers_503_without_changes(as_user, company, fake_bulk_catalog, test_engine):
    _, (presentation,) = fake_bulk_catalog.add_product()
    fake_bulk_catalog.unavailable = True

    response = _post(as_user("admin.dao"), company, [presentation])

    assert response.status_code == 503 and code_of(response) == "DEPENDENCY_UNAVAILABLE"
    assert _counts(test_engine, company) == (0, 0)


def test_audit_has_one_event_per_adoption_with_the_requesting_user(as_user, company, fake_bulk_catalog, outbox):
    _, ids = _four_products(fake_bulk_catalog)

    assert _post(as_user("admin.dao"), company, ids).status_code == 200

    events = outbox()
    assert len(events) == 14
    actions = [event["action"] for event in events]
    assert actions.count("ADOPT_COMPANY_PRODUCT") == 4
    assert actions.count("CREATE_COMPANY_PRODUCT_PRESENTATION") == 10
    assert {event["username_snapshot"] for event in events} == {"admin.dao"}
    assert {event["company_id"] for event in events} == {str(company)}


# ------------------------------------------------------------ validación de la solicitud


def test_products_mode_is_not_available_yet(as_user, company, fake_bulk_catalog):
    product, _ = fake_bulk_catalog.add_product()
    response = as_user("admin.dao").post(
        URL.format(company=company), json={"mode": "PRODUCTS", "items": [{"global_product_id": str(product)}]}
    )
    assert response.status_code == 422 and code_of(response) == "VALIDATION_ERROR"
    assert "PRODUCTS" in response.text
    assert fake_bulk_catalog.calls == []


def test_ids_that_do_not_match_the_mode_are_rejected(as_user, company):
    response = as_user("admin.dao").post(
        URL.format(company=company), json={"mode": "PRESENTATIONS", "items": [{"global_product_id": str(uuid4())}]}
    )
    assert response.status_code == 422 and code_of(response) == "VALIDATION_ERROR"


def test_invalid_currency_rejects_the_whole_request(as_user, company, fake_bulk_catalog, test_engine):
    _, (presentation,) = fake_bulk_catalog.add_product()
    response = _post(as_user("admin.dao"), company, [presentation], defaults={"currency_code": "XXX"})
    assert response.status_code == 422 and code_of(response) == "CURRENCY_NOT_SUPPORTED"
    assert _counts(test_engine, company) == (0, 0)


# ------------------------------------------------------------ permisos y membresía (como company_products.py)


def test_requires_both_create_permissions(as_user, as_token, make_token, company, fake_oc, fake_bulk_catalog, test_engine):
    _, (presentation,) = fake_bulk_catalog.add_product()
    body_ids = [presentation]

    assert _post(as_user("operario.dao"), company, body_ids).status_code == 403

    for permission in (
        "perm:commercial-relationship:company_products:create",
        "perm:commercial-relationship:company_product_presentations:create",
    ):
        fake_oc.add_member("sub-solo-uno", company)
        client = as_token(make_token(permission, sub="sub-solo-uno"))
        response = _post(client, company, body_ids)
        assert response.status_code == 403, permission
        assert "company_product" not in response.json().get("detail", "")

    assert _counts(test_engine, company) == (0, 0)
    assert as_token(None).post(URL.format(company=company), json={}).status_code == 401


def test_non_member_receives_404(as_user, other_company, fake_bulk_catalog, test_engine):
    _, (presentation,) = fake_bulk_catalog.add_product()
    response = _post(as_user("admin.dao"), other_company, [presentation])
    assert response.status_code == 404 and code_of(response) == "NOT_FOUND"
    assert fake_bulk_catalog.calls == []


def test_inactive_company_is_rejected_as_in_individual_adoption(as_user, company, fake_oc, fake_bulk_catalog):
    _, (presentation,) = fake_bulk_catalog.add_product()
    fake_oc.inactive_companies.add(company)
    response = _post(as_user("admin.dao"), company, [presentation])
    # Mismo error que la adopción individual (`422 COMPANY_INACTIVE`, test_company_products_create.py).
    assert response.status_code == 422 and code_of(response) == "COMPANY_INACTIVE"
