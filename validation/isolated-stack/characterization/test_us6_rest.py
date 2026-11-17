"""Historia 6: resto de lecturas entre servicios (spec 025, T017).

Lo grabado con las lecturas por HTTP debe repetirse igual con las lecturas por contrato. Con ``contract``, cada caso
no hace **ninguna** de las solicitudes de lectura migradas; las que siguen por API (FR-036) se permiten por nombre.

Mundo propio de cada ejecución (datos ficticios). Un caso por lectura:

- empresa y sucursal con ubicación válida e inválida (OC → Geography y OC → Party Identity);
- usuario operativo nuevo (OC → Party Identity, persona);
- perfil de contacto de una organización con ubicación (PI → Geography);
- un reporte JSON de Business Reporting (BRS → Operational Context);
- los casos de catálogo, Commercial Relationship y PIQ (ver el final del archivo).
"""

from __future__ import annotations

import json
import time
from uuid import uuid4

import pytest
from conftest import URLS, expect, outages_only
from support import Normalizer, RequestWindow, outage_case, owner_database_down, response_case

GEO, OC, PI = (URLS[k] for k in ("geography", "operational_context", "party_identity"))
PC, CR, PR = (URLS[k] for k in ("product_catalog", "commercial_relationship", "payment_reference"))
PIQ, BRS = URLS["product_inventory_query"], URLS["business_reporting"]
OWNERS = ("geography", "party-identity", "operational-context", "product-catalog", "commercial-relationship",
          "payment-reference", "inventory", "purchase", "sales")


@pytest.fixture(scope="module")
def world(seed, users, run_id):
    admin = users("admin.test")
    colombia = expect(admin.get(f"{GEO}/global-countries", params={"iso3_code": "COL"}))["items"][0]["id"]
    city = next(item for item in expect(admin.get(f"{GEO}/global-cities", params={
        "country_id": colombia, "status": "ACTIVE", "page_size": 100}))["items"] if item.get("administrative_division_id"))
    company = seed.company(admin, colombia, f"US6{run_id}")
    member = seed.member(admin, colombia, company, "admin.test")
    organization = seed.party(admin, colombia, "ORGANIZATION", "NIT", "organization-identities", {
        "country_id": colombia, "identification_type": "NIT",
        "legal_name": f"ORGANIZACION FICTICIA US6 {run_id} (DATO FICTICIO DE VALIDACION)"})
    person = seed.party(admin, colombia, "PERSON", "CC", "person-identities", {
        "identification_country_id": colombia, "identification_type": "CC",
        "first_name": f"PERSONAUS6{run_id}", "last_name": "DATO FICTICIO", "birth_date": "1990-01-01"})
    location = {"country_id": colombia, "administrative_division_id": city["administrative_division_id"], "city_id": city["id"]}
    aliases = {colombia: "colombia", city["id"]: "ciudad", city["administrative_division_id"]: "division",
               company: "empresa", member: "admin", organization: "organizacion", person: "persona"}
    state = {"company": company, "member": member, "organization": organization, "person": person,
             "location": location, "aliases": aliases, "run": run_id, "memberships": []}
    yield state
    # `consulta.test` debe quedar solo en sus empresas: el resumen de la Historia 4 cuenta sus membresías activas.
    for member_id in state["memberships"]:
        current = expect(admin.get(f"{OC}/application-users/{member_id}"))
        if current["status"] == "ACTIVE":
            expect(admin.post(f"{OC}/application-users/{member_id}/deactivate", json={"version": current["version"]}))


def _observe(source: str, action):
    # Los registros de acceso llegan con retraso: se espera a que salgan los de la preparación anterior.
    time.sleep(1.5)
    window = RequestWindow(tuple(f"sio-it-{name}-service" for name in OWNERS), sources=(f"sio-it-{source}-service",))
    response = action()
    window.close()
    return response, window.counts()


