"""Idempotencia de la confirmación (R-04, FR-023; RC-01; T054)."""

from __future__ import annotations

from tests.conftest import base, count_rows, fetch, line, new_key


def test_same_key_returns_same_result_without_second_output(world, fakes, make_sequence, make_draft, confirm) -> None:
    make_sequence()
    draft = make_draft()
    key = new_key()
    first = confirm(draft, key)
    for _ in range(20):  # SC-002: 20 reintentos con la misma clave
        again = confirm(draft, key)
        assert again.status_code == 200
        assert again.json()["number"] == first.json()["number"]
        assert again.json()["inventory_operation_id"] == first.json()["inventory_operation_id"]
    assert len(fakes.inventory.outputs()) == 1
    assert fakes.inventory.output_calls == 1


def test_same_key_after_failure_repeats_the_error(seller, world, fakes, make_sequence, make_draft, confirm) -> None:
    make_sequence()
    draft = make_draft()
    key = new_key()
    fakes.inventory.reject_output = (422, "VALIDATION_ERROR")
    first = confirm(draft, key)
    fakes.inventory.reject_output = None
    again = confirm(draft, key)
    assert again.status_code == first.status_code == 409
    assert again.json()["code"] == first.json()["code"] == "SALES.INVENTORY_REJECTED"
    assert again.json()["details"] == first.json()["details"]
    assert fakes.inventory.outputs() == []
    # El intento refrescó los snapshots (versión nueva): una clave nueva vuelve a intentar con la versión vigente.
    current = seller.get(f"{base(world)}/sales/{draft['id']}").json()
    assert current["version"] == draft["version"] + 1
    assert confirm(current, new_key()).status_code == 200


def test_key_conflicts(seller, as_user, world, make_sequence, make_draft, confirm, cancel) -> None:
    make_sequence()
    first, second = make_draft(), make_draft()
    key = new_key()
    assert confirm(first, key).status_code == 200
    other_sale = confirm(second, key)
    assert other_sale.status_code == 409 and other_sale.json()["code"] == "SALES.IDEMPOTENCY_KEY_CONFLICT"
    assert "number" not in other_sale.text
    other_type = cancel(first, key, version=2)
    assert other_type.status_code == 409 and other_type.json()["code"] == "SALES.IDEMPOTENCY_KEY_CONFLICT"
    other_identity = confirm(first, key, client=as_user("admin.test"))
    assert other_identity.status_code == 409 and other_identity.json()["code"] == "SALES.IDEMPOTENCY_KEY_CONFLICT"


def test_pending_operation_blocks_other_keys_and_edits(seller, world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence()
    draft = make_draft()
    fakes.inventory.availability.down = True
    pending = confirm(draft)
    assert pending.status_code == 503
    operation_id = pending.json()["operation_id"]

    other = confirm(draft)  # otra clave
    assert other.status_code == 409 and other.json()["code"] == "SALES.OPERATION_IN_PROGRESS"
    assert other.json()["operation_id"] == operation_id
    stale = confirm(draft, version=99)  # D-10 (014): la operación en curso precede al conflicto de versión
    assert stale.status_code == 409 and stale.json()["code"] == "SALES.OPERATION_IN_PROGRESS"
    current = seller.get(f"{base(world)}/sales/{draft['id']}").json()
    assert current["pending_operation_id"] == operation_id
    edit = seller.post(f"{base(world)}/sales/{draft['id']}/details", json={**line(world.product_2), "version": current["version"]})
    assert edit.status_code == 409 and edit.json()["code"] == "SALES.OPERATION_IN_PROGRESS"
    assert count_rows(test_engine, "sale_operations", "status = 'PENDING'") == 1


def test_operations_listing_hides_the_key(seller, world, make_sequence, make_draft, confirm) -> None:
    make_sequence()
    draft = make_draft()
    key = new_key()
    confirm(draft, key)
    operations = seller.get(f"{base(world)}/sales/{draft['id']}/operations").json()
    assert len(operations) == 1 and operations[0]["status"] == "SUCCEEDED"
    assert key not in str(operations) and "idempotency_key" not in operations[0]
    single = seller.get(f"{base(world)}/sale-operations/{operations[0]['id']}")
    assert single.status_code == 200 and single.json()["operation_type"] == "CONFIRM"


def test_invalid_key_format(seller, world, make_draft) -> None:
    draft = make_draft()
    for key in ("con espacio", "x" * 151):
        response = seller.post(
            f"{base(world)}/sales/{draft['id']}/confirmation", json={"version": 1}, headers={"Idempotency-Key": key}
        )
        assert response.status_code == 422, key


def test_number_not_consumed_by_failures(world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence()
    fakes.inventory.reject_output = (409, "OPERATION_KEY_CONFLICT")
    confirm(make_draft())
    fakes.inventory.reject_output = None
    fakes.inventory.availability.down = True
    confirm(make_draft())
    fakes.inventory.availability.down = False
    assert confirm(make_draft()).json()["number"] == "FV-000001"
    assert fetch(test_engine, "SELECT current_number FROM sale_sequence_counters")[0]["current_number"] == 1
