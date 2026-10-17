"""`Idempotency-Key` documentada en OpenAPI y con el mismo comportamiento en ejecución.

La dependencia leía la cabecera de `request.headers`, así que OpenAPI no la publicaba y Swagger no permitía
enviarla (la confirmación respondía `422 IDEMPOTENCY_KEY_REQUIRED` desde `/docs`). Ahora se declara con `Header`
y `openapi.py` la marca obligatoria; la validación propia y sus códigos de error no cambian (contrato 015).
"""

from __future__ import annotations

import pytest

from tests.conftest import base, new_key

IDEMPOTENT = {
    ("post", "/api/v1/companies/{company_id}/sales/{sale_id}/confirmation"),
    ("post", "/api/v1/companies/{company_id}/sales/{sale_id}/cancellation"),
}


def _header(operation: dict) -> list[dict]:
    return [p for p in operation.get("parameters", []) if p["in"] == "header" and p["name"] == "Idempotency-Key"]


def test_openapi_documents_the_header_exactly_where_it_is_required(test_client) -> None:
    schema = test_client.get("/openapi.json").json()
    found = set()
    for path, item in schema["paths"].items():
        for method, operation in item.items():
            if _header(operation):
                found.add((method, path))
    assert found == IDEMPOTENT  # ni falta en una operación que la exige ni sobra en otras

    for method, path in IDEMPOTENT:
        [parameter] = _header(schema["paths"][path][method])
        assert parameter["in"] == "header" and parameter["required"] is True
        assert parameter["schema"]["type"] == "string"
        assert (parameter["schema"]["minLength"], parameter["schema"]["maxLength"]) == (1, 150)
        assert "anyOf" not in parameter["schema"]  # sin la variante `null` del tipo opcional de Python
        assert "idempotencia" in parameter["description"].lower()
        # la seguridad y las respuestas de error no cambian
        operation = schema["paths"][path][method]
        assert operation["security"] == [{"BearerAuth": []}]
        assert {"401", "403", "409", "422", "503"} <= set(operation["responses"])


def test_the_documented_header_is_what_the_service_reads(seller, world, make_sequence, make_draft) -> None:
    """Lo que Swagger envía (la cabecera con el nombre documentado) es lo que el servicio usa como clave."""
    make_sequence()
    draft = make_draft()
    key = new_key()
    url = f"{base(world)}/sales/{draft['id']}/confirmation"
    first = seller.post(url, json={"version": 1}, headers={"Idempotency-Key": key})
    assert first.status_code == 200, first.text
    again = seller.post(url, json={"version": 1}, headers={"idempotency-key": key})  # sin distinguir mayúsculas
    assert again.status_code == 200 and again.json()["number"] == first.json()["number"]


@pytest.mark.parametrize("action", ["confirmation", "cancellation"])
@pytest.mark.parametrize("headers", [{}, {"Idempotency-Key": ""}, {"Idempotency-Key": "   "}])
def test_missing_header_keeps_the_contract_error(seller, world, make_draft, action, headers) -> None:
    draft = make_draft()
    body = {"version": 1} if action == "confirmation" else {"version": 1, "reason": "Error de registro"}
    response = seller.post(f"{base(world)}/sales/{draft['id']}/{action}", json=body, headers=headers)
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "SALES.VALIDATION_ERROR"
    assert response.json()["errors"] == [
        {"field": "Idempotency-Key", "message": "La cabecera Idempotency-Key es obligatoria.",
         "code": "IDEMPOTENCY_KEY_REQUIRED"}
    ]
    assert seller.get(f"{base(world)}/sales/{draft['id']}").json()["status"] == "DRAFT"


@pytest.mark.parametrize("key", ["con espacio", "x" * 151])
def test_invalid_format_keeps_the_contract_error(seller, world, make_draft, key) -> None:
    draft = make_draft()
    response = seller.post(
        f"{base(world)}/sales/{draft['id']}/confirmation", json={"version": 1}, headers={"Idempotency-Key": key}
    )
    assert response.status_code == 422
    [error] = response.json()["errors"]
    assert (error["field"], error["code"]) == ("Idempotency-Key", "INVALID_FORMAT")


def test_authentication_and_authorization_are_still_checked_first(as_token, as_user, world, make_draft) -> None:
    draft = make_draft()
    url = f"{base(world)}/sales/{draft['id']}/confirmation"
    # sin token: 401 aunque falte la cabecera (no revela reglas de validación)
    assert as_token(None).post(url, json={"version": 1}).status_code == 401
    # sin permiso de confirmar: 403 aunque falte la cabecera
    response = as_user("consulta.test").post(url, json={"version": 1})
    assert response.status_code == 403 and response.json()["code"] == "SALES.FORBIDDEN"