def _check(world, book, reads, name, response, requests, status, *, allowed=()):
    """Compara con lo grabado y, con ``contract``, exige 0 solicitudes salvo las que siguen por API (``allowed``)."""
    assert response.status_code == status, f"{name}: {response.status_code} {response.text[:300]}"
    case = response_case(response, Normalizer(world["aliases"], run=world["run"]))
    body = case.get("body")
    if isinstance(body, dict) and isinstance(body.get("branches"), list):
        # El orden de las sucursales del resumen no está definido (también por API): se ordenan por etiqueta.
        body["branches"].sort(key=lambda item: str(item.get("branch_id")))
    book.check(name, json.loads(json.dumps(case, ensure_ascii=False)), requests=requests)
    if reads == "contract":
        unexpected = {key: value for key, value in requests.items() if not any(fragment in key for fragment in allowed)}
        assert not unexpected, f"{name}: solicitudes de lectura con contract: {unexpected}"
    return case


# --------------------------------------------------------------------------- Operational Context


def _organization(admin, seed, run_id, label):
    colombia = expect(admin.get(f"{GEO}/global-countries", params={"iso3_code": "COL"}))["items"][0]["id"]
    return seed.party(admin, colombia, "ORGANIZATION", "NIT", "organization-identities", {
        "country_id": colombia, "identification_type": "NIT",
        "legal_name": f"EMPRESA FICTICIA US6 {label} {run_id} (DATO FICTICIO DE VALIDACION)"})


def test_empresa_con_ubicacion(world, users, seed, book, reads):
    admin = users("admin.test")
    organization = _organization(admin, seed, world["run"], "UBICADA")
    world["aliases"][organization] = "organizacion_empresa"
    response, requests = _observe("operational-context", lambda: admin.post(f"{OC}/companies", json={
        "organization_identity_id": organization, **world["location"]}))
    _check(world, book, reads, "empresa_con_ubicacion", response, requests, 201)


def test_empresa_con_ciudad_inexistente(world, users, seed, book, reads):
    admin = users("admin.test")
    organization = _organization(admin, seed, world["run"], "SIN CIUDAD")
    world["aliases"][organization] = "organizacion_sin_ciudad"
    response, requests = _observe("operational-context", lambda: admin.post(f"{OC}/companies", json={
        "organization_identity_id": organization, **world["location"], "city_id": str(uuid4())}))
    _check(world, book, reads, "empresa_ciudad_inexistente", response, requests, 422)


def test_sucursal_con_ubicacion(world, users, book, reads):
    admin = users("admin.test")
    response, requests = _observe("operational-context", lambda: admin.post(
        f"{OC}/companies/{world['company']}/branches",
        json={"code": f"G1{world['run']}", "name": f"Sucursal ficticia G1 {world['run']}", **world["location"]}))
    _check(world, book, reads, "sucursal_con_ubicacion", response, requests, 201)


def test_sucursal_con_division_inexistente(world, users, book, reads):
    admin = users("admin.test")
    response, requests = _observe("operational-context", lambda: admin.post(
        f"{OC}/companies/{world['company']}/branches",
        json={"code": f"G2{world['run']}", "name": f"Sucursal ficticia G2 {world['run']}", **world["location"],
              "administrative_division_id": str(uuid4())}))
    _check(world, book, reads, "sucursal_division_inexistente", response, requests, 422)


def test_usuario_operativo_nuevo(world, users, book, reads):
    admin = users("admin.test")
    company = world["company"]
    response, requests = _observe("operational-context", lambda: admin.post(
        f"{OC}/companies/{company}/application-users",
        json={"username": "consulta.test", "person_identity_id": world["person"],
              "display_name": f"consulta.test (ficticio {world['run']})"}))
    if response.status_code == 201:
        world["memberships"].append(response.json()["id"])
    _check(world, book, reads, "usuario_operativo_nuevo", response, requests, 201)


# --------------------------------------------------------------------------- Party Identity


def test_perfil_de_contacto_con_ubicacion(world, users, book, reads):
    admin = users("admin.test")
    response, requests = _observe("party-identity", lambda: admin.post(
        f"{PI}/organization-identities/{world['organization']}/contact-profile",
        json={"email": "contacto.us6@example.com", "address_line": "Calle ficticia 1",
              **world["location"], "confirmed_by_company_id": world["company"]}))
    # La validación de la empresa que confirma (operational-access, identidad técnica) sigue por API.
    _check(world, book, reads, "perfil_contacto_con_ubicacion", response, requests, 201,
           allowed=("operational-context GET /api/v1/operational-access",))


# --------------------------------------------------------------------------- Business Reporting


