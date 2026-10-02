"""Prueba conductual de no recursión con Operational Context (T045; C-07, FR-009, FR-029).

Con el doble espía del puerto `MembershipResolver`, ninguna lectura de la Fase A
ni de la Fase B (ni el cierre de perfil) lo invoca; la confirmación sí.
"""

from __future__ import annotations

from tests.phase_b import create_organization, create_person, profile_payload, profile_url


def _all_get_paths(api) -> list[str]:
    paths = api.get("/openapi.json").json()["paths"]
    return sorted(path for path, item in paths.items() if "get" in item and path.startswith("/api/v1/"))


def test_reads_and_close_never_call_operational_context(api, fake_membership) -> None:
    organization = create_organization(api)
    person = create_person(api)
    url = profile_url("organization", organization["id"])
    profile = api.post(url, json=profile_payload()).json()
    fake_membership.calls.clear()

    values = {
        "organization_identity_id": organization["id"],
        "person_identity_id": person["id"],
        "profile_id": profile["id"],
    }
    paths = _all_get_paths(api)
    assert paths, "No se encontraron rutas GET"
    for path in paths:
        concrete = path
        for name in (
            "organization_identity_id", "person_identity_id", "profile_id", "rule_id",
            "contact_id", "sector_id", "assignment_id", "representative_id", "identity_id",
        ):
            concrete = concrete.replace("{" + name + "}", values.get(name, organization["id"]))
        api.get(concrete)

    api.post(f"{url}:close", json={"version": profile["version"]})

    assert fake_membership.calls == []

    # Control positivo: la confirmación de un perfil sí consulta Operational Context.
    api.post(url, json=profile_payload())
    assert len(fake_membership.calls) == 1
