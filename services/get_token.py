"""Obtiene un token de Keycloak para los usuarios de prueba de SIO.

Uso:
    python services/get_token.py              # menú para elegir el rol
    python services/get_token.py consulta     # rol directo (también acepta el número o `consulta.test`)
    TOKEN=$(python services/get_token.py admin)

La contraseña se lee de la variable de entorno `KEYCLOAK_TEST_USER_PASSWORD`; si no está
definida, se toma de `infrastructure/.env`. Nunca se escribe en el código (Principio IX).

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


def leer_contrasena() -> str:
    valor = os.environ.get(PASSWORD_VARIABLE, "").strip()
    if valor:
        return valor

    if INFRASTRUCTURE_ENV.is_file():
        for linea in INFRASTRUCTURE_ENV.read_text(encoding="utf-8").splitlines():
            nombre, separador, contenido = linea.partition("=")
            if separador and nombre.strip() == PASSWORD_VARIABLE:
                valor = contenido.strip().strip('"').strip("'")
                if valor:
                    return valor

    raise SystemExit(
        f"Defina la variable {PASSWORD_VARIABLE} o agréguela a {INFRASTRUCTURE_ENV}."
    )


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

    try:
        respuesta = requests.post(TOKEN_URL, data=payload, timeout=5)
        respuesta.raise_for_status()
        return respuesta.json()["access_token"]
    except Exception as error:
        raise SystemExit(f"Error al obtener el token: {error}") from None


def main() -> int:
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