def test_reporte_de_compras(world, users, book, reads):
    admin = users("admin.test")
    response, requests = _observe("business-reporting", lambda: admin.get(
        f"{BRS}/companies/{world['company']}/reports/purchases",
        params={"date_from": "2026-10-01", "date_to": "2026-10-31"}))
    # Los agregados de compras siguen por API (FR-036).
    _check(world, book, reads, "reporte_de_compras", response, requests, 200, allowed=("purchase ",))


# --------------------------------------------------------------------------- catálogo, CR y PIQ


@pytest.fixture(scope="module")
def catalog(world, users):
    admin = users("admin.test")
    run, company = world["run"], world["company"]
    unit = next(item["id"] for item in expect(admin.get(f"{PC}/units-of-measure", params={"status": "ACTIVE", "page_size": 100}))["items"]
                if item["code"] == "UND")
    category = expect(admin.post(f"{PC}/categories", json={"code": f"US6-{run}", "name": f"Categoría US6 (ficticia {run})"}))["id"]
    product = expect(admin.post(f"{PC}/products", json={
        "product_type": "GOOD", "canonical_name": f"PRODUCTO US6 {run}", "base_unit_id": unit}))["id"]
    expect(admin.post(f"{PC}/products/{product}/categories", json={"global_category_id": category}))
    presentation = expect(admin.post(f"{PC}/products/{product}/presentations", json={
        "code": f"UND-{run}", "name": "Unidad", "is_base": True}))["id"]
    adopted = expect(admin.post(f"{CR}/companies/{company}/company-products", json={
        "global_product_id": product, "internal_code": f"P6-{run}", "display_name": f"Producto US6 {run}",
        "currency_code": "COP", "inventory_control_enabled": True}))["id"]
    row = expect(admin.post(f"{CR}/companies/{company}/company-product-presentations", json={
        "company_product_id": adopted, "global_product_presentation_id": presentation, "sku": f"SKU-6-{run}"}))["id"]
    loose = expect(admin.post(f"{PC}/products", json={
        "product_type": "GOOD", "canonical_name": f"PRODUCTO FABRICANTE US6 {run}", "base_unit_id": unit}))["id"]
    supplier = expect(admin.post(f"{CR}/companies/{company}/company-suppliers", json={
        "organization_identity_id": world["organization"], "internal_code": f"PRV6-{run}",
        "display_name": f"Proveedor ficticio US6 {run}"}))["id"]
    types = expect(admin.get(f"{PR}/global-payment-condition-types", params={"page_size": 100}))["items"]
    cash_type = next(item["id"] for item in types if item["code"] == "CASH" and item["status"] == "ACTIVE")
    branch = expect(admin.post(f"{OC}/companies/{company}/branches", json={
        "code": f"Q1{run}", "name": f"Sucursal ficticia Q1 {run}"}))["id"]
    expect(admin.post(f"{OC}/application-users/{world['member']}/user-branches", json={"branch_id": branch}))
    world["aliases"].update({unit: "unidad", category: "categoria", product: "producto_global", presentation: "presentacion_global",
                             adopted: "producto", loose: "producto_fabricante", row: "presentacion", supplier: "proveedor", cash_type: "contado",
                             branch: "Q1"})
    return {"unit": unit, "product": product, "adopted": adopted, "supplier": supplier, "cash_type": cash_type, "loose": loose,
            "branch": branch, "category": category}


def test_condicion_de_pago_de_proveedor(world, catalog, users, book, reads):
    """CR → Payment Reference: el tipo de condición de pago se lee de la vista."""
    admin = users("admin.test")
    response, requests = _observe("commercial-relationship", lambda: admin.post(
        f"{CR}/companies/{world['company']}/supplier-payment-conditions",
        json={"company_supplier_id": catalog["supplier"], "payment_condition_type_id": catalog["cash_type"],
              "currency_code": "COP", "payment_terms_days": 0, "valid_from": "2026-01-01T00:00:00Z"}))
    _check(world, book, reads, "condicion_de_pago_proveedor", response, requests, 201)


def test_condicion_de_pago_tipo_inexistente(world, catalog, users, book, reads):
    admin = users("admin.test")
    response, requests = _observe("commercial-relationship", lambda: admin.post(
        f"{CR}/companies/{world['company']}/supplier-payment-conditions",
        json={"company_supplier_id": catalog["supplier"], "payment_condition_type_id": str(uuid4()),
              "currency_code": "COP", "payment_terms_days": 0, "valid_from": "2026-01-01T00:00:00Z"}))
    _check(world, book, reads, "condicion_de_pago_tipo_inexistente", response, requests, 422)


