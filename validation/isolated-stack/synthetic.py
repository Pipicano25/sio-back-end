"""Juego sintético de rendimiento de la spec 022 (T141; RNF-022-1, RNF-022-5, RNF-022-8; research R-15).

Siembra **solo por API** en la pila aislada, con semilla fija, después de `validation/isolation_guard.py`:

- perfil `dao`: volumen de DAO (2.340 productos adoptados, ~4.142 presentaciones, 3 sucursales);
- perfil `sesgado`: 20.000 productos adoptados con ~50.000 presentaciones, de un catálogo global de 200.000
  (`--globales`), con una marca de 15 productos y otra de 15.000, 30 % con imagen, 5 % con existencias y políticas
  en el 20 %.

Cada perfil crea su propia empresa (`SINTETICO-<perfil>-<ejecución>`), con los 7 usuarios de prueba como miembros.
Las imágenes reutilizan un único objeto PNG del almacenamiento aislado (PC-1 solo mira el registro del activo).
Escribe el manifiesto en `$SIO_IT_STATE_DIR/synthetic-<perfil>.json`. No imprime secretos.

    eval "$(bash validation/isolated-stack/stack.sh entorno)"
    services/product-catalog-service/.venv/bin/python validation/isolated-stack/synthetic.py --perfil dao
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import secrets
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seed as base  # noqa: E402  (mismas URL, barrera, identidades y PNG)

PROFILES = {
    "dao": dict(adopted=2340, extra_presentations=1802, globals_=2340, small_brand=15, big_brand=1500,
                image=0.30, stock=0.30, policy=0.20),
    "sesgado": dict(adopted=20000, extra_presentations=30000, globals_=200000, small_brand=15, big_brand=15000,
                    image=0.30, stock=0.05, policy=0.20),
}


class SharedToken(httpx.Auth):
    """Un solo token por identidad para todos los hilos (muchos inicios de sesión simultáneos los rechaza Keycloak)."""

    def __init__(self, data: dict) -> None:
        self._inner = base.Token(data)
        self._lock = threading.Lock()

    def auth_flow(self, request):
        with self._lock:
            flow = self._inner.auth_flow(request)
            prepared = next(flow)
        yield prepared


class Pool:
    """Un cliente HTTP por hilo con el token compartido; reintenta los `5xx` transitorios."""

    def __init__(self, env: dict, workers: int) -> None:
        self.env, self.workers = env, workers
        self.local = threading.local()
        self.calls = 0
        self.lock = threading.Lock()
        self.tokens = {
            "admin": SharedToken({"grant_type": "password", "client_id": "sio-web", "scope": "openid",
                                  "username": "admin.test", "password": env["KEYCLOAK_TEST_USER_PASSWORD"]}),
            "operator": SharedToken({"grant_type": "client_credentials", "client_id": "inventory-test-operator",
                                     "client_secret": env["INVENTORY_TEST_OPERATOR_CLIENT_SECRET"]}),
        }

    def client(self, kind: str = "admin") -> httpx.Client:
        client = getattr(self.local, kind, None)
        if client is None:
            client = httpx.Client(auth=self.tokens[kind], timeout=60)
            setattr(self.local, kind, client)
        return client

    def post(self, url: str, body: dict, *, kind: str = "admin", expected=(200, 201)) -> dict:
        for attempt in range(5):
            try:
                response = self.client(kind).post(url, json=body)
            except httpx.TransportError:
                time.sleep(1.0 * (attempt + 1))  # conexión cortada o tiempo agotado: se reintenta
                continue
            with self.lock:
                self.calls += 1
            if response.status_code in expected:
                return response.json() if response.content else {}
            if response.status_code < 500:
                raise SystemExit(f"POST {response.request.url.path} → {response.status_code}: {response.text[:300]}")
            time.sleep(0.5 * (attempt + 1))
        raise SystemExit(f"POST {url} falló 5 veces")

    def map(self, function, items) -> list:
        with ThreadPoolExecutor(self.workers) as executor:
            return list(executor.map(function, items))


def build(profile: str, *, globals_override: int | None, workers: int) -> dict:
    spec = dict(PROFILES[profile])
    if globals_override:
        spec["globals_"] = max(globals_override, spec["adopted"])
    env = base.isolated_env()
    base.guard().check_targets(base.URLS)
    print(f"Destinos verificados como aislados; perfil {profile}: {spec}")
    rng = random.Random(f"spec022-{profile}")
    run = secrets.token_hex(3).upper()
    pool = Pool(env, workers)
    admin = pool.client()
    pc, cr, oc, inv = (base.URLS[k] for k in ("product_catalog", "commercial_relationship", "operational_context", "inventory"))
    started = time.monotonic()

    colombia = base.ok(admin.get(f"{base.URLS['geography']}/global-countries", params={"iso3_code": "COL"}))["items"][0]["id"]
    company = base.company(admin, colombia, f"SINTETICO-{profile}")
    members = {name: base.member(admin, colombia, company, name) for name in base.USERS}
    branches = [base.ok(admin.post(f"{oc}/companies/{company}/branches", json={
        "code": f"S{index}{run}", "name": f"Sucursal sintética {index} {run}"}))["id"] for index in range(1, 4)]
    unit = next(item["id"] for item in base.ok(admin.get(f"{pc}/units-of-measure", params={"status": "ACTIVE", "page_size": 100}))["items"]
                if item["code"] == "UND")
    brands = {name: base.ok(admin.post(f"{pc}/brands", json={"code": f"{name}-{run}", "name": f"Marca {name} {run}"}))["id"]
              for name in ("PEQUENA", "GRANDE", "OTRA")}
    category = base.ok(admin.post(f"{pc}/categories", json={"code": f"SINT-{run}", "name": f"Sintética {run}"}))["id"]

    # Un solo objeto PNG para todas las imágenes sintéticas.
    import boto3

    content = base.png(22)
    sha = hashlib.sha256(content).hexdigest()
    boto3.client("s3", endpoint_url=base.URLS["object_storage"], region_name="us-east-1",
                 aws_access_key_id=env["SIO_IT_WRITER_STORAGE_ACCESS_KEY"],
                 aws_secret_access_key=env["SIO_IT_WRITER_STORAGE_SECRET_KEY"]).put_object(
        Bucket=base.BUCKET, Key=f"assets/{sha}.png", Body=content, ContentType="image/png", Metadata={"sha256": sha})

    total = spec["globals_"]
    adopted_indexes = set(rng.sample(range(total), spec["adopted"]))
    adopted_sorted = sorted(adopted_indexes)
    small = set(adopted_sorted[: spec["small_brand"]])
    big = set(adopted_sorted[spec["small_brand"]: spec["small_brand"] + spec["big_brand"]])
    images = {index for index in range(total) if rng.random() < spec["image"]}
    names = [f"Sintético {rng.choice(base.CATALOG)[0].split()[0]} {index:06d}" for index in range(total)]

    def create_global(index: int) -> tuple[int, str, str | None]:
        brand = brands["PEQUENA"] if index in small else brands["GRANDE"] if index in big else (
            brands["OTRA"] if index % 2 else None)
        body = {"product_type": "GOOD", "canonical_name": f"{names[index].upper()} {run}", "base_unit_id": unit}
        if brand:
            body["global_brand_id"] = brand
        product = pool.post(f"{pc}/products", body)["id"]
        if index in images:
            pool.post(f"{pc}/products/{product}/assets", {"asset_type": "IMAGE", "file_name": "s.png", "mime_type": "image/png",
                                                          "storage_uri": f"s3://{base.BUCKET}/assets/{sha}.png", "is_primary": True})
        presentation = None
        if index in adopted_indexes:
            pool.post(f"{pc}/products/{product}/categories", {"global_category_id": category})
            presentation = pool.post(f"{pc}/products/{product}/presentations",
                                     {"code": f"U-{index}-{run}", "name": "Unidad", "is_base": True})["id"]
        return index, product, presentation

    globals_ = pool.map(create_global, range(total))
    print(f"Catálogo global: {total} productos ({len(images)} con imagen) en {time.monotonic() - started:.0f} s")

    extra_for = {}
    adopted_list = [row for row in globals_ if row[2] is not None]
    for position in range(spec["extra_presentations"]):
        extra_for.setdefault(adopted_list[position % len(adopted_list)][0], []).append(position)

    def adopt(row) -> dict:
        index, product, presentation = row
        company_product = pool.post(f"{cr}/companies/{company}/company-products", {
            "global_product_id": product, "internal_code": f"S-{index:06d}-{run}", "display_name": names[index],
            "currency_code": "COP", "inventory_control_enabled": True})
        rows = [pool.post(f"{cr}/companies/{company}/company-product-presentations", {
            "company_product_id": company_product["id"], "global_product_presentation_id": presentation,
            "sku": f"SK-{index:06d}-{run}"})["id"]]
        for number, _ in enumerate(extra_for.get(index, []), start=2):
            box = pool.post(f"{pc}/products/{product}/presentations", {
                "code": f"C{number}-{index}-{run}", "name": f"Caja x {number * 6}", "is_base": False,
                "base_quantity": str(number * 6), "display_order": number})["id"]
            rows.append(pool.post(f"{cr}/companies/{company}/company-product-presentations", {
                "company_product_id": company_product["id"], "global_product_presentation_id": box,
                "sku": f"SK-{index:06d}-{number}-{run}"})["id"])
        return {"id": company_product["id"], "index": index, "presentations": rows}

    products = pool.map(adopt, adopted_list)
    print(f"Adoptados: {len(products)} con {sum(len(p['presentations']) for p in products)} presentaciones "
          f"({time.monotonic() - started:.0f} s)")

    price_list = base.ok(admin.post(f"{cr}/companies/{company}/price-lists", json={
        "code": f"LS-{run}", "name": f"Lista sintética {run}", "currency_code": "COP", "is_default": True}))["id"]
    priced = [p for p in products if p["index"] % 2 == 0]
    pool.map(lambda p: pool.post(f"{cr}/companies/{company}/price-list-items", {
        "price_list_id": price_list, "company_product_id": p["id"], "unit_price": "1000.00",
        "company_product_presentation_id": p["presentations"][0]}), priced)

    with_stock = [p for p in products if rng.random() < spec["stock"]]
    for branch in branches:
        for start in range(0, len(with_stock), 50):
            pool.post(f"{inv}/inventory-entries", {
                "operation_key": str(uuid4()), "company_id": company, "branch_id": branch, "origin_type": "PURCHASE",
                "origin_id": str(uuid4()), "application_user_id": members["admin.test"], "correlation_id": str(uuid4()),
                "lines": [{"origin_detail_id": str(uuid4()), "company_product_id": p["id"],
                           "quantity": str(1 + p["index"] % 40), "unit_cost": "1000"}
                          for p in with_stock[start:start + 50]]}, kind="operator")
    with_policy = [p for p in products if rng.random() < spec["policy"]]
    pool.map(lambda p: pool.post(f"{inv}/companies/{company}/inventory-policies", {
        "branch_id": branches[p["index"] % 3], "company_product_id": p["id"], "minimum_stock": str(5 + p["index"] % 30),
        "safety_stock_method": "BASIC", "replenishment_mode": "MANUAL"}), with_policy)

    manifest = {"profile": profile, "run": run, "company": company, "branches": branches, "brands": brands,
                "category": category, "price_list": price_list, "spec": spec, "adopted": len(products),
                "presentations": sum(len(p["presentations"]) for p in products), "with_stock": len(with_stock),
                "with_policy": len(with_policy), "images": len(images), "calls": pool.calls,
                "seconds": round(time.monotonic() - started)}
    state = Path(os.environ.get("SIO_IT_STATE_DIR", "/tmp/sio-it-state"))
    state.mkdir(parents=True, exist_ok=True)
    (state / f"synthetic-{profile}.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Listo: {json.dumps({k: v for k, v in manifest.items() if k not in ('branches', 'brands')})}")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--perfil", choices=sorted(PROFILES), required=True)
    parser.add_argument("--globales", type=int, default=None, help="Tamaño del catálogo global (reduce el perfil)")
    parser.add_argument("--hilos", type=int, default=12)
    arguments = parser.parse_args()
    build(arguments.perfil, globals_override=arguments.globales, workers=arguments.hilos)
