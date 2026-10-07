"""Ejecuta los ejercicios contra la API y verifica los permisos de cada llamada (Principio XXII).

Para cada llamada:

1. la repite con un usuario humano sin permisos y lee el permiso exacto del log de `sio-auth`
   (la respuesta `403` nunca lo revela, y se comprueba);
2. comprueba que ese permiso exista en la plantilla del realm;
3. acción (escritura): cada usuario sin el permiso recibe `403`; una cuenta de servicio con el
   permiso por comodín recibe `403` (RC-05); los usuarios con el permiso no la repiten (cambiaría el
   estado del ejercicio); consulta: cada usuario sin el permiso recibe `403` y cada usuario con él
   obtiene el mismo estado que el actor;
4. aplica los cambios `before` en los dobles y la ejecuta con el actor, comprobando el estado.

Operational Context, Commercial Relationship, Product Catalog, Party Identity, Payment Reference
e Inventory no se ejecutan (Principio IV): los sustituyen sus dobles con los datos ficticios.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable

from sio_auth import DENIED_PERMISSION_ATTRIBUTE, LOGGER_NAME

from tests.examples.exercises import ACCION
from tests.examples.users import REALM_ROLES, USERS, allowed, matching_grant

PLACEHOLDER = re.compile(r"<([A-Z0-9_]+)>")
NO_PERMISSIONS_HUMAN = "__humano_sin_permisos__"
WILDCARD_SERVICE = "__cuenta_de_servicio_con_comodin__"


class _DeniedPermissions(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.permissions: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        value = getattr(record, DENIED_PERMISSION_ATTRIBUTE, None)
        if value:
            self.permissions.append(value)


def substitute(value, ctx):
    if isinstance(value, str):
        return PLACEHOLDER.sub(lambda match: str(ctx[match.group(1)]), value)
    if isinstance(value, dict):
        return {key: substitute(item, ctx) for key, item in value.items()}
    if isinstance(value, list):
        return [substitute(item, ctx) for item in value]
    return value


def resolve(data, path: str):
    current = data
    for part in path.split("."):
        match = re.fullmatch(r"(\w+)(?:\[(\d+)\])?", part)
        current = current[match.group(1)]
        if match.group(2) is not None:
            current = current[int(match.group(2))]
    return current


def _request(client, step, path, body):
    kwargs = {"json": body} if body is not None else {}
    if step.get("headers"):
        kwargs["headers"] = dict(step["headers"])
    return client.request(step["method"], path, **kwargs)


def _probe(client, step, path, body):
    handler = _DeniedPermissions()
    log = logging.getLogger(LOGGER_NAME)
    log.addHandler(handler)
    try:
        response = _request(client, step, path, body)
    finally:
        log.removeHandler(handler)
    return response, handler.permissions


def run_exercise(exercise: dict, clients: dict, apply_before: Callable[[str, dict], None]) -> list[dict]:
    """Ejecuta un ejercicio y devuelve un registro por paso para generar la documentación."""
    ctx: dict[str, str] = {}
    records = []

    for step in exercise["steps"]:
        path = substitute(step["path"], ctx)
        body = substitute(step.get("body"), ctx)
        title = f"{exercise['folder']} / {step['file']}"
        action = step["kind"] == ACCION

        probe, denied = _probe(clients[NO_PERMISSIONS_HUMAN], step, path, body)
        assert probe.status_code == 403, f"{title}: sin permisos respondió {probe.status_code}"
        assert "perm:" not in probe.text, f"{title}: el 403 revela un permiso"
        assert len(denied) == 1, f"{title}: sio-auth registró {denied}"
        permission = denied[0]
        assert permission in REALM_ROLES, f"{title}: {permission} no existe en la plantilla del realm"

        access: dict[str, dict] = {}
        for user in USERS:
            name = user["username"]
            grant = matching_grant(user["perms"], permission)
            if action and allowed(user, permission):
                status = step["expect"] if step["actor"] == name else "—"
                reason = f"tiene `{grant}` y asignación a la sucursal"
                if step["actor"] != name:
                    reason += "; no se repite (cambiaría el estado)"
                access[name] = {"allowed": True, "status": status, "reason": reason}
            elif allowed(user, permission):
                if step["actor"] != name:
                    response = _request(clients[name], step, path, body)
                    assert response.status_code == step["expect"], f"{title}: {name} → {response.status_code}"
                access[name] = {"allowed": True, "status": step["expect"], "reason": f"tiene `{grant}`"}
            else:
                response = _request(clients[name], step, path, body)
                assert response.status_code == 403, f"{title}: {name} sin permiso → {response.status_code}"
                access[name] = {"allowed": False, "status": 403, "reason": f"no tiene `{permission}`"}

        if action:
            response = _request(clients[WILDCARD_SERVICE], step, path, body)
            assert response.status_code == 403, f"{title}: una cuenta de servicio con comodín → {response.status_code}"

        for change in step.get("before", []):
            apply_before(change, ctx)

        response = _request(clients[step["actor"]], step, path, body)
        payload = response.json() if response.content else None
        assert response.status_code == step["expect"], f"{title}: {response.status_code} {payload}"

        for variable, where in step.get("save", {}).items():
            ctx[variable] = resolve(payload, where)

        records.append(
            dict(
                step=step,
                path=path,
                body=body,
                permission=permission,
                access=access,
                status=response.status_code,
                response=payload,
                forbidden=probe.json(),
                ctx=dict(ctx),
            )
        )

    return records
