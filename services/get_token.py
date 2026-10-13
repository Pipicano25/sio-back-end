"""Obtiene un token de Keycloak para los usuarios de prueba o los clientes técnicos de SIO.

Uso:
    python services/get_token.py              # menú para elegir el rol
    python services/get_token.py consulta     # rol directo (también acepta el número o `consulta.test`)
    TOKEN=$(python services/get_token.py admin)
    TOKEN=$(python services/get_token.py --cliente sio-data-importer)   # cliente técnico (client_credentials)
    TOKEN=$(python services/get_token.py --usuario santiago.rodriguez)  # usuario nominal (contraseña en el entorno)

La contraseña se lee de la variable de entorno `KEYCLOAK_TEST_USER_PASSWORD`; si no está
definida, se toma de `infrastructure/.env`. El secreto de un cliente técnico se lee igual, de
`<CLIENTE>_CLIENT_SECRET` (p. ej. `SIO_DATA_IMPORTER_CLIENT_SECRET`), y la de un usuario nominal, de
`<USUARIO>_PASSWORD` (p. ej. `SANTIAGO_RODRIGUEZ_PASSWORD`). Nunca se escriben en el código
(Principio IX).

La salida estándar contiene únicamente el token; el menú y los errores van a la salida de
errores, para poder capturar el token con `$(...)`.
"""

import os
import sys
from pathlib import Path

import requests

TOKEN_URL = os.environ.get(
    "KEYCLOAK_TOKEN_URL",
    "http://localhost:8081/realms/sio/protocol/openid-connect/token",
)
PASSWORD_VARIABLE = "KEYCLOAK_TEST_USER_PASSWORD"
INFRASTRUCTURE_ENV = Path(__file__).resolve().parents[1] / "infrastructure" / ".env"

ROLES = {
    "1": "admin",
    "2": "supervisor",
    "3": "compras",
    "4": "ventas",
    "5": "inventario",
    "6": "reportes",
    "7": "consulta",
}


def mensaje(texto: str = "") -> None:
    print(texto, file=sys.stderr)


def leer_variable(variable: str) -> str:
    valor = os.environ.get(variable, "").strip()
    if valor:
        return valor

    if INFRASTRUCTURE_ENV.is_file():
        for linea in INFRASTRUCTURE_ENV.read_text(encoding="utf-8").splitlines():
            nombre, separador, contenido = linea.partition("=")
            if separador and nombre.strip() == variable:
                valor = contenido.strip().strip('"').strip("'")
                if valor:
                    return valor

    raise SystemExit(
        f"Defina la variable {variable} o agréguela a {INFRASTRUCTURE_ENV}."
    )


def leer_contrasena() -> str:
    return leer_variable(PASSWORD_VARIABLE)


def variable_contrasena_usuario(username: str) -> str:
    """`santiago.rodriguez` -> `SANTIAGO_RODRIGUEZ_PASSWORD`."""
    return username.strip().upper().replace(".", "_").replace("-", "_") + "_PASSWORD"


def variable_secreto_cliente(client_id: str) -> str:
    """`sio-data-importer` -> `SIO_DATA_IMPORTER_CLIENT_SECRET` (convención de infrastructure/.env)."""
    return client_id.strip().upper().replace("-", "_") + "_CLIENT_SECRET"


def normalizar_rol(opcion: str) -> str | None:
    opcion = opcion.strip().lower().removesuffix(".test")
    if opcion in ROLES:
        return ROLES[opcion]
    if opcion in ROLES.values():
        return opcion
    return None


def elegir_rol() -> str | None:
    while True:
        mensaje("\nSeleccione un rol:")
        for numero, rol in ROLES.items():
            mensaje(f"{numero}. {rol.capitalize()}")
        mensaje("0. Salir")

        mensaje("\nIngrese el número o nombre del rol: ")
        opcion = input().strip().lower()

        if opcion in ("0", "salir", "exit"):
            mensaje("Saliendo...")
            return None

        rol = normalizar_rol(opcion)
        if rol:
            return rol
        mensaje("Opción no válida. Intente nuevamente.")


def obtener_token(rol: str) -> str:
    payload = {
        "grant_type": "password",
        "client_id": "sio-web",
        "username": f"{rol}.test",
        "password": leer_contrasena(),
        "scope": "openid",
    }
    mensaje(f"Usuario: {payload['username']}")

    return _solicitar_token(payload)


def obtener_token_usuario(username: str) -> str:
    """Token de un usuario nominal del realm (no `*.test`) con su contraseña del entorno."""
    payload = {
        "grant_type": "password",
        "client_id": "sio-web",
        "username": username.strip(),
        "password": leer_variable(variable_contrasena_usuario(username)),
        "scope": "openid",
    }
    mensaje(f"Usuario: {payload['username']}")
    return _solicitar_token(payload)


def obtener_token_cliente(client_id: str) -> str:
    """Token de un cliente técnico (cuenta de servicio) con `client_credentials`."""
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": leer_variable(variable_secreto_cliente(client_id)),
    }
    mensaje(f"Cliente: {client_id}")
    return _solicitar_token(payload)


def _solicitar_token(payload: dict[str, str]) -> str:
    try:
        respuesta = requests.post(TOKEN_URL, data=payload, timeout=5)
        respuesta.raise_for_status()
        return respuesta.json()["access_token"]
    except Exception as error:
        raise SystemExit(f"Error al obtener el token: {error}") from None


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--usuario":
        if len(sys.argv) != 3 or not sys.argv[2].strip():
            mensaje("Uso: python services/get_token.py --usuario <nombre de usuario>")
            return 1
        print(obtener_token_usuario(sys.argv[2].strip()))
        return 0

    if len(sys.argv) > 1 and sys.argv[1] == "--cliente":
        if len(sys.argv) != 3 or not sys.argv[2].strip():
            mensaje("Uso: python services/get_token.py --cliente <client_id>")
            return 1
        print(obtener_token_cliente(sys.argv[2].strip()))
        return 0

    if len(sys.argv) > 1:
        rol = normalizar_rol(sys.argv[1])
        if rol is None:
            mensaje(f"Rol no válido: {sys.argv[1]}. Opciones: {', '.join(ROLES.values())}.")
            return 1
    else:
        rol = elegir_rol()
        if rol is None:
            return 0

    print(obtener_token(rol))
    return 0


if __name__ == "__main__":
    sys.exit(main())
