"""INV-3 ejecuta una sola consulta agregada, sin recorrer saldos en la aplicación (spec 022, FR-022-57; T042)."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import event
from sqlalchemy.engine import Engine

from tests.spec022_support import insert_balance, insert_policy

INVENTORY_TABLES = ("inventory_balances", "inventory_policies")


def _statements(client, world) -> list[str]:
    seen: list[str] = []

    def listener(conn, cursor, statement, parameters, context, executemany) -> None:
        seen.append(statement)

    event.listen(Engine, "before_cursor_execute", listener)
    try:
        response = client.post(
            f"/api/v1/companies/{world.company}/inventory-summary",
            json={"branch_ids": [str(world.branch), str(world.other_branch)], "include_valuation": True},
        )
        assert response.status_code == 200, response.text
    finally:
        event.remove(Engine, "before_cursor_execute", listener)
    return [statement for statement in seen if any(table in statement for table in INVENTORY_TABLES)]


def test_single_aggregate_query_regardless_of_volume(as_user, world, test_engine) -> None:
    reader = as_user("inventario.test")
    assert len(_statements(reader, world)) == 1

    for _ in range(40):
        product = uuid4()
        insert_balance(test_engine, world.company, world.branch, product, "2")
        insert_policy(test_engine, world.company, world.other_branch, product, "1")

    statements = _statements(reader, world)
    assert len(statements) == 1
    assert "GROUP BY" in statements[0].upper()
