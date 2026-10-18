"""Rutas por sucursal con servicios reales en la pila aislada (ampliación aditiva de la spec 022).

Requiere que el contenedor `sio-it-product-inventory-query-service` tenga la versión con las rutas
`/companies/{c}/branches/{b}/…`; si no las tiene (`404` en la ruta sin documentar), las pruebas se omiten con el
motivo, nunca se aprueban sin ejecutarse.
"""

from __future__ import annotations

import pytest

from tests.integration.support import PIQ, anonymous_client, walk

pytestmark = pytest.mark.integration

ENDPOINTS = ("product-overviews", "inventory-overviews", "low-stock-products", "inventory-summary")
MATRIX = {
    "admin.test": (200, 200, 200, 200),
    "supervisor.test": (200, 200, 200, 200),
    "ventas.test": (200, 200, 403, 403),
    "inventario.test": (200, 200, 200, 200),
    "compras.test": (403, 403, 403, 403),
    "reportes.test": (403, 403, 403, 403),
    "consulta.test": (403, 403, 403, 403),
}


def branch_url(company: str, branch: str, endpoint: str) -> str:
    return f"{PIQ}/companies/{company}/branches/{branch}/{endpoint}"


@pytest.fixture(scope="module", autouse=True)
def branch_routes_deployed():
    with anonymous_client() as client:
        paths = client.get(PIQ.removesuffix("/api/v1") + "/openapi.json").json().get("paths", {})
    if "/api/v1/companies/{company_id}/branches/{branch_id}/product-overviews" not in paths:
        pytest.skip("El contenedor aislado no tiene todavía las rutas por sucursal (no se ha recreado).")


@pytest.mark.parametrize("username", list(MATRIX))
def test_matrix_per_group(users, seed, username) -> None:
    client = users(username)
    branch = seed["branches"]["PPAL"]
    for endpoint, expected in zip(ENDPOINTS, MATRIX[username], strict=True):
        response = client.get(branch_url(seed["company"], branch, endpoint))
        assert response.status_code == expected, (username, endpoint, response.text[:200])
        if expected == 403:
            assert "perm:" not in response.text


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_same_result_as_branch_id_in_the_query(users, seed, endpoint) -> None:
    client = users("supervisor.test")
    branch = seed["branches"]["NORTE"]
    by_path = client.get(branch_url(seed["company"], branch, endpoint)).raise_for_status().json()
    by_query = client.get(f"{PIQ}/companies/{seed['company']}/{endpoint}",
                          params={"branch_id": branch}).raise_for_status().json()
    by_path.pop("resolved_at"), by_query.pop("resolved_at")
    assert by_path == by_query


@pytest.mark.parametrize("endpoint", ("inventory-overviews", "low-stock-products"))
def test_only_the_branch_in_the_path(users, seed, endpoint) -> None:
    branch = seed["branches"]["SUR"]
    items, _ = walk(users("supervisor.test"), f"/companies/{seed['company']}/branches/{branch}/{endpoint}",
                    [("page_size", "20")])
    for item in items:
        rows = item["stock"]["branches"] if endpoint == "inventory-overviews" else [item]
        assert {row["branch_id"] for row in rows} == {branch}


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_branch_of_another_company_and_other_company(users, seed, endpoint) -> None:
    client = users("supervisor.test")
    assert client.get(branch_url(seed["company"], seed["branch_b"], endpoint)).status_code == 404
    # inventario.test no es miembro de la empresa B
    assert users("inventario.test").get(branch_url(seed["other_company"], seed["branch_b"], endpoint)).status_code == 404


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_query_scope_is_rejected_and_anonymous_is_401(users, seed, endpoint) -> None:
    url = branch_url(seed["company"], seed["branches"]["PPAL"], endpoint)
    assert users("supervisor.test").get(url, params={"scope": "COMPANY"}).status_code == 422
    with anonymous_client() as client:
        assert client.get(url).status_code == 401


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_branch_id_is_required_and_must_be_a_uuid(users, seed, endpoint) -> None:
    client = users("supervisor.test")
    assert client.get(f"{PIQ}/companies/{seed['company']}/branches/no-es-uuid/{endpoint}").status_code == 422
    assert client.get(f"{PIQ}/companies/{seed['company']}/branches//{endpoint}").status_code == 404  # sin sucursal
    assert client.get(f"{PIQ}/companies/no-es-uuid/branches/{seed['branches']['PPAL']}/{endpoint}").status_code == 422


def test_cursor_of_another_branch_restarts_and_a_tampered_cursor_is_422(users, seed) -> None:
    client = users("supervisor.test")
    company, branches = seed["company"], seed["branches"]
    first = client.get(branch_url(company, branches["PPAL"], "product-overviews"),
                       params={"page_size": "2"}).raise_for_status().json()
    assert first["next_cursor"], "la semilla debe tener más de una página"
    moved = client.get(branch_url(company, branches["NORTE"], "product-overviews"),
                       params={"page_size": "2", "cursor": first["next_cursor"]}).raise_for_status().json()
    assert moved["pagination_reset"] is True and moved["pagination_reset_reason"] == "FILTERS_CHANGED"
    tampered = first["next_cursor"][:-2] + ("AA" if not first["next_cursor"].endswith("AA") else "BB")
    response = client.get(branch_url(company, branches["PPAL"], "product-overviews"),
                          params={"page_size": "2", "cursor": tampered})
    assert response.status_code == 422 and "INVALID_CURSOR" in response.text


def test_cursor_of_another_company_is_422(users, seed) -> None:
    client = users("ventas.test")  # miembro de las dos empresas de la semilla
    other = client.get(f"{PIQ}/companies/{seed['other_company']}/branches/{seed['branch_b']}/product-overviews",
                       params={"page_size": "1"}).raise_for_status().json()
    if not other["next_cursor"]:
        pytest.skip("La empresa B de la semilla tiene una sola página")
    response = client.get(branch_url(seed["company"], seed["branches"]["PPAL"], "product-overviews"),
                          params={"page_size": "1", "cursor": other["next_cursor"]})
    assert response.status_code == 422 and "INVALID_CURSOR" in response.text
