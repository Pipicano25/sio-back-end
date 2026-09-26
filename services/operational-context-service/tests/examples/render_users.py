"""Documentación de usuarios y permisos para los ejercicios de Operational Context."""

import json
import re
from collections import OrderedDict

from tests.examples.users import USERS, matching_grant

SHORT = {u["username"]: u["username"].replace(".test", "") for u in USERS}
KEYCLOAK = "http://localhost:8081/realms/sio/protocol/openid-connect/token"
SERVICE_URL = "http://localhost:8004"
UUID_IN_TEXT = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
PLACEHOLDER = re.compile(r"<[A-Z0-9_]+>")

NOTES = {
    "perm:operational-context:companies:delete": "Inactivar una empresa (`POST .../deactivate`) exige `delete`, "
    "aunque no la elimina; reactivar (`POST .../reactivate`) exige `update`. Por eso `supervisor.test` puede "
    "reactivar pero no inactivar.",
    "perm:operational-context:branches:delete": "Inactivar una sucursal exige `delete`; reactivarla exige `update`.",
    "perm:operational-context:companies:create": "Para registrar o cambiar la organización o la ubicación, el token "
    "del usuario debe poder además **leer** en Party Identity y Geography: el servicio valida esas referencias con el "
    "mismo token. `administradores` y `supervisores` tienen esa lectura.",
    "perm:operational-context:branches:read": "Las rutas de sucursales exigen solo permisos de `branches`, aunque la "
    "colección y el alta estén bajo `/api/v1/companies/{id}/branches`.",
}


# ------------------------------------------------------------------ utilidades

def parts(permission):
    _, service, resource, action = permission.split(":")
    return service, resource, action


def reason(user, permission):
    service, resource, action = parts(permission)
    related = []
    for role in user["perms"]:
        _, g_service, g_resource, g_action = role.split(":")
        if g_service in ("all", service) and g_resource in ("all", resource):
            related.append(g_action)
    if not related:
        return f"no tiene ningún permiso sobre `{service}`"
    actions = ", ".join(f"`{a}`" for a in sorted(set(related)))
    return f"sobre `{service}` solo tiene {actions}; le falta `{action}`"


def plural(text):
    return (text.replace("solo tiene", "solo tienen").replace("le falta", "les falta")
            .replace("no tiene ningún", "no tienen ningún"))


def endpoint(c):
    path = c["path"].split("?")[0]
    path = PLACEHOLDER.sub("{id}", path)
    return f"{c['method']} {path}"


def permission_lines(permission):
    """Bloque que se agrega en cada llamada de los pasos."""
    yes, no = [], OrderedDict()
    for user in USERS:
        grant = matching_grant(user, permission)
        if grant:
            yes.append(f"`{user['username']}` (por `{grant}`)")
        else:
            no.setdefault(reason(user, permission), []).append(f"`{user['username']}`")
    out = [f"**Permiso que exige la URL:** `{permission}`", ""]
    out.append("- ✅ **Pueden:** " + ", ".join(yes))
    if no:
        denied = "; ".join(f"{', '.join(users)} — {plural(why) if len(users) > 1 else why}" for why, users in no.items())
        out.append(f"- ❌ **No pueden (responde `403`):** {denied}")
    note = NOTES.get(permission)
    if note:
        out.append(f"- ℹ️ {note}")
    out.append("")
    return out


def mark(user, permission):
    return "✅" if matching_grant(user, permission) else "❌"


def calls_with_permission(ex, records):
    rows = []
    for s_index, s in enumerate(ex["steps"]):
        for c_index, c in enumerate(s["calls"]):
            record = records.get((s_index, c_index), {})
            permission = record.get("permission") or c.get("perm")
            if permission:
                rows.append((s_index, c_index, s, c, permission, record))
    return rows


def user_table_header():
    head = "| " + " | ".join(SHORT[u["username"]] for u in USERS) + " |"
    sep = "| " + " | ".join("---" for _ in USERS) + " |"
    return head, sep


def token_command(username, var):
    return [
        "```bash",
        f"{var}=$(curl -s -X POST {KEYCLOAK} \\",
        "  -d grant_type=password -d client_id=sio-web -d scope=openid \\",
        f"  -d username={username} -d \"password=$KEYCLOAK_TEST_USER_PASSWORD\" \\",
        "  | python -c \"import sys, json; print(json.load(sys.stdin)['access_token'])\")",
        "```",
    ]


