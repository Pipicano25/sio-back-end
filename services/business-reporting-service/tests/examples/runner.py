"""Ejecuta los ejercicios contra la API y verifica los permisos de cada llamada (Principio XXII).

Para cada paso:

1. lo repite con una identidad sin permisos y lee el permiso funcional exacto del log de `sio-auth` (el `403` nunca
   lo revela, y se comprueba) y que exista en la plantilla del realm;
2. cada usuario de prueba con el permiso funcional **y** los del propietario (`requires`, DR-07) obtiene la
   respuesta; los demás, `403`;
3. lo ejecuta con el actor y comprueba el estado documentado.
"""

from __future__ import annotations

import logging

from sio_auth import DENIED_PERMISSION_ATTRIBUTE, LOGGER_NAME

from tests.examples.users import REALM_ROLES, USERS, allowed, matching_grant

NO_PERMISSIONS = "__sin_permisos__"


class _DeniedPermissions(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.permissions: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        value = getattr(record, DENIED_PERMISSION_ATTRIBUTE, None)
        if value:
            self.permissions.append(value)


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
        return False, f"tiene `{grant}`, pero no `{missing[0]}` (lo exige el propietario)"
    return True, f"tiene `{grant}` y los permisos de lectura del propietario"


def run_exercise(exercise: dict, clients: dict) -> list[dict]:
    records = []
    for step in exercise["steps"]:
        path = step["path"]
        title = f"{exercise['folder']} / {step['file']}"
        probe, denied = _probe(clients[NO_PERMISSIONS], path)
        assert probe.status_code == 403, f"{title}: sin permisos respondió {probe.status_code}"
        assert "perm:" not in probe.text, f"{title}: el 403 revela un permiso"
        assert len(denied) == 1, f"{title}: sio-auth registró {denied}"
        permission = denied[0]
        assert permission in REALM_ROLES, f"{title}: {permission} no existe en la plantilla del realm"
        for item in step["requires"]:
            assert item in REALM_ROLES, f"{title}: {item} no existe en la plantilla del realm"

        access: dict[str, dict] = {}
        for user in USERS:
            name = user["username"]
            can, reason = _reason(user, permission, step["requires"])
            expected = (step["expect"] if name == step["actor"] else step["allowed_status"]) if can else 403
            response = clients[name].get(path)
            assert response.status_code == expected, f"{title}: {name} → {response.status_code} ≠ {expected}"
            if expected == 403:
                assert "perm:" not in response.text, f"{title}: el 403 revela un permiso"
            access[name] = {"allowed": can, "status": expected, "reason": reason}

        response = clients[step["actor"]].get(path)
        assert response.status_code == step["expect"], f"{title}: {response.status_code} {response.text[:200]}"
        payload = response.text if step["kind"] == "csv" else response.json()
        records.append(dict(step=step, path=path, permission=permission, access=access, status=response.status_code,
                            response=payload, forbidden=probe.json(),
                            headers={k: response.headers[k] for k in ("content-type", "content-disposition")
                                     if k in response.headers}))
    return records
