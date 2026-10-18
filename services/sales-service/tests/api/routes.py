"""Las 18 rutas de `contracts/rest-api.md` con su permiso (T030) y las agregaciones de la spec 023 (SAL-R1, SAL-R2)."""

from __future__ import annotations

from uuid import uuid4

C = "/api/v1/companies/{company}"
S = C + "/sales/{sale}"

ROUTES: list[tuple[str, str, str]] = [
    ("POST", C + "/sales", "perm:sales:sales:create"),
    ("GET", C + "/sales", "perm:sales:sales:read"),
    ("GET", S, "perm:sales:sales:read"),
    ("PUT", S, "perm:sales:sales:update"),
    ("POST", S + "/details", "perm:sales:sale_details:create"),
    ("PUT", S + "/details/{detail}", "perm:sales:sale_details:update"),
    ("DELETE", S + "/details/{detail}?version=1", "perm:sales:sale_details:delete"),
    ("GET", S + "/details", "perm:sales:sale_details:read"),
    ("GET", S + "/availability", "perm:sales:sales:read"),
    ("POST", S + "/confirmation", "perm:sales:sales:update"),
    ("POST", S + "/cancellation", "perm:sales:sales:delete"),
    ("GET", S + "/operations", "perm:sales:sale_operations:read"),
    ("GET", C + "/sale-operations/{operation}", "perm:sales:sale_operations:read"),
    ("POST", C + "/sale-sequences", "perm:sales:sale_sequences:create"),
    ("GET", C + "/sale-sequences", "perm:sales:sale_sequences:read"),
    ("GET", C + "/sale-sequences/{sequence}", "perm:sales:sale_sequences:read"),
    ("PUT", C + "/sale-sequences/{sequence}", "perm:sales:sale_sequences:update"),
    ("POST", C + "/sale-sequences/{sequence}/deactivate", "perm:sales:sale_sequences:update"),
    ("POST", C + "/sale-sequences/{sequence}/reactivate", "perm:sales:sale_sequences:update"),
    # Spec 023 (contracts/owner-extensions.md): agregaciones de solo lectura para business-reporting-service.
    ("GET", C + "/sales-aggregates/by-product?date_from=2026-01-01&date_to=2026-01-31", "perm:sales:sales:read"),
    ("GET", C + "/sales-aggregates/by-branch?date_from=2026-01-01&date_to=2026-01-31", "perm:sales:sales:read"),
]


def fill(path: str, company=None) -> str:
    return path.format(
        company=company or uuid4(), sale=uuid4(), detail=uuid4(), operation=uuid4(), sequence=uuid4()
    )
