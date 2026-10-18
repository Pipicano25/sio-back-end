"""Genera la documentación de `docs/ejemplo/` a partir de las ejecuciones (Principio XXII).

Los valores que cambian en cada ejecución (`generated_at`, `trace_id`) se muestran como marcadores.
"""

from __future__ import annotations

import json
from typing import Any

from tests.examples.users import USERS

ASSIGNED = "<asignado por el servicio>"
VOLATILE = {"generated_at", "trace_id"}


def _mask(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: (ASSIGNED if key in VOLATILE and item is not None else _mask(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [_mask(item) for item in value]
    return value


def _json(value: Any) -> str:
    return "```json\n" + json.dumps(_mask(value), ensure_ascii=False, indent=2) + "\n```"


def _access_table(record: dict) -> list[str]:
    lines = ["| Usuario | ¿Puede? | Respuesta | Motivo |", "| --- | --- | --- | --- |"]
    for user in USERS:
        info = record["access"][user["username"]]
        lines.append(f"| `{user['username']}` | {'Sí' if info['allowed'] else 'No'} | `{info['status']}` | "
                     f"{info['reason']} |")
    return lines


def render_step(exercise: dict, index: int, record: dict) -> str:
    step = record["step"]
    lines = [f"# Paso {index}. {step['title']}", "", f"Ejercicio {exercise['number']}: {exercise['title']}.", "",
             "## Llamada", "", f"`{step['method']} {record['path']}`", "", f"Ejecuta: `{step['actor']}`.", "",
             "### Por qué", ""]
    lines += [f"- {item}" for item in step["why"]] + [""]
    lines += ["## Permisos", "", f"La URL exige `{record['permission']}`.", "",
              "Como el servicio consulta a los propietarios **con el token del usuario**, el usuario también "
              "necesita: " + ", ".join(f"`{item}`" for item in step["requires"]) + ". Además debe ser miembro "
              "`ACTIVE` de la empresa (no se exige asignación a la sucursal).", ""]
    lines += _access_table(record)
    lines += ["", "Respuesta sin permiso (`403`), que no revela el permiso exigido:", "", _json(record["forbidden"]),
              "", "## Respuesta", "", f"`{record['status']}`", ""]
    if step["kind"] == "csv":
        lines += [f"Cabeceras: `Content-Type: {record['headers'].get('content-type')}` y "
                  f"`Content-Disposition: {record['headers'].get('content-disposition')}`.", "",
                  "Contenido (el archivo empieza con el BOM UTF-8, invisible):", "", "```csv",
                  record["response"].lstrip("﻿").rstrip("\r\n").replace("\r\n", "\n"), "```"]
    else:
        lines.append(_json(record["response"]))
    return "\n".join(lines) + "\n"


def render_exercise(exercise: dict, records: list[dict], common: list[str]) -> dict[str, str]:
    files: dict[str, str] = {}
    files["00-datos-ficticios.md"] = "\n".join(
        [f"# Datos del ejercicio {exercise['number']}: {exercise['title']}", "",
         "Todos los datos son **ficticios** (ningún dato de DAO ni identificación real).", ""]
        + [f"- {item}" for item in common + exercise["data"]]) + "\n"
    files["ORDEN.md"] = "\n".join(
        [f"# Orden del ejercicio {exercise['number']}: {exercise['title']}", ""]
        + [f"- {item}" for item in exercise["order"]] + ["", "| Paso | Archivo | Llamada |", "| --- | --- | --- |"]
        + [f"| {i} | [{r['step']['file']}]({r['step']['file']}) | `GET {r['path']}` |"
           for i, r in enumerate(records, start=1)]
        + ["", "No se guardan variables entre pasos: todos usan los identificadores fijos de los datos."]) + "\n"
    for index, record in enumerate(records, start=1):
        files[record["step"]["file"]] = render_step(exercise, index, record)
    users = [f"# Usuarios del ejercicio {exercise['number']}: {exercise['title']}", ""]
    for index, record in enumerate(records, start=1):
        users += [f"## Paso {index}: `GET {record['path']}`", "", f"Permiso: `{record['permission']}`.", ""]
        users += _access_table(record) + [""]
    files["USUARIOS.md"] = "\n".join(users)
    return files


def render_general(results: dict[int, list[dict]]) -> str:
    lines = ["# Usuarios y permisos de business-reporting-service", "",
             "- Cada reporte exige su permiso `perm:business-reporting:<reporte>:read`, evaluado por `sio-auth`; el "
             "`403` nunca revela el permiso.",
             "- El servicio consulta Sales, Purchase, Inventory, Operational Context, Commercial Relationship y "
             "Product Catalog **con el token del usuario** (DR-07): el usuario necesita además el permiso de lectura "
             "de cada propietario. Si el propietario responde `403`, el reporte responde el mismo `403` genérico.",
             "- `reportes` consulta la evolución de existencias con `perm:inventory:stock_evolution:read`, que **no** "
             "abre el kardex ni los costos (DR-11).",
             "- Sin costos ni márgenes: el margen bruto es de la fase 2 de la spec 023.", "",
             "## Usuarios de prueba", "", "| Usuario | Grupo |", "| --- | --- |"]
    lines += [f"| `{u['username']}` | `{u['group']}` |" for u in USERS]
    lines += ["", "## Cómo obtener el token", "", "```bash",
              "curl -s -X POST \"$KEYCLOAK_TOKEN_URL\" \\",
              "  -d grant_type=password -d client_id=sio-web \\",
              "  -d username=reportes.test -d password=\"$KEYCLOAK_TEST_USER_PASSWORD\"", "```", "",
              "## Matriz de las URL", "", "| Ejercicio | Paso | URL | Permiso | "
              + " | ".join(f"`{u['username']}`" for u in USERS) + " |",
              "| --- | --- | --- | --- | " + " | ".join("---" for _ in USERS) + " |"]
    for number in sorted(results):
        for index, record in enumerate(results[number], start=1):
            cells = ["✅" if record["access"][u["username"]]["allowed"] else "❌" for u in USERS]
            lines.append(f"| {number} | {index} | `GET {record['path']}` | `{record['permission']}` | "
                         + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"
