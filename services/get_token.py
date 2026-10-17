"""Obtiene un token de Keycloak para los usuarios de prueba o los clientes técnicos de SIO.

Uso:
    python services/get_token.py              # menú: rol de prueba o usuario de una empresa (opción 8)
    python services/get_token.py consulta     # rol directo (también acepta el número o `consulta.test`)
    TOKEN=$(python services/get_token.py admin)
    TOKEN=$(python services/get_token.py --cliente sio-data-importer)   # cliente técnico (client_credentials)
    TOKEN=$(python services/get_token.py --usuario santiago.rodriguez)  # usuario nominal (contraseña en el entorno)

La contraseña se lee de la variable de entorno `KEYCLOAK_TEST_USER_PASSWORD`; si no está
definida, se toma de `infrastructure/.env`. El secreto de un cliente técnico se lee igual, de
`<CLIENTE>_CLIENT_SECRET` (p. ej. `SIO_DATA_IMPORTER_CLIENT_SECRET`), y la de un usuario nominal, de
`<USUARIO>_PASSWORD` (p. ej. `SANTIAGO_RODRIGUEZ_PASSWORD`). Nunca se escriben en el código
(Principio IX).

Opción 8 del menú (usuarios de empresas): las empresas y sus usuarios se leen de
`services/get_token_empresas.json` (o del archivo indicado en `SIO_TOKEN_EMPRESAS_FILE`), que
solo contiene nombres de usuario, grupos y sucursales. Para agregar una empresa basta con
añadirla a ese archivo.

Credenciales locales (solo desarrollo): la contraseña del usuario elegido se busca en el archivo
local de credenciales (`~/sio-credenciales-dev/dao-usuarios-demo.txt`, o el de
`SIO_DEV_CREDENTIALS_FILE`; formato `usuario=contraseña` por línea, `#` para comentarios). Solo se
usa si Keycloak es local (`localhost`/`127.0.0.1`), si el archivo es del usuario del sistema y nadie
más puede leerlo (permisos `600`), y solo se lee la línea del usuario elegido. En cualquier otro
caso, o si Keycloak rechaza esa contraseña, se pide por teclado sin mostrarla. Elegir un usuario
nunca evita su autenticación.

La salida estándar contiene únicamente el token; el menú y los errores van a la salida de
errores, para poder capturar el token con `$(...)`. No se imprimen contraseñas, refresh tokens
ni secretos, y el token no se guarda en ningún archivo.
"""

import getpass
import json
import os
import stat
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests

TOKEN_URL = os.environ.get(
    "KEYCLOAK_TOKEN_URL",
    "http://localhost:8081/realms/sio/protocol/openid-connect/token",
)
PASSWORD_VARIABLE = "KEYCLOAK_TEST_USER_PASSWORD"
INFRASTRUCTURE_ENV = Path(__file__).resolve().parents[1] / "infrastructure" / ".env"
EMPRESAS_FILE = Path(
    os.environ.get("SIO_TOKEN_EMPRESAS_FILE", Path(__file__).resolve().parent / "get_token_empresas.json")
)
OPCION_EMPRESAS = "8"
CREDENCIALES_LOCALES = Path(
    os.environ.get("SIO_DEV_CREDENTIALS_FILE", Path.home() / "sio-credenciales-dev" / "dao-usuarios-demo.txt")
).expanduser()
HOSTS_LOCALES = {"localhost", "127.0.0.1", "::1"}

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


class CredencialesInvalidas(Exception):
    """Keycloak rechazó el usuario o la contraseña (sin detalles que revelen secretos)."""


def elegir_rol() -> str | None:
    """Menú principal: un rol de prueba (`<rol>.test`) o `OPCION_EMPRESAS` para un usuario de empresa."""
    while True:
        mensaje("\nSeleccione un rol:")
        for numero, rol in ROLES.items():
            mensaje(f"{numero}. {rol.capitalize()}")
        mensaje(f"{OPCION_EMPRESAS}. Usuarios de empresas")
        mensaje("0. Salir")

        mensaje("\nIngrese el número o nombre del rol: ")
        opcion = input().strip().lower()

        if opcion in ("0", "salir", "exit"):
            mensaje("Saliendo...")
            return None

        if opcion in (OPCION_EMPRESAS, "empresas"):
            return OPCION_EMPRESAS

        rol = normalizar_rol(opcion)
        if rol:
            return rol
        mensaje("Opción no válida. Intente nuevamente.")


