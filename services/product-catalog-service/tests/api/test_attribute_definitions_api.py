"""Historia 5: definiciones y opciones (RC-09, FR-009, FR-038 a FR-040)."""

from tests import factories

URL = "/api/v1/attribute-definitions"


def _create(api, code: str, data_type: str, **extra) -> dict:
    response = api.post(
        URL,
        json={"code": code, "name": code.title(), "description": f"Atributo {code}", "data_type": data_type, **extra},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_option_definition_with_options(api) -> None:
    color = _create(api, "COLOR", "OPTION")

    red = api.post(f"{URL}/{color['id']}/options", json={"code": "red", "name": "Rojo", "display_order": 2})
    blue = api.post(f"{URL}/{color['id']}/options", json={"code": "BLUE", "name": "Azul", "display_order": 1})

    assert red.status_code == 201
    assert red.json()["code"] == "RED"
    options = api.get(f"{URL}/{color['id']}/options").json()
    assert [item["code"] for item in options] == ["BLUE", "RED"]
    assert blue.json()["attribute_definition_id"] == color["id"]

    duplicate = api.post(f"{URL}/{color['id']}/options", json={"code": "Red", "name": "Rojo 2"})
    assert duplicate.json()["code"] == "PRODUCT_CATALOG.DUPLICATE_CODE"


def test_options_only_for_option_definitions(api) -> None:
    weight = _create(api, "PESO_NETO", "DECIMAL")

    response = api.post(f"{URL}/{weight['id']}/options", json={"code": "X", "name": "X"})

    assert response.status_code == 422
    assert response.json()["code"] == "PRODUCT_CATALOG.DEFINITION_NOT_OPTION"


def test_unit_only_for_numeric(api, session_factory) -> None:
    unit = factories.unit(session_factory, "KG")

    text = api.post(
        URL,
        json={"code": "NOMBRE", "name": "Nombre", "description": "d", "data_type": "TEXT", "unit_of_measure_id": str(unit.id)},
    )
    assert text.json()["code"] == "PRODUCT_CATALOG.UNIT_NOT_ALLOWED_FOR_DATA_TYPE"

    decimal = _create(api, "PESO", "DECIMAL", unit_of_measure_id=str(unit.id))
    assert decimal["unit_of_measure_id"] == str(unit.id)


def test_inactive_unit_rejected(api, session_factory) -> None:
    unit = factories.unit(session_factory, "LB", status="INACTIVE")
    response = api.post(
        URL,
        json={"code": "PESO", "name": "Peso", "description": "d", "data_type": "DECIMAL", "unit_of_measure_id": str(unit.id)},
    )
    assert response.json()["code"] == "PRODUCT_CATALOG.REFERENCE_INACTIVE"


def test_description_required(api) -> None:
    response = api.post(URL, json={"code": "X", "name": "X", "description": "  ", "data_type": "TEXT"})
    assert response.status_code == 422


def test_data_type_and_unit_immutable(api) -> None:
    weight = _create(api, "PESO", "DECIMAL")

    for field, value in (("data_type", "INTEGER"), ("unit_of_measure_id", None)):
        response = api.put(
            f"{URL}/{weight['id']}",
            json={"name": "Peso", "description": "d", "version": 1, field: value},
        )
        assert response.json()["code"] == "PRODUCT_CATALOG.IMMUTABLE_FIELD"

    ok = api.put(f"{URL}/{weight['id']}", json={"name": "Peso neto", "description": "Peso sin empaque", "version": 1})
    assert ok.status_code == 200


def test_option_lifecycle_and_permissions(api, api_as) -> None:
    color = _create(api, "COLOR", "OPTION")
    red = api.post(f"{URL}/{color['id']}/options", json={"code": "RED", "name": "Rojo"}).json()
    option_url = f"{URL}/{color['id']}/options/{red['id']}"

    assert api_as("attribute-definitions:update").post(f"{option_url}/deactivate", json={"version": 1}).status_code == 403
    assert api.post(f"{option_url}/deactivate", json={"version": 1}).json()["status"] == "INACTIVE"
    assert api.put(option_url, json={"name": "Rojo vivo", "display_order": 3, "version": 2}).status_code == 200
    assert api.post(f"{option_url}/reactivate", json={"version": 3}).json()["status"] == "ACTIVE"


def test_list_filters(api) -> None:
    _create(api, "COLOR", "OPTION")
    _create(api, "PESO", "DECIMAL")

    def codes(query: str) -> list[str]:
        return [item["code"] for item in api.get(f"{URL}?{query}").json()["items"]]

    assert codes("data_type=OPTION") == ["COLOR"]
    assert codes("code=peso") == ["PESO"]
    assert codes("search=colo") == ["COLOR"]
    assert codes("status=INACTIVE") == []