def curl_for(c, token_var):
    url = c["path"] if c["path"].startswith("http") else f"{SERVICE_URL}{c['path']}"
    lines = [f"curl -s -X {c['method']} \"{url}\" \\", f"  -H \"Authorization: Bearer ${token_var}\""]
    if c["body"] is not None:
        lines[-1] += " \\"
        lines += ["  -H \"Content-Type: application/json\" \\",
                  "  -d '" + json.dumps(c["body"], ensure_ascii=False) + "'"]
    return ["```bash", *lines, "```"]


def forbidden_body(record, permission, path):
    body = dict(record.get("forbidden_example") or {})
    if not body:
        return {"detail": f"Falta el permiso requerido: {permission}"}
    body["instance"] = UUID_IN_TEXT.sub("{id}", PLACEHOLDER.sub("{id}", path.split("?")[0]))
    body["trace_id"] = "<trace_id>"
    return body


# ------------------------------------------------------------------ USUARIOS.md de cada ejercicio

def user_summary(rows):
    lines = []
    for user in USERS:
        blocked = [(s_i, c) for s_i, _, _, c, p, _ in rows if not matching_grant(user, p)]
        reads = sorted({s_i + 1 for s_i, _, _, c, p, _ in rows if c["method"] == "GET" and not c["external"]
                        and matching_grant(user, p)})
        name = f"**`{user['username']}`**"
        if not blocked:
            text = f"{name}: puede ejecutar **todo el ejercicio**."
        else:
            first_step, first_call = blocked[0]
            permission = next(p for s_i, _, _, c, p, _ in rows if c is first_call)
            text = (f"{name}: **no puede completar el ejercicio**. Se detiene en el paso {first_step + 1:02d} "
                    f"(*{first_call['title']}*): {reason(user, permission)}.")
            if reads:
                text += " Sí puede hacer las consultas (`GET`) de los pasos " + ", ".join(f"{n:02d}" for n in reads) + "."
            else:
                text += " No puede hacer ninguna consulta de Operational Context."
        lines.append(f"- {text}")
    return lines


def pick_example(rows, predicate):
    return next(((s_i, c_i, s, c, p, r) for s_i, c_i, s, c, p, r in rows if predicate(s_i, c, p, r)), None)


