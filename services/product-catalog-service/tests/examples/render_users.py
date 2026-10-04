"""Documentación de usuarios y permisos para los ejercicios."""

import json
import re
from collections import OrderedDict

from sio_auth import FORBIDDEN_DETAIL

from tests.examples.users import USERS, matching_grant

SHORT = {u["username"]: u["username"].replace(".test", "") for u in USERS}
KEYCLOAK = "http://localhost:8081/realms/sio/protocol/openid-connect/token"
UUID_IN_TEXT = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
PLACEHOLDER = re.compile(r"<[A-Z0-9_]+>")

NOTES = {
    "perm:product-catalog:attribute-definitions:update": "Crear una **opción** modifica la definición del atributo: exige `update`, no `create`.",
    "perm:product-catalog:categories:update": "Asociar un atributo a una categoría modifica la categoría: exige `update`.",
    "perm:product-catalog:group-types:create": "Los grupos se crean dentro de su tipo de grupo: exige `create` sobre `group-types`.",
    "perm:product-catalog:products:update": "Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, "
                                           "códigos, grupos, imágenes) exige `update` sobre `products`.",
    "perm:product-catalog:products:deactivate": "Inactivar es una acción propia (`deactivate`): no la cubren `create` ni `update`.",
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
    path = re.sub(r"/by-identifier/[^/]+$", "/by-identifier/{codigo}", path)
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
    url = c["path"] if c["path"].startswith("http") else f"http://localhost:8003{c['path']}"
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
    body["instance"] = UUID_IN_TEXT.sub("{id}", PLACEHOLDER.sub("{id}", path.split("?")[0])).replace("http://localhost:8003", "")
    body["trace_id"] = "<trace_id>"
    return body


# ------------------------------------------------------------------ USUARIOS.md de cada ejercicio

def user_summary(ex, rows):
    lines = []
    for user in USERS:
        blocked = [(s_i, c) for s_i, _, _, c, p, _ in rows if not matching_grant(user, p) and not c["cond"]]
        cond_blocked = [(s_i, c) for s_i, _, _, c, p, _ in rows if not matching_grant(user, p) and c["cond"]]
        reads = sorted({s_i + 1 for s_i, _, _, c, p, _ in rows if c["method"] == "GET" and matching_grant(user, p)})
        name = f"**`{user['username']}`**"
        if not blocked:
            text = f"{name}: puede ejecutar **todo el ejercicio**."
            if cond_blocked:
                text += (f" Excepto crear el fabricante (paso {cond_blocked[0][0] + 1:02d}): solo puede continuar "
                         "si el fabricante ya existe.")
        else:
            first_step, first_call = blocked[0]
            permission = next(p for s_i, _, _, c, p, _ in rows if c is first_call)
            text = (f"{name}: **no puede completar el ejercicio**. Se detiene en el paso {first_step + 1:02d} "
                    f"(*{first_call['title']}*): {reason(user, permission)}.")
            if reads:
                text += " Sí puede hacer las consultas (`GET`) de los pasos " + ", ".join(f"{n:02d}" for n in reads) + "."
            else:
                text += " No puede hacer ninguna llamada del ejercicio."
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
            "usuario sin permiso recibió `403`, y los usuarios de solo lectura obtuvieron `200` en las consultas.", ""]

    out += ["## Resumen por usuario", ""]
    out += user_summary(ex, rows)
    out += ["", "**Para hacer el ejercicio completo use `admin.test`.** `supervisor.test` también sirve para crear y "
            "modificar, pero no para inactivar.", ""]

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
    create = pick_example(rows, lambda s_i, c, p, r: c["method"] == "POST" and p.endswith(":products:create"))
    if create:
        out += ["", f"Por ejemplo, el paso {create[0] + 1:02d} (*{create[2]['title']}*):", ""]
        out += curl_for(create[3], "TOKEN_ADMIN")
        out += ["", f"Responde `201 Created`: `admin.test` tiene `perm:all:all:all`, que cubre `{create[4]}`. "
                "Reemplace las variables `<…>` por los `id` guardados.", ""]

    n += 1
    denied = pick_example(rows, lambda s_i, c, p, r: not c["external"] and c["method"] != "GET"
                          and not matching_grant(USERS[-1], p))
    if denied:
        s_i, c_i, s, c, p, r = denied
        out += [f"### {n}. `consulta.test` intenta crear (rechazado)", ""]
        out += token_command("consulta.test", "TOKEN_CONSULTA")
        out += ["", f"Intenta el paso {s_i + 1:02d} (*{s['title']}*), llamada {c_i + 1}:", ""]
        out += curl_for(c, "TOKEN_CONSULTA")
        out += ["", "Respuesta `403 Forbidden`:", "", "```json",
                json.dumps(forbidden_body(r, p, c["path"]), ensure_ascii=False, indent=2), "```", ""]
        consulta = next(u for u in USERS if u["username"] == "consulta.test")
        grants = ", ".join(f"`{g}`" for g in consulta["perms"] if g.startswith("perm:product-catalog:")) or "ninguno"
        out += [f"`consulta.test` solo tiene lecturas explícitas (en el catálogo: {grants}): puede **leer**, pero la "
                f"URL exige `{p}`. El servicio no ejecuta nada: ni siquiera valida el cuerpo.", ""]

    n += 1
    read = pick_example(rows, lambda s_i, c, p, r: not c["external"] and c["method"] == "GET" and s_i == len(ex["steps"]) - 1)
    if read:
        s_i, c_i, s, c, p, r = read
        out += [f"### {n}. `consulta.test` consulta el resultado (permitido)", ""]
        out += curl_for(c, "TOKEN_CONSULTA")
        consulta = next(u for u in USERS if u["username"] == "consulta.test")
        readers = [f"`{u['username']}`" for u in USERS
                   if u["username"] not in ("admin.test", "consulta.test") and matching_grant(u, p)]
        out += ["", f"Responde `200 OK` con la misma información que ve `admin.test` en el paso {s_i + 1:02d}: "
                f"`{matching_grant(consulta, p)}` cubre `{p}`. Lo mismo pasa con {', '.join(readers)}, que tienen "
                "lectura sobre `product-catalog`.", ""]

    deactivate = pick_example(rows, lambda s_i, c, p, r: p.endswith(":deactivate"))
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
                "`deactivate`. Por eso pudo cargar todo el producto y no puede inactivarlo: esa acción queda para `admin.test`.", ""]

    party = pick_example(rows, lambda s_i, c, p, r: p == "perm:party-identity:organization_identities:read")
    if party:
        n += 1
        s_i, c_i, s, c, p, r = party
        out += [f"### {n}. `inventario.test` busca el fabricante (rechazado)", ""]
        out += token_command("inventario.test", "TOKEN_INVENTARIO")
        out += [""]
        out += curl_for(c, "TOKEN_INVENTARIO")
        out += ["", "Respuesta `403 Forbidden` (formato de Party Identity Service):", "", "```json",
                json.dumps({"detail": FORBIDDEN_DETAIL}, ensure_ascii=False, indent=2), "```", ""]
        searchers = [f"`{u['username']}`" for u in USERS
                     if u["username"] not in ("admin.test", "inventario.test") and matching_grant(u, p)]
        out += ["`inventario.test` lee el catálogo (`perm:product-catalog:all:read`) y Geography, pero **no** tiene "
                f"ningún permiso sobre `party-identity`. Sí pueden hacer esta búsqueda: {', '.join(searchers)} "
                f"(lectura explícita de `{p}`).", ""]

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
            "**grupo** al que pertenece el usuario (el usuario no tiene roles propios).",
            "3. Cada permiso tiene la forma `perm:{servicio}:{recurso}:{acción}`. En los permisos del usuario, "
            "`all` vale como comodín en cualquier parte:",
            "   - `perm:all:all:all` → cualquier acción, en cualquier recurso, de cualquier servicio.",
            "   - `perm:all:all:read` → solo `read`, pero en todos los servicios (en el realm vigente solo lo tiene "
            "`supervisores`; `reportes` y `consulta` tienen lecturas **explícitas** de todos los servicios, salvo los "
            "datos de contacto y representantes legales de Party Identity).",
            "   - `perm:product-catalog:all:read` → solo `read`, solo en el catálogo.",
            "4. Cada URL exige **un** permiso concreto (por ejemplo `perm:product-catalog:brands:create`). "
            "Si ninguno de los permisos del usuario lo cubre, el servicio responde `403 Forbidden` e indica cuál falta. "
            "Sin token, o con un token vencido, responde `401 Unauthorized`.",
            "5. El permiso se revisa **antes** que el cuerpo: un usuario sin permiso recibe `403` aunque el JSON esté mal.", ""]

    out += ["## Usuarios de prueba", "",
            "Todos comparten la contraseña de la variable `KEYCLOAK_TEST_USER_PASSWORD` (`infrastructure/.env`).", "",
            "| Usuario | Grupo | Permisos del grupo | En el catálogo puede |", "| --- | --- | --- | --- |"]
    summary = {
        "admin.test": "Todo, incluido inactivar",
        "supervisor.test": "Consultar, crear y modificar. **No** inactivar",
        "compras.test": "Solo consultar",
        "ventas.test": "Solo consultar",
        "inventario.test": "Solo consultar (y no puede consultar fabricantes en Party Identity)",
        "reportes.test": "Solo consultar",
        "consulta.test": "Solo consultar",
    }
    for u in USERS:
        if len(u["perms"]) <= 10:
            perms = "<br>".join(f"`{p}`" for p in u["perms"])
        else:
            own = [p for p in u["perms"] if p.startswith("perm:product-catalog:") or ":all:" in p]
            perms = (f"{len(u['perms'])} permisos explícitos; en el catálogo: "
                     + "<br>".join(f"`{p}`" for p in own))
        out.append(f"| `{u['username']}` | `{u['group']}` | {perms} | {summary.get(u['username'], '')} |")
    out.append("")

    out += ["## Cómo obtener el token de cada usuario", "",
            "Cambie `username` por el usuario que quiera probar:", ""]
    out += token_command("consulta.test", "TOKEN")
    out += ["", "En **PowerShell** (Windows), donde `curl` no es el curl real:", "",
            "```powershell",
            "$body = @{ grant_type = 'password'; client_id = 'sio-web'; scope = 'openid'",
            "           username = 'consulta.test'; password = $env:KEYCLOAK_TEST_USER_PASSWORD }",
            f"$TOKEN = (Invoke-RestMethod -Method Post -Uri '{KEYCLOAK}' -Body $body).access_token",
            "Invoke-RestMethod -Uri 'http://localhost:8003/api/v1/units-of-measure?code=UND' `",
            "  -Headers @{ Authorization = \"Bearer $TOKEN\" }",
            "```", "",
            "En Postman: pestaña *Authorization* → tipo *OAuth 2.0* → *Password Credentials*, con la URL del token de arriba, "
            "cliente `sio-web` y el usuario y contraseña.", "",
            "Luego envíe el token en cada llamada:", "", "```http", "Authorization: Bearer <TOKEN>", "```", "",
            "Atajo: `python services/get_token.py <rol>` (por ejemplo `TOKEN=$(python services/get_token.py consulta)`) "
            "obtiene el token de `<rol>.test`; sin argumento muestra un menú. Lee la contraseña de "
            "`KEYCLOAK_TEST_USER_PASSWORD` o de `infrastructure/.env`.", ""]

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
    out += ["- Las URL de `http://localhost:8002` son de **Party Identity** y las de `http://localhost:8000` de "
            "**Geography**: exigen permisos de esos servicios, no del catálogo.", ""]

    out += ["## Qué usuario usar", "",
            "| Para… | Usuario |", "| --- | --- |",
            "| Hacer los ejercicios completos | `admin.test` |",
            "| Cargar productos sin poder inactivarlos | `supervisor.test` (falla en el paso de inactivar del ejercicio 5) |",
            "| Verificar lo cargado (pasos de consulta y verificación) | `consulta.test` o `reportes.test` |",
            "| Probar rechazos por falta de permiso | `consulta.test` en cualquier `POST` o `PUT`; `inventario.test` al buscar fabricantes |", ""]
    return "\n".join(out)