def cargar_empresas() -> list[dict]:
    """Empresas y usuarios de `EMPRESAS_FILE`; un archivo ausente o mal formado detiene el script."""
    try:
        datos = json.loads(EMPRESAS_FILE.read_text(encoding="utf-8"))
        empresas = datos["empresas"]
        for empresa in empresas:
            if not empresa["nombre"].strip() or not all(u["usuario"].strip() for u in empresa["usuarios"]):
                raise ValueError("nombre o usuario vacío")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        raise SystemExit(f"No se pudo leer la configuración de empresas {EMPRESAS_FILE}: {error}") from None
    return empresas


def _elegir(titulo: str, opciones: list[str], salida: str) -> int | None:
    """Índice elegido (desde 0) o `None` con `0`/`volver`."""
    while True:
        mensaje(f"\n{titulo}\n")
        for numero, texto in enumerate(opciones, start=1):
            mensaje(f"{numero}. {texto}")
        mensaje(f"0. {salida}")
        mensaje("\nIngrese el número: ")
        opcion = input().strip().lower()
        if opcion in ("0", "volver", salida.lower()):
            return None
        if opcion.isdigit() and 1 <= int(opcion) <= len(opciones):
            return int(opcion) - 1
        mensaje("Opción no válida. Intente nuevamente.")


def describir_usuario(usuario: dict) -> str:
    grupo = usuario.get("grupo") or "sin grupo registrado"
    sucursales = ", ".join(usuario.get("sucursales") or [])
    return f"{usuario['usuario']:<20} - {grupo.capitalize()}" + (f" ({sucursales})" if sucursales else "")


def elegir_usuario_empresa() -> tuple[dict, dict] | None:
    """Empresa y usuario elegidos en los submenús; `None` si se vuelve al menú principal."""
    empresas = cargar_empresas()
    while True:
        indice = _elegir("Seleccione una empresa:", [empresa["nombre"] for empresa in empresas], "Volver")
        if indice is None:
            return None
        empresa = empresas[indice]
        usuarios = empresa["usuarios"]
        elegido = _elegir(f"Usuarios de {empresa['nombre']}", [describir_usuario(u) for u in usuarios], "Volver")
        if elegido is not None:
            return empresa, usuarios[elegido]


class CredencialLocalNoDisponible(Exception):
    """La contraseña no puede tomarse del archivo local; el motivo nunca incluye valores del archivo."""


def keycloak_es_local() -> bool:
    return (urlparse(TOKEN_URL).hostname or "") in HOSTS_LOCALES


def contrasena_local(username: str) -> str:
    """Contraseña de `username` en el archivo local de desarrollo (solo su línea; nada se imprime)."""
    if not keycloak_es_local():
        raise CredencialLocalNoDisponible("Keycloak no es local: el archivo de credenciales solo se usa en desarrollo")
    try:
        info = CREDENCIALES_LOCALES.stat()
    except OSError:
        raise CredencialLocalNoDisponible(f"no existe el archivo {CREDENCIALES_LOCALES}") from None
    if not stat.S_ISREG(info.st_mode):
        raise CredencialLocalNoDisponible(f"{CREDENCIALES_LOCALES} no es un archivo")
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        raise CredencialLocalNoDisponible(f"{CREDENCIALES_LOCALES} pertenece a otro usuario del sistema")
    if info.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise CredencialLocalNoDisponible(
            f"permisos inseguros en {CREDENCIALES_LOCALES} ({stat.filemode(info.st_mode)}); use chmod 600"
        )
    buscado = username.strip()
    try:
        with CREDENCIALES_LOCALES.open(encoding="utf-8") as archivo:
            for linea in archivo:
                linea = linea.strip()
                if not linea or linea.startswith("#"):
                    continue
                nombre, separador, valor = linea.partition("=")
                if separador and nombre.strip() == buscado and valor.strip():
                    return valor.strip()
    except (OSError, UnicodeDecodeError):
        raise CredencialLocalNoDisponible(f"no se pudo leer {CREDENCIALES_LOCALES}") from None
    raise CredencialLocalNoDisponible(f"{buscado} no tiene credenciales en {CREDENCIALES_LOCALES}")


