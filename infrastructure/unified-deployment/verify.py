"""Comprobación de solo lectura de un despliegue unificado de SIO.

Para cada uno de los 12 servicios: health, OpenAPI (requiere `SIO_DOCS_ENABLED=true`),
preflight CORS en cada operación y `401` sin token en cada operación protegida (las que
declaran `security`; las públicas, como health o la imagen firmada de Product Catalog,
solo se cuentan). No envía tokens ni ejecuta escrituras: toda petición protegida se
rechaza en `sio-auth` antes del handler.

    python verify.py http://localhost:8000
    python verify.py https://sio-unified.onrender.com --expected-operations 411
"""

from __future__ import annotations

import argparse
import re
import sys
from uuid import uuid4

import httpx

SERVICES = (
    "geography", "party-identity", "product-catalog", "operational-context", "payment-reference",
    "commercial-relationship", "purchase", "sales", "inventory", "audit",
    "product-inventory-query", "business-reporting",
)
ORIGIN = "https://verificacion.example.com"


def check(base: str, expected_operations: int | None, timeout: float) -> int:
    failures: list[str] = []
    total = 0
    with httpx.Client(base_url=base.rstrip("/"), timeout=timeout) as client:
        for service in SERVICES:
            prefix = f"/{service}"
            live = client.get(f"{prefix}/health/live")
            if live.status_code != 200:
                failures.append(f"{service}: /health/live → {live.status_code}")
            schema = client.get(f"{prefix}/openapi.json")
            if schema.status_code != 200:
                failures.append(f"{service}: /openapi.json → {schema.status_code} (¿SIO_DOCS_ENABLED?)")
                continue
            document = schema.json()
            operations = [
                (method.upper(), re.sub(r"\{[^}]+\}", str(uuid4()), template),
                 bool(operation.get("security", document.get("security"))))
                for template, item in document["paths"].items()
                for method, operation in item.items()
                if method in {"get", "post", "put", "patch", "delete"}
            ]
            total += len(operations)
            bad = 0
            for method, path, protected in operations:
                if not protected:
                    continue
                url = prefix + path
                preflight = client.options(
                    url,
                    headers={"Origin": ORIGIN, "Access-Control-Request-Method": method,
                             "Access-Control-Request-Headers": "authorization, content-type"},
                )
                anonymous = client.request(method, url, headers={"Origin": ORIGIN})
                if (
                    preflight.status_code != 200
                    or preflight.headers.get("access-control-allow-origin") != "*"
                    or anonymous.status_code != 401
                    or anonymous.headers.get("access-control-allow-origin") != "*"
                    or "access-control-allow-credentials" in anonymous.headers
                ):
                    bad += 1
                    failures.append(f"{service}: {method} {path} → preflight {preflight.status_code}, sin token {anonymous.status_code}")
            public = sum(1 for *_, protected in operations if not protected)
            print(f"{service:26} live={live.status_code} operaciones={len(operations):3} públicas={public} con fallos={bad}")

    print(f"\nTotal de operaciones: {total}")
    if expected_operations is not None and total != expected_operations:
        failures.append(f"se esperaban {expected_operations} operaciones y hay {total}")
    for failure in failures[:50]:
        print("FALLO:", failure)
    print("RESULTADO:", "OK" if not failures else f"{len(failures)} fallos")
    return 0 if not failures else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("base_url")
    parser.add_argument("--expected-operations", type=int, default=None)
    parser.add_argument("--timeout", type=float, default=90.0, help="segundos; Render Free puede tardar en despertar")
    args = parser.parse_args()
    sys.exit(check(args.base_url, args.expected_operations, args.timeout))


if __name__ == "__main__":
    main()
