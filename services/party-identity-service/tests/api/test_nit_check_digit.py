"""NIT colombiano estricto (enmienda del 2026-11-18).

Base de 6 a 10 dígitos, guion y dígito de verificación de la DIAN (módulo 11). Las letras o un
dígito que no corresponde responden `422` `INVALID_IDENTIFICATION_NUMBER` y no guardan nada.
"""

import pytest

from party_identity_service.application.identification_rules import nit_check_digit
from tests.conftest import organization_payload, person_payload

ORGS = "/api/v1/organization-identities"
PEOPLE = "/api/v1/person-identities"
CODE = "PARTY_IDENTITY.INVALID_IDENTIFICATION_NUMBER"


@pytest.mark.parametrize(
    ("base", "digit"),
    [
        ("817004260", 0),  # GRUPO DAO S.A.S.
        ("890300466", 5),  # TECNOQUIMICAS S A
        ("830105173", 9),  # CDE LABORATORIOS S A S
        ("900123456", 8),
        ("800000123", 1),
    ],
)
def test_check_digit_matches_dian(base: str, digit: int) -> None:
    assert nit_check_digit(base) == digit


def test_valid_nit_is_accepted(api) -> None:
    response = api.post(ORGS, json=organization_payload(identification_number="817004260-0"))

    assert response.status_code == 201, response.text


def test_wrong_check_digit_is_rejected_with_expected_digit(api) -> None:
    response = api.post(ORGS, json=organization_payload(identification_number="817004260-5"))

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == CODE
    assert "corresponde 0, no 5" in body["detail"]
    assert api.get(ORGS).json()["total_records"] == 0


@pytest.mark.parametrize("number", ["GENERICO-0", "90012A456-8", "12345-1", "12345678901-1", "900123456"])
def test_nit_with_letters_or_bad_length_is_rejected(api, number: str) -> None:
    response = api.post(ORGS, json=organization_payload(identification_number=number))

    assert response.status_code == 422
    assert response.json()["code"] == CODE


def test_person_nit_also_checks_digit(api) -> None:
    bad = api.post(PEOPLE, json=person_payload(identification_type="NIT", identification_number="1061700000-5"))
    good = api.post(
        PEOPLE,
        json=person_payload(identification_type="NIT", identification_number=f"1061700000-{nit_check_digit('1061700000')}"),
    )

    assert bad.status_code == 422
    assert bad.json()["code"] == CODE
    assert good.status_code == 201, good.text


def test_update_to_wrong_check_digit_is_rejected(api) -> None:
    created = api.post(ORGS, json=organization_payload(identification_number="890300466-5")).json()
    payload = organization_payload(identification_number="890300466-4")
    payload["version"] = created["version"]

    response = api.put(f"{ORGS}/{created['id']}", json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == CODE
