"""Utilidades de las pruebas de integración (entorno integrado; secretos solo por entorno o `.env`).

Los datos se crean con los servicios reales y son **ficticios de validación**: organizaciones
`PRUEBA SIO INV … <ejecución>`, personas `PRUEBAINV<ejecución>`, productos `Producto ficticio de
validación INV <ejecución>`. No se eliminan (los movimientos son inmutables).
"""

from __future__ import annotations

import os
import random
import re
import secrets
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
RUN_ID = secrets.token_hex(4).upper()


def _base(variable: str, default: str) -> str:
    return os.environ.get(variable, default).rstrip("/")


INVENTORY = _base("INVENTORY_INTEGRATION_BASE_URL", "http://localhost:8109/api/v1")
INVENTORY_ROOT = INVENTORY.removesuffix("/api/v1")
OPERATIONAL_CONTEXT = _base("OPERATIONAL_CONTEXT_INTEGRATION_BASE_URL", "http://localhost:8104/api/v1")
COMMERCIAL_RELATIONSHIP = _base("COMMERCIAL_RELATIONSHIP_INTEGRATION_BASE_URL", "http://localhost:8106/api/v1")
PRODUCT_CATALOG = _base("PRODUCT_CATALOG_INTEGRATION_BASE_URL", "http://localhost:8103/api/v1")
PARTY_IDENTITY = _base("PARTY_IDENTITY_INTEGRATION_BASE_URL", "http://localhost:8101/api/v1")
GEOGRAPHY = _base("GEOGRAPHY_INTEGRATION_BASE_URL", "http://localhost:8102")
AUDIT = _base("AUDIT_INTEGRATION_BASE_URL", "http://localhost:8110/api/v1")
TOKEN_URL = _base("KEYCLOAK_TOKEN_URL", "http://localhost:8081/realms/sio/protocol/openid-connect/token")
OPERATOR = os.environ.get("INVENTORY_TEST_OPERATOR_CLIENT_ID", "inventory-test-operator")


def secret(variable: str) -> str | None:
    value = os.environ.get(variable, "").strip()
    env_file = REPO_ROOT / "infrastructure" / ".env"
    if not value and env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, separator, content = line.partition("=")
            if separator and name.strip() == variable:
                value = content.strip().strip('"').strip("'")
    return value or None


def user_client(username: str) -> httpx.Client:
    password = secret("KEYCLOAK_TEST_USER_PASSWORD")
    if not password:
        pytest.skip("Defina KEYCLOAK_TEST_USER_PASSWORD (o infrastructure/.env).")
    token = httpx.post(
        TOKEN_URL,
        data={"grant_type": "password", "client_id": "sio-web", "scope": "openid", "username": username, "password": password},
        timeout=15,
    ).raise_for_status().json()["access_token"]
    return httpx.Client(headers={"Authorization": f"Bearer {token}"}, timeout=30)


def operator_client() -> httpx.Client:
    client_secret = secret("INVENTORY_TEST_OPERATOR_CLIENT_SECRET")
    if not client_secret:
        pytest.skip("Defina INVENTORY_TEST_OPERATOR_CLIENT_SECRET (o infrastructure/.env).")
    token = httpx.post(
        TOKEN_URL,
        data={"grant_type": "client_credentials", "client_id": OPERATOR, "client_secret": client_secret},
        timeout=15,
    ).raise_for_status().json()["access_token"]
    return httpx.Client(headers={"Authorization": f"Bearer {token}"}, timeout=30)


def require_services(*roots: str) -> None:
    for url in roots:
        try:
            httpx.get(url, timeout=5).raise_for_status()
        except httpx.HTTPError:
            pytest.skip(f"Servicio no disponible para integración: {url}")


def require_inventory() -> None:
    require_services(
        f"{INVENTORY_ROOT}/health/ready",
        f"{OPERATIONAL_CONTEXT.removesuffix('/api/v1')}/health/ready",
        f"{COMMERCIAL_RELATIONSHIP.removesuffix('/api/v1')}/health/ready",
        f"{PRODUCT_CATALOG.removesuffix('/api/v1')}/health/ready",
        f"{PARTY_IDENTITY.removesuffix('/api/v1')}/health/ready",
        f"{GEOGRAPHY}/health/live",
    )