def pedir_contrasena(username: str) -> str:
    """Contraseña por teclado sin eco; nunca se imprime ni se guarda."""
    return getpass.getpass(f"Contraseña de {username} (no se muestra): ", stream=sys.stderr)


def _autenticar(username: str, contrasena: str) -> dict:
    if not contrasena:
        raise CredencialesInvalidas
    return _solicitar(
        {"grant_type": "password", "client_id": "sio-web", "username": username, "password": contrasena, "scope": "openid"}
    )


def token_de_usuario_empresa(empresa: dict, usuario: dict) -> str:
    """Autentica al usuario elegido: contraseña del archivo local o, si no sirve, la que escribe la persona."""
    username = usuario["usuario"].strip()
    try:
        respuesta = _autenticar(username, contrasena_local(username))
        mensaje(f"Contraseña de {username} tomada del archivo local de credenciales.")
    except CredencialLocalNoDisponible as motivo:
        mensaje(f"No se usó el archivo local de credenciales: {motivo}.")
        respuesta = _autenticar(username, pedir_contrasena(username))
    except CredencialesInvalidas:
        mensaje(f"Keycloak rechazó la contraseña de {username} del archivo local; escríbala manualmente.")
        respuesta = _autenticar(username, pedir_contrasena(username))
    mensaje(f"\nUsuario: {username} ({empresa['nombre']}, grupo {usuario.get('grupo') or '-'})")
    if isinstance(respuesta.get("expires_in"), int):
        mensaje(f"El token vence en {respuesta['expires_in']} segundos ({respuesta['expires_in'] // 60} min).")
    mensaje("Token de acceso (péguelo en Authorize de /docs, sin anteponer 'Bearer'):\n")
    return respuesta["access_token"]


def menu() -> str | None:
    """Menú completo: devuelve el token elegido o `None` al salir."""
    while True:
        rol = elegir_rol()
        if rol is None:
            return None
        if rol != OPCION_EMPRESAS:
            return obtener_token(rol)
        while (elegido := elegir_usuario_empresa()) is not None:
            try:
                token = token_de_usuario_empresa(*elegido)
            except CredencialesInvalidas:
                mensaje("Usuario o contraseña incorrectos, o usuario deshabilitado. Intente nuevamente.")
                continue
            print(token, flush=True)
            mensaje("\n¿Obtener el token de otro usuario? [s/N]: ")
            if input().strip().lower() not in ("s", "si", "sí"):
                return ""


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


def _solicitar(payload: dict[str, str]) -> dict:
    """Respuesta de Keycloak; credenciales rechazadas → `CredencialesInvalidas` (sin el cuerpo enviado)."""
    try:
        respuesta = requests.post(TOKEN_URL, data=payload, timeout=5)
    except Exception as error:
        raise SystemExit(f"Error al obtener el token: no se pudo conectar con Keycloak ({type(error).__name__}).") from None
    if respuesta.status_code in (400, 401) and payload.get("grant_type") == "password":
        try:
            rechazo = respuesta.json().get("error")
        except ValueError:
            rechazo = None
        if rechazo == "invalid_grant":
            raise CredencialesInvalidas
    try:
        respuesta.raise_for_status()
        cuerpo = respuesta.json()
        cuerpo["access_token"]
        return cuerpo
    except Exception as error:
        raise SystemExit(f"Error al obtener el token: {error}") from None


def _solicitar_token(payload: dict[str, str]) -> str:
    try:
        return _solicitar(payload)["access_token"]
    except CredencialesInvalidas:
        raise SystemExit("Error al obtener el token: usuario o contraseña incorrectos.") from None


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
        token = menu()
        if token:  # los tokens de usuarios de empresas ya se imprimieron en el menú
            print(token)
        return 0

    print(obtener_token(rol))
    return 0


if __name__ == "__main__":
    sys.exit(main())
