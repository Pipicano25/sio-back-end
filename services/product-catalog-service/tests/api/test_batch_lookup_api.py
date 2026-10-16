"""Consultas por lotes para servicios consumidores (FR-008, FR-070, RC-16)."""

from uuid import uuid4

from tests import factories


def test_product_batch_lookup(api_as, session_factory) -> None:
    client = api_as("products:read", sub="service-commercial")
    complete, _, _ = factories.complete_product(session_factory)
    incomplete = factories.product(session_factory, factories.unit(session_factory, "KG").id, "Incompleto")
    inactive = factories.product(session_factory, factories.unit(session_factory, "LB").id, "Viejo", status="INACTIVE")
    missing = uuid4()
    ids = [str(complete.id), str(incomplete.id), str(inactive.id), str(missing), str(complete.id)]
    ids += [str(uuid4()) for _ in range(45)]

    response = client.post("/api/v1/products/batch-lookup", json={"ids": ids})

    assert response.status_code == 200
    items = {item["id"]: item for item in response.json()["items"]}
    assert len(response.json()["items"]) == 49
    assert items[str(complete.id)]["eligible_for_adoption"] is True
    assert items[str(incomplete.id)]["is_complete"] is False
    assert items[str(incomplete.id)]["eligible_for_adoption"] is False
    assert items[str(inactive.id)]["status"] == "INACTIVE"
    assert items[str(missing)] == {
        "id": str(missing),
        "found": False,
        "status": None,
        "is_complete": None,
        "eligible_for_adoption": None,
        "first_used_at": None,
    }


def test_batch_limit(api) -> None:
    too_many = [str(uuid4()) for _ in range(101)]
    exactly = too_many[:100]

    over = api.post("/api/v1/products/batch-lookup", json={"ids": too_many})
    assert over.status_code == 422
    assert over.json()["code"] == "PRODUCT_CATALOG.BATCH_LIMIT_EXCEEDED"
    assert api.post("/api/v1/products/batch-lookup", json={"ids": exactly}).status_code == 200


def test_presentation_batch_lookup(api, session_factory) -> None:
    product, _, _ = factories.complete_product(session_factory)
    active = factories.presentation(session_factory, product.id, "CAJA", base_quantity=20)
    inactive = factories.presentation(session_factory, product.id, "VIEJA", status="INACTIVE")

    response = api.post(
        "/api/v1/presentations/batch-lookup",
        json={"ids": [str(active.id), str(inactive.id), str(uuid4())]},
    )

    items = response.json()["items"]
    assert items[0]["eligible_for_adoption"] is True
    assert items[0]["global_product_id"] == str(product.id)
    assert items[0]["base_quantity"] == "20.00000000"
    # spec 021 (H-2): código y nombre para que Purchase no consulte una por una
    assert (items[0]["code"], items[0]["name"]) == (active.code, active.name)
    assert (items[2]["code"], items[2]["name"]) == (None, None)
    assert items[1]["eligible_for_adoption"] is False
    assert items[2]["found"] is False


def test_unit_batch_lookup(api, session_factory) -> None:
    unit = factories.unit(session_factory, "KG", allows_decimals=True)

    items = api.post("/api/v1/units-of-measure/batch-lookup", json={"ids": [str(unit.id)]}).json()["items"]

    assert items == [
        {"id": str(unit.id), "found": True, "status": "ACTIVE", "measurement_type": "UNIT", "allows_decimals": True}
    ]


def test_empty_batch_rejected(api) -> None:
    assert api.post("/api/v1/products/batch-lookup", json={"ids": []}).status_code == 422
