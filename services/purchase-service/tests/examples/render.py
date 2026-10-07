"""Genera la documentación de `docs/ejemplo/` a partir de las ejecuciones (Principio XXII).

Los valores que asignan Purchase o los dobles en cada ejecución (`id`, momentos de registro,
`trace_id`, operación de Inventory) se muestran como marcadores para que la documentación sea
estable: `<VARIABLE>` si el ejercicio la guarda y `<asignado por el servicio>` en los demás casos.
"""

from __future__ import annotations

import json
import re
from typing import Any

from tests.examples.exercises import ACCION, EXERCISES
from tests.examples.users import USERS, allowed

ASSIGNED = "<asignado por el servicio>"
VOLATILE = {
    "id",
    "purchase_id",
    "purchase_sequence_id",
    "inventory_operation_id",
    "pending_operation_id",
    "operation_id",
    "correlation_id",
    "compensation_operation_id",
    "conflicting_event_id",
    "created_at",
    "updated_at",
    "started_at",
    "completed_at",
    "cancelled_at",
    "trace_id",
    "ORDERED",
    "SUPPLIER_DISPATCHED",
    "ARRIVED",
    "RECEIVED",
    "AVAILABLE_FOR_SALE",
}


def _fixed_ids() -> set[str]:
    return set(re.findall(r"d14[0-9a-f]{5}-0000-4000-8000-[0-9]{12}", json.dumps(EXERCISES)))


FIXED_IDS = _fixed_ids()


def _volatile(key: str, item: Any) -> bool:
    return item is not None and key in VOLATILE and str(item) not in FIXED_IDS


def _mask(value: Any, reverse: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {
            key: (reverse.get(str(item), ASSIGNED) if _volatile(key, item) else _mask(item, reverse))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_mask(item, reverse) for item in value]
    if isinstance(value, str):
        for original, placeholder in reverse.items():
            value = value.replace(original, placeholder)
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
    ]
    if step.get("headers"):
        lines += ["Cabeceras: " + ", ".join(f"`{name}: {value}`" for name, value in step["headers"].items()) + ".", ""]
    if step.get("before"):
        lines += [
            "Situación simulada antes de la llamada: "
            + ", ".join(f"`{item}`" for item in step["before"])
            + " (en la prueba automática, sobre el doble de Inventory).",
            "",
        ]
    if record["body"] is not None:
        lines += ["### Solicitud", "", _json(step["body"]), ""]

    lines += ["### Por qué", ""] + [f"- {item}" for item in step["why"]] + [""]

    lines += ["## Permiso", "", f"La URL exige `{record['permission']}`."]
    if step["kind"] == ACCION:
        lines += [
            "",
            "Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por "
            "comodín), miembro `ACTIVE` de la empresa y, en compras, hitos, confirmación y anulación, con "
            "asignación `ACTIVE` a la sucursal de la compra (lo resuelve Operational Context con el token del "
            "usuario). Los usuarios con el permiso no repiten la llamada porque cambiaría el estado del ejercicio.",
        ]
    else:
        lines += [
            "",
            "Además, el usuario debe ser miembro `ACTIVE` de la empresa (Operational Context, con su token). No se "
            "exige asignación a la sucursal.",
        ]

    lines += ["", "| Usuario | ¿Puede? | Respuesta | Motivo |", "| --- | --- | --- | --- |"]
    for user in USERS:
        info = record["access"][user["username"]]
        lines.append(f"| `{user['username']}` | {'Sí' if info['allowed'] else 'No'} | `{info['status']}` | {info['reason']} |")

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
        lines += ["## Variables que se guardan", ""] + [f"- `<{name}>` = `{where}` de la respuesta." for name, where in saved.items()] + [""]
    return "\n".join(lines)


def render_order(exercise: dict, records: list[dict]) -> str:
    lines = [
        f"# Ejercicio {exercise['number']}: {exercise['title']}",
        "",
        exercise["purpose"],
        "",
        "Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base "
        "nueva con el reloj fijo en el 5 de noviembre de 2026.",
        "",
        "## Orden de los pasos",
        "",
        "| Paso | Archivo | Llamada | Ejecuta | Estado |",
        "| --- | --- | --- | --- | --- |",
    ]
    for index, record in enumerate(records, start=1):
        step = record["step"]
        lines.append(f"| {index} | [{step['file']}]({step['file']}) | `{step['method']} {step['path']}` | `{step['actor']}` | `{record['status']}` |")
    lines += [
        "",
        "## Por qué este orden",
        "",
        "- La numeración necesita una secuencia activa antes de confirmar; la confirmación necesita un borrador; "
        "la anulación y los hitos de recepción necesitan una compra confirmada.",
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
                if f"<{name}>" in json.dumps([record["step"]["path"], record["step"].get("body"), record["step"].get("before")])
            ]
            lines.append(f"| `<{name}>` | paso {index} (`{where}`) | pasos {', '.join(used) or '—'} |")
    return "\n".join(lines) + "\n"


