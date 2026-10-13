"""Consulta de solo lectura a las API de SIO (herramienta general de ia-tools).

Uso:
    python tools/data-migration/ia-tools/sio_query.py <servicio> --list
    python tools/data-migration/ia-tools/sio_query.py <servicio> <ruta> [--param clave=valor ...] [--all-pages] [--rol consulta]

Ejemplos:
    sio_query.py product-catalog /api/v1/products/by-identifier/{value} --param value=07702031244486
    sio_query.py party-identity /api/v1/organization-identities --param search=817004260 --param identification_type=NIT
    sio_query.py product-catalog /api/v1/units-of-measure --all-pages

- Las rutas y los parámetros se validan contra el OpenAPI publicado por el servicio (`/openapi.json`):
  no se inventan rutas ni se suponen filtros comunes. La ruta puede ser la plantilla del contrato
  (`/api/v1/products/{product_id}`) o una ruta concreta (`/api/v1/products/<uuid>`).
- Solo GET. No existe código para POST, PUT, PATCH ni DELETE.
- El token se obtiene con `services/get_token.py`: `obtener_token(rol)` para los usuarios de prueba y
  `obtener_token_cliente(client_id)` para un cliente técnico (`--rol cliente:<client_id>`, p. ej.
  `cliente:sio-data-importer`) y `obtener_token_usuario(nombre)` para un usuario nominal
  (`--rol usuario:<nombre>`, p. ej. `usuario:santiago.rodriguez`). Vive solo en memoria y nunca se imprime ni se guarda. Ante un 401 se pide
  uno nuevo una sola vez.
- La salida estándar es el JSON de la respuesta; el código HTTP va a la salida de errores.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parents[3]
TOKEN_SCRIPT = REPO_ROOT / "services" / "get_token.py"
INFRASTRUCTURE_ENV = REPO_ROOT / "infrastructure" / ".env"
# Servicio → (clave pública de puerto en infrastructure/.env, puerto documentado en docs/port-map.md).
SERVICES = {
    "party-identity": ("PARTY_IDENTITY_SERVICE_PORT", 8101),
    "geography": ("GEOGRAPHY_SERVICE_PORT", 8102),
    "product-catalog": ("PRODUCT_CATALOG_SERVICE_PORT", 8103),
    "operational-context": ("OPERATIONAL_CONTEXT_SERVICE_PORT", 8104),
    "payment-reference": ("PAYMENT_REFERENCE_SERVICE_PORT", 8105),
    "commercial-relationship": ("COMMERCIAL_RELATIONSHIP_SERVICE_PORT", 8106),
    "purchase": ("PURCHASE_SERVICE_PORT", 8107),
    "sales": ("SALES_SERVICE_PORT", 8108),
    "inventory": ("INVENTORY_SERVICE_PORT", 8109),
    "audit": ("AUDIT_SERVICE_PORT", 8110),
}


class QueryError(Exception):
    """Consulta no permitida por el contrato (ruta, método o parámetro inexistente)."""


def _public_port(key: str) -> str | None:
    """Lee solo la clave de puerto pedida de infrastructure/.env (nunca secretos)."""
    if os.environ.get(key):
        return os.environ[key]
    if INFRASTRUCTURE_ENV.is_file():
        for line in INFRASTRUCTURE_ENV.read_text(encoding="utf-8").splitlines():
            name, sep, value = line.partition("=")
            if sep and name.strip() == key:
                return value.strip().strip('"').strip("'") or None
    return None


CLIENT_PREFIX = "cliente:"
USER_PREFIX = "usuario:"


def _load_token_function(rol: str):
    """Función de services/get_token.py que emite el token del rol (usuario de prueba o cliente técnico)."""
    spec = importlib.util.spec_from_file_location("sio_get_token", TOKEN_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # el script no ejecuta nada al importarse (__main__)
    if rol.startswith(CLIENT_PREFIX):
        client_id = rol.removeprefix(CLIENT_PREFIX)
        return lambda _rol: module.obtener_token_cliente(client_id)
    if rol.startswith(USER_PREFIX):
        username = rol.removeprefix(USER_PREFIX)
        return lambda _rol: module.obtener_token_usuario(username)
    return module.obtener_token


class SioQuery:
    def __init__(self, rol: str = "consulta", host: str | None = None, timeout: float = 30.0) -> None:
        self.rol = rol
        self.host = host or os.environ.get("SIO_QUERY_HOST", "127.0.0.1")
        self.timeout = timeout
        self.session = requests.Session()
        self._token: str | None = None
        self._obtener_token = None
        self._specs: dict[str, dict[str, Any]] = {}

    # --- contrato -----------------------------------------------------------------------------
    def base_url(self, service: str) -> str:
        if service not in SERVICES:
            raise QueryError(f"Servicio desconocido '{service}'. Disponibles: {', '.join(SERVICES)}")
        key, default = SERVICES[service]
        return f"http://{self.host}:{_public_port(key) or default}"

    def spec(self, service: str) -> dict[str, Any]:
        if service not in self._specs:
            url = f"{self.base_url(service)}/openapi.json"
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
            except requests.RequestException as error:
                raise QueryError(f"No se pudo leer el contrato de {service} ({url}): {error}. "
                                 "El servicio debe publicar su OpenAPI (SIO_DOCS_ENABLED).") from None
            self._specs[service] = response.json()
        return self._specs[service]

    def operations(self, service: str) -> list[tuple[str, dict[str, Any]]]:
        return [(path, ops["get"]) for path, ops in self.spec(service).get("paths", {}).items() if "get" in ops]

    def resolve(self, service: str, path: str, params: dict[str, str]) -> tuple[str, str, dict[str, str]]:
        """(plantilla, ruta concreta, parámetros de consulta) validados contra el contrato."""
        paths = self.spec(service).get("paths", {})
        template, path_values = None, {}
        if path in paths:
            template = path
        else:
            for candidate in paths:
                pattern = "^" + re.sub(r"\\\{([^}]+)\\\}", r"(?P<\1>[^/]+)", re.escape(candidate)) + "$"
                match = re.match(pattern, path)
                if match:
                    template, path_values = candidate, match.groupdict()
                    break
        if template is None:
            raise QueryError(f"La ruta '{path}' no existe en el contrato de {service} (use --list)")
        if "get" not in paths[template]:
            raise QueryError(f"'{template}' no admite GET en {service}: esta herramienta solo permite lecturas")
        operation = paths[template]["get"]
        declared = {p["name"]: p["in"] for p in operation.get("parameters", [])}
        values = {**path_values, **params}
        concrete = template
        for name in re.findall(r"\{([^}]+)\}", template):
            if not values.get(name):
                raise QueryError(f"Falta el parámetro de ruta '{name}' para {template}")
            concrete = concrete.replace("{" + name + "}", requests.utils.quote(str(values[name]), safe=""))
        query = {k: v for k, v in values.items() if declared.get(k) == "query"}
        unknown = sorted(k for k in values if k not in declared)
        if unknown:
            raise QueryError(f"Parámetros no declarados en el contrato de {template}: {', '.join(unknown)}. "
                             f"Admitidos: {', '.join(sorted(declared)) or 'ninguno'}")
        return template, concrete, query

    # --- autenticación (reutiliza services/get_token.py) ----------------------------------------
    def _authorization(self, renew: bool = False) -> dict[str, str]:
        if self._token is None or renew:
            if self._obtener_token is None:
                self._obtener_token = _load_token_function(self.rol)
            self._token = self._obtener_token(self.rol)
        return {"Authorization": f"Bearer {self._token}"}

    # --- lectura ------------------------------------------------------------------------------
    def get(self, service: str, path: str, params: dict[str, str] | None = None, all_pages: bool = False) -> tuple[int, Any]:
        template, concrete, query = self.resolve(service, path, dict(params or {}))
        status, body = self._get(service, concrete, query)
        declared = {p["name"] for p in self.spec(service)["paths"][template]["get"].get("parameters", [])}
        if not (all_pages and status == 200 and "page" in declared and isinstance(body, dict)
                and isinstance(body.get("items"), list) and body.get("total_pages")):
            return status, body
        items, page = list(body["items"]), int(body.get("page") or query.get("page") or 1)
        while page < int(body["total_pages"]):
            page += 1
            status, body = self._get(service, concrete, {**query, "page": page})
            if status != 200:
                return status, body
            items.extend(body.get("items", []))
        return 200, {"items": items, "total_records": len(items), "pages_read": page}

    def _get(self, service: str, concrete: str, query: dict[str, Any]) -> tuple[int, Any]:
        url = self.base_url(service) + concrete
        response = self.session.get(url, params=query, headers=self._authorization(), timeout=self.timeout)
        if response.status_code == 401:
            response = self.session.get(url, params=query, headers=self._authorization(renew=True), timeout=self.timeout)
        try:
            return response.status_code, response.json()
        except ValueError:
            return response.status_code, {"raw": response.text[:2000]}


def _parse_params(items: list[str]) -> dict[str, str]:
    out = {}
    for item in items:
        name, sep, value = item.partition("=")
        if not sep:
            raise QueryError(f"--param espera clave=valor (recibido '{item}')")
        out[name] = value
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Consulta de solo lectura a las API de SIO (contratos OpenAPI reales).")
    parser.add_argument("service", choices=sorted(SERVICES))
    parser.add_argument("path", nargs="?", help="Ruta del contrato (plantilla o concreta)")
    parser.add_argument("--param", action="append", default=[], help="Parámetro de ruta o de consulta clave=valor (repetible)")
    parser.add_argument("--all-pages", action="store_true", help="Recorrer todas las páginas cuando la operación pagina")
    parser.add_argument("--list", action="store_true", help="Listar las operaciones GET del servicio y sus parámetros")
    parser.add_argument("--rol", default="consulta",
                        help="Rol de services/get_token.py (por defecto consulta), cliente:<client_id> o usuario:<nombre>")
    args = parser.parse_args(argv)
    client = SioQuery(rol=args.rol)
    try:
        if args.list:
            for path, operation in client.operations(args.service):
                params = ", ".join(f"{p['name']}({p['in']})" for p in operation.get("parameters", []))
                print(f"GET {path}  {params}")
            return 0
        if not args.path:
            parser.error("indique la ruta o --list")
        status, body = client.get(args.service, args.path, _parse_params(args.param), all_pages=args.all_pages)
    except QueryError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    print(f"HTTP {status}", file=sys.stderr)
    print(json.dumps(body, ensure_ascii=False, indent=2))
    return 0 if status < 400 else 1


if __name__ == "__main__":
    sys.exit(main())
