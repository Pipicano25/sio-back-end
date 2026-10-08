"""Visibilidad de la rentabilidad (FR-027a, DS-12, C-08; SC-006; T067).

Con `perm:sales:sales:read-profitability` se reciben costo, `cost_known`, margen, porcentaje y
el indicador de costo desconocido; sin él esos campos se omiten en todas las respuestas que
devuelven una venta o líneas. Los errores nunca los incluyen.
"""

from __future__ import annotations

import pytest

from tests.conftest import base, line, new_key, sale_body, user_sub

LINE_FIELDS = ("unit_cost_snapshot", "cost_total", "cost_known", "gross_margin_amount", "gross_margin_percentage")


def has_profitability(body) -> bool:
    text = str(body)
    return any(name in text for name in (*LINE_FIELDS, "has_unknown_cost"))


def responses_for(client, world, fakes, make_draft, confirm, cancel, username):
    """Ejecuta cada ruta que devuelve una venta o líneas con el cliente dado."""
    fakes.oc.add_member(user_sub(username), world.company, branches=(world.branch,))
    url = f"{base(world)}/sales"
    created = client.post(url, json=sale_body(world, line(world.product)))
    sale = created.json()
    out = {"create": created}
    out["update"] = client.put(
        f"{url}/{sale['id']}", json={"branch_id": str(world.branch), "company_customer_id": str(world.customer), "version": 1}
    )
    added = client.post(f"{url}/{sale['id']}/details", json={**line(world.product_2), "version": 2})
    out["add_line"] = added
    second = added.json()["lines"][1]
    out["update_line"] = client.put(f"{url}/{sale['id']}/details/{second['id']}", json={**line(world.product_2, "1"), "version": 3})
    out["delete_line"] = client.delete(f"{url}/{sale['id']}/details/{second['id']}", params={"version": 4})
    key = new_key()
    out["confirm"] = confirm(client.get(f"{url}/{sale['id']}").json(), key, client=client)
    out["confirm_replay"] = confirm(client.get(f"{url}/{sale['id']}").json(), key, client=client)
    out["get"] = client.get(f"{url}/{sale['id']}")
    out["list"] = client.get(url)
    out["lines"] = client.get(f"{url}/{sale['id']}/details")
    out["cancel"] = cancel(out["get"].json(), client=client)
    return out


def test_without_permission_every_sale_response_omits_profitability(seller, world, fakes, make_sequence, make_draft, confirm, cancel) -> None:
    make_sequence()
    responses = responses_for(seller, world, fakes, make_draft, confirm, cancel, "ventas.test")
    for name, response in responses.items():
        assert response.status_code in (200, 201), (name, response.text)
        assert not has_profitability(response.json()), name
    # Omitidos, no nulos: los demás campos sí están.
    assert "unit_price" in responses["get"].json()["lines"][0]


def test_with_permission_every_sale_response_includes_profitability(supervisor, world, fakes, make_sequence, make_draft, confirm, cancel) -> None:
    make_sequence()
    responses = responses_for(supervisor, world, fakes, make_draft, confirm, cancel, "supervisor.test")
    # La matriz del realm no da `delete` a supervisores: borrar líneas y anular son 403 para ellos.
    assert responses["delete_line"].status_code == responses["cancel"].status_code == 403
    for name in ("create", "update", "add_line", "update_line", "confirm", "confirm_replay", "get"):
        body = responses[name].json()
        assert "has_unknown_cost" in body, name
        assert all(field in body["lines"][0] for field in LINE_FIELDS), name
    assert all("has_unknown_cost" in item for item in responses["list"].json()["items"])
    assert all(field in responses["lines"].json()[0] for field in LINE_FIELDS)
    confirmed_line = responses["confirm"].json()["lines"][0]
    assert confirmed_line["cost_known"] is True and confirmed_line["gross_margin_amount"] is not None


@pytest.mark.parametrize("username", ["reportes.test", "consulta.test"])
def test_readers_do_not_see_profitability(as_user, seller, world, make_sequence, make_draft, confirm, username) -> None:
    make_sequence()
    draft = make_draft()
    confirm(draft)
    reader = as_user(username)
    for response in (
        reader.get(f"{base(world)}/sales/{draft['id']}"),
        reader.get(f"{base(world)}/sales"),
        reader.get(f"{base(world)}/sales/{draft['id']}/details"),
    ):
        assert response.status_code == 200 and not has_profitability(response.json())


def test_admin_sees_profitability_through_the_global_wildcard(as_user, world, make_sequence, make_draft, confirm) -> None:
    make_sequence()
    draft = make_draft()
    confirm(draft)
    body = as_user("admin.test").get(f"{base(world)}/sales/{draft['id']}").json()
    assert body["lines"][0]["cost_known"] is True


def test_errors_never_include_profitability(seller, world, fakes, make_sequence, make_draft, confirm) -> None:
    make_sequence()
    draft = make_draft()
    fakes.inventory.reject_output = (422, "VALIDATION_ERROR")
    response = confirm(draft)
    assert response.status_code == 409 and not has_profitability(response.json())


def test_delete_line_and_cancel_include_profitability_with_permission(as_user, world, fakes, make_sequence, make_draft, confirm, cancel) -> None:
    make_sequence()
    admin = as_user("admin.test")
    responses = responses_for(admin, world, fakes, make_draft, confirm, cancel, "admin.test")
    for name in ("delete_line", "cancel"):
        assert responses[name].status_code == 200, responses[name].text
        assert all(field in responses[name].json()["lines"][0] for field in LINE_FIELDS), name
