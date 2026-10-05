"""Contrato Provider: consulta de `GlobalPaymentConditionType` por UUID (RC-05; FR-019 a FR-021).

`contracts/payment-condition-type-provider.md` (feature 008).
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import text

from payment_reference_service.infrastructure.database import engine
from tests.conftest import CONDITION_TYPES, CT_READ

GUARANTEED = {"id", "code", "name", "status", "version"}


def _row_count() -> int:
    with engine.connect() as connection:
        return connection.execute(text("SELECT count(*) FROM global_payment_condition_types")).scalar_one()


def test_active_type_by_uuid_with_guaranteed_fields(as_roles, condition_type):
    response = as_roles(CT_READ).get(f"{CONDITION_TYPES}/{condition_type['id']}")

    assert response.status_code == 200
    body = response.json()
    assert GUARANTEED <= set(body)
    assert body["id"] == condition_type["id"]
    assert body["status"] == "ACTIVE"
    assert body["version"] == 1


def test_inactive_type_stays_consultable_and_is_not_deleted(admin, as_roles, condition_type):
    """FR-019: inactivar no elimina, no hay cascadas y el registro sigue consultable históricamente.

    008 no introduce integraciones salientes ni notificaciones: el comportamiento observable es que la
    fila sigue existiendo con el mismo `id` y el número de filas no cambia.
    """
    rows_before = _row_count()
    deactivated = admin.post(
        f"{CONDITION_TYPES}/{condition_type['id']}/deactivate",
        json={"version": condition_type["version"]},
    )
    assert deactivated.status_code == 200, deactivated.text

    reader = as_roles(CT_READ)
    response = reader.get(f"{CONDITION_TYPES}/{condition_type['id']}")
    listed = reader.get(CONDITION_TYPES, params={"status": "INACTIVE"})

    assert response.status_code == 200
    assert response.json()["id"] == condition_type["id"]
    assert response.json()["status"] == "INACTIVE"
    assert [item["id"] for item in listed.json()["items"]] == [condition_type["id"]]
    assert _row_count() == rows_before


def test_unknown_uuid_is_404(as_roles):
    response = as_roles(CT_READ).get(f"{CONDITION_TYPES}/{uuid4()}")

    assert response.status_code == 404


def test_malformed_uuid_is_422(as_roles):
    response = as_roles(CT_READ).get(f"{CONDITION_TYPES}/no-es-un-uuid")

    assert response.status_code == 422


def test_listing_includes_version(as_roles, condition_type):
    items = as_roles(CT_READ).get(CONDITION_TYPES).json()["items"]

    assert items[0]["version"] == 1