# ---------------------------------------------------------------------------------------
# Datos ficticios con los servicios reales
# ---------------------------------------------------------------------------------------


def _first_id(client, url, **params) -> str:
    items = client.get(url, params=params).raise_for_status().json()["items"]
    if not items:
        pytest.skip(f"Sin datos en {url} {params}")
    return items[0]["id"]


def _conforming_number(pattern: str) -> str:
    regex = re.compile(pattern)
    for _ in range(200):
        base_length = random.randint(8, 10)
        base = str(random.randint(1, 9)) + "".join(random.choice("0123456789") for _ in range(base_length - 1))
        for candidate in (f"{base}-{random.randint(0, 9)}", base):
            if regex.fullmatch(candidate):
                return candidate
    pytest.skip(f"No se pudo generar un número que cumpla el patrón {pattern!r}.")


def _create_party(client, colombia, kind, sigla, path, payload) -> str:
    rules = client.get(
        f"{PARTY_IDENTITY}/identification-type-rules",
        params={"party_kind": kind, "country_id": colombia, "sigla": sigla, "is_active": "true"},
    ).raise_for_status().json()["items"]
    if not rules:
        pytest.skip(f"Party Identity no tiene la regla {sigla} activa para Colombia (ejecute su seed).")
    for _ in range(5):
        response = client.post(
            f"{PARTY_IDENTITY}/{path}",
            json={**payload, "identification_number": _conforming_number(rules[0]["number_pattern"])},
        )
        if response.status_code == 201:
            return response.json()["id"]
        if response.status_code != 409:
            pytest.fail(f"Party Identity respondió {response.status_code}: {response.text}")
    pytest.fail("No se obtuvo un número de identificación libre tras 5 intentos.")


def _organization(client, colombia, label: str) -> str:
    return _create_party(client, colombia, "ORGANIZATION", "NIT", "organization-identities", {
        "country_id": colombia,
        "identification_type": "NIT",
        "legal_name": f"PRUEBA SIO INV {label}{RUN_ID} (DATO FICTICIO DE VALIDACION)",
    })


def _person(client, colombia, label: str) -> str:
    return _create_party(client, colombia, "PERSON", "CC", "person-identities", {
        "identification_country_id": colombia,
        "identification_type": "CC",
        "first_name": f"PRUEBAINV{label}{RUN_ID}",
        "last_name": "DATO FICTICIO DE VALIDACION",
        "birth_date": "1990-01-01",
    })


def _member(client, company: str, username: str, person: str) -> str:
    response = client.post(f"{OPERATIONAL_CONTEXT}/companies/{company}/application-users", json={
        "username": username,
        "person_identity_id": person,
        "display_name": f"Validación INV {username} {RUN_ID} (dato ficticio)",
    })
    if response.status_code == 503:
        pytest.skip("Operational Context no pudo resolver el usuario en Keycloak Admin.")
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _adopt(client, company: str, label: str, *, inventory_control: bool) -> str:
    unit = _first_id(client, f"{PRODUCT_CATALOG}/units-of-measure", status="ACTIVE")
    category = client.post(f"{PRODUCT_CATALOG}/categories", json={
        "code": f"VAL-INV-{label}-{RUN_ID}", "name": f"Categoría ficticia de validación INV {label} {RUN_ID}",
    })
    assert category.status_code == 201, category.text
    product = client.post(f"{PRODUCT_CATALOG}/products", json={
        "product_type": "GOOD",
        "canonical_name": f"Producto ficticio de validación INV {label} {RUN_ID}",
        "base_unit_id": unit,
    })
    assert product.status_code == 201, product.text
    product_id = product.json()["id"]
    assert client.post(
        f"{PRODUCT_CATALOG}/products/{product_id}/categories", json={"global_category_id": category.json()["id"]}
    ).status_code == 201
    assert client.post(f"{PRODUCT_CATALOG}/products/{product_id}/presentations", json={
        "code": f"UND-{label}-{RUN_ID}", "name": "Unidad (dato ficticio)", "is_base": True,
    }).status_code == 201
    adopted = client.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company}/company-products", json={
        "global_product_id": product_id,
        "internal_code": f"INV-{label}-{RUN_ID}",
        "display_name": f"Producto ficticio INV {label} {RUN_ID}",
        "currency_code": "COP",
        "inventory_control_enabled": inventory_control,
    })
    assert adopted.status_code == 201, adopted.text
    return adopted.json()["id"]


