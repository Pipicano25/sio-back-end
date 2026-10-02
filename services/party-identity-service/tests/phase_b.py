"""Apoyo común de las pruebas de la Fase B (datos ficticios, no reales)."""

from __future__ import annotations

from typing import Any

from tests.conftest import (
    CITY_ID,
    COLOMBIA_ID,
    COMPANY_ID,
    DIVISION_ID,
    organization_payload,
    person_payload,
)

PROFILE_PERMISSIONS = {
    "person": "person_contact_profiles",
    "organization": "organization_contact_profiles",
}


def create_organization(api, number: str = "900000001-1") -> dict[str, Any]:
    response = api.post("/api/v1/organization-identities", json=organization_payload(identification_number=number))
    assert response.status_code == 201, response.text
    return response.json()


def create_person(api, number: str = "1000000001") -> dict[str, Any]:
    payload = person_payload(identification_number=number)
    payload.pop("birth_date", None)
    response = api.post("/api/v1/person-identities", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def deactivate(api, kind: str, identity: dict[str, Any]) -> dict[str, Any]:
    response = api.post(
        f"/api/v1/{kind}-identities/{identity['id']}/deactivate",
        json={"version": identity["version"]},
    )
    assert response.status_code == 200, response.text
    return response.json()


def profile_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "email": "contacto@ejemplo-ficticio.co",
        "phone": "+57 601 555 0100",
        "address_line": "Calle 00 # 00-00 (ficticia)",
        "country_id": str(COLOMBIA_ID),
        "administrative_division_id": str(DIVISION_ID),
        "city_id": str(CITY_ID),
        "postal_code": "110111",
        "confirmed_by_company_id": str(COMPANY_ID),
    }
    payload.update(overrides)
    return payload


def profile_url(kind: str, identity_id: str) -> str:
    return f"/api/v1/{kind}-identities/{identity_id}/contact-profile"


def code(response) -> str:
    return response.json()["code"].removeprefix("PARTY_IDENTITY.")
