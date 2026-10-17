"""`Idempotency-Key` documentada en OpenAPI y con el mismo comportamiento en ejecución.

La dependencia leía la cabecera de `request.headers`, así que OpenAPI no la publicaba y Swagger no permitía
enviarla (confirmación, recepción y anulación respondían `422 IDEMPOTENCY_KEY_REQUIRED` desde `/docs`). Ahora se
declara con `Header` y `openapi.py` la marca obligatoria; la validación propia y sus códigos de error no cambian.
"""

from __future__ import annotations

import pytest

from tests.conftest import base, new_key

IDEMPOTENT = {
    ("post", "/api/v1/companies/{company_id}/purchases/{purchase_id}/confirmation"),
    ("post", "/api/v1/companies/{company_id}/purchases/{purchase_id}/receipt"),
    ("post", "/api/v1/companies/{company_id}/purchases/{purchase_id}/cancellation"),
}
BODIES = {
    "confirmation": {"version": 1},
    "receipt": {"version": 1, "full_receipt_confirmed": True},
    "cancellation": {"version": 1, "reason": "Error de registro"},
}


def _header(operation: dict) -> list[dict]:
    return [p for p in operation.get("parameters", []) if p["in"] == "header" and p["name"] == "Idempotency-Key"]


def test_openapi_documents_the_header_exactly_where_it_is_required(test_client) -> None:
    schema = test_client.get("/openapi.json").json()
    found = {(method, path) for path, item in schema["paths"].items() for method, operation in item.items() if _header(operation)}
    assert found == IDEMPOTENT  # ni falta en una operación que la exige ni sobra en otras

    for method, path in IDEMPOTENT:
        operation = schema["paths"][path][method]
        [parameter] = _header(operation)
        assert parameter["in"] == "header" and parameter["required"] is True
        assert parameter["schema"]["type"] == "string" and "anyOf" not in parameter["schema"]
        assert (parameter["schema"]["minLength"], parameter["schema"]["maxLength"]) == (1, 150)
        assert "idempotencia" in parameter["description"].lower()
        assert operation["security"] == [{"BearerAuth": []}]  # la seguridad no cambia
        assert {"401", "403", "409", "422", "503"} <= set(operation["responses"])


def test_the_documented_header_is_what_the_service_reads(buyer, world, make_sequence, make_draft) -> None:
    make_sequence()
    draft = make_draft()
    key = new_key()
    url = f"{base(world)}/purchases/{draft['id']}/confirmation"
    first = buyer.post(url, json={"version": 1}, headers={"Idempotency-Key": key})
    assert first.status_code == 200, first.text
    again = buyer.post(url, json={"version": 1}, headers={"idempotency-key": key})  # sin distinguir mayúsculas
    assert again.status_code == 200 and again.json()["number"] == first.json()["number"]


@pytest.mark.parametrize("action", sorted(BODIES))
@pytest.mark.parametrize("headers", [{}, {"Idempotency-Key": ""}, {"Idempotency-Key": "   "}])
def test_missing_header_keeps_the_contract_error(buyer, world, make_draft, action, headers) -> None:
    draft = make_draft()
    response = buyer.post(f"{base(world)}/purchases/{draft['id']}/{action}", json=BODIES[action], headers=headers)
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "PURCHASE.VALIDATION_ERROR"
    assert response.json()["errors"] == [
        {"field": "Idempotency-Key", "message": "La cabecera Idempotency-Key es obligatoria.",
         "code": "IDEMPOTENCY_KEY_REQUIRED"}
    ]
    assert buyer.get(f"{base(world)}/purchases/{draft['id']}").json()["status"] == "DRAFT"


@pytest.mark.parametrize("key", ["con espacio", "x" * 151])
def test_invalid_format_keeps_the_contract_error(buyer, world, make_draft, key) -> None:
    draft = make_draft()
    response = buyer.post(f"{base(world)}/purchases/{draft['id']}/confirmation", json={"version": 1},
                          headers={"Idempotency-Key": key})
    assert response.status_code == 422
    [error] = response.json()["errors"]
    assert (error["field"], error["code"]) == ("Idempotency-Key", "INVALID_FORMAT")


def test_authentication_and_authorization_are_still_checked_first(as_token, as_user, world, make_draft) -> None:
    draft = make_draft()
    url = f"{base(world)}/purchases/{draft['id']}/confirmation"
    assert as_token(None).post(url, json={"version": 1}).status_code == 401  # sin token: 401 aunque falte la cabecera
    response = as_user("consulta.test").post(url, json={"version": 1})  # sin permiso: 403 aunque falte la cabecera
    assert response.status_code == 403 and response.json()["code"] == "PURCHASE.FORBIDDEN"
