"""Seguridad de las políticas de precios (T019; FR-021-32, FR-021-32a; CP-67 políticas, CP-T15).

- Vendedores, compradores, consulta, reportes e inventario: `403` genérico, sin revelar el permiso (D3).
- Identidad técnica: `403` en todas las rutas de políticas (la exención técnica solo vale para la ruta A1).
- Otra empresa: `404`, el aislamiento vigente.
"""

from __future__ import annotations

import pytest

from tests.api.helpers import create_price_list

LIST_URL = "/api/v1/companies/{company}/price-lists/{price_list}/pricing-policies"
URL = "/api/v1/pricing-policies/{id}"
LOOKUP = "perm:commercial-relationship:platform:lookup"


@pytest.fixture
def policy(as_user, company):
    supervisor = as_user("supervisor.test")
    public = create_price_list(supervisor, company)
    response = supervisor.post(
        LIST_URL.format(company=company, price_list=public["id"]),
        json={"name": "Alimentos", "markup_percentage": "15", "company_product_presentation_ids": []},
    )
    assert response.status_code == 201, response.text
    return public, response.json()


def _calls(company, public, policy):
    body = {"version": 1}
    return [
        ("get", LIST_URL.format(company=company, price_list=public["id"]), None),
        ("post", LIST_URL.format(company=company, price_list=public["id"]), {"name": "Y", "markup_percentage": "1", "company_product_presentation_ids": []}),
        ("get", URL.format(id=policy["id"]), None),
        ("get", URL.format(id=policy["id"]) + "/terms", None),
        ("get", URL.format(id=policy["id"]) + "/presentations", None),
        ("put", URL.format(id=policy["id"]), {**body, "name": "Z"}),
        ("post", URL.format(id=policy["id"]) + "/percentage", {**body, "markup_percentage": "2"}),
        ("post", URL.format(id=policy["id"]) + "/presentations", {**body, "company_product_presentation_ids": []}),
        ("post", URL.format(id=policy["id"]) + "/presentations/remove", {**body, "company_product_presentation_ids": []}),
        ("post", URL.format(id=policy["id"]) + "/deactivate", {**body, "reason": "X"}),
    ]


@pytest.mark.parametrize("username", ["ventas.test", "compras.test", "consulta.test", "reportes.test", "inventario.test"])
def test_non_supervisors_are_forbidden_without_revealing_the_permission(as_user, company, policy, username) -> None:
    client = as_user(username)
    public, created = policy
    for method, url, body in _calls(company, public, created):
        response = getattr(client, method)(url, **({"json": body} if body else {}))
        assert response.status_code == 403, (username, method, url, response.text)
        assert "pricing_policies" not in response.text and "perm:" not in response.text


def test_technical_identity_is_forbidden(as_token, service_token, company, policy) -> None:
    client = as_token(service_token("perm:all:all:all", LOOKUP, client_id="purchase-service"))
    public, created = policy
    for method, url, body in _calls(company, public, created):
        response = getattr(client, method)(url, **({"json": body} if body else {}))
        assert response.status_code in (403, 404), (method, url, response.status_code)


def test_other_company_is_isolated(as_user, other_company, fake_oc) -> None:
    """Una política de otra empresa no existe para quien no es miembro de ella (`404`)."""
    from tests.conftest import user_sub

    admin = as_user("admin.test")
    fake_oc.add_member(user_sub("admin.test"), other_company)
    foreign_list = create_price_list(admin, other_company)
    created = admin.post(
        LIST_URL.format(company=other_company, price_list=foreign_list["id"]),
        json={"name": "Ajena", "markup_percentage": "10", "company_product_presentation_ids": []},
    )
    assert created.status_code == 201, created.text

    supervisor = as_user("supervisor.test")  # miembro de `company`, no de `other_company`
    assert supervisor.get(URL.format(id=created.json()["id"])).status_code == 404
    assert supervisor.get(LIST_URL.format(company=other_company, price_list=foreign_list["id"])).status_code == 404
