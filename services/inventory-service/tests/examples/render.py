"""Genera la documentación de `docs/ejemplo/` a partir de las ejecuciones (Principio XXII).

Los valores que asigna Inventory en cada ejecución (`id` de operaciones y movimientos, momentos,
`trace_id`) se muestran como marcadores para que la documentación sea estable: `<VARIABLE>` si el
ejercicio la guarda y `<asignado por Inventory>` en los demás casos.
"""

from __future__ import annotations

import json
from typing import Any

from tests.examples.exercises import ACCION, OPERACION
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
    # 013: identificadores y momentos que asigna Inventory en ajustes, conteos y valoración.
    "movement_id",
    "updated_at",
    "started_at",
    "completed_at",
    "cancelled_at",
    "counted_at",
    "received_at",
    "cost_layer_id",
    "restores_consumption_id",
    "origin_movement_id",
    "inventory_adjustment_id",
    "inventory_count_id",
}
CONDITIONAL = {"origin_detail_id", "origin_id"}
"""Se ocultan solo si no son datos fijos del ejercicio (en ajustes y conteos los asigna Inventory)."""


def _fixed_ids() -> set[str]:
    import re

    from tests.examples.exercises import EXERCISES

    return set(re.findall(r"d44[0-9a-f]{5}-0000-4000-8000-[0-9]{12}", json.dumps(EXERCISES)))


FIXED_IDS = _fixed_ids()


def _volatile(key: str, item: Any) -> bool:
    if item is None:
        return False
    return key in VOLATILE or (key in CONDITIONAL and str(item) not in FIXED_IDS)


def _mask(value: Any, reverse: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {
            key: (reverse.get(str(item), ASSIGNED) if _volatile(key, item) else _mask(item, reverse))
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


def _operator_cell(record: dict) -> str:
    if record["step"]["kind"] == OPERACION:
        return f"`{record['status']}`"
    if record["step"]["kind"] == ACCION:
        return "`403` (cuenta de servicio)"
    return "— (no consulta)"


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
    elif step["kind"] == ACCION:
        lines += [
            "",
            "Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso "
            "por comodín), miembro `ACTIVE` de la empresa y, en ajustes y conteos, con asignación `ACTIVE` a "
            "la sucursal (lo resuelve Operational Context con el token del usuario). Los usuarios con el "
            "permiso no repiten la llamada en este ejercicio porque cambiaría su estado.",
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
        + " | ".join(_operator_cell(r) for r in records)
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
        "- Puede: `inventario.test`, `admin.test` y `supervisor.test` consultan inventario de las "
        "empresas donde son miembros; `inventario.test` registra ajustes y conteos en las sucursales "
        "asignadas; `admin.test` y `supervisor.test` configuran políticas (comodín).",
        "- No puede: ningún usuario humano aplica ni revierte operaciones (ni siquiera `admin.test`, que "
        "tiene el permiso por comodín); ninguna cuenta de servicio registra ajustes, conteos ni políticas; "
        "`compras.test`, `ventas.test`, `reportes.test` y `consulta.test` reciben `403`.",
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
        "- **Ajustes y conteos** (`perm:inventory:adjustments:create`, `perm:inventory:counts:create`, 013) "
        "exigen un **usuario humano** miembro `ACTIVE` y con asignación `ACTIVE` a la sucursal; una "
        "cuenta de servicio recibe `403` aunque tenga el permiso. Las **políticas** "
        "(`perm:inventory:company-policies:update`, `perm:inventory:product-policies:update`) exigen un "
        "usuario humano miembro de la empresa.",
        "- **Lecturas de 013** (`adjustments:read`, `counts:read`, `company-policies:read`, "
        "`product-policies:read`, `valuation:read`): mismo alcance por empresa que las consultas de stock.",
        "- El grupo `inventario` tiene las lecturas de inventario y registra ajustes y conteos; "
        "`administradores` y `supervisores` lo obtienen todo por comodín (las políticas solo ellos). "
        "Ningún grupo puede aplicar operaciones.",
        "",
        "## Usuarios de prueba",
        "",
        "| Usuario | Grupo | Stock y kardex | Ajustes y conteos | Políticas | Valoración | Aplicar operaciones |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]

    def yes(user, permission):
        return "Sí" if allowed(user, permission) else "No"

    for user in USERS:
        lines.append(
            f"| `{user['username']}` | `{user['group']}` | "
            f"{yes(user, 'perm:inventory:balances:read')} | "
            f"{yes(user, 'perm:inventory:adjustments:create')} | "
            f"{yes(user, 'perm:inventory:company-policies:update')} | "
            f"{yes(user, 'perm:inventory:valuation:read')} | No (no es cuenta de servicio) |"
        )
    lines.append(
        f"| `{OPERATOR}` | cuenta de servicio | Sí (`platform:lookup`) | No (no es usuario humano) | "
        "No (no es usuario humano) | Sí (`platform:lookup`) | Sí (entradas y salidas) |"
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