def render_users(ex, records):
    rows = calls_with_permission(ex, records)
    out = [f"# Usuarios y permisos — {ex['title']}", "",
           "[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)", ""]
    out += ["Qué usuario de prueba del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`) puede "
            "ejecutar cada URL de este ejercicio y por qué. Todos los resultados se comprobaron contra la API: cada "
            "usuario sin permiso recibió `403`, y los usuarios con lectura obtuvieron la respuesta en las consultas.", ""]

    out += ["## Resumen por usuario", ""]
    out += user_summary(rows)
    out += ["", "**Para hacer el ejercicio completo use `admin.test`.** `supervisor.test` puede crear, modificar y "
            "reactivar, pero no inactivar.", ""]

    out += ["## Permiso por URL", "",
            "✅ = el usuario puede ejecutar la llamada · ❌ = recibe `403 Forbidden`.", ""]
    head, sep = user_table_header()
    out += ["| Paso | Llamada | Método y URL | Permiso requerido " + head, "| --- | --- | --- | --- " + sep]
    for s_i, c_i, s, c, p, _ in rows:
        cells = " | ".join(mark(u, p) for u in USERS)
        out.append(f"| [{s_i + 1:02d}]({s['file']}) | {c_i + 1}. {c['title']} | `{endpoint(c)}` | `{p}` | {cells} |")
    out.append("")

    out += ["## Ejemplos de uso con los usuarios", ""]
    out += ["La contraseña de todos los usuarios de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de "
            "`infrastructure/.env`. Cárguela en la terminal antes de pedir tokens.", ""]

    n = 1
    out += [f"### {n}. Ejecutar el ejercicio con `admin.test`", ""]
    out += token_command("admin.test", "TOKEN_ADMIN")
    create = pick_example(rows, lambda s_i, c, p, r: c["method"] == "POST" and p.endswith(":create") and not c["external"])
    if create:
        out += ["", f"Por ejemplo, el paso {create[0] + 1:02d} (*{create[2]['title']}*):", ""]
        out += curl_for(create[3], "TOKEN_ADMIN")
        out += ["", f"Responde `201 Created`: `admin.test` tiene `perm:all:all:all`, que cubre `{create[4]}`. "
                "Reemplace las variables `<…>` por los `id` guardados.", ""]

    n += 1
    consulta = next(u for u in USERS if u["username"] == "consulta.test")
    denied = pick_example(rows, lambda s_i, c, p, r: not c["external"] and c["method"] != "GET"
                          and not matching_grant(consulta, p))
    if denied:
        s_i, c_i, s, c, p, r = denied
        out += [f"### {n}. `consulta.test` intenta crear (rechazado)", ""]
        out += token_command("consulta.test", "TOKEN_CONSULTA")
        out += ["", f"Intenta el paso {s_i + 1:02d} (*{s['title']}*), llamada {c_i + 1}:", ""]
        out += curl_for(c, "TOKEN_CONSULTA")
        out += ["", "Respuesta `403 Forbidden`:", "", "```json",
                json.dumps(forbidden_body(r, p, c["path"]), ensure_ascii=False, indent=2), "```", ""]
        out += [f"`consulta.test` solo tiene `perm:all:all:read`: puede **leer**, pero la URL exige `{p}`. "
                "El servicio no ejecuta nada: ni siquiera valida el cuerpo.", ""]

    read = pick_example(rows, lambda s_i, c, p, r: not c["external"] and c["method"] == "GET")
    if read:
        n += 1
        s_i, c_i, s, c, p, r = read
        out += [f"### {n}. `consulta.test` consulta (permitido)", ""]
        out += curl_for(c, "TOKEN_CONSULTA")
        out += ["", f"Responde `200 OK` con la misma información que ve `admin.test` en el paso {s_i + 1:02d}: "
                f"`perm:all:all:read` cubre `{p}`. Lo mismo pasa con `reportes.test`, `compras.test`, `ventas.test` "
                "e `inventario.test`.", ""]

        n += 1
        out += [f"### {n}. `inventario.test` consulta (permitido)", ""]
        out += token_command("inventario.test", "TOKEN_INVENTARIO")
        out += [""]
        out += curl_for(c, "TOKEN_INVENTARIO")
        out += ["", "Responde `200 OK`: `inventario.test` tiene `perm:operational-context:all:read`, porque Inventory "
                "trabaja por empresa y sucursal. No tiene lectura en Party Identity, así que no podría consultar allá "
                "la razón social de la empresa.", ""]

    deactivate = pick_example(rows, lambda s_i, c, p, r: p.endswith(":delete"))
    if deactivate:
        n += 1
        s_i, c_i, s, c, p, r = deactivate
        out += [f"### {n}. `supervisor.test` intenta inactivar (rechazado)", ""]
        out += token_command("supervisor.test", "TOKEN_SUPERVISOR")
        out += [""]
        out += curl_for(c, "TOKEN_SUPERVISOR")
        out += ["", "Respuesta `403 Forbidden`:", "", "```json",
                json.dumps(forbidden_body(r, p, c["path"]), ensure_ascii=False, indent=2), "```", ""]
        out += ["`supervisor.test` tiene `perm:all:all:read`, `perm:all:all:create` y `perm:all:all:update`, pero **no** "
                "`delete`. Inactivar queda para `admin.test`.", ""]

    n += 1
    out += [f"### {n}. Sin token (rechazado)", "",
            "Cualquier URL de `/api/v1` sin el encabezado `Authorization` responde `401 Unauthorized`, antes de revisar permisos.", ""]
    out += ["---", "", "[← Orden del ejercicio](ORDEN.md)", ""]
    return "\n".join(out)


# ------------------------------------------------------------------ documento general

