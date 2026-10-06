"""La API no modifica ni elimina eventos (US5; RC-02; T049)."""

from __future__ import annotations

import pytest

from tests.api.helpers import register


@pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE"])
def test_mutation_methods_are_not_allowed(as_user, emitter, company, method: str) -> None:
    event = register(emitter, company_id=str(company))
    paths = [
        f"/api/v1/companies/{company}/audit-events/{event['id']}",
        f"/api/v1/platform-audit-events/{event['id']}",
        "/api/v1/audit-events",
    ]

    for client in (as_user("admin.test"), emitter):
        for path in paths:
            response = client.request(method, path, json={})
            assert response.status_code == 405, (method, path)


def test_openapi_publishes_no_mutation(as_user) -> None:
    schema = as_user("admin.test").get("/openapi.json").json()

    for path, operations in schema["paths"].items():
        assert not {"put", "patch", "delete"} & set(operations), path
