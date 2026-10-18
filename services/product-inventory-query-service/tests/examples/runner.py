"""Ejecuta los ejercicios contra la API y verifica los permisos de cada llamada (Principio XXII; T128).

Para cada paso:

1. lo repite con una identidad sin permisos y lee el permiso exacto del log de `sio-auth` (el `403` nunca lo
   revela, y se comprueba);
2. comprueba que ese permiso exista en la plantilla del realm;
3. cada usuario de prueba sin el permiso recibe `403` (`compras`, `reportes` y `consulta` en todas las consultas);
   cada usuario con él, y con los permisos de bloque que el paso exija (`requires`), obtiene `allowed_status`, y
   los que tienen el permiso funcional pero no los de bloque reciben `403`;
4. lo ejecuta con el actor y comprueba el estado documentado.
"""

from __future__ import annotations

import logging
import re

from sio_auth import DENIED_PERMISSION_ATTRIBUTE, LOGGER_NAME

from tests.examples.users import REALM_ROLES, USERS, allowed, matching_grant

PLACEHOLDER = re.compile(r"<([A-Z0-9_]+)>")
NO_PERMISSIONS = "__sin_permisos__"


class _DeniedPermissions(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.permissions: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        value = getattr(record, DENIED_PERMISSION_ATTRIBUTE, None)
        if value:
            self.permissions.append(value)


def substitute(value: str, ctx: dict) -> str:
    return PLACEHOLDER.sub(lambda match: str(ctx[match.group(1)]), value)


def _probe(client, path):
    handler = _DeniedPermissions()
    log = logging.getLogger(LOGGER_NAME)
    log.addHandler(handler)
    try:
        response = client.get(path)
    finally:
        log.removeHandler(handler)
    return response, handler.permissions


def _reason(user: dict, permission: str, requires: list[str]) -> tuple[bool, str]:
    grant = matching_grant(user["perms"], permission)
    if grant is None:
        return False, f"no tiene `{permission}`"
    missing = [item for item in requires if not allowed(user, item)]
    if missing:
        return False, f"tiene `{grant}`, pero no `{missing[0]}`"
    extra = [f"`{matching_grant(user['perms'], item)}`" for item in requires]
    return True, "tiene " + ", ".join([f"`{grant}`", *extra])


def run_exercise(exercise: dict, clients: dict) -> list[dict]:
    """Ejecuta un ejercicio y devuelve un registro por paso para generar la documentación."""
    ctx: dict[str, str] = {}
    records = []

    for step in exercise["steps"]:
        path = substitute(step["path"], ctx)
        title = f"{exercise['folder']} / {step['file']}"

        probe, denied = _probe(clients[NO_PERMISSIONS], path)
        assert probe.status_code == 403, f"{title}: sin permisos respondió {probe.status_code}"
        assert "perm:" not in probe.text, f"{title}: el 403 revela un permiso"
        assert len(denied) == 1, f"{title}: sio-auth registró {denied}"
        permission = denied[0]
        assert permission in REALM_ROLES, f"{title}: {permission} no existe en la plantilla del realm"

        access: dict[str, dict] = {}
        for user in USERS:
            name = user["username"]
            can, reason = _reason(user, permission, step["requires"])
            expected = (step["expect"] if name == step["actor"] else step["allowed_status"]) if can else 403
            if name == step["actor"]:
                assert expected == step["expect"], f"{title}: el actor {name} debería recibir {expected}"
            else:
                response = clients[name].get(path)
                assert response.status_code == expected, f"{title}: {name} → {response.status_code} ≠ {expected}"
            access[name] = {"allowed": can, "status": expected, "reason": reason}

        response = clients[step["actor"]].get(path)
        payload = response.json() if response.content else None
        assert response.status_code == step["expect"], f"{title}: {response.status_code} {payload}"
        if step["expect"] == 403:
            assert "perm:" not in response.text, f"{title}: el 403 revela un permiso"

        for variable, where in step["save"].items():
            ctx[variable] = payload[where]

        records.append(dict(step=step, path=path, permission=permission, access=access, status=response.status_code,
                            response=payload, forbidden=probe.json(), ctx=dict(ctx)))
    return records
