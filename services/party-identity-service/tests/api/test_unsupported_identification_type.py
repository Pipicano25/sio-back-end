"""Siglas sin regla activa se rechazan (DS-03, enmienda del 2026-11-18).

La base arranca con las 8 reglas de Colombia (NIT para organizaciones; CC, CE, TI, RC y NIT
para personas). Cualquier otra sigla, o un país sin reglas, responde `422`
`UNSUPPORTED_IDENTIFICATION_TYPE` y no guarda nada.
"""

from uuid import uuid4

from tests.conftest import organization_payload, person_payload

ORGS = "/api/v1/organization-identities"
PEOPLE = "/api/v1/person-identities"
CODE = "PARTY_IDENTITY.UNSUPPORTED_IDENTIFICATION_TYPE"


def _total(api, url: str) -> int:
    return api.get(url).json()["total_records"]


def test_typo_in_organization_sigla_is_rejected(api) -> None:
    response = api.post(ORGS, json=organization_payload(identification_type="TRPE"))

    assert response.status_code == 422
    assert response.json()["code"] == CODE
    assert "'TRPE'" in response.json()["detail"]
    assert _total(api, ORGS) == 0


def test_lowercase_nit_is_normalized_and_accepted(api) -> None:
    response = api.post(ORGS, json=organization_payload(identification_type=" nit "))

    assert response.status_code == 201, response.text
    assert response.json()["identification_type"] == "NIT"


def test_person_sigla_of_organization_is_rejected_for_organizations(api) -> None:
    response = api.post(ORGS, json=organization_payload(identification_type="CC", identification_number="1000000001"))

    assert response.status_code == 422
    assert response.json()["code"] == CODE


def test_unknown_person_sigla_is_rejected(api) -> None:
    response = api.post(PEOPLE, json=person_payload(identification_type="PA", identification_number="AB123456"))

    assert response.status_code == 422
    assert response.json()["code"] == CODE
    assert _total(api, PEOPLE) == 0


def test_country_without_rules_is_rejected(api, fake_countries) -> None:
    other_country = uuid4()
    fake_countries.countries[other_country] = "PER"

    response = api.post(ORGS, json=organization_payload(country_id=str(other_country), identification_number="20100070970"))

    assert response.status_code == 422
    assert response.json()["code"] == CODE


def test_update_to_unknown_sigla_is_rejected(api) -> None:
    created = api.post(ORGS, json=organization_payload()).json()
    body = organization_payload(identification_type="TRPE", version=created["version"])

    response = api.put(f"{ORGS}/{created['id']}", json=body)

    assert response.status_code == 422
    assert response.json()["code"] == CODE
    assert api.get(f"{ORGS}/{created['id']}").json()["identification_type"] == "NIT"
