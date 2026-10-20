"""Servicios del despliegue unificado y aislamiento de su configuración.

Lo comparten la API (`main.py`) y el proceso de workers (`workers.py`); no importa
ninguna aplicación, para que el proceso de workers no construya las 12 API.

Los 12 servicios leen variables con los mismos nombres (`DATABASE_URL`,
`KEYCLOAK_CLIENT_ID`…). Cada servicio, y cada worker de ese servicio, ve el entorno
compartido más sus variables con prefijo (`PURCHASE__DATABASE_URL` → `DATABASE_URL`),
y las URL entre servicios apuntan por defecto a la API de este mismo contenedor.
"""

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass(frozen=True)
class Service:
    prefix: str
    module: str
    env_prefix: str
    api_suffix: str = "/api/v1"

    @property
    def path(self) -> str:
        return f"/{self.prefix}"


SERVICES: tuple[Service, ...] = (
    Service("geography", "geography_service.main", "GEOGRAPHY", api_suffix=""),
    Service("party-identity", "party_identity_service.main", "PARTY_IDENTITY"),
    Service("product-catalog", "product_catalog_service.main", "PRODUCT_CATALOG"),
    Service("operational-context", "operational_context_service.main", "OPERATIONAL_CONTEXT"),
    Service("payment-reference", "payment_reference_service.main", "PAYMENT_REFERENCE", api_suffix=""),
    Service("commercial-relationship", "commercial_relationship_service.main", "COMMERCIAL_RELATIONSHIP"),
    Service("purchase", "purchase_service.main", "PURCHASE"),
    Service("sales", "sales_service.main", "SALES"),
    Service("inventory", "inventory_service.main", "INVENTORY"),
    Service("audit", "audit_service.main", "AUDIT"),
    Service("product-inventory-query", "product_inventory_query_service.main", "PRODUCT_INVENTORY_QUERY"),
    Service("business-reporting", "business_reporting_service.main", "BUSINESS_REPORTING"),
)

SERVICES_BY_PREFIX: dict[str, Service] = {service.prefix: service for service in SERVICES}

# Archivos de estado compartidos entre procesos del contenedor (latidos, estado de workers, bloqueos).
STATE_DIR_DEFAULT = "/tmp/sio-unified"


def state_dir(environ: Mapping[str, str] | None = None) -> str:
    env = os.environ if environ is None else environ
    return env.get("SIO_UNIFIED_STATE_DIR", "").strip() or STATE_DIR_DEFAULT


def service_environment(service: Service, environ: Mapping[str, str]) -> dict[str, str]:
    """Entorno con el que se construye `service`: compartido, URL locales y sus variables con prefijo."""

    own_prefixes = tuple(f"{s.env_prefix}__" for s in SERVICES)
    env = {key: value for key, value in environ.items() if not key.startswith(own_prefixes)}

    port = environ.get("PORT", "8000")
    for other in SERVICES:
        env.setdefault(f"{other.env_prefix}_SERVICE_BASE_URL", f"http://127.0.0.1:{port}{other.path}{other.api_suffix}")
    public_url = environ.get("SIO_UNIFIED_PUBLIC_URL", "").rstrip("/")
    if public_url:
        env.setdefault("PRODUCT_CATALOG_PUBLIC_BASE_URL", f"{public_url}/product-catalog")

    marker = f"{service.env_prefix}__"
    env.update({key[len(marker):]: value for key, value in environ.items() if key.startswith(marker)})
    return env


@contextmanager
def temporary_environment(values: Mapping[str, str]) -> Iterator[None]:
    """Sustituye `os.environ` mientras se construye un servicio o worker (siempre en un solo hilo)."""

    saved = dict(os.environ)
    os.environ.clear()
    os.environ.update(values)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(saved)
