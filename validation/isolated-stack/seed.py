"""Datos ficticios de la pila aislada para la spec 022 (T131; quickstart §3).

Se cargan **solo por API** de los servicios de la pila `sio-it-*` (y, para el contenido de las imágenes, con la API
S3 del almacenamiento aislado). Antes de la primera solicitud se llama a `validation/isolation_guard.py`
(`check_targets`) con todas las URL, incluido Keycloak: si algún destino no es un contenedor aislado, se detiene
sin escribir nada.

Datos (todos ficticios: crema dental, jarabe y analgésicos; ningún NIT, razón social ni dato de DAO):

- empresa A con 3 sucursales (PPAL, NORTE, SUR) y los 7 usuarios de prueba como miembros; `inventario.test`
  asignado solo a PPAL (A-08) y `admin.test` a las tres;
- empresa B, de la que solo `admin.test` y `ventas.test` son miembros (cursores de otra empresa);
- productos globales con marca, categoría, presentaciones e imagen principal (PNG real en el almacenamiento), y
  productos globales que la empresa no adopta;
- productos adoptados con y sin precio en la lista predeterminada, una segunda lista, un servicio sin control de
  inventario y un producto inactivo con saldo;
- saldos por entradas y salidas de la cuenta técnica de pruebas de Inventory: positivos, cero registrados y sin
  registro;
- políticas de mínimo: bajo, igual y sobre el mínimo, y mínimo 0.

Uso (desde la raíz, con el intérprete de Product Catalog, que trae `httpx` y `boto3`):

    eval "$(bash validation/isolated-stack/stack.sh entorno)"
    services/product-catalog-service/.venv/bin/python validation/isolated-stack/seed.py

Escribe el manifiesto (identificadores, sin secretos) en `$SIO_IT_STATE_DIR/seed.json` (por omisión
`/tmp/sio-it-state`). No imprime contraseñas, tokens ni secretos.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import random
import secrets
import struct
import sys
import time
import zlib
from pathlib import Path
from uuid import uuid4

import httpx

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RUN = secrets.token_hex(3).upper()
BUCKET = "sio-it-product-assets"

URLS = {
    "keycloak": "http://127.0.0.1:18081/realms/sio/protocol/openid-connect/token",
    "geography": "http://127.0.0.1:18102",
    "party_identity": "http://127.0.0.1:18101/api/v1",
    "operational_context": "http://127.0.0.1:18104/api/v1",
    "product_catalog": "http://127.0.0.1:18103/api/v1",
    "commercial_relationship": "http://127.0.0.1:18106/api/v1",
    "inventory": "http://127.0.0.1:18109/api/v1",
    "product_inventory_query": "http://127.0.0.1:18112/api/v1",
    "object_storage": "http://127.0.0.1:18902",
}
USERS = ("admin.test", "supervisor.test", "compras.test", "ventas.test", "inventario.test", "reportes.test",
         "consulta.test")


def guard():
    spec = importlib.util.spec_from_file_location("sio_isolation_guard", REPO / "validation" / "isolation_guard.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def isolated_env() -> dict[str, str]:
    """Secretos de ESTA pila (`validation/isolated-stack/.env`); nunca los de `infrastructure/.env`."""
    path = Path(os.environ.get("SIO_IT_ENV_FILE", HERE / ".env"))
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        name, separator, value = line.partition("=")
        if separator and not name.startswith("#"):
            values[name.strip()] = value.strip()
    return values


class Token(httpx.Auth):
    def __init__(self, data: dict) -> None:
        self._data, self._token, self._expires = data, None, 0.0

    def auth_flow(self, request):
        if self._token is None or time.monotonic() > self._expires - 30:
            body = httpx.post(URLS["keycloak"], data=self._data, timeout=20).raise_for_status().json()
            self._token, self._expires = body["access_token"], time.monotonic() + float(body.get("expires_in", 300))
        request.headers["Authorization"] = f"Bearer {self._token}"
        yield request


def user(env: dict, username: str) -> httpx.Client:
    return httpx.Client(auth=Token({"grant_type": "password", "client_id": "sio-web", "scope": "openid",
                                    "username": username, "password": env["KEYCLOAK_TEST_USER_PASSWORD"]}), timeout=60)


def service(env: dict, client_id: str, variable: str) -> httpx.Client:
    return httpx.Client(auth=Token({"grant_type": "client_credentials", "client_id": client_id,
                                    "client_secret": env[variable]}), timeout=60)


def ok(response: httpx.Response, *expected: int) -> dict:
    if response.status_code not in (expected or (200, 201)):
        raise SystemExit(f"{response.request.method} {response.request.url.path} → {response.status_code}: "
                         f"{response.text[:400]}")
    return response.json() if response.content else {}


def png(seed: int) -> bytes:
    """PNG válido de 8 × 8 píxeles con un color propio (contenido distinto → SHA-256 distinto)."""
    rng = random.Random(seed)
    color = bytes(rng.randrange(256) for _ in range(3))
    raw = b"".join(b"\x00" + color * 8 for _ in range(8))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 8, 8, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


# --------------------------------------------------------------------------- catálogo y empresa


def conforming(pattern: str) -> str:
    import re

    regex = re.compile(pattern)
    for _ in range(500):
        base = str(random.randint(1, 9)) + "".join(random.choice("0123456789") for _ in range(random.randint(7, 9)))
        for candidate in (f"{base}-{random.randint(0, 9)}", base):
            if regex.fullmatch(candidate):
                return candidate
    raise SystemExit(f"Sin número válido para {pattern!r}")


def party(admin, colombia, kind, sigla, path, payload) -> str:
    rules = ok(admin.get(f"{URLS['party_identity']}/identification-type-rules",
                         params={"party_kind": kind, "country_id": colombia, "sigla": sigla, "is_active": "true"}))
    pattern = rules["items"][0]["number_pattern"]
    for _ in range(5):
        response = admin.post(f"{URLS['party_identity']}/{path}",
                              json={**payload, "identification_number": conforming(pattern)})
        if response.status_code == 201:
            return response.json()["id"]
        ok(response, 409)
    raise SystemExit("Sin número de identificación libre")


def company(admin, colombia, label: str) -> str:
    organization = party(admin, colombia, "ORGANIZATION", "NIT", "organization-identities", {
        "country_id": colombia, "identification_type": "NIT",
        "legal_name": f"EMPRESA FICTICIA SIO-IT {label} {RUN} (DATO FICTICIO DE VALIDACION)",
    })
    created = ok(admin.post(f"{URLS['operational_context']}/companies", json={"organization_identity_id": organization}))
    return created["id"]


def member(admin, colombia, company_id: str, username: str) -> str:
    person = party(admin, colombia, "PERSON", "CC", "person-identities", {
        "identification_country_id": colombia, "identification_type": "CC",
        "first_name": f"PRUEBASIOIT{username.split('.')[0].upper()}{RUN}", "last_name": "DATO FICTICIO",
        "birth_date": "1990-01-01",
    })
    return ok(admin.post(f"{URLS['operational_context']}/companies/{company_id}/application-users", json={
        "username": username, "person_identity_id": person, "display_name": f"{username} (ficticio {RUN})",
    }))["id"]


# --------------------------------------------------------------------------- productos

CATALOG = [
    # nombre, marca, categoría, imagen, presentaciones (código, nombre, factor, precio lista predeterminada)
    ("Crema dental Colgate Triple Acción 100 ml", "COLGATE", "ORAL", True, [("UND", "Unidad", "1", "4500.00"), ("CJ12", "Caja x 12", "12", None)]),
    ("Crema dental Colgate Herbal 75 ml", "COLGATE", "ORAL", True, [("UND", "Unidad", "1", "3900.00")]),
    ("Crema dental Colgate Kids 50 ml", "COLGATE", "ORAL", True, [("UND", "Unidad", "1", "3200.00")]),
    ("Crema dental Colgate Máxima 150 ml", "COLGATE", "ORAL", False, [("UND", "Unidad", "1", "6100.00")]),
    ("Enjuague Colgate Plax 250 ml", "COLGATE", "ORAL", True, [("UND", "Unidad", "1", None)]),
    ("Jarabe Abrilar 100 ml", None, "RESP", True, [("FR", "Frasco", "1", "28000.00")]),
    ("Loratadina 10 mg tabletas", "GENFAR", "ANALG", False, [("TAB", "Tableta", "1", None), ("CJ10", "Caja x 10", "10", "8500.00")]),
    ("Acetaminofén 500 mg tabletas", "GENFAR", "ANALG", False, [("TAB", "Tableta", "1", None), ("CJ10", "Caja x 10", "10", "4200.00")]),
    ("Ibuprofeno 400 mg tabletas", "GENFAR", "ANALG", True, [("TAB", "Tableta", "1", None), ("CJ10", "Caja x 10", "10", None)]),
] + [
    (f"Producto ficticio {index:02d}", None, "VARIOS", index % 3 == 0, [("UND", "Unidad", "1", "1000.00" if index % 2 else None)])
    for index in range(1, 25)
]
NOT_ADOPTED = [(f"Colgate global no adoptado {index}", "COLGATE", "ORAL", True) for index in range(1, 6)]


def build() -> dict:
    env = isolated_env()
    targets = {name: url for name, url in URLS.items()}
    guard().check_targets(targets)  # antes de la primera solicitud: falla si algún destino no es sio-it-*
    print(f"Destinos verificados como aislados: {len(targets)}")

    import boto3

    storage = boto3.client("s3", endpoint_url=URLS["object_storage"], region_name="us-east-1",
                           aws_access_key_id=env["SIO_IT_WRITER_STORAGE_ACCESS_KEY"],
                           aws_secret_access_key=env["SIO_IT_WRITER_STORAGE_SECRET_KEY"])
    admin = user(env, "admin.test")
    operator = service(env, "inventory-test-operator", "INVENTORY_TEST_OPERATOR_CLIENT_SECRET")
    pc, cr, oc, inv = (URLS[k] for k in ("product_catalog", "commercial_relationship", "operational_context", "inventory"))

    colombia = ok(admin.get(f"{URLS['geography']}/global-countries", params={"iso3_code": "COL"}))["items"][0]["id"]
    company_a, company_b = company(admin, colombia, "A"), company(admin, colombia, "B")
    members = {name: member(admin, colombia, company_a, name) for name in USERS}
    for name in ("admin.test", "ventas.test"):
        member(admin, colombia, company_b, name)

    branches = {}
    for code in ("PPAL", "NORTE", "SUR"):
        branches[code] = ok(admin.post(f"{oc}/companies/{company_a}/branches", json={
            "code": f"{code}{RUN}", "name": f"Sucursal ficticia {code} {RUN}"}))["id"]
    branch_b = ok(admin.post(f"{oc}/companies/{company_b}/branches", json={"code": f"B{RUN}", "name": f"Sucursal B {RUN}"}))["id"]
    for name, codes in (("admin.test", ("PPAL", "NORTE", "SUR")), ("inventario.test", ("PPAL",))):
        for code in codes:
            ok(admin.post(f"{oc}/application-users/{members[name]}/user-branches", json={"branch_id": branches[code]}))

    unit = next(item["id"] for item in ok(admin.get(f"{pc}/units-of-measure", params={"status": "ACTIVE", "page_size": 100}))["items"]
                if item["code"] == "UND")
    brands = {code: ok(admin.post(f"{pc}/brands", json={"code": f"{code}-{RUN}", "name": f"{code.title()} (ficticia {RUN})"}))["id"]
              for code in ("COLGATE", "GENFAR")}
    categories = {code: ok(admin.post(f"{pc}/categories", json={"code": f"{code}-{RUN}", "name": f"Categoría {code} (ficticia {RUN})"}))["id"]
                  for code in ("ORAL", "RESP", "ANALG", "VARIOS")}
    images = 0

    def global_product(name, brand, category, image, presentations=(("UND", "Unidad", "1", None),)) -> tuple[str, dict]:
        """Producto global completo (categoría y presentación base) para que la empresa lo pueda adoptar."""
        nonlocal images
        body = {"product_type": "GOOD", "canonical_name": f"{name.upper()} {RUN}", "base_unit_id": unit}
        if brand:
            body["global_brand_id"] = brands[brand]
        product = ok(admin.post(f"{pc}/products", json=body))["id"]
        ok(admin.post(f"{pc}/products/{product}/categories", json={"global_category_id": categories[category]}))
        identifier = f"SIOIT-{RUN}-{secrets.token_hex(4).upper()}"  # alfanumérico: nunca es un GTIN
        ok(admin.post(f"{pc}/products/{product}/identifiers", json={"identifier_type": "BARCODE", "value": identifier}), 200, 201)
        if image:
            images += 1
            content = png(int(hashlib.sha256(f"{RUN}{name}".encode()).hexdigest()[:8], 16))
            sha = hashlib.sha256(content).hexdigest()
            storage.put_object(Bucket=BUCKET, Key=f"assets/{sha}.png", Body=content, ContentType="image/png",
                               Metadata={"sha256": sha})
            ok(admin.post(f"{pc}/products/{product}/assets", json={
                "asset_type": "IMAGE", "file_name": f"imagen-{images}.png", "mime_type": "image/png",
                "storage_uri": f"s3://{BUCKET}/assets/{sha}.png", "is_primary": True}))
        globals_ = []
        for position, (code, label, factor, _) in enumerate(presentations, start=1):
            body = {"code": f"{code}-{position}-{product[:8]}", "name": label, "is_base": factor == "1"}
            if factor != "1":
                body.update({"base_quantity": factor, "display_order": position})
            globals_.append(ok(admin.post(f"{pc}/products/{product}/presentations", json=body))["id"])
        return product, {"identifier": identifier, "global_presentations": globals_}

    default_list = ok(admin.post(f"{cr}/companies/{company_a}/price-lists", json={
        "code": f"LP-{RUN}", "name": f"Lista ficticia predeterminada {RUN}", "currency_code": "COP", "is_default": True}))["id"]
    other_list = ok(admin.post(f"{cr}/companies/{company_a}/price-lists", json={
        "code": f"LP2-{RUN}", "name": f"Lista ficticia mayorista {RUN}", "currency_code": "COP"}))["id"]

    products = {}
    for index, (name, brand, category, image, presentations) in enumerate(CATALOG, start=1):
        global_id, extra = global_product(name, brand, category, image, presentations)
        adopted = ok(admin.post(f"{cr}/companies/{company_a}/company-products", json={
            "global_product_id": global_id, "internal_code": f"P-{index:04d}-{RUN}", "display_name": name,
            "currency_code": "COP", "inventory_control_enabled": True}))
        rows = []
        for position, ((code, label, factor, price), global_presentation) in enumerate(
                zip(presentations, extra.pop("global_presentations"), strict=True), start=1):
            row = ok(admin.post(f"{cr}/companies/{company_a}/company-product-presentations", json={
                "company_product_id": adopted["id"], "global_product_presentation_id": global_presentation,
                "sku": f"SKU-{index:02d}{position}-{RUN}"}))
            if price is not None:
                ok(admin.post(f"{cr}/companies/{company_a}/price-list-items", json={
                    "price_list_id": default_list, "company_product_id": adopted["id"], "unit_price": price,
                    "company_product_presentation_id": row["id"]}))
            rows.append({"id": row["id"], "code": label, "factor": factor, "price": price})
        products[name] = {"company_product_id": adopted["id"], "global_product_id": global_id, "image": image,
                          "brand": brand, "category": category, "presentations": rows, **extra}

    # Un precio en la segunda lista (una sola lista por consulta, FR-022-33).
    triple = products[CATALOG[0][0]]
    ok(admin.post(f"{cr}/companies/{company_a}/price-list-items", json={
        "price_list_id": other_list, "company_product_id": triple["company_product_id"], "unit_price": "4100.00",
        "company_product_presentation_id": triple["presentations"][0]["id"]}))

    not_adopted = [global_product(name, brand, category, image)[0] for name, brand, category, image in NOT_ADOPTED]

    service_global, _ = global_product("Servicio de domicilio", None, "VARIOS", False)
    service_product = ok(admin.post(f"{cr}/companies/{company_a}/company-products", json={
        "global_product_id": service_global, "internal_code": f"SRV-{RUN}", "display_name": "Servicio de domicilio",
        "currency_code": "COP", "inventory_control_enabled": False}))["id"]
    inactive_global, _ = global_product("Antiácido descontinuado", None, "ANALG", False)
    inactive = ok(admin.post(f"{cr}/companies/{company_a}/company-products", json={
        "global_product_id": inactive_global, "internal_code": f"INA-{RUN}", "display_name": "Antiácido descontinuado",
        "currency_code": "COP", "inventory_control_enabled": True}))

    # Empresa B: productos «Colgate» propios (aislamiento de cursores y de filas).
    products_b = []
    for index in range(1, 4):
        global_id, _ = global_product(f"Colgate empresa B {index}", "COLGATE", "ORAL", False)
        products_b.append(ok(admin.post(f"{cr}/companies/{company_b}/company-products", json={
            "global_product_id": global_id, "internal_code": f"B-{index}-{RUN}", "display_name": f"Crema dental Colgate B {index}",
            "currency_code": "COP", "inventory_control_enabled": True}))["id"])

    # Saldos (entradas y salidas de la cuenta técnica de pruebas) y políticas.
    def operation(kind: str, branch: str, lines: list[tuple[str, str]]) -> None:
        origin = "PURCHASE" if kind == "entries" else "SALE"
        ok(operator.post(f"{inv}/inventory-{kind}", json={
            "operation_key": str(uuid4()), "company_id": company_a, "branch_id": branches[branch], "origin_type": origin,
            "origin_id": str(uuid4()), "application_user_id": members["admin.test"], "correlation_id": str(uuid4()),
            "lines": [{"origin_detail_id": str(uuid4()), "company_product_id": product, "quantity": quantity,
                       **({"unit_cost": "1000"} if kind == "entries" else {})} for product, quantity in lines]}))

    p = {name: data["company_product_id"] for name, data in products.items()}
    operation("entries", "PPAL", [(p["Loratadina 10 mg tabletas"], "120"), (p["Acetaminofén 500 mg tabletas"], "5"),
                                  (p["Ibuprofeno 400 mg tabletas"], "2"), (p["Crema dental Colgate Triple Acción 100 ml"], "36"),
                                  (p["Crema dental Colgate Herbal 75 ml"], "10"), (inactive["id"], "9")]
              + [(p[f"Producto ficticio {i:02d}"], str(i)) for i in range(1, 25, 2)])
    operation("entries", "NORTE", [(p["Loratadina 10 mg tabletas"], "4"), (p["Acetaminofén 500 mg tabletas"], "3"),
                                   (p["Crema dental Colgate Triple Acción 100 ml"], "6")])
    # Saldos registrados en cero: Ibuprofeno en PPAL y Loratadina en NORTE.
    operation("outputs", "PPAL", [(p["Ibuprofeno 400 mg tabletas"], "2")])
    operation("outputs", "NORTE", [(p["Loratadina 10 mg tabletas"], "4")])
    ok(admin.post(f"{cr}/company-products/{inactive['id']}/deactivate", json={"version": inactive["version"]}))

    policies = [("Loratadina 10 mg tabletas", "PPAL", "150"), ("Acetaminofén 500 mg tabletas", "PPAL", "5"),
                ("Acetaminofén 500 mg tabletas", "NORTE", "5"), ("Ibuprofeno 400 mg tabletas", "PPAL", "0"),
                ("Crema dental Colgate Triple Acción 100 ml", "PPAL", "10")]
    for name, branch, minimum in policies:
        ok(admin.post(f"{inv}/companies/{company_a}/inventory-policies", json={
            "branch_id": branches[branch], "company_product_id": p[name], "minimum_stock": minimum,
            "safety_stock_method": "BASIC", "replenishment_mode": "MANUAL"}))
    # Producto sin registro de saldo y con política: cuenta con cantidad 0 bajo el mínimo (FR-022-50).
    ok(admin.post(f"{inv}/companies/{company_a}/inventory-policies", json={
        "branch_id": branches["SUR"], "company_product_id": p["Crema dental Colgate Kids 50 ml"], "minimum_stock": "2",
        "safety_stock_method": "BASIC", "replenishment_mode": "MANUAL"}))

    manifest = {
        "run": RUN, "company": company_a, "other_company": company_b, "branches": branches, "branch_b": branch_b,
        "members": members, "default_price_list": default_list, "other_price_list": other_list,
        "brands": brands, "categories": categories, "products": products, "not_adopted": not_adopted,
        "service_product": service_product, "inactive_product": inactive["id"], "products_b": products_b,
    }
    state = Path(os.environ.get("SIO_IT_STATE_DIR", "/tmp/sio-it-state"))
    state.mkdir(parents=True, exist_ok=True)
    (state / "seed.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Datos ficticios cargados (ejecución {RUN}): {len(products)} productos adoptados, {images} imágenes, "
          f"{len(not_adopted)} globales no adoptados. Manifiesto: {state / 'seed.json'}")
    return manifest


if __name__ == "__main__":
    sys.exit(0 if build() else 1)