def render_data(exercise: dict) -> str:
    lines = [
        f"# Datos del ejercicio {exercise['number']} (ficticios)",
        "",
        "Todos los datos son **ficticios** y sus identificadores son fijos para que la documentación sea estable. "
        "En la prueba automática, Operational Context, Commercial Relationship, Product Catalog, Party Identity, "
        "Payment Reference e Inventory se simulan con estos datos.",
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
    for user in USERS:
        lines.append(f"| `{user['username']}` | " + " | ".join(f"`{r['access'][user['username']]['status']}`" for r in records) + " |")
    lines += ["", "## Permiso por URL", "", "| Paso | URL | Permiso |", "| --- | --- | --- |"]
    lines += [f"| {i} | `{r['step']['method']} {r['step']['path']}` | `{r['permission']}` |" for i, r in enumerate(records, start=1)]
    lines += [
        "",
        "## Ejemplos",
        "",
        "- Puede: `compras.test` (grupo `compras`, `perm:purchase:all:all`) registra, confirma y anula compras de las "
        "sucursales asignadas; `admin.test` también, por comodín; `supervisor.test` registra y confirma, pero no anula "
        "(no tiene `delete`); `reportes.test` y `consulta.test` solo consultan.",
        "- No puede: ninguna cuenta de servicio escribe compras (ni el propio `purchase-service`); `ventas.test` e "
        "`inventario.test` reciben `403`; sin asignación a la sucursal, ni el comodín permite escribir.",
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
        "# Usuarios y permisos de purchase-service",
        "",
        "Generado por `tests/examples/test_examples.py` a partir de la plantilla del realm "
        "(`infrastructure/keycloak/realm-template/sio-realm.template.json`).",
        "",
        "## Cómo se evalúan los permisos",
        "",
        "- Cada URL exige un permiso `perm:purchase:{recurso}:{accion}` (`sio-auth`). El `403` nunca revela el "
        "permiso exigido; queda solo en el log del servidor con el `trace_id`.",
        "- **Todas** las rutas exigen un **usuario humano**: una cuenta de servicio recibe `403` aunque tenga el "
        "permiso por comodín (ni siquiera el cliente técnico `purchase-service`, que solo consulta dependencias y "
        "opera Inventory).",
        "- **Escribir** compras, líneas, hitos, confirmar y anular exige además membresía `ACTIVE` en la empresa y "
        "asignación `ACTIVE` a la sucursal de la compra (Operational Context con el token del usuario). **No obvio**: "
        "tener `perm:purchase:all:all` o `perm:all:all:all` no basta sin la asignación.",
        "- **Secuencias** exigen membresía (no asignación). **Leer** exige permiso y membresía.",
        "- Crear una compra con líneas exige además `perm:purchase:purchase_details:create`; anular exige "
        "`perm:purchase:purchases:delete` (`supervisor.test` no lo tiene).",
        "",
        "## Usuarios de prueba",
        "",
        "| Usuario | Grupo | Registrar y confirmar | Anular | Hitos | Secuencias | Consultar |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]

    def yes(user, permission):
        return "Sí" if allowed(user, permission) else "No"

    for user in USERS:
        lines.append(
            f"| `{user['username']}` | `{user['group']}` | "
            f"{yes(user, 'perm:purchase:purchases:update')} | "
            f"{yes(user, 'perm:purchase:purchases:delete')} | "
            f"{yes(user, 'perm:purchase:purchase_lifecycle_events:create')} | "
            f"{yes(user, 'perm:purchase:purchase_sequences:create')} | "
            f"{yes(user, 'perm:purchase:purchases:read')} |"
        )
    lines += [
        "",
        "Las escrituras requieren además la asignación a la sucursal.",
        "",
        "## Cómo obtener los tokens",
        "",
        "Usuarios (contraseña en la variable `KEYCLOAK_TEST_USER_PASSWORD`, nunca en estos documentos):",
        "",
        "```bash",
        "curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \\",
        "  -d grant_type=password -d client_id=sio-web -d scope=openid \\",
        "  -d username=compras.test -d password=\"$KEYCLOAK_TEST_USER_PASSWORD\"",
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
