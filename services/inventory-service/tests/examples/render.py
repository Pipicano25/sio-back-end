"""Genera la documentación de `docs/ejemplo/` a partir de las ejecuciones (Principio XXII).

Los valores que asigna Inventory en cada ejecución (`id` de operaciones y movimientos, momentos,
`trace_id`) se muestran como marcadores para que la documentación sea estable: `<VARIABLE>` si el
ejercicio la guarda y `<asignado por Inventory>` en los demás casos.
"""

from __future__ import annotations

import json
from typing import Any

from tests.examples.exercises import OPERACION
from tests.examples.users import OPERATOR, OC_PERMISSION, USERS, allowed

ASSIGNED = "<asignado por Inventory>"
VOLATILE = {
    "id",
    "operation_id",
    "reversed_movement_id",
    "reverses_operation_id",
    "reversed_by_operation_id",
    "created_at",
    "last_movement_at",
    "trace_id",
}


def _mask(value: Any, reverse: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {
            key: (
                reverse.get(str(item), ASSIGNED) if key in VOLATILE and item is not None else _mask(item, reverse)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_mask(item, reverse) for item in value]
    if isinstance(value, str):
        # Los valores guardados también aparecen dentro de textos (p. ej. `instance` de un error).
        for original, placeholder in reverse.items():
            value = value.replace(original, placeholder)
    return value


def _json(value: Any) -> str:
    return "```json\n" + json.dumps(value, ensure_ascii=False, indent=2) + "\n```"


def _reverse(ctx: dict[str, str]) -> dict[str, str]:
    return {str(value): f"<{name}>" for name, value in ctx.items()}


def _actor_label(step: dict) -> str:
    return f"`{OPERATOR}` (cuenta de servicio)" if step["actor"] == "operador" else f"`{step['actor']}`"


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
        f"Ejecuta: {_actor_label(step)}.",
        "",
    ]

    if record["body"] is not None:
        lines += ["### Solicitud", "", _json(step["body"]), ""]

    lines += ["### Por qué", ""] + [f"- {item}" for item in step["why"]] + [""]

    lines += ["## Permiso", "", f"La URL exige `{record['permission']}`."]
    if step["kind"] == OPERACION:
        lines += [
            "",
            "Además exige que el token sea de una **cuenta de servicio**: un usuario humano recibe `403` "
            "aunque tenga el permiso por comodín. Solo puede ejecutarla `inventory-test-operator` "
            "(o el cliente técnico de Purchase o Sales con el mismo permiso).",
        ]
    else:
        lines += [
            "",
            "Además, el usuario debe ser miembro `ACTIVE` de la empresa y tener "
            f"`{OC_PERMISSION}` (lo exige Operational Context al resolver su acceso). No se exige "
            "asignación a la sucursal.",
        ]

    lines += ["", "| Usuario | ¿Puede? | Respuesta | Motivo |", "| --- | --- | --- | --- |"]
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

    saved = step.get("save", {})
    if saved:
        lines += ["## Variables que se guardan", ""] + [
            f"- `<{name}>` = `{where}` de la respuesta." for name, where in saved.items()
        ] + [""]

    return "\n".join(lines)


def render_order(exercise: dict, records: list[dict]) -> str:
    lines = [
        f"# Ejercicio {exercise['number']}: {exercise['title']}",
        "",
        exercise["purpose"],
        "",
        "Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta "
        "en una base nueva.",
        "",
        "## Orden de los pasos",
        "",
        "| Paso | Archivo | Llamada | Ejecuta | Estado |",
        "| --- | --- | --- | --- | --- |",
    ]
    for index, record in enumerate(records, start=1):
        step = record["step"]
        lines.append(
            f"| {index} | [{step['file']}]({step['file']}) | `{step['method']} {step['path']}` | "
            f"{_actor_label(step)} | `{record['status']}` |"
        )

    lines += [
        "",
        "## Por qué este orden",
        "",
        "- Los saldos nacen de las entradas: las entradas van primero; las salidas, reversos y consultas "
        "dependen del saldo que dejan los pasos anteriores.",
    ]
    saved = [
        (index, name, where)
        for index, record in enumerate(records, start=1)
        for name, where in record["step"].get("save", {}).items()
    ]
    if saved:
        lines += ["", "## Variables", "", "| Variable | Se guarda en | Se usa en |", "| --- | --- | --- |"]
        for index, name, where in saved:
            used = [
                str(other)
                for other, record in enumerate(records, start=1)
                if f"<{name}>" in json.dumps([record["step"]["path"], record["step"].get("body")])
            ]
            lines.append(f"| `<{name}>` | paso {index} (`{where}`) | pasos {', '.join(used) or '—'} |")
    return "\n".join(lines) + "\n"


def render_data(exercise: dict) -> str:
    lines = [
        f"# Datos del ejercicio {exercise['number']} (ficticios)",
        "",
        "No existe una fuente del sistema anterior para movimientos de inventario: todos los datos son "
        "**ficticios** y sus identificadores son fijos para que la documentación sea estable. En la "
        "prueba automática, Operational Context y Commercial Relationship se simulan con estos datos.",
        "",
        "| Dato | Valor | Interpretación |",
        "| --- | --- | --- |",
    ]
    lines += [f"| {name} | `{value}` | {meaning} |" for name, value, meaning in exercise["data"]]
    return "\n".join(lines) + "\n"


def render_users(exercise: dict, records: list[dict]) -> str:
    lines = [
        f"# Usuarios del ejercicio {exercise['number']}",
        "",
        "| Usuario | " + " | ".join(f"Paso {i}" for i in range(1, len(records) + 1)) + " |",
        "| --- | " + " | ".join("---" for _ in records) + " |",
    ]
    lines.append(
        f"| `{OPERATOR}` | "
        + " | ".join(f"`{r['status']}`" if r["step"]["kind"] == OPERACION else "— (no consulta)" for r in records)
        + " |"
    )
    for user in USERS:
        lines.append(
            f"| `{user['username']}` | " + " | ".join(f"`{r['access'][user['username']]['status']}`" for r in records) + " |"
        )
    lines += ["", "## Permiso por URL", "", "| Paso | URL | Permiso |", "| --- | --- | --- |"]
    lines += [
        f"| {i} | `{r['step']['method']} {r['step']['path']}` | `{r['permission']}` |"
        for i, r in enumerate(records, start=1)
    ]
    lines += [
        "",
        "## Ejemplos",
        "",
        "- Puede: `inventario.test`, `admin.test` y `supervisor.test` consultan stock y kardex de las "
        "empresas donde son miembros.",
        "- No puede: ningún usuario humano aplica ni revierte operaciones (ni siquiera `admin.test`, que "
        "tiene el permiso por comodín); `compras.test`, `ventas.test`, `reportes.test` y `consulta.test` "
        "reciben `403` en las consultas.",
    ]
    return "\n".join(lines) + "\n"


def render_exercise(exercise: dict, records: list[dict]) -> dict[str, str]:
    files = {
        "ORDEN.md": render_order(exercise, records),
        "00-datos-ficticios.md": render_data(exercise),
        "USUARIOS.md": render_users(exercise, records),
    }
    for index, record in enumerate(records, start=1):
        files[record["step"]["file"]] = render_step(exercise, index, record)
    return files


def render_general(all_records: dict[int, list[dict]]) -> str:
    lines = [
        "# Usuarios y permisos de inventory-service",
        "",
        "Generado por `tests/examples/test_examples.py` a partir de la plantilla del realm "
        "(`infrastructure/keycloak/realm-template/sio-realm.template.json`).",
        "",
        "## Cómo se evalúan los permisos",
        "",
        "- Cada URL exige un permiso `perm:inventory:{recurso}:{accion}` (`sio-auth`). El `403` nunca "
        "revela el permiso exigido; queda solo en el log del servidor con el `trace_id`.",
        "- **Aplicar y revertir** (`perm:inventory:entries:create`, `perm:inventory:outputs:create`) "
        "exige además un token de **cuenta de servicio**: ningún usuario humano mueve inventario, aunque "
        "tenga el permiso por comodín. El reverso usa el permiso del tipo original y exige `company_id`.",
        "- **Consultar** (`perm:inventory:balances:read`, `perm:inventory:movements:read`) exige además "
        f"la membresía `ACTIVE` en la empresa y `{OC_PERMISSION}`, que pide Operational Context al "
        "resolver el acceso. No se exige asignación a la sucursal.",
        "- **Lectura técnica** (`perm:inventory:platform:lookup`): una cuenta de servicio con lectura y "
        "esta capacidad consulta sin membresía (Sales antes de confirmar una venta).",
        "- El grupo `inventario` tiene las dos lecturas de inventario; `administradores` y `supervisores` "
        "las obtienen por comodín. Ningún grupo puede aplicar operaciones.",
        "",
        "## Usuarios de prueba",
        "",
        "| Usuario | Grupo | Stock (`balances:read`) | Kardex (`movements:read`) | Aplicar operaciones |",
        "| --- | --- | --- | --- | --- |",
    ]
    for user in USERS:
        lines.append(
            f"| `{user['username']}` | `{user['group']}` | "
            f"{'Sí' if allowed(user, 'perm:inventory:balances:read') else 'No'} | "
            f"{'Sí' if allowed(user, 'perm:inventory:movements:read') else 'No'} | No (no es cuenta de servicio) |"
        )
    lines.append(f"| `{OPERATOR}` | cuenta de servicio | Sí (`platform:lookup`) | Sí (`platform:lookup`) | Sí (entradas y salidas) |")

    lines += [
        "",
        "## Cómo obtener los tokens",
        "",
        "Usuarios (contraseña en la variable `KEYCLOAK_TEST_USER_PASSWORD`, nunca en estos documentos):",
        "",
        "```bash",
        "curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \\",
        "  -d grant_type=password -d client_id=sio-web -d scope=openid \\",
        "  -d username=inventario.test -d password=\"$KEYCLOAK_TEST_USER_PASSWORD\"",
        "```",
        "",
        "Cuenta de servicio de pruebas (secreto en `INVENTORY_TEST_OPERATOR_CLIENT_SECRET`):",
        "",
        "```bash",
        "curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \\",
        "  -d grant_type=client_credentials -d client_id=inventory-test-operator \\",
        "  -d client_secret=\"$INVENTORY_TEST_OPERATOR_CLIENT_SECRET\"",
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
