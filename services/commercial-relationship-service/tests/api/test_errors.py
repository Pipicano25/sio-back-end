"""Formato de errores RFC 9457 con `code` y `trace_id` (FR-003, FR-004, R-15)."""

from __future__ import annotations

from uuid import uuid4

from tests.api.helpers import code_of, product_body


def _assert_problem(response, status: int, code: str) -> dict:
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"] == f"COMMERCIAL_RELATIONSHIP.{code}"
    assert body["status"] == status
    assert body["trace_id"] and body["trace_id"] == response.headers["x-trace-id"]
    return body


def test_malformed_json_is_400(as_user, company):
    response = as_user("admin.test").post(
        f"/api/v1/companies/{company}/company-products",
        content=b"{no-json",
        headers={"content-type": "application/json"},
    )
    _assert_problem(response, 400, "MALFORMED_REQUEST")


def test_unknown_field_is_422_with_field(as_user, company, fake_catalog):
    product = fake_catalog.add(uuid4())
    response = as_user("admin.test").post(
        f"/api/v1/companies/{company}/company-products",
        json=product_body(product, created_by="intruso"),
    )
    body = _assert_problem(response, 422, "VALIDATION_ERROR")
    assert body["errors"][0]["field"] == "created_by"


def test_unknown_route_is_404(as_user):
    _assert_problem(as_user("admin.test").get("/api/v1/no-existe"), 404, "NOT_FOUND")


def test_method_not_allowed_is_405(as_user):
    response = as_user("admin.test").request("DELETE", f"/api/v1/company-products/{uuid4()}")
    _assert_problem(response, 405, "METHOD_NOT_ALLOWED")


def test_unauthenticated_is_401_problem(as_token, company):
    _assert_problem(as_token(None).get(f"/api/v1/companies/{company}/company-products"), 401, "UNAUTHENTICATED")


def test_dependency_unavailable_has_dependency_extension(as_user, company, fake_oc):
    fake_oc.access_unavailable = True
    response = as_user("admin.test").get(f"/api/v1/companies/{company}/company-products")
    body = _assert_problem(response, 503, "DEPENDENCY_UNAVAILABLE")
    assert body["dependency"] == "operational-context"
    assert "FAKE_UNAVAILABLE" not in response.text  # la causa interna nunca se expone


def test_unhandled_error_is_500_without_details(as_user, company, app, monkeypatch):
    class Broken:
        def check_company_access(self, company_id):
            raise RuntimeError("detalle interno secreto")

    monkeypatch.setattr(app.state, "access_directory_factory", lambda request: Broken())
    response = as_user("admin.test").get(f"/api/v1/companies/{company}/company-products")
    assert response.status_code == 500
    assert code_of(response) == "INTERNAL_ERROR"
    assert "secreto" not in response.text
