"""Documentación de usuarios y permisos para los ejercicios de Operational Context."""

import json
import re
from collections import OrderedDict

from sio_auth import FORBIDDEN_DETAIL

from tests.examples.users import USERS, allowed_all, as_list, first_missing, matching_grant

SHORT = {u["username"]: u["username"].replace(".test", "") for u in USERS}
KEYCLOAK = "http://localhost:8081/realms/sio/protocol/openid-connect/token"
SERVICE_URL = "http://localhost:8004"
UUID_IN_TEXT = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
PLACEHOLDER = re.compile(r"<[A-Z0-9_]+>")

NOTES = {
    "perm:operational-context:companies:delete": "Inactivar una empresa (`POST .../deactivate`) exige `delete`, "
    "aunque no la elimina; reactivar (`POST .../reactivate`) exige `update`. Desde la Fase B ambas exigen además "
    "`perm:operational-context:platform:administer`: `supervisor.test` no puede ninguna de las dos.",
    "perm:operational-context:platform:administer": "Alcance de plataforma (Fase B, DS-05): registrar, inactivar y "
    "reactivar empresas y ver todas las empresas sin ser miembro. Solo lo concede `perm:all:all:all` "
    "(`administradores`); los comodines de lectura, creación o modificación **no** lo conceden.",
    "perm:operational-context:platform:lookup": "Consulta técnica entre servicios (Fase B, FR-045): leer por UUID sin "
    "membresía y comprobar el acceso de otro usuario. Es para identidades técnicas; ningún grupo de usuarios la tiene "
    "salvo `administradores` (por `perm:all:all:all`).",
    "perm:operational-context:application_users:create": "Para registrar un usuario operativo el token debe poder leer "
    "`person_identities` en Party Identity (el servicio valida la persona con ese token); la cuenta de Keycloak la "
    "verifica el servicio con su propia identidad técnica.",
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
    permission = first_missing(user, permission) or as_list(permission)[0]
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


# Rutas que no se filtran por empresa del usuario (Fase B, DS-06).
UNSCOPED = ("/me/operational-context", "/operational-access")


def scoped(c):
    """La URL aplica el aislamiento por empresa (`404` fuera del alcance)."""
    if c is None or c["external"]:
        return False
    path = c["path"].split("?")[0]
    if path.endswith(UNSCOPED):
        return False
    return not (c["method"] == "POST" and path.endswith("/companies"))


def permission_text(permissions):
    return " + ".join(f"`{p}`" for p in as_list(permissions))


def permission_lines(permissions, c=None):
    """Bloque que se agrega en cada llamada de los pasos."""
    permissions = as_list(permissions)
    yes, no = [], OrderedDict()
    for user in USERS:
        if allowed_all(user, permissions):
            grants = ", ".join(f"`{g}`" for g in OrderedDict.fromkeys(matching_grant(user, p) for p in permissions))
            yes.append(f"`{user['username']}` (por {grants})")
        else:
            no.setdefault(reason(user, permissions), []).append(f"`{user['username']}`")
    label = "Permiso que exige la URL" if len(permissions) == 1 else "Permisos que exige la URL (todos)"
    out = [f"**{label}:** {permission_text(permissions)}", ""]
    out.append("- ✅ **Pueden:** " + ", ".join(yes))
    if no:
        denied = "; ".join(f"{', '.join(users)} — {plural(why) if len(users) > 1 else why}" for why, users in no.items())
        out.append(f"- ❌ **No pueden (responde `403`):** {denied}")
    for permission in permissions:
        note = NOTES.get(permission)
        if note:
            out.append(f"- ℹ️ {note}")
    if scoped(c):
        out.append("- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía "
                   "`ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un "
                   "`id` inexistente.")
    out.append("")
    return out


def mark(user, permission):
    return "✅" if allowed_all(user, permission) else "❌"


def calls_with_permission(ex, records):
    rows = []
    for s_index, s in enumerate(ex["steps"]):
        for c_index, c in enumerate(s["calls"]):
            record = records.get((s_index, c_index), {})
            permission = record.get("permission") or c.get("perm")
            if permission:
                permissions = [permission, *record.get("also", c.get("also", []))]
                rows.append((s_index, c_index, s, c, permissions, record))
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
        return {"detail": FORBIDDEN_DETAIL}
    body["instance"] = UUID_IN_TEXT.sub("{id}", PLACEHOLDER.sub("{id}", path.split("?")[0]))
    body["trace_id"] = "<trace_id>"
    return body


# ------------------------------------------------------------------ USUARIOS.md de cada ejercicio

def user_summary(rows):
    lines = []
    for user in USERS:
        blocked = [(s_i, c) for s_i, _, _, c, p, _ in rows if not allowed_all(user, p)]
        reads = sorted({s_i + 1 for s_i, _, _, c, p, r in rows if c["method"] == "GET" and not c["external"]
                        and allowed_all(user, p) and r.get("verified", {}).get(user["username"], 200) == 200})
        isolated = sorted({s_i + 1 for s_i, _, _, c, p, r in rows if c["method"] == "GET" and not c["external"]
                           and r.get("verified", {}).get(user["username"]) == 404})
        reads = [n for n in reads if n not in isolated]
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
            elif not isolated:
                text += " No puede hacer ninguna consulta de Operational Context."
        if isolated:
            text += (" Con permiso de lectura pero **sin membresía** en la empresa, sus consultas de los pasos "
                     + ", ".join(f"{n:02d}" for n in isolated) + " responden `404` (aislamiento por empresa).")
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
    out += ["", "**Para hacer el ejercicio completo use `admin.test`** (tiene `platform:administer` por "
            "`perm:all:all:all`). Los demás usuarios solo operan en las empresas donde tienen membresía `ACTIVE`; "
            "`supervisor.test` puede crear y modificar allí, pero no inactivar ni registrar, inactivar o reactivar "
            "empresas.", ""]

    out += ["## Permiso por URL", "",
            "✅ = el usuario tiene el permiso (o los permisos) de la llamada · ❌ = recibe `403 Forbidden`. "
            "Tener el permiso no basta en las URL con 🔒: fuera de sus empresas el usuario recibe `404`.", ""]
    head, sep = user_table_header()
    out += ["| Paso | Llamada | Método y URL | Permiso requerido " + head, "| --- | --- | --- | --- " + sep]
    for s_i, c_i, s, c, p, _ in rows:
        cells = " | ".join(mark(u, p) for u in USERS)
        lock = " 🔒" if scoped(c) else ""
        out.append(f"| [{s_i + 1:02d}]({s['file']}) | {c_i + 1}. {c['title']} | `{endpoint(c)}`{lock} | "
                   f"{permission_text(p)} | {cells} |")
    out.append("")

    out += ["## Ejemplos de uso con los usuarios", ""]
    out += ["La contraseña de todos los usuarios de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de "
            "`infrastructure/.env`. Cárguela en la terminal antes de pedir tokens.", ""]

    n = 1
    out += [f"### {n}. Ejecutar el ejercicio con `admin.test`", ""]
    out += token_command("admin.test", "TOKEN_ADMIN")
    create = pick_example(rows, lambda s_i, c, p, r: c["method"] == "POST" and p[0].endswith(":create") and not c["external"])
    if create:
        out += ["", f"Por ejemplo, el paso {create[0] + 1:02d} (*{create[2]['title']}*):", ""]
        out += curl_for(create[3], "TOKEN_ADMIN")
        out += ["", f"Responde `201 Created`: `admin.test` tiene `perm:all:all:all`, que cubre {permission_text(create[4])}. "
                "Reemplace las variables `<…>` por los `id` guardados.", ""]

    n += 1
    consulta = next(u for u in USERS if u["username"] == "consulta.test")
    denied = pick_example(rows, lambda s_i, c, p, r: not c["external"] and c["method"] != "GET"
                          and not allowed_all(consulta, p))
    if denied:
        s_i, c_i, s, c, p, r = denied
        out += [f"### {n}. `consulta.test` intenta crear (rechazado)", ""]
        out += token_command("consulta.test", "TOKEN_CONSULTA")
        out += ["", f"Intenta el paso {s_i + 1:02d} (*{s['title']}*), llamada {c_i + 1}:", ""]
        out += curl_for(c, "TOKEN_CONSULTA")
        out += ["", "Respuesta `403 Forbidden`:", "", "```json",
                json.dumps(forbidden_body(r, p, c["path"]), ensure_ascii=False, indent=2), "```", ""]
        out += [f"`consulta.test` solo tiene lecturas explícitas (sin `create`, `update` ni `delete`): puede **leer**, "
                f"pero la URL exige {permission_text(p)}. El servicio no ejecuta nada: ni siquiera valida el cuerpo.", ""]

    read = pick_example(rows, lambda s_i, c, p, r: not c["external"] and c["method"] == "GET")
    if read:
        n += 1
        s_i, c_i, s, c, p, r = read
        verified = r.get("verified", {})
        out += [f"### {n}. `consulta.test` consulta", ""]
        out += curl_for(c, "TOKEN_CONSULTA")
        if verified.get("consulta.test", 200) == 404:
            out += ["", f"Responde `404 Not Found`: `{matching_grant(consulta, as_list(p)[0])}` cubre {permission_text(p)}, pero "
                    "`consulta.test` **no es miembro** de la empresa del paso " f"{s_i + 1:02d}. Fuera de su alcance, "
                    "el recurso se trata como inexistente (aislamiento por empresa, DS-06).", ""]
        else:
            out += ["", f"Responde `200 OK` con la misma información que ve `admin.test` en el paso {s_i + 1:02d}: "
                    f"`{matching_grant(consulta, as_list(p)[0])}` cubre {permission_text(p)}.", ""]

        n += 1
        out += [f"### {n}. `inventario.test` consulta", ""]
        out += token_command("inventario.test", "TOKEN_INVENTARIO")
        out += [""]
        out += curl_for(c, "TOKEN_INVENTARIO")
        if verified.get("inventario.test", 200) == 404:
            out += ["", "Responde `404 Not Found`: `inventario.test` tiene `perm:operational-context:all:read`, pero no "
                    "es miembro de la empresa. Tener el permiso no basta: también se necesita la membresía.", ""]
        else:
            out += ["", "Responde `200 OK`: `inventario.test` tiene `perm:operational-context:all:read` y es miembro "
                    "de la empresa.", ""]

    deactivate = pick_example(rows, lambda s_i, c, p, r: p[0].endswith(":delete"))
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
            key = (endpoint(c), tuple(p), scoped(c))
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
            "   - `perm:all:all:read` → solo `read`, pero en todos los servicios (en el realm vigente solo lo tiene "
            "`supervisores`; `reportes` y `consulta` tienen lecturas **explícitas** de todos los servicios, salvo los "
            "datos de contacto y representantes legales de Party Identity).",
            "   - `perm:operational-context:all:read` → solo `read`, solo en Operational Context.",
            "4. Cada URL exige un permiso concreto (por ejemplo `perm:operational-context:companies:create`); registrar, "
            "inactivar y reactivar empresas exigen además `perm:operational-context:platform:administer`. "
            "Si falta alguno, el servicio responde `403 Forbidden` e indica cuál. "
            "Sin token, o con un token vencido, responde `401 Unauthorized`.",
            "5. El permiso se revisa **antes** que el cuerpo: un usuario sin permiso recibe `403` aunque el JSON esté mal.",
            "6. **Aislamiento por empresa (Fase B):** el permiso dice *qué* puede hacer el usuario; la membresía dice "
            "*dónde*. Un usuario sin `platform:administer` solo ve y opera las empresas donde tiene una membresía "
            "`ACTIVE`; el resto responde `404`, igual que un `id` inexistente (URL marcadas con 🔒).", ""]

    out += ["## Usuarios de prueba", "",
            "Todos comparten la contraseña de la variable `KEYCLOAK_TEST_USER_PASSWORD` (`infrastructure/.env`).", "",
            "| Usuario | Grupo | Permisos del grupo | En Operational Context puede |", "| --- | --- | --- | --- |"]
    summary = {
        "admin.test": "Todo, en todas las empresas (alcance de plataforma)",
        "supervisor.test": "En sus empresas: consultar, crear, modificar y reactivar sucursales, usuarios y asignaciones. "
        "**No** inactivar ni registrar, inactivar o reactivar empresas",
        "compras.test": "Solo consultar, en sus empresas",
        "ventas.test": "Solo consultar, en sus empresas",
        "inventario.test": "Solo consultar, en sus empresas",
        "reportes.test": "Solo consultar, en sus empresas",
        "consulta.test": "Solo consultar, en sus empresas",
    }
    for u in USERS:
        if len(u["perms"]) <= 10:
            perms = "<br>".join(f"`{p}`" for p in u["perms"])
        else:
            own = [p for p in u["perms"] if p.startswith("perm:operational-context:") or ":all:" in p]
            perms = (f"{len(u['perms'])} permisos explícitos; en Operational Context: "
                     + "<br>".join(f"`{p}`" for p in own))
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
            "✅ = tiene el permiso · ❌ = recibe `403`. 🔒 = además exige membresía en la empresa (si no, `404`). "
            "Columna *Ejercicios*: en cuáles se usa la URL.", ""]
    head, sep = user_table_header()
    out += ["| Método y URL | Permiso requerido " + head + " Ejercicios |", "| --- | --- " + sep + " --- |"]
    for (ep, p, is_scoped), numbers in matrix.items():
        cells = " | ".join(mark(u, list(p)) for u in USERS)
        lock = " 🔒" if is_scoped else ""
        out.append(f"| `{ep}`{lock} | {permission_text(p)} | {cells} | {', '.join(numbers)} |")
    out.append("")

    out += ["## Permisos que no son obvios", ""]
    out += [f"- `{p}`: {text}" for p, text in NOTES.items()]
    out += ["- Las URL de `http://localhost:8000` son de **Geography** y las de `http://localhost:8002` de **Party "
            "Identity**: exigen permisos de esos servicios.", ""]

    out += ["## Qué usuario usar", "",
            "| Para… | Usuario |", "| --- | --- |",
            "| Hacer los ejercicios completos | `admin.test` |",
            "| Crear y modificar sin poder inactivar, dentro de sus empresas | `supervisor.test` (con membresía) |",
            "| Verificar lo cargado | `consulta.test` o `reportes.test` (con membresía en la empresa) |",
            "| Probar rechazos por falta de permiso | `consulta.test` o `inventario.test` en cualquier `POST` o `PUT`; `supervisor.test` al inactivar |", ""]
    return "\n".join(out)
