"""Autorización de perfiles de contacto (T044, T050; RC-01, RC-14, FR-008)."""

from __future__ import annotations

import pytest

ID = "00000000-0000-0000-0000-000000000001"

OPERATIONS = [
    (kind, method, path, body, action)
    for kind in ("person", "organization")
    for method, path, body, action in (
        ("GET", f"/api/v1/{kind}-identities/{ID}/contact-profile", None, "read"),
        ("GET", f"/api/v1/{kind}-identities/{ID}/contact-profile/versions", None, "read"),
        ("GET", f"/api/v1/{kind}-contact-profiles/{ID}", None, "read"),
        ("POST", f"/api/v1/{kind}-identities/{ID}/contact-profile", {}, "create"),
        ("POST", f"/api/v1/{kind}-identities/{ID}/contact-profile:close", {"version": 1}, "delete"),
    )
]
IDS = [f"{method} {path.replace(ID, '{id}')}" for _, method, path, _, _ in OPERATIONS]
ACTIONS = ("read", "create", "update", "delete")


@pytest.mark.parametrize(("kind", "method", "path", "body", "action"), OPERATIONS, ids=IDS)
def test_without_token_is_unauthenticated(anonymous, kind, method, path, body, action) -> None:
    assert anonymous.request(method, path, json=body).status_code == 401


@pytest.mark.parametrize(("kind", "method", "path", "body", "action"), OPERATIONS, ids=IDS)
def test_without_exact_permission_is_forbidden(api_as, kind, method, path, body, action) -> None:
    resource = f"{kind}_contact_profiles"
    others = [f"perm:party-identity:{resource}:{other}" for other in ACTIONS if other != action]

    assert api_as(*others).request(method, path, json=body).status_code == 403


@pytest.mark.parametrize(("kind", "method", "path", "body", "action"), OPERATIONS, ids=IDS)
def test_with_exact_permission_passes_authorization(api_as, kind, method, path, body, action) -> None:
    response = api_as(f"perm:party-identity:{kind}_contact_profiles:{action}").request(method, path, json=body)

    assert response.status_code not in {401, 403}


@pytest.mark.parametrize("kind", ["person", "organization"])
def test_identity_read_permission_does_not_grant_contact_profile(api_as, kind) -> None:
    """RC-14: leer la identidad no concede leer su perfil de contacto."""
    reader = api_as(f"perm:party-identity:{kind}_identities:read")

    assert reader.get(f"/api/v1/{kind}-identities/{ID}/contact-profile").status_code == 403
    assert reader.get(f"/api/v1/{kind}-contact-profiles/{ID}").status_code == 403
