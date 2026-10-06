"""Ejecuta los ejercicios contra la API y verifica los permisos de cada llamada (Principio XXII).

Para cada llamada:

1. la repite con una identidad sin permisos y lee el permiso exacto del log de `sio-auth`
   (la respuesta `403` nunca lo revela, y se comprueba);
2. comprueba que ese permiso exista en la plantilla del realm;
3. registro: cada usuario de prueba recibe `403` (solo cuentas de servicio registran, aunque
   tengan el permiso por comodín) y `audit-test-emitter` tiene el permiso en la plantilla;
   consulta: cada usuario sin el permiso recibe `403` y cada usuario con él obtiene el mismo
   estado que el actor;
4. la ejecuta con el actor y comprueba el estado documentado.

Operational Context (clase C) no se ejecuta: se simula con el doble del puerto y todos los
usuarios de prueba son miembros `ACTIVE` de la empresa de los ejercicios.
"""

from __future__ import annotations

import logging
import re

from sio_auth import DENIED_PERMISSION_ATTRIBUTE, LOGGER_NAME

from tests.examples.exercises import REGISTRO
from tests.examples.users import EMITTER_ROLES, REALM_ROLES, USERS, allowed, matching_grant

PLACEHOLDER = re.compile(r"<([A-Z0-9_]+)>")
EMITTER = "emisor"
NO_PERMISSIONS_HUMAN = "__humano_sin_permisos__"
NO_PERMISSIONS_SERVICE = "__cuenta_de_servicio_sin_permisos__"


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
    return client.request(step["method"], path, **({"json": body} if body is not None else {}))


def _probe(client, step, path, body):
    handler = _DeniedPermissions()
    log = logging.getLogger(LOGGER_NAME)
    log.addHandler(handler)
    try:
        response = _request(client, step, path, body)
    finally:
        log.removeHandler(handler)
    return response, handler.permissions


def run_exercise(exercise: dict, clients: dict) -> list[dict]:
    """Ejecuta un ejercicio y devuelve un registro por paso para generar la documentación."""
    ctx: dict[str, str] = {}
    records = []

    for step in exercise["steps"]:
        path = substitute(step["path"], ctx)
        body = substitute(step.get("body"), ctx)
        title = f"{exercise['folder']} / {step['file']}"

        probe_client = clients[NO_PERMISSIONS_SERVICE if step["kind"] == REGISTRO else NO_PERMISSIONS_HUMAN]
        probe, denied = _probe(probe_client, step, path, body)
        assert probe.status_code == 403, f"{title}: sin permisos respondió {probe.status_code}"
        assert "perm:" not in probe.text, f"{title}: el 403 revela un permiso"
        assert len(denied) == 1, f"{title}: sio-auth registró {denied}"
        permission = denied[0]
        assert permission in REALM_ROLES, f"{title}: {permission} no existe en la plantilla del realm"

        access: dict[str, dict] = {}
        for user in USERS:
            name = user["username"]
            if step["kind"] == REGISTRO:
                response = _request(clients[name], step, path, body)
                assert response.status_code == 403, f"{title}: {name} registró ({response.status_code})"
                grant = matching_grant(user["perms"], permission)
                reason = (
                    f"tiene `{grant}` por comodín, pero no es una cuenta de servicio" if grant
                    else f"no tiene `{permission}` y no es una cuenta de servicio"
                )
                access[name] = {"allowed": False, "status": 403, "reason": reason}
            elif allowed(user, permission):
                expected = step["expect"]
                if step["actor"] != name:
                    response = _request(clients[name], step, path, body)
                    assert response.status_code == expected, f"{title}: {name} → {response.status_code}"
                access[name] = {
                    "allowed": True,
                    "status": expected,
                    "reason": f"tiene `{matching_grant(user['perms'], permission)}`",
                }
            else:
                response = _request(clients[name], step, path, body)
                assert response.status_code == 403, f"{title}: {name} sin permiso → {response.status_code}"
                access[name] = {"allowed": False, "status": 403, "reason": f"no tiene `{permission}`"}

        if step["kind"] == REGISTRO:
            assert matching_grant(EMITTER_ROLES, permission), f"{title}: audit-test-emitter no tiene {permission}"

        actor = clients[EMITTER if step["actor"] == "emisor" else step["actor"]]
        response = _request(actor, step, path, body)
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
