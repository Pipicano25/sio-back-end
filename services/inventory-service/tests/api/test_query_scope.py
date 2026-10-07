"""Alcance de las consultas por empresa y lectura técnica (DS-12, DS-16; RC-06; T048)."""

from __future__ import annotations

import jwt
import pytest

from tests.conftest import BALANCES_READ, MOVEMENTS_READ, PLATFORM_LOOKUP, line, operation_body, user_sub

ENTRIES = "/api/v1/inventory-entries"


def read_urls(world, company=None) -> list[tuple[str, str]]:
    company = company or world.company
    product = world.products[0]
    base = f"/api/v1/companies/{company}"
    return [
        ("GET", f"{base}/branches/{world.branch}/balances"),
        ("GET", f"{base}/branches/{world.branch}/balances/{product}"),
        ("POST", f"{base}/branches/{world.branch}/balances/lookup"),
        ("GET", f"{base}/branches/{world.branch}/kardex/{product}"),
    ]


def call(client, method, url, world):
    if method == "POST":
        return client.post(url, json={"company_product_ids": [str(world.products[0])]})
    return client.get(url)


@pytest.mark.parametrize("username", ["admin.test", "supervisor.test", "inventario.test"])
def test_members_with_read_permission(as_user, world, username) -> None:
    for method, url in read_urls(world):
        assert call(as_user(username), method, url, world).status_code == 200


@pytest.mark.parametrize("username", ["compras.test", "ventas.test", "reportes.test", "consulta.test"])
def test_without_read_permission_403(as_user, world, username) -> None:
    for method, url in read_urls(world):
        assert call(as_user(username), method, url, world).status_code == 403


def test_non_member_404(as_user, world, fake_oc) -> None:
    fake_oc.members.discard((user_sub("inventario.test"), world.company))
    for method, url in read_urls(world):
        response = call(as_user("inventario.test"), method, url, world)
        assert response.status_code == 404
        assert response.json()["code"] == "INVENTORY.NOT_FOUND"


def test_branch_assignment_is_not_required(as_user, world, fake_oc) -> None:
    # El doble solo evalúa la membresía de empresa: no existe asignación a sucursal (DS-16).
    assert call(as_user("inventario.test"), "GET", read_urls(world)[0][1], world).status_code == 200
    assert all(company == world.company for _, _, company in fake_oc.access_calls)


def test_operational_context_403_and_unavailable(as_user, world, fake_oc) -> None:
    fake_oc.forbidden_subjects.add(user_sub("inventario.test"))
    response = call(as_user("inventario.test"), "GET", read_urls(world)[0][1], world)
    assert response.status_code == 403
    assert response.json()["code"] == "INVENTORY.OPERATIONAL_ACCESS_DENIED"

    fake_oc.forbidden_subjects.clear()
    fake_oc.unavailable = True
    response = call(as_user("inventario.test"), "GET", read_urls(world)[0][1], world)
    assert response.status_code == 503
    assert response.json()["dependency"] == "operational-context"


def test_user_authorization_is_propagated_never_the_technical_token(as_user, world, fake_oc) -> None:
    call(as_user("inventario.test"), "GET", read_urls(world)[1][1], world)
    sub, authorization, company = fake_oc.access_calls[-1]
    assert sub == user_sub("inventario.test")
    assert company == world.company
    # Se valida la identidad del token propagado por claims estables (no el JWT completo, cuyo `iat`
    # cambia entre segundos): es el token del usuario, nunca el técnico de Inventory.
    scheme, token = authorization.split(" ", 1)
    claims = jwt.decode(token, options={"verify_signature": False})
    assert scheme == "Bearer"
    assert claims["sub"] == user_sub("inventario.test")
    assert claims["preferred_username"] == "inventario.test"
    assert "client_id" not in claims  # el token técnico de Inventory es de una cuenta de servicio


def test_technical_lookup_without_membership(as_token, service_token, world, fake_oc) -> None:
    fake_oc.fail_if_called = True
    client = as_token(service_token(BALANCES_READ, MOVEMENTS_READ, PLATFORM_LOOKUP, client_id="sales-service"))
    for method, url in read_urls(world):
        assert call(client, method, url, world).status_code == 200


def test_technical_reader_without_platform_lookup_gets_normal_isolation(as_token, service_token, world, fake_oc) -> None:
    client = as_token(service_token(BALANCES_READ, MOVEMENTS_READ, client_id="sales-service"))
    assert call(client, "GET", read_urls(world)[0][1], world).status_code == 404
    assert fake_oc.access_calls


def test_never_returns_data_of_another_company(operator, as_user, world, fake_oc) -> None:
    product = world.products[0]
    operator.post(ENTRIES, json=operation_body(world, line(product, "5")))
    fake_oc.add_member(user_sub("inventario.test"), world.other_company)
    reader = as_user("inventario.test")
    base = f"/api/v1/companies/{world.other_company}/branches/{world.branch}"
    assert reader.get(f"{base}/balances").json()["items"] == []
    assert reader.get(f"{base}/balances/{product}").json()["quantity"] == "0.0000"
    assert reader.get(f"{base}/kardex/{product}").json()["items"] == []
