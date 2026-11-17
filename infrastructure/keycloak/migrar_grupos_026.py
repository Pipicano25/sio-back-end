"""Migra un realm existente de los 7 grupos anteriores a `superadmin`, `admin` y `empleado` (spec 026).

`--import-realm` no modifica un realm que ya existe (VPS, entornos persistentes), así que este script aplica la
plantilla con la API de administración de Keycloak. Solo usa la biblioteca estándar de Python.

Pasos (todos idempotentes; se puede repetir sin efectos dobles):

1. `plan` (por defecto): muestra qué haría, sin cambiar nada.
2. `aplicar`: crea los roles de perfil y los tres grupos con los roles **exactos** de la plantilla y mueve a cada
   usuario de los grupos anteriores a su grupo nuevo. Si un usuario estaba en varios, queda en el de más alcance
   (superadmin > admin > empleado). Los grupos anteriores **no** se tocan todavía: sirven de vuelta atrás.
3. `retirar`: quita a los usuarios de los grupos anteriores y elimina esos grupos y sus roles de perfil. Hacerlo
   solo después de comprobar los tokens (ver `MIGRACION-GRUPOS.md`).

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
NEW_GROUPS = ("superadmin", "admin", "empleado")  # de más a menos alcance
OLD_TO_NEW = {
    "administradores": "superadmin",
    "supervisores": "admin",
    "compras": "empleado",
    "ventas": "empleado",
    "inventario": "empleado",
    "reportes": "empleado",  # aclaración P2 de la spec 026: ganan escritura
    "consulta": "empleado",
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


def template_groups() -> dict[str, list[str]]:
    data = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    groups = {group["name"]: group["clientRoles"][API_CLIENT] for group in data["groups"]}
    assert set(groups) == set(NEW_GROUPS), f"La plantilla no tiene los grupos de la spec 026: {sorted(groups)}"
    roles = {role["name"]: role.get("description", "") for role in data["roles"]["client"][API_CLIENT]}
    return {name: [(role, roles[role]) for role in groups[name]] for name in NEW_GROUPS}


def apply(kc: Keycloak, dry: bool) -> None:
    cid = kc.client_uuid()
    desired = template_groups()
    new_ids: dict[str, str | None] = {}
    for name, roles in desired.items():
        for role, description in roles:
            if kc.call("GET", f"/clients/{cid}/roles/{urllib.parse.quote(role, safe='')}") is None:
                if not role.startswith("perm:"):
                    print(f"crear rol de perfil {role}")
                    if not dry:
                        kc.call("POST", f"/clients/{cid}/roles", {"name": role, "description": description})
                else:
                    raise SystemExit(f"El permiso {role} no existe en el realm: aplique antes los permisos de la plantilla.")
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

    target: dict[str, tuple[str, str]] = {}  # user id → (username, grupo nuevo)
    for old, new in OLD_TO_NEW.items():
        group = kc.group(old)
        if group is None:
            continue
        for member in kc.members(group["id"]):
            previous = target.get(member["id"], (member["username"], new))[1]
            best = min(previous, new, key=NEW_GROUPS.index)
            target[member["id"]] = (member["username"], best)
    for name in NEW_GROUPS:  # quien ya está en un grupo nuevo conserva el de más alcance
        if new_ids.get(name):
            for member in kc.members(new_ids[name]):
                if member["id"] in target:
                    username, chosen = target[member["id"]]
                    target[member["id"]] = (username, min(chosen, name, key=NEW_GROUPS.index))
    for user_id, (username, new) in sorted(target.items(), key=lambda item: item[1]):
        current = {g["name"] for g in kc.call("GET", f"/users/{user_id}/groups") or []}
        extra = (current & set(NEW_GROUPS)) - {new}
        if new not in current or extra:
            print(f"usuario {username} → {new}" + (f" (sale de {', '.join(sorted(extra))})" if extra else ""))
            if not dry:
                kc.call("PUT", f"/users/{user_id}/groups/{new_ids[new]}")
                for name in extra:
                    kc.call("DELETE", f"/users/{user_id}/groups/{new_ids[name]}")


def retire(kc: Keycloak, dry: bool) -> None:
    cid = kc.client_uuid()
    for old in OLD_TO_NEW:
        group = kc.group(old)
        if group is None:
            continue
        orphans = [m["username"] for m in kc.members(group["id"])
                   if not {g["name"] for g in kc.call("GET", f"/users/{m['id']}/groups") or []} & set(NEW_GROUPS)]
        if orphans:
            raise SystemExit(f"{old}: {', '.join(orphans)} aún no tienen grupo nuevo. Ejecute primero `aplicar`.")
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
