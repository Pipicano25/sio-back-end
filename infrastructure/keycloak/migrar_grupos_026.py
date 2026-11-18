"""Lleva un realm existente a los grupos de la spec 026, versión del servidor OCI: `superadmin`, `admin`, `Compras`,
`Ventas` e `Inventario`.

`--import-realm` no modifica un realm que ya existe (VPS, entornos persistentes), así que este script aplica la
plantilla con la API de administración de Keycloak. Solo usa la biblioteca estándar de Python.

Pasos (todos idempotentes; se puede repetir sin efectos dobles):

1. `plan` (por defecto): muestra qué haría, sin cambiar nada.
2. `aplicar`: crea los cinco grupos (o completa los que ya existen, como las áreas vacías del servidor OCI) con los
   roles **exactos** de la plantilla y agrega a cada usuario de un grupo anterior a sus grupos nuevos. Un usuario
   puede quedar en varios grupos (sus permisos se suman). Los grupos anteriores **no** se tocan todavía: sirven de
   vuelta atrás.
3. `retirar`: elimina los grupos anteriores (los siete de antes de la 026 y `empleado`) y los roles de perfil de
   antes de la 026. El rol `empleado` se conserva en el catálogo, como en el servidor. Hacerlo solo después de
   comprobar los tokens (ver `MIGRACION-GRUPOS.md`).

Estados de partida admitidos: los siete grupos anteriores a la 026; `superadmin`/`admin`/`empleado`; y el servidor
OCI (`superadmin`, `admin` y áreas vacías).

Variables de entorno (nunca se escriben en el código):

- `KC_URL`: URL base de Keycloak, p. ej. `http://localhost:8081`.
- `KC_REALM`: realm de SIO (por defecto `sio`).
- `KC_ADMIN_USER` y `KC_ADMIN_PASSWORD`: administrador del realm `master`.

Uso:

    python infrastructure/keycloak/migrar_grupos_026.py plan
    python infrastructure/keycloak/migrar_grupos_026.py aplicar
    python infrastructure/keycloak/migrar_grupos_026.py retirar
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent / "realm-template" / "sio-realm.template.json"
API_CLIENT = "sio-api"
NEW_GROUPS = ("superadmin", "admin", "Compras", "Ventas", "Inventario")
AREAS = ("Compras", "Ventas", "Inventario")
OLD_TO_NEW = {
    "administradores": ("superadmin",),
    "supervisores": ("admin",),
    "compras": ("Compras",),
    "ventas": ("Ventas",),
    "inventario": ("Inventario",),
    "reportes": AREAS,  # aclaración de la spec 026: ganan escritura
    "consulta": AREAS,
    "empleado": AREAS,  # cierre anterior de la 026: el operario son las tres áreas
}
OLD_PROFILE_ROLES = ("administrador", "supervisor", "compras", "ventas", "inventario", "reportes", "consulta")


class Keycloak:
    def __init__(self, url: str, realm: str, user: str, password: str) -> None:
        self.base = url.rstrip("/")
        self.realm = realm
        body = urllib.parse.urlencode({"grant_type": "password", "client_id": "admin-cli", "username": user,
                                       "password": password}).encode()
        request = urllib.request.Request(f"{self.base}/realms/master/protocol/openid-connect/token", data=body)
        with urllib.request.urlopen(request, timeout=30) as response:
            self.token = json.load(response)["access_token"]

    def call(self, method: str, path: str, body=None):
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(f"{self.base}/admin/realms/{self.realm}{path}", data=data, method=method)
        request.add_header("Authorization", f"Bearer {self.token}")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
        except urllib.error.HTTPError as error:
            if error.code == 404 and method == "GET":
                return None
            raise SystemExit(f"{method} {path} → {error.code}: {error.read()[:300]!r}") from None
        return json.loads(raw) if raw else None

    # --- consultas
    def client_uuid(self) -> str:
        return self.call("GET", f"/clients?clientId={API_CLIENT}")[0]["id"]

    def group(self, name: str) -> dict | None:
        found = self.call("GET", f"/groups?search={urllib.parse.quote(name)}&exact=true&briefRepresentation=true") or []
        return next((group for group in found if group["name"] == name and group.get("path") == f"/{name}"), None)

    def members(self, group_id: str) -> list[dict]:
        result, first = [], 0
        while True:
            page = self.call("GET", f"/groups/{group_id}/members?first={first}&max=200&briefRepresentation=true") or []
            result += page
            if len(page) < 200:
                return result
            first += 200


def template_groups() -> dict[str, list[tuple[str, str]]]:
    data = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    groups = {group["name"]: group["clientRoles"][API_CLIENT] for group in data["groups"]}
    assert set(groups) == set(NEW_GROUPS), f"La plantilla no tiene los grupos de la spec 026: {sorted(groups)}"
    roles = {role["name"]: role.get("description", "") for role in data["roles"]["client"][API_CLIENT]}
    return {name: [(role, roles[role]) for role in groups[name]] for name in NEW_GROUPS}


def apply(kc: Keycloak, dry: bool) -> None:
    cid = kc.client_uuid()
    new_ids: dict[str, str | None] = {}
    for name, roles in template_groups().items():
        for role, description in roles:
            if kc.call("GET", f"/clients/{cid}/roles/{urllib.parse.quote(role, safe='')}") is None:
                if role.startswith("perm:"):
                    raise SystemExit(f"El permiso {role} no existe en el realm: aplique antes los permisos de la plantilla.")
                print(f"crear rol de perfil {role}")
                if not dry:
                    kc.call("POST", f"/clients/{cid}/roles", {"name": role, "description": description})
        group = kc.group(name)
        if group is None:
            print(f"crear grupo {name}")
            if not dry:
                kc.call("POST", "/groups", {"name": name})
                group = kc.group(name)
        new_ids[name] = group["id"] if group else None
        current = set()
        if group:
            current = {r["name"] for r in kc.call("GET", f"/groups/{group['id']}/role-mappings/clients/{cid}") or []}
        wanted = {role for role, _ in roles}
        add, remove = sorted(wanted - current), sorted(current - wanted)
        if add or remove:
            print(f"grupo {name}: +{len(add)} roles, -{len(remove)} roles")
        if not dry and group:
            if add:
                kc.call("POST", f"/groups/{group['id']}/role-mappings/clients/{cid}",
                        [kc.call("GET", f"/clients/{cid}/roles/{urllib.parse.quote(r, safe='')}") for r in add])
            if remove:
                kc.call("DELETE", f"/groups/{group['id']}/role-mappings/clients/{cid}",
                        [kc.call("GET", f"/clients/{cid}/roles/{urllib.parse.quote(r, safe='')}") for r in remove])

    target: dict[str, tuple[str, set[str]]] = {}  # user id → (username, grupos nuevos)
    for old, news in OLD_TO_NEW.items():
        group = kc.group(old)
        if group is None:
            continue
        for member in kc.members(group["id"]):
            target.setdefault(member["id"], (member["username"], set()))[1].update(news)
    for user_id, (username, news) in sorted(target.items(), key=lambda item: item[1][0]):
        current = {g["name"] for g in kc.call("GET", f"/users/{user_id}/groups") or []}
        missing = [name for name in NEW_GROUPS if name in news and name not in current]
        if missing:
            print(f"usuario {username} → {', '.join(missing)}")
            if not dry:
                for name in missing:
                    kc.call("PUT", f"/users/{user_id}/groups/{new_ids[name]}")


def retire(kc: Keycloak, dry: bool) -> None:
    cid = kc.client_uuid()
    for old, news in OLD_TO_NEW.items():
        group = kc.group(old)
        if group is None:
            continue
        orphans = [m["username"] for m in kc.members(group["id"])
                   if not set(news) <= {g["name"] for g in kc.call("GET", f"/users/{m['id']}/groups") or []}]
        if orphans:
            raise SystemExit(f"{old}: {', '.join(orphans)} aún no están en sus grupos nuevos. Ejecute primero `aplicar`.")
        print(f"eliminar grupo {old}")
        if not dry:
            kc.call("DELETE", f"/groups/{group['id']}")
    for role in OLD_PROFILE_ROLES:
        if kc.call("GET", f"/clients/{cid}/roles/{role}") is not None:
            print(f"eliminar rol de perfil {role}")
            if not dry:
                kc.call("DELETE", f"/clients/{cid}/roles/{role}")


def main(argv: list[str]) -> int:
    action = argv[1] if len(argv) > 1 else "plan"
    if action not in ("plan", "aplicar", "retirar", "plan-retirar"):
        print(__doc__, file=sys.stderr)
        return 2
    missing = [v for v in ("KC_URL", "KC_ADMIN_USER", "KC_ADMIN_PASSWORD") if not os.environ.get(v)]
    if missing:
        print(f"Faltan variables de entorno: {', '.join(missing)}", file=sys.stderr)
        return 2
    kc = Keycloak(os.environ["KC_URL"], os.environ.get("KC_REALM", "sio"), os.environ["KC_ADMIN_USER"],
                  os.environ["KC_ADMIN_PASSWORD"])
    if action in ("plan", "aplicar"):
        apply(kc, dry=action == "plan")
    else:
        retire(kc, dry=action == "plan-retirar")
    print("Hecho." if action in ("aplicar", "retirar") else "Plan (sin cambios).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
