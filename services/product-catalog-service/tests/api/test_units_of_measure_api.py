"""Historia 1: unidades de medida (RC-01, RC-09, RC-10, RC-11, FR-009, FR-013 a FR-015)."""

URL = "/api/v1/units-of-measure"

KG = {
    "code": "KG",
    "name": "Kilogramo",
    "symbol": "kg",
    "measurement_type": "MASS",
    "allows_decimals": True,
}


def _create(api, **overrides):
    response = api.post(URL, json={**KG, **overrides})
    assert response.status_code == 201, response.text
    return response.json()


def test_create_unit(api) -> None:
    response = api.post(URL, json=KG)

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "KG"
    assert body["status"] == "ACTIVE"
    assert body["version"] == 1
    assert body["created_by"] == "user-admin"
    assert body["updated_by"] == "user-admin"
    assert response.headers["location"].endswith(body["id"])


def test_audit_fields_cannot_be_sent(api) -> None:
    response = api.post(URL, json={**KG, "created_by": "otro"})
    assert response.status_code == 422


def test_duplicate_code_is_case_insensitive(api) -> None:
    _create(api)
    response = api.post(URL, json={**KG, "code": " kg "})

    assert response.status_code == 409
    assert response.json()["code"] == "PRODUCT_CATALOG.DUPLICATE_CODE"


def test_invalid_measurement_type(api) -> None:
    assert api.post(URL, json={**KG, "measurement_type": "TIME"}).status_code == 422


def test_update_name_and_symbol(api, api_as) -> None:
    unit = _create(api)
    editor = api_as("units-of-measure:update", sub="editor")

    response = editor.put(
        f"{URL}/{unit['id']}",
        json={"name": "Kilo gramo", "symbol": "KG", "version": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Kilo gramo"
    assert body["version"] == 2
    assert body["created_by"] == "user-admin"
    assert body["updated_by"] == "editor"


def test_immutable_fields_rejected(api) -> None:
    unit = _create(api)

    for field, value in (("measurement_type", "UNIT"), ("allows_decimals", False), ("code", "KGS")):
        response = api.put(
            f"{URL}/{unit['id']}",
            json={"name": "Kilogramo", "symbol": "kg", "version": 1, field: value},
        )
        assert response.status_code == 422
        assert response.json()["code"] == "PRODUCT_CATALOG.IMMUTABLE_FIELD"


def test_stale_version_conflict(api) -> None:
    unit = _create(api)
    url = f"{URL}/{unit['id']}"
    assert api.put(url, json={"name": "A", "symbol": "kg", "version": 1}).status_code == 200

    response = api.put(url, json={"name": "B", "symbol": "kg", "version": 1})

    assert response.status_code == 409
    assert response.json()["code"] == "PRODUCT_CATALOG.VERSION_CONFLICT"


def test_deactivate_and_reactivate(api, api_as) -> None:
    unit = _create(api)
    url = f"{URL}/{unit['id']}"

    only_update = api_as("units-of-measure:update")
    assert only_update.post(f"{url}/deactivate", json={"version": 1}).status_code == 403

    deactivated = api.post(f"{url}/deactivate", json={"version": 1})
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "INACTIVE"
    assert deactivated.json()["version"] == 2

    reactivated = api.post(f"{url}/reactivate", json={"version": 2})
    assert reactivated.json()["status"] == "ACTIVE"


def test_list_filters(api) -> None:
    _create(api)
    _create(api, code="UND", name="Unidad", symbol="und", measurement_type="UNIT", allows_decimals=False)
    gram = _create(api, code="G", name="Gramo", symbol="g")
    api.post(f"{URL}/{gram['id']}/deactivate", json={"version": 1})

    def codes(query: str) -> list[str]:
        response = api.get(f"{URL}?{query}")
        assert response.status_code == 200
        return [item["code"] for item in response.json()["items"]]

    assert codes("") == ["G", "KG", "UND"]
    assert codes("status=ACTIVE") == ["KG", "UND"]
    assert codes("code=kg") == ["KG"]
    assert codes("search=GRAM") == ["G", "KG"]
    assert codes("measurement_type=UNIT") == ["UND"]

    page = api.get(f"{URL}?page=1&page_size=2").json()
    assert page["total_records"] == 3
    assert page["total_pages"] == 2
    assert len(page["items"]) == 2


def test_create_requires_permission(api_as) -> None:
    response = api_as("units-of-measure:read").post(URL, json=KG)
    assert response.status_code == 403
