"""Pruebas de API de reglas de identificación (FR-004, FR-010–FR-014, FR-029, U2)."""

import pytest

from tests.conftest import COLOMBIA_ID, random_uuid, rule_payload

BASE = "/api/v1/identification-type-rules"


def _code(response) -> str:
    return response.json()["code"].removeprefix("PARTY_IDENTITY.")


def _create(api, **overrides) -> dict:
    response = api.post(BASE, json=rule_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


def _put(api, rule: dict, **overrides):
    body = {
        "number_pattern_description": rule["number_pattern_description"],
        "example_value": rule["example_value"],
        "version": rule["version"],
    }
    body.update(overrides)
    return api.put(f"{BASE}/{rule['id']}", json=body)


def test_create_returns_201_with_location(api) -> None:
    response = api.post(BASE, json=rule_payload(identification_type="citizen_id_modern", sigla="cc"))

    assert response.status_code == 201
    body = response.json()
    assert response.headers["location"] == f"{BASE}/{body['id']}"
    assert body["is_active"] is True
    assert body["identification_type"] == "CITIZEN_ID_MODERN"
    assert body["sigla"] == "CC"


def test_list_filters(api) -> None:
    person = _create(api)
    organization = _create(
        api,
        party_kind="ORGANIZATION",
        identification_type="TAX_ID",
        sigla="NIT",
        number_pattern="^[0-9]{9}-[0-9]$",
        example_value="900000001-1",
        min_age_years=None,
    )

    def ids(**params):
        return [item["id"] for item in api.get(BASE, params=params).json()["items"]]

    assert ids(party_kind="ORGANIZATION") == [organization["id"]]
    assert ids(sigla="cc") == [person["id"]]
    assert ids(identification_type="TAX_ID", country_id=str(COLOMBIA_ID)) == [organization["id"]]
    assert set(ids(is_active="true")) == {person["id"], organization["id"]}
    assert ids(is_active="false") == []


def test_invalid_party_kind_filter_is_422(api) -> None:
    response = api.get(BASE, params={"party_kind": "FOO"})

    assert response.status_code == 422
    assert _code(response) == "VALIDATION_ERROR"


def test_duplicate_active_rule_is_409(api) -> None:
    _create(api)

    response = api.post(BASE, json=rule_payload())

    assert response.status_code == 409
    assert _code(response) == "DUPLICATE_ACTIVE_RULE"


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"number_pattern": "[0-9"}, "INVALID_NUMBER_PATTERN"),
        ({"example_value": "12AB"}, "EXAMPLE_DOES_NOT_MATCH_PATTERN"),
        ({"min_age_years": 18, "max_age_years": 10}, "INVALID_AGE_RANGE"),
        ({"valid_from": "2030-01-02T00:00:00Z", "valid_to": "2030-01-01T00:00:00Z"}, "INVALID_VALIDITY_RANGE"),
        ({"country_id": random_uuid()}, "COUNTRY_NOT_FOUND"),
        ({"party_kind": "FOO"}, "VALIDATION_ERROR"),
        ({"is_active": False}, "VALIDATION_ERROR"),
    ],
)
def test_create_validation_errors_are_422(api, overrides, code) -> None:
    response = api.post(BASE, json=rule_payload(**overrides))

    assert response.status_code == 422, response.text
    assert _code(response) == code


def test_create_with_geography_down_is_503(api, fake_countries) -> None:
    fake_countries.mode = "unavailable"

    assert api.post(BASE, json=rule_payload()).status_code == 503


def test_put_changes_description_and_example_only(api) -> None:
    rule = _create(api)

    response = _put(api, rule, number_pattern_description="Descripción nueva.", example_value="2000000000")

    assert response.status_code == 200
    body = response.json()
    assert body["number_pattern_description"] == "Descripción nueva."
    assert body["example_value"] == "2000000000"
    assert body["version"] == 2
    assert body["id"] == rule["id"]


def test_identical_put_is_200_without_new_version(api) -> None:
    rule = _create(api)

    response = _put(api, rule)

    assert response.status_code == 200
    assert response.json()["version"] == 1
    assert response.json()["updated_at"] == rule["updated_at"]