@dataclass(frozen=True)
class RealWorld:
    company: str
    branch: str
    user: str
    products: tuple[str, str]
    no_control_product: str
    foreign_company: str
    branch_b: str = ""
    """013: segunda sucursal `ACTIVE` sin asignaciones (ajustes y conteos → `BRANCH_ACCESS_DENIED`)."""
    inventario_user: str = ""
    """013: usuario operativo de `inventario.test`, asignado solo a `branch`."""


def build_world(admin: httpx.Client) -> RealWorld:
    """Empresa con sucursal, `admin.test` e `inventario.test` como miembros y productos adoptados."""
    colombia = _first_id(admin, f"{GEOGRAPHY}/global-countries", iso3_code="COL")
    company = admin.post(f"{OPERATIONAL_CONTEXT}/companies", json={"organization_identity_id": _organization(admin, colombia, "")})
    assert company.status_code == 201, company.text
    company_id = company.json()["id"]

    user = _member(admin, company_id, "admin.test", _person(admin, colombia, "A"))
    inventario = _member(admin, company_id, "inventario.test", _person(admin, colombia, "I"))

    branch = admin.post(f"{OPERATIONAL_CONTEXT}/companies/{company_id}/branches", json={
        "code": f"INV{RUN_ID}", "name": f"Bodega ficticia de validación INV {RUN_ID}",
    })
    assert branch.status_code == 201, branch.text
    branch_b = admin.post(f"{OPERATIONAL_CONTEXT}/companies/{company_id}/branches", json={
        "code": f"INVB{RUN_ID}", "name": f"Bodega B ficticia de validación INV {RUN_ID}",
    })
    assert branch_b.status_code == 201, branch_b.text
    # 013 (DS-14): `inventario.test` y `admin.test` asignados a la sucursal principal, no a la B.
    for member in (inventario, user):
        assigned = admin.post(
            f"{OPERATIONAL_CONTEXT}/application-users/{member}/user-branches", json={"branch_id": branch.json()["id"]}
        )
        assert assigned.status_code == 201, assigned.text

    foreign = admin.post(f"{OPERATIONAL_CONTEXT}/companies", json={"organization_identity_id": _organization(admin, colombia, "AJENA ")})
    assert foreign.status_code == 201, foreign.text

    return RealWorld(
        company=company_id,
        branch=branch.json()["id"],
        user=user,
        products=(_adopt(admin, company_id, "A", inventory_control=True), _adopt(admin, company_id, "B", inventory_control=True)),
        no_control_product=_adopt(admin, company_id, "S", inventory_control=False),
        foreign_company=foreign.json()["id"],
        branch_b=branch_b.json()["id"],
        inventario_user=inventario,
    )


DEFAULT_UNIT_COST = "1000"
"""013 (DS-12, cambio incompatible aprobado): toda entrada lleva costo."""


def operation(world: RealWorld, *lines: tuple[str, str], origin_type: str = "PURCHASE", unit_cost: str | None = None) -> dict:
    from uuid import uuid4

    unit_cost = unit_cost or DEFAULT_UNIT_COST

    return {
        "operation_key": str(uuid4()),
        "company_id": world.company,
        "branch_id": world.branch,
        "origin_type": origin_type,
        "origin_id": str(uuid4()),
        "application_user_id": world.user,
        "correlation_id": str(uuid4()),
        "reason": None,
        "lines": [
            {
                "origin_detail_id": str(uuid4()),
                "company_product_id": product,
                "quantity": quantity,
                **({"unit_cost": unit_cost} if unit_cost and origin_type == "PURCHASE" else {}),
            }
            for product, quantity in lines
        ],
    }


def reversal(world: RealWorld, company: str | None = None) -> dict:
    from uuid import uuid4

    return {
        "operation_key": str(uuid4()),
        "company_id": company or world.company,
        "application_user_id": world.user,
        "correlation_id": str(uuid4()),
        "reason": f"Anulación ficticia de validación INV {RUN_ID}",
    }
