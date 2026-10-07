"""Las 19 rutas de `contracts/rest-api.md` con su permiso (T028)."""

from __future__ import annotations

from uuid import uuid4

C = "/api/v1/companies/{company}"
P = C + "/purchases/{purchase}"

ROUTES: list[tuple[str, str, str]] = [
    ("POST", C + "/purchases", "perm:purchase:purchases:create"),
    ("GET", C + "/purchases", "perm:purchase:purchases:read"),
    ("GET", P, "perm:purchase:purchases:read"),
    ("PUT", P, "perm:purchase:purchases:update"),
    ("POST", P + "/details", "perm:purchase:purchase_details:create"),
    ("PUT", P + "/details/{detail}", "perm:purchase:purchase_details:update"),
    ("DELETE", P + "/details/{detail}?version=1", "perm:purchase:purchase_details:delete"),
    ("GET", P + "/details", "perm:purchase:purchase_details:read"),
    ("POST", P + "/confirmation", "perm:purchase:purchases:update"),
    ("POST", P + "/cancellation", "perm:purchase:purchases:delete"),
    ("GET", P + "/operations", "perm:purchase:purchase_operations:read"),
    ("GET", C + "/purchase-operations/{operation}", "perm:purchase:purchase_operations:read"),
    ("POST", P + "/lifecycle-events", "perm:purchase:purchase_lifecycle_events:create"),
    ("GET", P + "/lifecycle-events", "perm:purchase:purchase_lifecycle_events:read"),
    ("POST", C + "/purchase-sequences", "perm:purchase:purchase_sequences:create"),
    ("GET", C + "/purchase-sequences", "perm:purchase:purchase_sequences:read"),
    ("GET", C + "/purchase-sequences/{sequence}", "perm:purchase:purchase_sequences:read"),
    ("PUT", C + "/purchase-sequences/{sequence}", "perm:purchase:purchase_sequences:update"),
    ("POST", C + "/purchase-sequences/{sequence}/deactivate", "perm:purchase:purchase_sequences:update"),
    ("POST", C + "/purchase-sequences/{sequence}/reactivate", "perm:purchase:purchase_sequences:update"),
]


def fill(path: str, company=None) -> str:
    return path.format(
        company=company or uuid4(), purchase=uuid4(), detail=uuid4(), operation=uuid4(), sequence=uuid4()
    )