def test_identical_put_with_stale_version_is_409(api) -> None:
    rule = _create(api)
    assert _put(api, rule, number_pattern_description="Cambio.").status_code == 200

    response = _put(api, rule, number_pattern_description="Cambio.")

    assert response.status_code == 409
    assert _code(response) == "VERSION_CONFLICT"


def test_put_with_different_pattern_requires_new_version(api) -> None:
    rule = _create(api)

    response = _put(api, rule, number_pattern="^[0-9]{11}$")

    assert response.status_code == 422
    assert _code(response) == "RULE_CHANGE_REQUIRES_NEW_VERSION"


@pytest.mark.parametrize("field_value", [("sigla", "TI"), ("party_kind", "ORGANIZATION"), ("country_id", "00000000-0000-0000-0000-000000000009")])
def test_put_with_identity_field_is_immutable(api, field_value) -> None:
    rule = _create(api)
    field, value = field_value

    response = _put(api, rule, **{field: value})

    assert response.status_code == 422
    assert _code(response) == "IMMUTABLE_FIELD"


def test_versions_creates_successor_and_closes_previous(api) -> None:
    rule = _create(api)

    response = api.post(
        f"{BASE}/{rule['id']}/versions",
        json={
            "number_pattern": "^[0-9]{11}$",
            "number_pattern_description": "Ahora 11 dígitos.",
            "example_value": "10000000000",
            "min_age_years": 18,
            "version": 1,
        },
    )

    assert response.status_code == 201, response.text
    successor = response.json()
    assert response.headers["location"] == f"{BASE}/{successor['id']}"
    assert successor["id"] != rule["id"]
    assert successor["is_active"] is True
    previous = api.get(f"{BASE}/{rule['id']}").json()
    assert previous["is_active"] is False
    assert previous["valid_to"] is not None


def test_deactivate_and_historic_rule_is_immutable(api) -> None:
    rule = _create(api)

    retired = api.post(f"{BASE}/{rule['id']}/deactivate", json={"version": 1})

    assert retired.status_code == 200
    assert retired.json()["is_active"] is False
    for response in (
        _put(api, retired.json(), number_pattern_description="x"),
        api.post(f"{BASE}/{rule['id']}/deactivate", json={"version": retired.json()["version"]}),
        api.post(
            f"{BASE}/{rule['id']}/versions",
            json={"number_pattern": "^1$", "number_pattern_description": "x", "version": retired.json()["version"]},
        ),
    ):
        assert response.status_code == 409
        assert _code(response) == "INVALID_STATUS_TRANSITION"


def test_read_only_user_can_read_but_not_create(api, api_as) -> None:
    rule = _create(api)
    reader = api_as("perm:party-identity:all:read")

    assert reader.get(f"{BASE}/{rule['id']}").status_code == 200
    assert reader.post(BASE, json=rule_payload(identification_type="X")).status_code == 403


def test_versions_requires_create_and_deactivate_requires_delete(api, api_as) -> None:
    rule = _create(api)
    updater = api_as("perm:party-identity:identification_type_rules:update")

    assert updater.post(f"{BASE}/{rule['id']}/versions", json={"number_pattern": "^1$", "number_pattern_description": "x", "version": 1}).status_code == 403
    assert updater.post(f"{BASE}/{rule['id']}/deactivate", json={"version": 1}).status_code == 403


def test_person_validation_uses_new_rule_version(api) -> None:
    rule = _create(api)
    api.post(
        f"{BASE}/{rule['id']}/versions",
        json={"number_pattern": "^[0-9]{11}$", "number_pattern_description": "11 dígitos.", "min_age_years": 18, "version": 1},
    )

    person = {
        "identification_country_id": str(COLOMBIA_ID),
        "identification_type": "CC",
        "identification_number": "1000000000",
        "first_name": "ANA",
        "last_name": "PRUEBA",
        "birth_date": "1990-01-01",
    }

    assert api.post("/api/v1/person-identities", json=person).status_code == 422
    assert api.post("/api/v1/person-identities", json={**person, "identification_number": "10000000000"}).status_code == 201
