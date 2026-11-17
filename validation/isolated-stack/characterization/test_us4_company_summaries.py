"""Historia 4: resumen de empresas de un usuario con 100 empresas (spec 025, T015).

Lo grabado con las lecturas por HTTP debe repetirse igual con las lecturas por contrato. Con ``contract``,
``GET /company-summaries`` no hace **ninguna** solicitud a otros servicios y responde en menos de 1 s con
``page_size=100`` (SC-003).

Mundo propio de cada ejecución (datos ficticios): ``consulta.test`` es miembro activo de 101 empresas nuevas
(una con la membresía inactivada, que no debe aparecer, y otra con la empresa inactivada, que aparece con
``company_status=INACTIVE``); se observan ``page_size=100`` y la segunda página con ``page_size=60``. Al terminar se inactivan sus membresías para que la siguiente ejecución vea solo las suyas.

El orden de las empresas es el de su UUID (aleatorio): los casos se ordenan por etiqueta. La razón social nula
(Operational Context o Party Identity responden 403/404) no se puede provocar con datos válidos en la pila; la cubren
las pruebas de paridad de CR (T062).
"""

from __future__ import annotations

import json
import time

import pytest
from conftest import URLS, expect
from support import Normalizer, RequestWindow, response_case

OC, CR, PI = (URLS[k] for k in ("operational_context", "commercial_relationship", "party_identity"))
CONTAINERS = tuple(f"sio-it-{name}-service" for name in ("commercial-relationship", "operational-context", "party-identity"))
USER = "consulta.test"
COMPANIES = 100
LIMIT_MS = 1000


@pytest.fixture(scope="module")
def world(seed, users, run_id):
    admin = users("admin.test")
    colombia = expect(admin.get(f"{URLS['geography']}/global-countries", params={"iso3_code": "COL"}))["items"][0]["id"]
    person = seed.party(admin, colombia, "PERSON", "CC", "person-identities", {
        "identification_country_id": colombia, "identification_type": "CC",
        "first_name": f"CONSULTAUS4{run_id}", "last_name": "DATO FICTICIO", "birth_date": "1990-01-01"})
    memberships, names = [], {}
    for index in range(COMPANIES + 1):
        legal_name = f"EMPRESA FICTICIA US4 {index:03d} {run_id} (DATO FICTICIO DE VALIDACION)"
        organization = seed.party(admin, colombia, "ORGANIZATION", "NIT", "organization-identities", {
            "country_id": colombia, "identification_type": "NIT", "legal_name": legal_name})
        company = expect(admin.post(f"{OC}/companies", json={"organization_identity_id": organization}))["id"]
        member = expect(admin.post(f"{OC}/companies/{company}/application-users", json={
            "username": USER, "person_identity_id": person, "display_name": f"{USER} (ficticio {run_id})"}))
        memberships.append(member)
        names[company] = f"<empresa_{index:03d}>"
    # Una membresía inactiva: su empresa no aparece en el resumen.
    _deactivate(admin, memberships[-1])
    # Una empresa inactiva (con membresía activa): aparece con `company_status=INACTIVE`.
    inactive = next(iter(names))
    current = expect(admin.get(f"{OC}/companies/{inactive}"))
    expect(admin.post(f"{OC}/companies/{inactive}/deactivate", json={"version": current["version"]}))
    yield {"names": names, "run": run_id, "total": COMPANIES}
    for member in memberships[:-1]:
        _deactivate(admin, member)


def _deactivate(admin, member):
    current = expect(admin.get(f"{OC}/application-users/{member['id']}"))
    if current["status"] == "ACTIVE":
        expect(admin.post(f"{OC}/application-users/{member['id']}/deactivate", json={"version": current["version"]}))


def _observe(action):
    time.sleep(1.5)
    window = RequestWindow(CONTAINERS, sources=("sio-it-commercial-relationship-service",))
    started = time.perf_counter()
    response = action()
    elapsed = (time.perf_counter() - started) * 1000
    window.close()
    return response, window.counts(), elapsed


def _case(world, response):
    """Empresas por razón social (su etiqueta), ordenadas por ella: el orden por UUID cambia en cada ejecución."""
    body = response.json() if response.status_code == 200 else None
    if body is None:
        return response_case(response, Normalizer(run=world["run"]))
    items = []
    for item in body["items"]:
        label = world["names"].get(item["company_id"], "<empresa_ajena>")
        name = item["legal_name"]
        items.append({**item, "company_id": label,
                      "legal_name": None if name is None else name.replace(world["run"], "<run>")})
    items.sort(key=lambda item: item["company_id"])
    if body["page"] > 1:
        # Qué empresas caen en la segunda página depende de los UUID: se comprueba que cada razón social sea la de
        # su empresa y se guarda solo su forma.
        for item in items:
            assert item["legal_name"] is None or item["company_id"][1:-1].split("_")[1] in item["legal_name"]
        items = [{**item, "company_id": "<empresa>", "company_status": "<estado>",
                  "legal_name": None if item["legal_name"] is None else "<razon_social>"} for item in items]
    return {"status": response.status_code,
            "body": {**{k: v for k, v in body.items() if k != "items"}, "items": items}}


def _internal(requests):
    return {key: value for key, value in requests.items() if not key.startswith("commercial-relationship ")}


def _summaries(client, **params):
    return client.get(f"{CR}/company-summaries", params=params)


@pytest.mark.parametrize(("name", "params"), [
    ("cien_empresas", {"page": 1, "page_size": 100}),
    ("segunda_pagina", {"page": 2, "page_size": 60}),
])
def test_company_summaries(world, users, book, reads, name, params):
    client = users(USER)
    response, requests, elapsed = _observe(lambda: _summaries(client, **params))
    assert response.status_code == 200, response.text[:300]
    case = _case(world, response)
    assert case["body"]["total_records"] == world["total"]
    assert all(item["company_id"] != "<empresa_ajena>" for item in case["body"]["items"])
    book.check(name, json.loads(json.dumps(case, ensure_ascii=False)), requests=requests)
    if reads == "contract":
        assert not _internal(requests), f"{name}: solicitudes a otros servicios con contract: {_internal(requests)}"
        if name == "cien_empresas":
            # SC-003: se mide con una segunda llamada ya caliente (la primera abre las conexiones).
            again, _, warm = _observe(lambda: _summaries(client, **params))
            assert again.status_code == 200
            assert warm < LIMIT_MS, f"company-summaries tardó {warm:.0f} ms (> {LIMIT_MS} ms)"
            print(f"\ncompany-summaries 100 empresas: {elapsed:.0f} ms (frío), {warm:.0f} ms (caliente)")
