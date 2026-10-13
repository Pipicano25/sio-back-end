"""Renderizado de la guía del recorrido `docs/validacion-mvp/` desde los pasos (research R-12).

Formato de los `docs/ejemplo/` de los servicios (Principio XXII): índice, `usuarios-y-permisos.md` y un
directorio por ejercicio con `ORDEN.md`, `USUARIOS.md` y un archivo por grupo de pasos. Los valores de la
corrida se muestran como marcadores estables (`<EMPRESA_A>`, `<COMPRA_1>`, `<RUN_ID>`), así que la guía no
depende del `RUN_ID`. Nunca contiene contraseñas, secretos ni tokens.
"""

from __future__ import annotations

import json
import re
from collections import OrderedDict
from pathlib import Path
from typing import Any, Iterable

from . import config
from .auth import TEST_USERS

GUIDE_DIR = config.REPO_ROOT / "docs" / "validacion-mvp"
MARKER = re.compile(r"\{([a-z0-9_]+)\}")
CHECK, CROSS = "✅", "❌"

FAMILY_TITLES = {
    "C-00": "Consultar los datos de referencia",
    "C-01": "Registrar las organizaciones",
    "C-02": "Registrar las personas",
    "C-03": "Registrar las empresas",
    "C-04": "Registrar las sucursales",
    "C-05": "Registrar los usuarios operativos",
    "C-06": "Asignar sucursales",
    "C-07": "Comprobar el contexto operativo",
    "C-08": "Seleccionar el proveedor y su condición de pago",
    "C-09": "Incorporar el cliente",
    "C-10": "Crear los productos globales",
    "C-11": "Adoptar productos y presentación",
    "C-12": "Crear las listas de precios",
    "C-13": "Crear las secuencias de numeración",
    "P-01": "Registrar las compras",
    "P-02": "Confirmar las compras",
    "P-03": "Consultar el inventario tras las compras",
    "V-01": "Registrar las ventas",
    "V-02": "Consultar la disponibilidad",
    "V-03": "Confirmar las ventas",
    "V-04": "Rechazo por existencias insuficientes",
    "V-05": "Rechazo por precio cambiado",
    "V-05b": "Rechazo por producto inactivo",
    "V-06": "Costo y margen según el permiso",
    "V-07": "Consultar el inventario tras las ventas",
    "A-01": "Anular borradores y documentos confirmados",
    "A-02": "Rechazo al anular una compra consumida",
    "A-03": "Consultar el inventario final",
    "U-01": "Consultar el historial de auditoría",
    "U-02": "Datos protegidos y permiso de auditoría",
    "I-01": "Aislamiento en Operational Context",
    "I-02": "Aislamiento en Commercial Relationship",
    "I-03": "Aislamiento en Purchase",
    "I-04": "Aislamiento en Sales",
    "I-05": "Aislamiento en Inventory",
    "I-06": "Aislamiento en Audit",
    "S-01": "Permisos: el vendedor no compra",
    "S-02": "Permisos: el comprador no vende",
    "S-03": "Permisos: consulta no escribe",
    "S-04": "Permisos: la cuenta de servicio de Sales no vende",
    "S-05": "Permisos: la cuenta de servicio de Purchase no compra",
    "S-06": "Sin token y con token inválido",
}


def marker_name(name: str) -> str:
    return "<RUN_ID>" if name == "run" else f"<{name.upper()}>"


