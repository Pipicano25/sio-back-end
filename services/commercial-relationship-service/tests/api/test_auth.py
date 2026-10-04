"""`401` y `403` en las 22 rutas (RC-01, SC-001; contracts/rest-api.md "Resumen de permisos").

El permiso se evalúa antes de cualquier llamada a Operational Context.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from tests.api.routes import ROUTES, route_id


def _url(route):
    return route.path.format(
        company_id=uuid4(), company_product_id=uuid4(), company_customer_id=uuid4(), company_supplier_id=uuid4()
    )


def _call(client, route):
    if route.method == "GET":
        return client.get(_url(route))
    return client.request(route.method, _url(route), json={})


@pytest.mark.parametrize("route", ROUTES, ids=route_id)
def test_without_token_is_401(as_token, fake_oc, route):
    response = _call(as_token(None), route)
    assert response.status_code == 401
    assert response.json()["code"] == "COMMERCIAL_RELATIONSHIP.UNAUTHENTICATED"
    assert fake_oc.access_calls == []


@pytest.mark.parametrize("route", ROUTES, ids=route_id)
def test_without_exact_permission_is_403(make_token, as_token, fake_oc, route):
    # Todos los permisos del servicio salvo el que exige la ruta.
    others = [
        f"perm:commercial-relationship:{resource}:{action}"
        for resource in ("company_products", "company_customers", "company_suppliers")
        for action in ("read", "create", "update", "delete")
        if (resource, action) != (route.resource, route.action)
    ]
    response = _call(as_token(make_token(*others, sub="sub-sin-permiso")), route)
    assert response.status_code == 403
    assert response.json()["code"] == "COMMERCIAL_RELATIONSHIP.FORBIDDEN"
    assert fake_oc.access_calls == []


@pytest.mark.parametrize("route", ROUTES, ids=route_id)
def test_exact_permission_passes_authorization(make_token, as_token, route):
    token = make_token(f"perm:commercial-relationship:{route.resource}:{route.action}", sub="sub-exacto")
    assert _call(as_token(token), route).status_code not in {401, 403}


def test_inventario_has_no_commercial_relationship_permissions(as_user, company):
    for route in ROUTES:
        assert _call(as_user("inventario.test"), route).status_code == 403, route_id(route)
