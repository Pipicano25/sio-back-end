"""Genera la documentación de `docs/ejemplo/` a partir de las ejecuciones (Principio XXII; T127).

Los valores que cambian en cada ejecución (`resolved_at`, `trace_id` y los cursores, que llevan su emisión y su
vencimiento) se muestran como marcadores para que la documentación sea estable: `<VARIABLE>` si el ejercicio la
guarda y `<asignado por el servicio>` en los demás casos.
"""

from __future__ import annotations

import json
from typing import Any

from tests.examples.users import BLOCKS, USERS, allowed

ASSIGNED = "<asignado por el servicio>"
VOLATILE = {"resolved_at", "trace_id", "next_cursor"}
FUNCTIONAL = {
    "product-overviews": "perm:product-inventory-query:product_overviews:read",
    "inventory-overviews": "perm:product-inventory-query:inventory_overviews:read",
    "low-stock-products": "perm:product-inventory-query:low_stock_products:read",
    "inventory-summary": "perm:product-inventory-query:inventory_summary:read",
}


def _mask(value: Any, reverse: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {
            key: (reverse.get(str(item), ASSIGNED) if key in VOLATILE and item is not None else _mask(item, reverse))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_mask(item, reverse) for item in value]
    return value


def _json(value: Any) -> str:
    return "```json\n" + json.dumps(value, ensure_ascii=False, indent=2) + "\n```"


def _reverse(ctx: dict[str, str]) -> dict[str, str]:
    return {str(value): f"<{name}>" for name, value in ctx.items()}


def render_step(exercise: dict, index: int, record: dict) -> str:
    step = record["step"]
    reverse = _reverse(record["ctx"])
    lines = [
        f"# Paso {index}. {step['title']}",
        "",
        f"Ejercicio {exercise['number']}: {exercise['title']}.",
        "",
        "## Llamada",
        "",
        f"`{step['method']} {step['path']}`",
        "",
        f"Ejecuta: `{step['actor']}`.",
        "",
        "### Por qué",
        "",
    ]
    lines += [f"- {item}" for item in step["why"]] + [""]
    lines += ["## Permiso", "", f"La URL exige `{record['permission']}`."]
    if step["requires"]:
        lines += ["", "Además exige " + ", ".join(f"`{item}`" for item in step["requires"]) + "."]
    lines += [
        "",
        "Además, el usuario debe ser miembro `ACTIVE` de la empresa (lo verifica Operational Context con su token "
        "antes de cualquier otra consulta). No se exige asignación a la sucursal.",
        "",
        "| Usuario | ¿Puede? | Respuesta | Motivo |",
        "| --- | --- | --- | --- |",
    ]
    for user in USERS:
        info = record["access"][user["username"]]
        lines.append(
            f"| `{user['username']}` | {'Sí' if info['allowed'] else 'No'} | `{info['status']}` | {info['reason']} |"
        )
    lines += [
        "",
        "Respuesta sin permiso (`403`), que no revela el permiso exigido:",
        "",
        _json(_mask(record["forbidden"], reverse)),
        "",
        "## Respuesta esperada",
        "",
        f"Estado `{record['status']}`.",
        "",
        _json(_mask(record["response"], reverse)),
        "",
    ]
    if step["save"]:
        lines += ["## Variables que se guardan", ""] + [
            f"- `<{name}>` = `{where}` de la respuesta." for name, where in step["save"].items()
        ] + [""]
    return "\n".join(lines)


def render_order(exercise: dict, records: list[dict]) -> str:
    lines = [
        f"# Ejercicio {exercise['number']}: {exercise['title']}",
        "",
        exercise["purpose"],
        "",
        "Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente y solo consulta: no "
        "cambia ningún dato.",
        "",
        "## Orden de los pasos",
        "",
        "| Paso | Archivo | Llamada | Ejecuta | Estado |",
        "| --- | --- | --- | --- | --- |",
    ]
    for index, record in enumerate(records, start=1):
        step = record["step"]
        lines.append(f"| {index} | [{step['file']}]({step['file']}) | `{step['method']} {step['path']}` | "
                     f"`{step['actor']}` | `{record['status']}` |")
    saved = [(index, name, where) for index, record in enumerate(records, start=1)
             for name, where in record["step"]["save"].items()]
    if saved:
        lines += [
            "",
            "## Por qué este orden",
            "",
            "- Los pasos que usan `<CURSOR>` necesitan el cursor de la respuesta anterior. Un cursor vence a los 15 "
            "minutos y solo vale con los mismos filtros, orden y `page_size`.",
            "",
            "## Variables",
            "",
            "| Variable | Se guarda en | Se usa en |",
            "| --- | --- | --- |",
        ]
        for index, name, where in saved:
            used = [str(other) for other, record in enumerate(records, start=1)
                    if f"<{name}>" in record["step"]["path"]]
            lines.append(f"| `<{name}>` | paso {index} (`{where}`) | pasos {', '.join(used) or '—'} |")
    return "\n".join(lines) + "\n"


def render_data(exercise: dict, data: list[tuple[str, str, str]]) -> str:
    lines = [
        f"# Datos del ejercicio {exercise['number']} (ficticios)",
        "",
        "Todos los datos son **ficticios** (ningún NIT, razón social ni dato de una empresa real) y sus "
        "identificadores son fijos para que la documentación sea estable. En la prueba automática, Operational "
        "Context, Commercial Relationship, Product Catalog e Inventory se simulan con estos datos.",
        "",
        "| Dato | Valor | Interpretación |",
        "| --- | --- | --- |",
    ]
    lines += [f"| {name} | `{value}` | {meaning} |" for name, value, meaning in data]
    return "\n".join(lines) + "\n"


def render_users(exercise: dict, records: list[dict]) -> str:
    lines = [
        f"# Usuarios del ejercicio {exercise['number']}",
        "",
        "| Usuario | " + " | ".join(f"Paso {i}" for i in range(1, len(records) + 1)) + " |",
        "| --- | " + " | ".join("---" for _ in records) + " |",
    ]
    for user in USERS:
        lines.append(f"| `{user['username']}` | "
                     + " | ".join(f"`{r['access'][user['username']]['status']}`" for r in records) + " |")
    lines += ["", "## Permiso por URL", "", "| Paso | URL | Permiso |", "| --- | --- | --- |"]
    lines += [f"| {i} | `{r['step']['method']} {r['step']['path']}` | `{r['permission']}` |"
              for i, r in enumerate(records, start=1)]
    lines += [
        "",
        "## Ejemplos",
        "",
        "- Puede: `ventas.test` consulta productos e inventario (con precios y existencias, sin mínimos); "
        "`inventario.test` consulta las cuatro (con existencias y mínimos, sin precios); `supervisor.test` y "
        "`admin.test` ven todos los bloques.",
        "- No puede: `compras.test`, `reportes.test` y `consulta.test` reciben `403` en las cuatro consultas.",
    ]
    return "\n".join(lines) + "\n"


def render_exercise(exercise: dict, records: list[dict], data: list[tuple[str, str, str]]) -> dict[str, str]:
    files = {
        "ORDEN.md": render_order(exercise, records),
        "00-datos-ficticios.md": render_data(exercise, data),
        "USUARIOS.md": render_users(exercise, records),
    }
    for index, record in enumerate(records, start=1):
        files[record["step"]["file"]] = render_step(exercise, index, record)
    return files


def render_general(all_records: dict[int, list[dict]]) -> str:
    def yes(user, permission):
        return "Sí" if allowed(user, permission) else "No"

    lines = [
        "# Usuarios y permisos de product-inventory-query-service",
        "",
        "Generado por `tests/examples/test_examples.py` a partir de la plantilla del realm "
        "(`infrastructure/keycloak/realm-template/sio-realm.template.json`).",
        "",
        "## Cómo se evalúan los permisos",
        "",
        "- Cada consulta exige su permiso funcional `perm:product-inventory-query:{recurso}:read` (`sio-auth`). El "
        "`403` nunca revela el permiso exigido; queda solo en el log del servidor con el `trace_id`.",
        "- Antes de consultar cualquier otro servicio, Operational Context verifica con el token del usuario la "
        "membresía `ACTIVE` en la empresa. Con ella se lee cualquier sucursal de la empresa, sin asignación.",
        "- Cada bloque de la respuesta exige su permiso; si falta, el bloque no aparece (no se envía con `null`) y "
        "un filtro que dependa de él responde `403`:",
        "",
        "| Bloque | Permiso |",
        "| --- | --- |",
    ]
    lines += [f"| {name} | `{permission}` |" for name, permission in BLOCKS.items()]
    lines += [
        "",
        "- `low-stock-products` exige además los permisos de existencias y de mínimos.",
        "- Ningún usuario recibe costos unitarios, promedio ni FIFO, márgenes ni valoración económica: no existen en "
        "las respuestas. La valoración está fuera del alcance de la spec 022; sigue disponible en Inventory con sus "
        "propios permisos.",
        "- Los precios de venta y su moneda vienen de Commercial Relationship; las existencias, de Inventory, y las "
        "imágenes, de Product Catalog.",
        "- `ventas` ve existencias sin tener `perm:inventory:balances:read`: las ve por "
        "`perm:product-inventory-query:stock:read` (D-022-1).",
        "",
        "## Usuarios de prueba",
        "",
        "| Usuario | Grupo | Productos | Inventario | Bajo stock | Resumen | " + " | ".join(BLOCKS) + " |",
        "| --- | --- | --- | --- | --- | --- | " + " | ".join("---" for _ in BLOCKS) + " |",
    ]
    for user in USERS:
        lines.append(
            f"| `{user['username']}` | `{user['group']}` | "
            + " | ".join(yes(user, FUNCTIONAL[name]) for name in FUNCTIONAL)
            + " | " + " | ".join(yes(user, permission) for permission in BLOCKS.values()) + " |"
        )
    lines += [
        "",
        "## Cómo obtener los tokens",
        "",
        "Usuarios (contraseña en la variable `KEYCLOAK_TEST_USER_PASSWORD`, nunca en estos documentos):",
        "",
        "```bash",
        "curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \\",
        "  -d grant_type=password -d client_id=sio-web -d scope=openid \\",
        "  -d username=ventas.test -d password=\"$KEYCLOAK_TEST_USER_PASSWORD\"",
        "```",
        "",
        "## Matriz de URL",
        "",
        "| Ejercicio | Paso | URL | Permiso |",
        "| --- | --- | --- | --- |",
    ]
    for number, records in sorted(all_records.items()):
        for index, record in enumerate(records, start=1):
            step = record["step"]
            lines.append(f"| {number} | {index} | `{step['method']} {step['path']}` | `{record['permission']}` |")
    return "\n".join(lines) + "\n"