def test_producto_de_proveedor(world, catalog, users, book, reads):
    """CR → Product Catalog: la unidad base del producto global se lee de la vista."""
    admin = users("admin.test")
    response, requests = _observe("commercial-relationship", lambda: admin.post(
        f"{CR}/companies/{world['company']}/supplier-products",
        json={"company_supplier_id": catalog["supplier"], "company_product_id": catalog["adopted"],
              "purchase_unit_id": catalog["unit"], "currency_code": "COP", "minimum_order_quantity": "1",
              "pack_quantity": "1", "is_preferred": True}))
    _check(world, book, reads, "producto_de_proveedor", response, requests, 201)


def test_fabricante_de_producto(world, catalog, users, book, reads):
    """PC → Party Identity: el fabricante se lee de la vista (existente → 201; inexistente → 422)."""
    admin = users("admin.test")
    product = catalog["loose"]
    current = expect(admin.get(f"{PC}/products/{product}"))
    body = {key: current[key] for key in ("canonical_name", "base_unit_id")}
    response, requests = _observe("product-catalog", lambda: admin.put(f"{PC}/products/{product}", json={
        **body, "manufacturer_organization_id": world["organization"], "version": current["version"]}))
    _check(world, book, reads, "fabricante_existente", response, requests, 200)
    current = response.json()
    response, requests = _observe("product-catalog", lambda: admin.put(f"{PC}/products/{product}", json={
        **body, "manufacturer_organization_id": str(uuid4()), "version": current["version"]}))
    _check(world, book, reads, "fabricante_inexistente", response, requests, 422)


# Lecturas de PIQ que siguen por API (FR-036).
PIQ_API = ("company-products/search", "presentations/batch-lookup", "applicable-prices/resolve", "products/match",
           "inventory-product-sets", "POST /api/v1/companies/{id}/inventory-summary", "operational-access")


def test_vista_de_productos_por_sucursal(world, catalog, users, book, reads):
    admin = users("admin.test")
    response, requests = _observe("product-inventory-query", lambda: admin.get(
        f"{PIQ}/companies/{world['company']}/branches/{catalog['branch']}/product-overviews",
        params={"page_size": 20}))
    _check(world, book, reads, "vista_productos_sucursal", response, requests, 200, allowed=PIQ_API)


def test_resumen_de_inventario(world, catalog, users, book, reads):
    admin = users("admin.test")
    response, requests = _observe("product-inventory-query", lambda: admin.get(
        f"{PIQ}/companies/{world['company']}/inventory-summary"))
    _check(world, book, reads, "resumen_inventario", response, requests, 200, allowed=PIQ_API)


# --------------------------------------------------------------------------- caídas (T079)

PIQ_LIMIT, LIMIT = 3.5, 5.5  # tiempo de espera de la integración de hoy (PIQ: 3 s; los demás: 5 s), con margen


