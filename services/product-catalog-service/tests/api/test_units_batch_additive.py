"""PC-3: `code` y `name` aditivos en el lote de unidades (spec 022, FR-022-84, FR-022-87; T030, CP-87)."""

from __future__ import annotations

from uuid import uuid4

from tests import factories

URL = "/api/v1/units-of-measure/batch-lookup"


def test_units_batch_adds_code_and_name_keeping_previous_fields(api_as, session_factory) -> None:
    unit = factories.unit(session_factory, "TAB", allows_decimals=True)
    missing = uuid4()

    response = api_as("units-of-measure:read").post(URL, json={"ids": [str(unit.id), str(missing)]})

    assert response.status_code == 200
    found, absent = response.json()["items"]
    assert found == {
        "id": str(unit.id),
        "found": True,
        "status": "ACTIVE",
        "measurement_type": "UNIT",
        "allows_decimals": True,
        "code": "TAB",
        "name": "Tab",
    }
    assert absent == {
        "id": str(missing),
        "found": False,
        "status": None,
        "measurement_type": None,
        "allows_decimals": None,
        "code": None,
        "name": None,
    }