def show(value: Any) -> Any:
    if isinstance(value, str):
        return MARKER.sub(lambda match: marker_name(match.group(1)), value)
    if isinstance(value, dict):
        return {key: show(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [show(item) for item in value]
    return value


def url(step) -> str:
    service = config.service(step.service)
    prefix = "" if step.root else service.api_prefix
    return f"http://127.0.0.1:{service.port}{prefix}{show(step.path)}"


def permissions(step) -> list[str]:
    return [item.strip() for item in step.permission.split("+") if item.strip().startswith("perm:")]


def who_can(step, realm) -> list[str]:
    needed = permissions(step)
    if not needed:
        return []
    return [user for user in TEST_USERS if all(realm.has_permission(user, permission) for permission in needed)]


def slug(text: str) -> str:
    replacements = str.maketrans("áéíóúñü", "aeiounu")
    text = text.lower().translate(replacements)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def render_call(step, realm, number: int) -> str:
    lines = [f"## {number}. {step.title}", ""]
    lines.append(f"Paso `{step.id}` · usuario **`{step.user}`** · ítems de la FASE 10: {', '.join(str(item) for item in step.items)}")
    lines += ["", "```http", f"{step.method} {url(step)}"]
    if step.params:
        query = "&".join(f"{key}={show(value)}" for key, value in step.params.items())
        lines[-1] += f"?{query}"
    if step.idempotent:
        lines += ["Idempotency-Key: mvp-<RUN_ID>-" + step.id + "-1", "X-Correlation-Id: <UUID de la corrida y el paso>"]
    lines += ["```", ""]
    if step.body is not None:
        lines += ["```json", json.dumps(show(step.body), ensure_ascii=False, indent=2), "```", ""]
    needed = permissions(step)
    if needed:
        lines.append("**Permiso que exige la URL:** " + " + ".join(f"`{item}`" for item in needed))
        allowed = who_can(step, realm)
        detail = []
        for user in allowed:
            roles = sorted({realm.granting_role(user, item) for item in needed} - {None})
            detail.append(f"`{user}` (por {', '.join(f'`{role}`' for role in roles)})")
        lines += ["", f"- {CHECK} **Pueden:** " + (", ".join(detail) if detail else "ninguno de los usuarios de prueba")]
    else:
        lines.append("**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.")
    lines.append("")
    if step.why:
        lines += ["**Por qué se hace así**", "", f"- {step.why}", ""]
    lines.append(f"**Respuesta esperada:** `{step.expect}`" + (f" — {step.expected_note}" if step.expected_note else ""))
    if step.save:
        lines += ["", "**Guardar:** " + ", ".join(f"`{source}` → `{marker_name(name)}`" for name, source in step.save.items())]
    if step.audit:
        actions = ", ".join(f"`{spec.action}` ({spec.service})" for spec in step.audit)
        lines += ["", f"**Auditoría que deja:** {actions}"]
    lines.append("")
    return "\n".join(lines)


def _families(steps: Iterable) -> "OrderedDict[str, OrderedDict[str, list]]":
    exercises: OrderedDict[str, OrderedDict[str, list]] = OrderedDict()
    for step in steps:
        exercises.setdefault(step.exercise, OrderedDict()).setdefault(step.family, []).append(step)
    return exercises


def _family_file(index: int, family: str, steps: list) -> str:
    title = FAMILY_TITLES.get(family, steps[0].title)
    return f"{index:02d}-{slug(title)}.md"


def render(steps: list, realm, exercises_titles: dict[str, str] | None = None) -> dict[str, str]:
    from scenario.steps import EXERCISES

    titles = exercises_titles or EXERCISES
    exercises = _families(steps)
    pages: dict[str, str] = {}
    index_rows = []
    for exercise, families in exercises.items():
        title = titles.get(exercise, exercise)
        number = exercise.split("-", 1)[0]
        index_rows.append(f"| [{number} — {title}]({exercise}/ORDEN.md) | {sum(len(item) for item in families.values())} |")
        order_rows, user_rows = [], []
        files = []
        for position, (family, family_steps) in enumerate(families.items(), start=1):
            name = _family_file(position, family, family_steps)
            files.append(name)
            family_title = FAMILY_TITLES.get(family, family_steps[0].title)
            produced = sorted({marker_name(var) for step in family_steps for var in step.save})
            order_rows.append(
                f"| {position:02d} | [{name}]({name}) | {family_title} | {len(family_steps)} | {', '.join(f'`{item}`' for item in produced) or '—'} |"
            )
            calls = [render_call(step, realm, number) for number, step in enumerate(family_steps, start=1)]
            nav = f"Ejercicio {number} — {title} · [Orden del ejercicio](ORDEN.md)"
            pages[f"{exercise}/{name}"] = "\n".join(
                [f"# Paso {position:02d} de {len(families):02d} — {family_title}", "", nav, "", "---", "", *calls]
            )
            for step in family_steps:
                marks = []
                for user in TEST_USERS:
                    allowed = bool(permissions(step)) and all(realm.has_permission(user, item) for item in permissions(step))
                    marks.append(CHECK if allowed else CROSS)
                permission = " + ".join(f"`{item}`" for item in permissions(step)) or "—"
                user_rows.append(
                    f"| [{position:02d}]({name}) | `{step.id}` | `{step.method} {show(step.path)}` | {permission} | `{step.user}` | {' | '.join(marks)} |"
                )
        pages[f"{exercise}/ORDEN.md"] = "\n".join(
            [
                f"# Ejercicio {number} — {title}",
                "",
                "[← Recorrido completo](../README.md)",
                "",
                "**Datos:** ficticios, con el `RUN_ID` de la corrida en nombres y códigos (`<RUN_ID>`).",
                "",
                "## Orden de ejecución",
                "",
                "Ejecute los archivos en este orden; cada paso usa los `id` guardados en los anteriores (y en los ejercicios previos).",
                "",
                "| Paso | Archivo | Qué hace | Llamadas | Deja guardado |",
                "| --- | --- | --- | --- | --- |",
                *order_rows,
                "",
                f"Usuarios y permisos de este ejercicio: [USUARIOS.md](USUARIOS.md).",
                "",
            ]
        )
        header = " | ".join(user.split(".")[0] for user in TEST_USERS)
        pages[f"{exercise}/USUARIOS.md"] = "\n".join(
            [
                f"# Usuarios y permisos — Ejercicio {number} — {title}",
                "",
                "[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)",
                "",
                f"{CHECK} = el usuario tiene el permiso (o los permisos) de la llamada según la plantilla del realm · {CROSS} = recibe `403`. "
                "Tener el permiso no basta en las rutas de empresa: fuera de sus empresas el usuario recibe `404` (aislamiento).",
                "",
                f"| Paso | Id | Método y ruta | Permiso requerido | Usuario del recorrido | {header} |",
                "| --- | --- | --- | --- | --- | " + " | ".join("---" for _ in TEST_USERS) + " |",
                *user_rows,
                "",
            ]
        )
    pages["README.md"] = _readme(index_rows)
    pages["usuarios-y-permisos.md"] = _users(realm)
    return pages


def _readme(index_rows: list[str]) -> str:
    return "\n".join(
        [
            "# Recorrido del MVP de SIO — guía de validación",
            "",
            "Recorrido completo del MVP con los servicios reales: configuración de la empresa → relación comercial y",
            "precios → compras e inventario → ventas con precio por presentación → anulaciones → auditoría →",
            "seguridad entre empresas. Cada paso indica el usuario de prueba, el permiso que exige la URL, la petición y",
            "la respuesta esperada (Principio XXII, feature 017).",
            "",
            "**Esta guía se genera desde los pasos de la suite** (`validation/mvp-e2e/scenario/`) y la etapa `guia` de",
            "`bash validation/mvp-e2e/run.sh` exige que sea idéntica a la generada y que cada paso se haya ejecutado contra",
            "los servicios: si una API, un permiso o un valor cambian, la validación falla hasta regenerarla con",
            "`SIO_MVP_GUIDE_WRITE=1 bash validation/mvp-e2e/run.sh --etapa recorrido --etapa seguridad --etapa guia`.",
            "",
            "## Datos",
            "",
            "**Todos los datos son ficticios**: organizaciones, personas, productos, precios y documentos llevan",
            "\"(dato ficticio)\" y el identificador de la corrida (`<RUN_ID>`). Los números de identificación se generan con",
            "el patrón de la regla vigente de Party Identity y no corresponden a personas ni empresas reales. Montos sin",
            "impuestos para que costos y márgenes sean exactos (`specs/017-mvp-integral-validation/data-model.md` §3).",
            "",
            "## Antes de empezar",
            "",
            "1. Entorno integrado levantado (`infrastructure/`), con migraciones y seeds; puertos en `docs/port-map.md`.",
            "2. Token de Keycloak (`http://127.0.0.1:8081`, realm `sio`, cliente `sio-web`); la contraseña de los usuarios",
            "   de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env` (ver",
            "   [usuarios-y-permisos.md](usuarios-y-permisos.md)).",
            "",
            "## Convenciones",
            "",
            "- `<NOMBRE>` es un valor guardado en un paso anterior (por ejemplo `<EMPRESA_A>` o `<COMPRA_1>`).",
            "- Las URL incluyen el servicio y su puerto; las rutas funcionales llevan `/api/v1` salvo Geography y Payment Reference.",
            "- Errores en RFC 9457 con `code` (`<SERVICIO>.<CAUSA>`).",
            "",
            "## Ejercicios",
            "",
            "| Ejercicio | Llamadas |",
            "| --- | --- |",
            *index_rows,
            "",
            "Evidencia de la validación: `specs/017-mvp-integral-validation/validation-evidence.md`.",
            "",
        ]
    )


def _users(realm) -> str:
    rows = []
    for user in TEST_USERS:
        groups = ", ".join(f"`{group.strip('/')}`" for group in realm.users[user].get("groups", []))
        perms = sorted(realm.user_permissions(user))
        summary = "<br>".join(f"`{perm}`" for perm in perms[:6]) + (f"<br>… ({len(perms)} en total)" if len(perms) > 6 else "")
        rows.append(f"| `{user}` | {groups} | {summary} |")
    return "\n".join(
        [
            "# Usuarios y permisos del recorrido",
            "",
            "[← Recorrido completo](README.md)",
            "",
            "Usuarios de prueba de la plantilla del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`).",
            "Los permisos tienen la forma `perm:{servicio}:{recurso}:{acción}`; `all` vale como comodín. El permiso dice",
            "*qué* puede hacer el usuario; la membresía en una empresa (Operational Context) dice *dónde*: fuera de sus",
            "empresas recibe `404`.",
            "",
            "## Usuarios de prueba y empresas del recorrido",
            "",
            "- Empresa A: `admin.test`, `compras.test`, `ventas.test`, `supervisor.test` (asignados a la sucursal A1) y `consulta.test` (sin sucursal).",
            "- Empresa B: `reportes.test` e `inventario.test` (este último asignado a la sucursal B1). `admin.test` no se registra en B.",
            "- El vendedor no ve costo ni margen; `supervisor.test` sí (`perm:sales:sales:read-profitability`).",
            "- Las cuentas de servicio (`sales-service`, `purchase-service`) no compran ni venden: reciben `403`.",
            "",
            "| Usuario | Grupo | Permisos del grupo |",
            "| --- | --- | --- |",
            *rows,
            "",
            "## Cómo obtener el token",
            "",
            "```bash",
            "TOKEN=$(curl -s -X POST http://127.0.0.1:8081/realms/sio/protocol/openid-connect/token \\",
            "  -d grant_type=password -d client_id=sio-web -d scope=openid \\",
            '  -d username=compras.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" | jq -r .access_token)',
            "```",
            "",
        ]
    )


def write(pages: dict[str, str], directory: Path = GUIDE_DIR) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for relative, content in pages.items():
        path = directory / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def read(directory: Path = GUIDE_DIR) -> dict[str, str]:
    if not directory.is_dir():
        return {}
    return {
        str(path.relative_to(directory)).replace("\\", "/"): path.read_text(encoding="utf-8")
        for path in sorted(directory.rglob("*.md"))
    }
