"""Integración real Party Identity ↔ Geography: país de las reglas de identificación (G-017-01).

Se ejecuta solo con `pytest -m integration` y exige los servicios en ejecución (mismas variables que
`test_phase_b_integration.py`): Party Identity en `PARTY_IDENTITY_INTEGRATION_BASE_URL`, Geography en
`GEOGRAPHY_SERVICE_BASE_URL` (con Colombia y Perú del `seed`), Keycloak en `KEYCLOAK_TOKEN_URL` y la
contraseña de los usuarios de prueba en `KEYCLOAK_TEST_USER_PASSWORD` o `infrastructure/.env`.

- **Validador** (repetible en regresiones): `country_id` de todas las reglas (activas e históricas,
  leídas por la API de Party Identity) ⊆ países de Geography (`GET /global-countries/{id}`).
  Esperado: 0 referencias huérfanas y exactamente las 8 reglas colombianas activas.
- **API real:** alta con país real → `201`; país inexistente → `422 COUNTRY_NOT_FOUND` sin escribir;
  `PUT` no cambia el país (`422 IMMUTABLE_FIELD`). La regla de prueba (tipo `SIO_IT_<id>`) se retira
  al final; las reglas no se eliminan (D7).

Geography no disponible (`503`) se cubre con el doble y con el adaptador HTTP
(`tests/api/test_identification_type_rule_country_integrity.py`,
`tests/unit/test_geography_country_validator.py`): no se detienen servicios compartidos.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest

from party_identity_service.infrastructure.geography_country_validator import (
    HTTPGeographyCountryValidator,
)
from party_identity_service.integrity.country_references import check_rule_country_references
from party_identity_service.seed.constants import HISTORIC_RULE_IDS

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[4]
PASSWORD_VARIABLE = "KEYCLOAK_TEST_USER_PASSWORD"
PARTY_IDENTITY = os.environ.get("PARTY_IDENTITY_INTEGRATION_BASE_URL", "http://localhost:8002").rstrip("/")
GEOGRAPHY = os.environ.get("GEOGRAPHY_SERVICE_BASE_URL", "http://localhost:8000").rstrip("/")
TOKEN_URL = os.environ.get("KEYCLOAK_TOKEN_URL", "http://localhost:8081/realms/sio/protocol/openid-connect/token")
RULES = f"{PARTY_IDENTITY}/api/v1/identification-type-rules"
USERNAME = "admin.test"
RUN_ID = secrets.token_hex(4).upper()


def _password() -> str | None:
    value = os.environ.get(PASSWORD_VARIABLE, "").strip()
    env_file = REPO_ROOT / "infrastructure" / ".env"
    if not value and env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, separator, content = line.partition("=")
            if separator and name.strip() == PASSWORD_VARIABLE:
                value = content.strip().strip('"').strip("'")
    return value or None


@pytest.fixture(scope="module")
def context():
    password = _password()
    if not password:
        pytest.skip(f"Defina {PASSWORD_VARIABLE} (o infrastructure/.env) para las pruebas de integración.")

    with httpx.Client(timeout=15) as http:
        for url in (f"{PARTY_IDENTITY}/health/ready", f"{GEOGRAPHY}/health/live"):
            try:
                http.get(url).raise_for_status()
            except httpx.HTTPError:
                pytest.skip(f"Servicio no disponible para integración: {url}")
        try:
            token = http.post(TOKEN_URL, data={
                "grant_type": "password", "client_id": "sio-web", "scope": "openid",
                "username": USERNAME, "password": password,
            }).raise_for_status().json()["access_token"]
        except (httpx.HTTPError, KeyError):
            pytest.skip(f"No fue posible obtener el token de {USERNAME} en Keycloak.")
        authorization = f"Bearer {token}"
        geography = HTTPGeographyCountryValidator(base_url=GEOGRAPHY, authorization=authorization)
        yield {
            "http": http,
            "headers": {"Authorization": authorization},
            "geography": geography,
            "colombia": geography.find_id_by_iso3("COL"),
            "peru": geography.find_id_by_iso3("PER"),
        }


def _all_rules(context, **params) -> list[dict]:
    rules, page = [], 1
    while True:
        response = context["http"].get(RULES, params={**params, "page": page, "page_size": 100}, headers=context["headers"])
        response.raise_for_status()
        body = response.json()
        rules += body["items"]
        if page >= body["total_pages"]:
            return rules
        page += 1


def test_rule_countries_exist_in_geography(context) -> None:
    rules = _all_rules(context)

    report = check_rule_country_references(
        [(UUID(rule["id"]), UUID(rule["country_id"])) for rule in rules],
        context["geography"],
    )

    assert report.checked_rules == len(rules) > 0
    assert report.orphan_count == 0, {str(country): [str(rule) for rule in ids] for country, ids in report.orphans.items()}


def test_exactly_the_eight_historic_colombian_rules_are_active(context) -> None:
    active = _all_rules(context, country_id=str(context["colombia"]), is_active="true")
    colombian = [rule for rule in active if (rule["party_kind"], rule["identification_type"]) in HISTORIC_RULE_IDS]

    assert len(colombian) == 8
    assert {rule["id"] for rule in colombian} == set(HISTORIC_RULE_IDS.values())


def test_create_with_unknown_country_is_422_without_writing(context) -> None:
    identification_type = f"SIO_IT_{RUN_ID}_X"
    response = context["http"].post(RULES, headers=context["headers"], json={
        "party_kind": "PERSON", "country_id": str(uuid4()), "identification_type": identification_type,
        "sigla": "IT", "number_pattern": "^[0-9]{6}$", "number_pattern_description": "Prueba de integración.",
    })

    assert response.status_code == 422, response.text
    assert response.json()["code"].removeprefix("PARTY_IDENTITY.") == "COUNTRY_NOT_FOUND"
    assert _all_rules(context, identification_type=identification_type) == []


def test_create_with_real_country_and_country_is_immutable(context) -> None:
    http, headers = context["http"], context["headers"]
    response = http.post(RULES, headers=headers, json={
        "party_kind": "PERSON", "country_id": str(context["colombia"]), "identification_type": f"SIO_IT_{RUN_ID}",
        "sigla": "IT", "number_pattern": "^[0-9]{6}$", "number_pattern_description": "Prueba de integración.",
        "example_value": "123456",
    })
    assert response.status_code == 201, response.text
    rule = response.json()

    try:
        assert rule["country_id"] == str(context["colombia"])
        changed = http.put(f"{RULES}/{rule['id']}", headers=headers, json={
            "country_id": str(context["peru"]),
            "number_pattern_description": rule["number_pattern_description"],
            "example_value": rule["example_value"],
            "version": rule["version"],
        })
        assert changed.status_code == 422, changed.text
        assert changed.json()["code"].removeprefix("PARTY_IDENTITY.") == "IMMUTABLE_FIELD"
        current = http.get(f"{RULES}/{rule['id']}", headers=headers).json()
        assert current["country_id"] == str(context["colombia"]) and current["version"] == rule["version"]
    finally:
        http.post(f"{RULES}/{rule['id']}/deactivate", headers=headers, json={"version": rule["version"]})
