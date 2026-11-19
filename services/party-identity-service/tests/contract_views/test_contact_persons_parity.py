"""Paridad de ``contract.v1_organization_contact_persons`` con ``GET /organization-contact-persons/{id}`` (spec 025, T059).

- Cada columna de la vista coincide con el mismo campo del GET, para contactos activos e inactivos, con y sin persona
  vinculada y de dos organizaciones; un contacto inexistente no tiene fila (``404`` en la API).
- La vista publica solo ``id``, ``organization_identity_id``, ``person_identity_id`` e ``is_active``: ni cargo, ni
  correo, ni teléfono, ni ``is_primary``.

El rol lector de Commercial Relationship (``contract/grants.yaml``) lo prueba ``test_identity_views_parity.py``.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import text

from tests.phase_b import create_organization, create_person

COLUMNS = ("id", "organization_identity_id", "person_identity_id", "is_active")


def _view_row(connection, contact_id: str) -> dict | None:
    row = connection.execute(
        text("SELECT * FROM contract.v1_organization_contact_persons WHERE id = :id"), {"id": contact_id}
    ).mappings().first()
    if row is None:
        return None
    return {key: (str(value) if value is not None and not isinstance(value, (str, bool)) else value)
            for key, value in row.items()}


def _create_contact(api, organization: dict, **payload) -> dict:
    response = api.post(f"/api/v1/organization-identities/{organization['id']}/contact-persons", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_contact_person_view_matches_get(api, test_engine):
    first = create_organization(api, "900000001-2")
    second = create_organization(api, "900000002-1")
    person = create_person(api, "1000000001")
    contacts = [
        _create_contact(api, first, person_identity_id=person["id"], position="Gerente", is_primary=True),
        _create_contact(api, first, phone="+57 601 555 0101"),
        _create_contact(api, second, email="contacto@empresa-ficticia.co"),
    ]
    closed = contacts[1]
    response = api.post(f"/api/v1/organization-contact-persons/{closed['id']}:deactivate",
                        json={"version": closed["version"]})
    assert response.status_code == 200, response.text

    observed_active = set()
    with test_engine.connect() as connection:
        for created in contacts:
            body = api.get(f"/api/v1/organization-contact-persons/{created['id']}").json()
            view = _view_row(connection, created["id"])
            assert tuple(view) == COLUMNS
            for column in COLUMNS:
                assert view[column] == body[column], column
            observed_active.add(view["is_active"])

        missing = str(uuid4())
        assert api.get(f"/api/v1/organization-contact-persons/{missing}").status_code == 404
        assert _view_row(connection, missing) is None

    assert observed_active == {True, False}


def test_contact_person_view_does_not_publish_private_fields(test_engine):
    with test_engine.connect() as connection:
        columns = connection.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_schema = 'contract' "
                 "AND table_name = 'v1_organization_contact_persons' ORDER BY ordinal_position")
        ).scalars().all()
    assert tuple(columns) == COLUMNS