def render_general(exercises, all_records):
    matrix = OrderedDict()
    for ex, records in zip(exercises, all_records):
        for s_i, c_i, s, c, p, r in calls_with_permission(ex, records):
            key = (endpoint(c), p)
            matrix.setdefault(key, [])
            number = ex["folder"].split("-")[0]
            if number not in matrix[key]:
                matrix[key].append(number)

    out = ["# Usuarios y permisos en los ejercicios", "", "[← Todos los ejercicios](README.md)", ""]
    out += ["Este documento explica qué usuarios de prueba trae el realm de Keycloak "
            "(`infrastructure/keycloak/realm-template/sio-realm.template.json`), qué permiso exige cada URL que usan "
            "los ejercicios y qué usuarios pueden llamarla. Cada ejercicio tiene además su propio `USUARIOS.md`.", ""]

    out += ["## Cómo funcionan los permisos", "",
            "1. El usuario inicia sesión en Keycloak (`http://localhost:8081`, realm `sio`, cliente `sio-web`) y recibe un token.",
            "2. Los permisos vienen en el token, en `resource_access.sio-api.roles`. Keycloak se los asigna por el "
            "**grupo** al que pertenece el usuario.",
            "3. Cada permiso tiene la forma `perm:{servicio}:{recurso}:{acción}`. En los permisos del usuario, "
            "`all` vale como comodín en cualquier parte:",
            "   - `perm:all:all:all` → cualquier acción, en cualquier recurso, de cualquier servicio.",
            "   - `perm:all:all:read` → solo `read`, pero en todos los servicios.",
            "   - `perm:operational-context:all:read` → solo `read`, solo en Operational Context.",
            "4. Cada URL exige **un** permiso concreto (por ejemplo `perm:operational-context:companies:create`). "
            "Si ninguno de los permisos del usuario lo cubre, el servicio responde `403 Forbidden` e indica cuál falta. "
            "Sin token, o con un token vencido, responde `401 Unauthorized`.",
            "5. El permiso se revisa **antes** que el cuerpo: un usuario sin permiso recibe `403` aunque el JSON esté mal.", ""]

    out += ["## Usuarios de prueba", "",
            "Todos comparten la contraseña de la variable `KEYCLOAK_TEST_USER_PASSWORD` (`infrastructure/.env`).", "",
            "| Usuario | Grupo | Permisos del grupo | En Operational Context puede |", "| --- | --- | --- | --- |"]
    summary = {
        "admin.test": "Todo, incluido inactivar",
        "supervisor.test": "Consultar, crear, modificar y reactivar. **No** inactivar",
        "compras.test": "Solo consultar",
        "ventas.test": "Solo consultar",
        "inventario.test": "Solo consultar",
        "reportes.test": "Solo consultar",
        "consulta.test": "Solo consultar",
    }
    for u in USERS:
        perms = "<br>".join(f"`{p}`" for p in u["perms"])
        out.append(f"| `{u['username']}` | `{u['group']}` | {perms} | {summary.get(u['username'], '')} |")
    out.append("")

    out += ["## Cómo obtener el token de cada usuario", "",
            "Cambie `username` por el usuario que quiera probar:", ""]
    out += token_command("consulta.test", "TOKEN")
    out += ["", "En **PowerShell** (Windows):", "",
            "```powershell",
            "$body = @{ grant_type = 'password'; client_id = 'sio-web'; scope = 'openid'",
            "           username = 'consulta.test'; password = $env:KEYCLOAK_TEST_USER_PASSWORD }",
            f"$TOKEN = (Invoke-RestMethod -Method Post -Uri '{KEYCLOAK}' -Body $body).access_token",
            f"Invoke-RestMethod -Uri '{SERVICE_URL}/api/v1/companies' `",
            "  -Headers @{ Authorization = \"Bearer $TOKEN\" }",
            "```", "",
            "Luego envíe el token en cada llamada:", "", "```http", "Authorization: Bearer <TOKEN>", "```", "",
            "Atajo: `python services/get_token.py <rol>` (por ejemplo `TOKEN=$(python services/get_token.py consulta)`) "
            "obtiene el token de `<rol>.test`. Lee la contraseña de `KEYCLOAK_TEST_USER_PASSWORD` o de `infrastructure/.env`.", ""]

    out += ["## Permiso de cada URL de los ejercicios", "",
            "✅ = puede · ❌ = recibe `403`. Columna *Ejercicios*: en cuáles se usa la URL.", ""]
    head, sep = user_table_header()
    out += ["| Método y URL | Permiso requerido " + head + " Ejercicios |", "| --- | --- " + sep + " --- |"]
    for (ep, p), numbers in matrix.items():
        cells = " | ".join(mark(u, p) for u in USERS)
        out.append(f"| `{ep}` | `{p}` | {cells} | {', '.join(numbers)} |")
    out.append("")

    out += ["## Permisos que no son obvios", ""]
    out += [f"- `{p}`: {text}" for p, text in NOTES.items()]
    out += ["- Las URL de `http://localhost:8000` son de **Geography** y las de `http://localhost:8002` de **Party "
            "Identity**: exigen permisos de esos servicios.", ""]

    out += ["## Qué usuario usar", "",
            "| Para… | Usuario |", "| --- | --- |",
            "| Hacer los ejercicios completos | `admin.test` |",
            "| Crear y modificar sin poder inactivar | `supervisor.test` |",
            "| Verificar lo cargado | `consulta.test` o `reportes.test` |",
            "| Probar rechazos por falta de permiso | `consulta.test` o `inventario.test` en cualquier `POST` o `PUT`; `supervisor.test` al inactivar |", ""]
    return "\n".join(out)