def _outage_actions(owner, world, catalog, admin, seed):
    """(nombre, límite, solicitud, repetir al volver o función de efectos) de cada pareja consumidor → ``owner``. Lo que necesita al
    propietario se prepara aquí, antes del corte. Repetir la misma solicitud al volver la base muestra que la caída
    no dejó efectos (si se hubiera aplicado, la repetición sería un 409 o un 422)."""
    run, company = world["run"], world["company"]
    piq = ("product-inventory-query", PIQ_LIMIT, lambda: admin.get(
        f"{PIQ}/companies/{company}/branches/{catalog['branch']}/product-overviews", params={"page_size": 20}), False)
    if owner == "geography":
        organization = _organization(admin, seed, run, "CAIDA GEO")
        world["aliases"][organization] = "organizacion_caida"
        return [
            ("operational-context", LIMIT, lambda: admin.post(f"{OC}/companies/{company}/branches", json={
                "code": f"GX{run}", "name": f"Sucursal ficticia GX {run}", **world["location"]}), True),
            ("party-identity", LIMIT, lambda: admin.post(f"{PI}/organization-identities/{organization}/contact-profile", json={
                "email": "caida.us6@example.com", "address_line": "Calle ficticia 2", **world["location"],
                "confirmed_by_company_id": company}), True),
        ]
    if owner == "party-identity":
        organization = _organization(admin, seed, run, "CAIDA PI")
        world["aliases"][organization] = "organizacion_caida_pi"
        current = expect(admin.get(f"{PC}/products/{catalog['loose']}"))
        body = {key: current[key] for key in ("canonical_name", "base_unit_id")}
        return [
            ("operational-context", LIMIT, lambda: admin.post(f"{OC}/companies", json={
                "organization_identity_id": organization}), True),
            ("product-catalog", LIMIT, lambda: admin.put(f"{PC}/products/{catalog['loose']}", json={
                # Un fabricante nuevo: Product Catalog solo consulta Party Identity si el fabricante cambia.
                **body, "manufacturer_organization_id": organization, "version": current["version"]}), True),
        ]
    if owner == "payment-reference":
        def count():
            return expect(admin.get(f"{CR}/companies/{company}/supplier-payment-conditions",
                                    params={"page_size": 1}))["total_records"]
        before = count()
        # Repetir daría 422 (ya hay una condición de contado vigente): se cuentan las condiciones antes y después.
        return [("commercial-relationship", LIMIT, lambda: admin.post(
            f"{CR}/companies/{company}/supplier-payment-conditions",
            json={"company_supplier_id": catalog["supplier"], "payment_condition_type_id": catalog["cash_type"],
                  "currency_code": "COP", "payment_terms_days": 30, "valid_from": "2026-02-01T00:00:00Z"}),
                 lambda: {"condiciones_nuevas": count() - before})]
    if owner == "product-catalog":
        product = expect(admin.post(f"{PC}/products", json={
            "product_type": "GOOD", "canonical_name": f"PRODUCTO CAIDA US6 {run}", "base_unit_id": catalog["unit"]}))["id"]
        # Completo para poder adoptarlo: categoría y presentación base, como en ``catalog``.
        expect(admin.post(f"{PC}/products/{product}/categories", json={"global_category_id": catalog["category"]}))
        expect(admin.post(f"{PC}/products/{product}/presentations", json={
            "code": f"UNDX-{run}", "name": "Unidad", "is_base": True}))
        adopted = expect(admin.post(f"{CR}/companies/{company}/company-products", json={
            "global_product_id": product, "internal_code": f"PX-{run}", "display_name": f"Producto caída US6 {run}",
            "currency_code": "COP", "inventory_control_enabled": False}))["id"]
        world["aliases"].update({product: "producto_global_caida", adopted: "producto_caida"})
        return [
            ("commercial-relationship", LIMIT, lambda: admin.post(f"{CR}/companies/{company}/supplier-products", json={
                "company_supplier_id": catalog["supplier"], "company_product_id": adopted,
                "purchase_unit_id": catalog["unit"], "currency_code": "COP", "minimum_order_quantity": "1",
                "pack_quantity": "1", "is_preferred": False}), True),
            piq,
        ]
    if owner in ("commercial-relationship", "inventory"):
        return [piq]
    if owner == "operational-context":
        return [piq, ("business-reporting", LIMIT, lambda: admin.get(
            f"{BRS}/companies/{company}/reports/purchases", params={"date_from": "2026-10-01", "date_to": "2026-10-31"}),
            False)]
    raise AssertionError(owner)


@outages_only
@pytest.mark.parametrize("owner", ("geography", "party-identity", "payment-reference", "product-catalog",
                                   "commercial-relationship", "inventory", "operational-context"))
def test_caida_del_propietario(world, catalog, users, seed, outage_book, owner):
    """T079: con la base del propietario caída, cada consumidor responde el 503 de hoy, a tiempo y sin efectos."""
    admin = users("admin.test")
    actions = _outage_actions(owner, world, catalog, admin, seed)
    observed = []
    with owner_database_down(owner):
        for _, _, action, _ in actions:
            start = time.monotonic()
            response = action()
            observed.append((response, time.monotonic() - start))
    normalizer = Normalizer(world["aliases"], run=world["run"])
    for (consumer, limit, action, replay), (response, elapsed) in zip(actions, observed, strict=True):
        effects = replay() if callable(replay) else {"repeticion": action().status_code} if replay else {}
        outage_book.check(f"{owner}:{consumer}", outage_case(response, normalizer, elapsed, limit, effects))
