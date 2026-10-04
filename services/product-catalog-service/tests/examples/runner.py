"""Ejecuta los ejercicios de docs/ejemplo/ contra la API (Principio XXII).

Para cada llamada del catálogo:

1. Si se entregan clientes por usuario, la repite sin permisos y lee el permiso exacto que exige
   la URL del log de `sio-auth` (la respuesta `403` nunca lo revela, y se comprueba); comprueba que cada usuario de prueba sin ese permiso
   reciba `403` y que los usuarios con permiso obtengan la misma respuesta en las consultas.
2. La ejecuta como administrador y comprueba el código de estado documentado.

Las llamadas a Party Identity y Geography (clase C, Principio IV) no se ejecutan: el fabricante se
simula con el doble `FakeManufacturerDirectory` y el permiso se toma del ejercicio.
"""

import logging
import re
import uuid

from sio_auth import DENIED_PERMISSION_ATTRIBUTE, LOGGER_NAME

from tests.examples.users import USERS, allowed

PLACEHOLDER = re.compile(r"<([A-Z0-9_]+)>")
ADMIN = "admin.test"
NO_PERMISSIONS = "__sin_permisos__"



class _DeniedPermissions(logging.Handler):
    """Captura el permiso que `sio-auth` registra al denegar (nunca viaja en la respuesta)."""

    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.permissions: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        value = getattr(record, DENIED_PERMISSION_ATTRIBUTE, None)
        if value:
            self.permissions.append(value)


def _probe(client, method, path, kwargs):
    """Repite la llamada sin permisos y devuelve la respuesta y el permiso registrado en el log."""
    handler = _DeniedPermissions()
    log = logging.getLogger(LOGGER_NAME)
    log.addHandler(handler)
    try:
        response = client.request(method, path, **kwargs)
    finally:
        log.removeHandler(handler)
    return response, handler.permissions

def substitute(value, ctx):
    if isinstance(value, str):
        def replace(match):
            name = match.group(1)
            if name not in ctx:
                raise KeyError(f"Variable sin valor: <{name}>")
            return str(ctx[name])

        return PLACEHOLDER.sub(replace, value)
    if isinstance(value, dict):
        return {key: substitute(item, ctx) for key, item in value.items()}
    if isinstance(value, list):
        return [substitute(item, ctx) for item in value]
    return value


def resolve(data, path):
    current = data
    for part in path.split("."):
        match = re.fullmatch(r"(\w+)(?:\[(\d+)\])?", part)
        key, index = match.group(1), match.group(2)
        current = current[key]
        if index is not None:
            current = current[int(index)]
    return current


def _check_access(call, clients, method, path, kwargs, expected, record):
    probe, denied = _probe(clients[NO_PERMISSIONS], method, path, kwargs)
    assert probe.status_code == 403, f"{call['title']}: sin permisos respondió {probe.status_code}"
    assert "perm:" not in probe.text, f"{call['title']}: el 403 revela un permiso: {probe.text}"
    assert len(denied) == 1, f"{call['title']}: sio-auth registró {denied} al denegar"
    permission = denied[0]
    record.update(permission=permission, forbidden_example=probe.json(), access={}, verified={})

    for user in USERS:
        name = user["username"]
        can = allowed(user, permission)
        record["access"][name] = can
        if not can:
            response = clients[name].request(method, path, **kwargs)
            assert response.status_code == 403, (
                f"{call['title']}: {name} no tiene {permission} y respondió {response.status_code}"
            )
            record["verified"][name] = 403
        elif method == "GET" and name != ADMIN:
            response = clients[name].request(method, path, **kwargs)
            assert response.status_code in expected, (
                f"{call['title']}: {name} tiene lectura y respondió {response.status_code}: {response.text}"
            )
            record["verified"][name] = response.status_code


def run_exercise(api, manufacturer_directory, exercise, clients=None):
    """Ejecuta un ejercicio. Devuelve (ctx, records) para generar la documentación."""
    ctx, records = {}, []
    for step_index, step in enumerate(exercise["steps"]):
        for call_index, call in enumerate(step["calls"]):
            record = {"step": step_index, "call": call_index}

            if call["external"]:
                if clients is not None:
                    record["permission"] = call["perm"]
                    record["access"] = {user["username"]: allowed(user, call["perm"]) for user in USERS}
                for var in call["save"]:
                    fake = uuid.uuid5(uuid.NAMESPACE_DNS, f"{exercise['folder']}-{var}")
                    manufacturer_directory.existing.add(fake)
                    ctx[var] = str(fake)
                record["external"] = True
                records.append(record)
                continue

            if call["cond"] and ctx[call["cond"]]:
                # El registro ya existía (lo creó otro ejercicio): se reutiliza su id.
                for var in call["save"]:
                    ctx[var] = ctx[call["cond"]][0]["id"]
                record["skipped"] = True
                records.append(record)
                continue

            path = substitute(call["path"], ctx)
            body = substitute(call["body"], ctx)
            kwargs = {"json": body} if body is not None else {}
            expected = [call["expect"]] if call["expect"] else [200, 201]

            if clients is not None:
                _check_access(call, clients, call["method"], path, kwargs, expected, record)

            response = api.request(call["method"], path, **kwargs)
            payload = response.json() if response.content else None
            assert response.status_code in expected, (
                f"{exercise['folder']} / {step['file']} / {call['title']}: "
                f"{response.status_code} {payload}"
            )
            for var, where in call["save"].items():
                ctx[var] = resolve(payload, where)
            record.update(status=response.status_code, response=payload)
            records.append(record)
    return ctx, records
