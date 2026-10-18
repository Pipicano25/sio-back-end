"""Ningún campo de costo ni de valoración en las respuestas (T125; FR-022-15, RC-022-2, SC-022-3; CP-60 a CP-62).

1. Recorre los esquemas de respuesta de OpenAPI: falla si aparece `average_unit_cost`, `unit_cost`, `cost`,
   `margin`, `profit`, `fifo` o `inventory_value`. La valoración económica está fuera de la spec 022.
2. Con datos: ningún usuario, ni siquiera `supervisor` o `admin`, recibe costos ni valoración.
"""

from __future__ import annotations

from tests.api.support import COST_WORDS, keys_in

ECONOMIC = {"inventory_value", "valuation_currency_code", "valuation"}


def test_no_cost_or_valuation_field_in_any_response_schema(test_client) -> None:
    schemas = test_client.get("/openapi.json").json()["components"]["schemas"]
    for name, schema in schemas.items():
        for field in schema.get("properties", {}):
            assert not any(word in field.lower() for word in COST_WORDS), f"{name}.{field}"
            assert field not in ECONOMIC, f"{name}.{field}"


def test_no_user_receives_costs_or_valuation(world, as_user) -> None:
    item = world.product("Arroz")
    world.stock(item, "4")
    world.minimum(item, "6")
    world.fakes.cr.set_price(item.presentations[0], "2500.00")
    paths = ("product-overviews", "inventory-overviews", "low-stock-products", "inventory-summary")
    for user in ("ventas.test", "inventario.test", "supervisor.test", "admin.test"):
        for path in paths:
            response = as_user(user).get(f"{world.base}/{path}")
            if response.status_code == 403:
                continue
            assert response.status_code == 200, (user, path, response.text)
            keys = keys_in(response.json())
            assert not keys & ECONOMIC, (user, path)
            assert not {key for key in keys if any(word in key for word in COST_WORDS)}, (user, path)
