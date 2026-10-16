"""Documentación de usuarios y permisos para los ejercicios de Commercial Relationship."""

import json
import re
from collections import OrderedDict

from sio_auth import FORBIDDEN_DETAIL

from tests.examples.users import USERS, allowed_all, as_list, first_missing, matching_grant

SHORT = {u["username"]: u["username"].replace(".test", "") for u in USERS}
KEYCLOAK = "http://localhost:8081/realms/sio/protocol/openid-connect/token"
SERVICE_URL = "http://localhost:8005"
UUID_IN_TEXT = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
PLACEHOLDER = re.compile(r"<[A-Z0-9_]+>")

NOTES = {
    "perm:commercial-relationship:company_products:create": "Adoptar no exige permisos en Product Catalog al "
    "usuario: la elegibilidad y el registro de primer uso los hace el servicio con su propia identidad técnica "
    "(cliente `commercial-relationship-service`).",
    "perm:commercial-relationship:company_products:delete": "Inactivar exige `delete` aunque no borra nada; reactivar "
    "exige `update`. `supervisor.test` no tiene `delete`.",
    "perm:commercial-relationship:company_customers:create": "Para incorporar clientes el token del usuario debe "
    "poder además **leer** en Party Identity (personas, organizaciones y personas de contacto) y, para "
    "organizaciones, `perm:operational-context:companies:read` (comprobación de la propia empresa). "
    "`administradores` y `supervisores` tienen esa lectura.",
    "perm:commercial-relationship:company_suppliers:create": "Igual que los clientes: el token debe poder leer "
    "organizaciones y personas de contacto en Party Identity y la empresa en Operational Context.",
    "perm:commercial-relationship:company_suppliers:delete": "Inactivar **y bloquear** un proveedor exigen `delete` "
    "(DS-16); reactivar y desbloquear exigen `update`. `supervisor.test` no puede bloquear.",
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
        return f"no tiene ningún permiso sobre `{resource}` de `{service}`"
    actions = ", ".join(f"`{a}`" for a in sorted(set(related)))
    return f"sobre `{resource}` solo tiene {actions}; le falta `{action}`"


def plural(text):
    return (text.replace("solo tiene", "solo tienen").replace("le falta", "les falta")
            .replace("no tiene ningún", "no tienen ningún"))


def endpoint(c):
    path = c["path"].split("?")[0]
    path = PLACEHOLDER.sub("{id}", path)
    return f"{c['method']} {path}"


def scoped(c):
    """La URL aplica el aislamiento por empresa (`404` fuera del alcance).

    Todas las rutas del servicio lo aplican salvo dos que no responden `404`: la
    consulta por lotes informa `found: false` para los productos de empresas ajenas y
    el resumen de empresas solo lista las empresas del usuario (FR-046).
    """
    if c is None or c["external"]:
        return False
    path = c["path"].split("?")[0]
    return not (path.endswith("/batch-lookup") or path.endswith("/company-summaries"))


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
        out.append("- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la "
                   "empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, "
                   "**también para `admin.test`** (DS-03).")
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
        own = [(s_i, c, p) for s_i, _, _, c, p, _ in rows if not c["external"]]
        reads = sorted({s_i + 1 for s_i, c, p in own if c["method"] == "GET" and allowed_all(user, p)})
        name = f"**`{user['username']}`**"
        if not blocked:
            text = f"{name}: puede ejecutar **todo el ejercicio** (con membresía en la empresa)."
        else:
            first_step, first_call = blocked[0]
            permission = next(p for s_i, _, _, c, p, _ in rows if c is first_call)
            text = (f"{name}: **no puede completar el ejercicio**. Se detiene en el paso {first_step + 1:02d} "
                    f"(*{first_call['title']}*): {reason(user, permission)}.")
            if reads:
                text += " Sí puede hacer las consultas (`GET`) de los pasos " + ", ".join(f"{n:02d}" for n in reads) + "."
            elif own and not any(allowed_all(user, p) for _, _, p in own):
                text += " No tiene ningún permiso de Commercial Relationship: todas sus llamadas a este servicio responden `403`."
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
            "usuario sin permiso recibió `403`, y los usuarios con lectura (miembros de la empresa) obtuvieron la "
            "respuesta en las consultas.", ""]

    out += ["## Resumen por usuario", ""]
    out += user_summary(rows)
    out += ["", "**Para hacer el ejercicio completo use `admin.test`**, siempre que tenga membresía `ACTIVE` en la "
            "empresa: en Commercial Relationship ni siquiera `perm:all:all:all` exime de la membresía (DS-03). "
            "`supervisor.test` puede crear y modificar, pero no inactivar ni bloquear (salvo políticas de ganancia, "
            "spec 021).", ""]

    out += ["## Permiso por URL", "",
            "✅ = el usuario tiene el permiso de la llamada · ❌ = recibe `403 Forbidden`. "
            "Tener el permiso no basta en las URL con 🔒: sin membresía en la empresa el usuario recibe `404`.", ""]
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
        out += ["", f"Responde `201 Created` si `admin.test` es miembro de la empresa: `perm:all:all:all` cubre "
                f"{permission_text(create[4])}. Reemplace las variables `<…>` por los `id` guardados.", ""]

    n += 1
    consulta = next(u for u in USERS if u["username"] == "consulta.test")
    denied = pick_example(rows, lambda s_i, c, p, r: not c["external"] and c["method"] != "GET"
                          and not allowed_all(consulta, p))
    if denied:
        s_i, c_i, s, c, p, r = denied
        out += [f"### {n}. `consulta.test` intenta escribir (rechazado)", ""]
        out += token_command("consulta.test", "TOKEN_CONSULTA")
        out += ["", f"Intenta el paso {s_i + 1:02d} (*{s['title']}*), llamada {c_i + 1}:", ""]
        out += curl_for(c, "TOKEN_CONSULTA")
        out += ["", "Respuesta `403 Forbidden`:", "", "```json",
                json.dumps(forbidden_body(r, p, c["path"]), ensure_ascii=False, indent=2), "```", ""]
        out += [f"`consulta.test` solo tiene lecturas: puede **leer**, pero la URL exige {permission_text(p)}. El "
                "servicio no ejecuta nada: ni siquiera consulta Operational Context ni valida el cuerpo.", ""]

    read = pick_example(rows, lambda s_i, c, p, r: not c["external"] and c["method"] == "GET")
    if read:
        n += 1
        s_i, c_i, s, c, p, r = read
        out += [f"### {n}. `consulta.test` consulta", ""]
        out += curl_for(c, "TOKEN_CONSULTA")
        out += ["", f"Responde `200 OK` con la misma información que ve `admin.test` en el paso {s_i + 1:02d}: "
                f"`{matching_grant(consulta, as_list(p)[0])}` cubre {permission_text(p)} y `consulta.test` es miembro "
                "de la empresa. Sin membresía respondería `404`.", ""]

        n += 1
        out += [f"### {n}. `inventario.test` consulta (rechazado)", ""]
        out += token_command("inventario.test", "TOKEN_INVENTARIO")
        out += [""]
        out += curl_for(c, "TOKEN_INVENTARIO")
        out += ["", "Responde `403 Forbidden`: `inventario.test` no tiene ningún permiso de Commercial Relationship "
                "en el realm vigente, aunque sea miembro de la empresa.", ""]

    deactivate = pick_example(rows, lambda s_i, c, p, r: p[0].endswith(":delete"))
    if deactivate:
        n += 1
        s_i, c_i, s, c, p, r = deactivate
        action = "bloquear" if c["path"].endswith("/block") else "inactivar"
        out += [f"### {n}. `supervisor.test` intenta {action} (rechazado)", ""]
        out += token_command("supervisor.test", "TOKEN_SUPERVISOR")
        out += [""]
        out += curl_for(c, "TOKEN_SUPERVISOR")
        out += ["", "Respuesta `403 Forbidden`:", "", "```json",
                json.dumps(forbidden_body(r, p, c["path"]), ensure_ascii=False, indent=2), "```", ""]
        out += ["`supervisor.test` tiene `perm:all:all:read`, `perm:all:all:create` y `perm:all:all:update`, pero **no** "
                f"`delete`. {action.capitalize()} queda para `admin.test`.", ""]

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
            "   - `perm:all:all:read` → solo `read`, en todos los servicios (`supervisores`).",
            "   - `perm:commercial-relationship:all:read` → solo `read`, solo en Commercial Relationship "
            "(`compras` y `ventas`).",
            "4. Cada URL exige un permiso concreto (por ejemplo `perm:commercial-relationship:company_products:create`). "
            "Si falta, el servicio responde `403 Forbidden` e indica cuál. Sin token, o con un token vencido, responde "
            "`401 Unauthorized`.",
            "5. El permiso se revisa **antes** que todo lo demás: un usuario sin permiso recibe `403` aunque el JSON esté "
            "mal, y el servicio ni siquiera consulta Operational Context.",
            "6. **Aislamiento por empresa:** el permiso dice *qué* puede hacer el usuario; la membresía en Operational "
            "Context dice *dónde*. Sin membresía `ACTIVE` en la empresa, la URL responde `404`, igual que un `id` "
            "inexistente (URL con 🔒). **Ningún permiso de usuario exime de la membresía**, ni `perm:all:all:all` (DS-03).",
            "7. **Consulta técnica:** solo una cuenta de servicio (`client_credentials`, con `client_id` y "
            "`preferred_username = service-account-{client_id}`) con `perm:commercial-relationship:platform:lookup` "
            "lee por UUID sin membresía. Es para Inventory, Purchase y Sales; ningún usuario de prueba la usa.", ""]

    out += ["## Usuarios de prueba", "",
            "Todos comparten la contraseña de la variable `KEYCLOAK_TEST_USER_PASSWORD` (`infrastructure/.env`).", "",
            "| Usuario | Grupo | Permisos del grupo en Commercial Relationship | Puede |", "| --- | --- | --- | --- |"]
    summary = {
        "admin.test": "Todo, en las empresas donde es miembro",
        "supervisor.test": "Consultar, adoptar, incorporar, seleccionar, modificar, reactivar y desbloquear; "
        "administrar políticas de ganancia (incluido inactivarlas) y resolver actualizaciones automáticas (spec 021). "
        "**No** inactivar ni bloquear el resto",
        "compras.test": "Solo consultar (sin políticas de ganancia ni actualizaciones automáticas)",
        "ventas.test": "Solo consultar (sin políticas de ganancia ni actualizaciones automáticas)",
        "inventario.test": "Nada (`403`)",
        "reportes.test": "Solo consultar",
        "consulta.test": "Solo consultar",
    }
    for u in USERS:
        own = [p for p in u["perms"] if p.startswith("perm:commercial-relationship:") or p.startswith("perm:all:")]
        own = [p for p in own if not any(p.endswith(f":{r}:read") for r in (
            "customer_credit_profiles", "customer_payment_conditions", "customer_segments", "product_pricing_policies",
            "supplier_commercial_conditions", "supplier_evaluations", "supplier_payment_conditions", "supplier_products"))]
        perms = "<br>".join(f"`{p}`" for p in own) or "—"
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
            f"Invoke-RestMethod -Uri '{SERVICE_URL}/api/v1/companies/<EMPRESA>/company-products' `",
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
    out += ["- Las URL de `http://localhost:8004` son de **Operational Context**, las de `http://localhost:8003` de "
            "**Product Catalog** y las de `http://localhost:8002` de **Party Identity**: exigen permisos de esos "
            "servicios.", ""]

    out += ["## Qué usuario usar", "",
            "| Para… | Usuario |", "| --- | --- |",
            "| Hacer los ejercicios completos | `admin.test` (con membresía en la empresa) |",
            "| Crear y modificar sin poder inactivar ni bloquear | `supervisor.test` (con membresía) |",
            "| Verificar lo cargado | `consulta.test`, `reportes.test`, `compras.test` o `ventas.test` (con membresía) |",
            "| Probar rechazos por falta de permiso | `consulta.test` en cualquier `POST` o `PUT`; `inventario.test` en "
            "cualquier URL; `supervisor.test` al inactivar o bloquear |", ""]
    return "\n".join(out)
