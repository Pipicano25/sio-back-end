"""Genera la documentación de `docs/ejemplo/` a partir de las ejecuciones (Principio XXII).

Los valores que asigna Audit en cada ejecución (`id`, `recorded_at`, `trace_id`) se muestran como
marcadores para que la documentación sea estable: `<VARIABLE>` si el ejercicio la guarda y
`<asignado por Audit>` en los demás casos.
"""

from __future__ import annotations

import json
from typing import Any

from tests.examples.exercises import REGISTRO
from tests.examples.users import EMITTER, OC_PERMISSION, USERS

ASSIGNED = "<asignado por Audit>"
VOLATILE = {"id", "recorded_at", "trace_id"}


def _mask(value: Any, reverse: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {
            key: (reverse.get(str(item), ASSIGNED) if key in VOLATILE else _mask(item, reverse))
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
    return f"`{EMITTER}` (cuenta de servicio)" if step["actor"] == "emisor" else f"`{step['actor']}`"


def render_step(exercise: dict, index: int, record: dict, previous_ctx: dict[str, str]) -> str:
    step = record["step"]
    reverse = _reverse(record["ctx"])
    shown_path = step["path"]
    lines = [
        f"# Paso {index}. {step['title']}",
        "",
        f"Ejercicio {exercise['number']}: {exercise['title']}.",
        "",
        "## Llamada",
        "",
        f"`{step['method']} {shown_path}`",
        "",
        f"Ejecuta: {_actor_label(step)}.",
        "",
    ]

    if record["body"] is not None:
        lines += ["### Solicitud", "", _json(_mask(step["body"], {})), ""]

    lines += ["### Por qué", ""] + [f"- {item}" for item in step["why"]] + [""]

    lines += ["## Permiso", "", f"La URL exige `{record['permission']}`."]
    if step["kind"] == REGISTRO:
        lines += [
            "",
            "Además exige que el token sea de una **cuenta de servicio**: un usuario humano recibe `403` "
            "aunque tenga el permiso por comodín. Solo puede ejecutarla `audit-test-emitter` "
            "(o el cliente técnico de un servicio emisor con el mismo permiso).",
        ]
    elif "/companies/" in step["path"]:
        lines += [
            "",
            "Además, el usuario debe ser miembro `ACTIVE` de la empresa y tener "
            f"`{OC_PERMISSION}` (lo exige Operational Context al resolver su acceso; FR-037).",
        ]
    else:
        lines += ["", "No exige membresía: es el permiso independiente de los eventos de plataforma."]

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

    lines += ["", "## Por qué este orden", ""]
    lines.append(
        "- Las consultas necesitan eventos registrados: los pasos de registro van primero."
    )
    saved = [(index, name, where) for index, r in enumerate(records, start=1) for name, where in r["step"].get("save", {}).items()]
    if saved:
        lines += ["", "## Variables", "", "| Variable | Se guarda en | Se usa en |", "| --- | --- | --- |"]
        for index, name, where in saved:
            used = [
                str(other) for other, r in enumerate(records, start=1)
                if f"<{name}>" in json.dumps([r["step"]["path"], r["step"].get("body")])
            ]
            lines.append(f"| `<{name}>` | paso {index} (`{where}`) | pasos {', '.join(used) or '—'} |")
    return "\n".join(lines) + "\n"


def render_data(exercise: dict) -> str:
    lines = [
        f"# Datos del ejercicio {exercise['number']} (ficticios)",
        "",
        "No existe una fuente del sistema anterior para eventos de auditoría: todos los datos son "
        "**ficticios** y sus identificadores son fijos para que la documentación sea estable.",
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
        f"| `{EMITTER}` | "
        + " | ".join(
            f"`{r['status']}`" if r["step"]["kind"] == REGISTRO else "— (no consulta)" for r in records
        )
        + " |"
    )
    for user in USERS:
        lines.append(
            f"| `{user['username']}` | "
            + " | ".join(f"`{r['access'][user['username']]['status']}`" for r in records)
            + " |"
        )
    lines += [
        "",
        "## Permiso por URL",
        "",
        "| Paso | URL | Permiso |",
        "| --- | --- | --- |",
    ]
    lines += [
        f"| {i} | `{r['step']['method']} {r['step']['path']}` | `{r['permission']}` |"
        for i, r in enumerate(records, start=1)
    ]
    lines += [
        "",
        "## Ejemplos",
        "",
        "- Puede: ver la respuesta esperada de cada paso.",
        "- No puede: `inventario.test` recibe `403` en todas las llamadas (no tiene permisos de "
        "auditoría); en el registro, incluso `admin.test` recibe `403` porque no es una cuenta de servicio.",
    ]
    return "\n".join(lines) + "\n"


def render_exercise(exercise: dict, records: list[dict]) -> dict[str, str]:
    files = {
        "ORDEN.md": render_order(exercise, records),
        "00-datos-ficticios.md": render_data(exercise),
        "USUARIOS.md": render_users(exercise, records),
    }
    for index, record in enumerate(records, start=1):
        files[record["step"]["file"]] = render_step(exercise, index, record, {})
    return files


def render_general(all_records: dict[int, list[dict]]) -> str:
    lines = [
        "# Usuarios y permisos de audit-service",
        "",
        "Generado por `tests/examples/test_examples.py` a partir de la plantilla del realm "
        "(`infrastructure/keycloak/realm-template/sio-realm.template.json`).",
        "",
        "## Cómo se evalúan los permisos",
        "",
        "- Cada URL exige un permiso `perm:audit:{recurso}:{accion}` (`sio-auth`). El `403` nunca revela "
        "el permiso exigido; queda solo en el log del servidor con el `trace_id`.",
        "- **Registrar** (`perm:audit:audit-events:create`) exige además un token de **cuenta de "
        "servicio**: ningún usuario humano registra eventos, aunque tenga el permiso por comodín.",
        "- **Auditoría de una empresa** (`perm:audit:audit-events:read`) exige además la membresía "
        f"`ACTIVE` en la empresa y `{OC_PERMISSION}`, que pide Operational Context al resolver el "
        "acceso. Ser miembro de una empresa **no** da acceso a su auditoría (FR-037).",
        "- **Eventos de plataforma** (`perm:audit:platform-events:read`): permiso independiente, sin "
        "membresía. El permiso de empresa no da acceso a estos eventos y viceversa.",
        "- Ningún grupo recibe permisos de auditoría explícitos: `administradores` y `supervisores` los "
        "obtienen por comodín. Otro grupo se habilita asignándolos en Keycloak, sin cambios de código.",
        "",
        "## Usuarios de prueba",
        "",
        "| Usuario | Grupo | Lectura de empresa | Lectura de plataforma | Registro |",
        "| --- | --- | --- | --- | --- |",
    ]
    from tests.examples.users import allowed

    for user in USERS:
        lines.append(
            f"| `{user['username']}` | `{user['group']}` | "
            f"{'Sí' if allowed(user, 'perm:audit:audit-events:read') else 'No'} | "
            f"{'Sí' if allowed(user, 'perm:audit:platform-events:read') else 'No'} | No (no es cuenta de servicio) |"
        )
    lines.append(f"| `{EMITTER}` | cuenta de servicio | No | No | Sí (`perm:audit:audit-events:create`) |")

    lines += [
        "",
        "## Cómo obtener los tokens",
        "",
        "Usuarios (contraseña en la variable `KEYCLOAK_TEST_USER_PASSWORD`, nunca en estos documentos):",
        "",
        "```bash",
        "curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \\",
        "  -d grant_type=password -d client_id=sio-web -d scope=openid \\",
        "  -d username=supervisor.test -d password=\"$KEYCLOAK_TEST_USER_PASSWORD\"",
        "```",
        "",
        "Cuenta de servicio de pruebas (secreto en `AUDIT_TEST_EMITTER_CLIENT_SECRET`):",
        "",
        "```bash",
        "curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \\",
        "  -d grant_type=client_credentials -d client_id=audit-test-emitter \\",
        "  -d client_secret=\"$AUDIT_TEST_EMITTER_CLIENT_SECRET\"",
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
