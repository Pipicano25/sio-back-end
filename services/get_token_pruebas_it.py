"""Obtiene un token de Keycloak para los usuarios de prueba de la pila de integración aislada `sio-it`.

Uso:
    python services/get_token_pruebas_it.py                     # menú interactivo (usuario y empresas)
    python services/get_token_pruebas_it.py ventas.test
    python services/get_token_pruebas_it.py --user ventas.test
    python services/get_token_pruebas_it.py ventas.test --copy  # al portapapeles, sin imprimirlo
    python services/get_token_pruebas_it.py ventas.test --empresas   # además, sus empresas (en stderr)
    TOKEN=$(python services/get_token_pruebas_it.py ventas.test)

Modo interactivo (sin usuario y con teclado): menú para elegir el usuario; después se muestran su información,
las empresas a las que pertenece y sus sucursales, y el token se copia al portapapeles sin imprimirlo. Si la
salida estándar se captura (`TOKEN=$(...)`), el token se escribe allí en vez de copiarse. Sin teclado y sin
usuario se usa `inventario.test`.

Solo trabaja contra la pila aislada: Keycloak `http://localhost:18081` (realm `sio`, cliente `sio-web`),
Operational Context `http://localhost:18104` y Party Identity `http://localhost:18101`. Las URL son fijas y no
se pueden cambiar por argumentos ni variables de entorno. El token se rechaza si su emisor no es el de `sio-it`,
de modo que nunca se usa contra el Keycloak habitual (`localhost:8081`).

Las empresas se leen con el token del propio usuario y solo con lecturas (`GET`): sus membresías de
`/me/operational-context`, la empresa y sus sucursales en Operational Context y el nombre legal en Party
Identity. Si una consulta falla, el dato se informa como **no confirmado**; nunca se supone una membresía.

La contraseña se lee únicamente de `KEYCLOAK_TEST_USER_PASSWORD` en `validation/isolated-stack/.env` (secretos
propios de la pila, no versionados); nunca de `infrastructure/.env` ni del entorno. No se imprimen contraseñas,
refresh tokens ni secretos, y el token no se guarda en ningún archivo.

La salida estándar contiene únicamente el token; el menú, la información y los errores van a la salida de
errores. Es la misma convención de `services/get_token.py`, que sigue siendo la utilidad del entorno habitual.
"""

from __future__ import annotations

import argparse
import base64
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

KEYCLOAK_URL = "http://localhost:18081"
REALM = "sio"
CLIENT_ID = "sio-web"
TOKEN_URL = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"
ISSUER = f"{KEYCLOAK_URL}/realms/{REALM}"
OPERATIONAL_CONTEXT_URL = "http://localhost:18104/api/v1"
PARTY_IDENTITY_URL = "http://localhost:18101/api/v1"
SWAGGER_URL = "http://localhost:18112/docs"
AMBIENTE = "sio-it"
# Únicos destinos permitidos (host, puerto): Keycloak, Operational Context y Party Identity de la pila.
DESTINOS_PERMITIDOS = frozenset({("localhost", 18081), ("localhost", 18104), ("localhost", 18101)})

PASSWORD_VARIABLE = "KEYCLOAK_TEST_USER_PASSWORD"
ISOLATED_ENV = Path(__file__).resolve().parents[1] / "validation" / "isolated-stack" / ".env"

USUARIOS = (
    "admin.test",
    "supervisor.test",
    "compras.test",
    "ventas.test",
    "inventario.test",
    "reportes.test",
    "consulta.test",
)
USUARIO_PREDETERMINADO = "inventario.test"
TIMEOUT_SEGUNDOS = 5
# Empresas sintéticas conocidas de la pila: solo sirven de etiqueta y para ordenar; no otorgan membresía.
EMPRESAS_CONOCIDAS = {
    "4e0f8c4a-f357-49fc-8b2b-d62c985e1ab2": "empresa tipo DAO",
    "7fd0c5f3-8f93-4e55-8a85-d862c53d76e6": "empresa de alto volumen",
    "5f715cf5-d895-4afc-b72a-be3bbdb91f4f": "empresa funcional",
}
NO_CONFIRMADO = "no confirmado"


class ErrorToken(Exception):
    """Error presentable al usuario; el mensaje nunca contiene contraseñas ni tokens."""


def mensaje(texto: str = "") -> None:
    print(texto, file=sys.stderr)


def normalizar_usuario(valor: str) -> str:
    """`ventas`, `Ventas.test` → `ventas.test`; cualquier otro valor es un error."""
    nombre = valor.strip().lower()
    if not nombre.endswith(".test"):
        nombre += ".test"
    if nombre not in USUARIOS:
        raise ErrorToken(f"Usuario no válido: {valor.strip()!r}. Opciones: {', '.join(USUARIOS)}.")
    return nombre


def leer_contrasena(archivo: Path = ISOLATED_ENV) -> str:
    """Valor de `KEYCLOAK_TEST_USER_PASSWORD` en el `.env` de la pila aislada (solo esa línea)."""
    try:
        lineas = archivo.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        raise ErrorToken(
            f"No existe {archivo}. Se genera al levantar la pila: bash validation/isolated-stack/stack.sh verificar"
        ) from None
    except (OSError, UnicodeDecodeError):
        raise ErrorToken(f"No se pudo leer {archivo}.") from None
    for linea in lineas:
        nombre, separador, contenido = linea.partition("=")
        if separador and nombre.strip() == PASSWORD_VARIABLE:
            valor = contenido.strip().strip('"').strip("'")
            if valor:
                return valor
    raise ErrorToken(f"La variable {PASSWORD_VARIABLE} no está definida en {archivo}.")


class _SinRedirecciones(urllib.request.HTTPRedirectHandler):
    """Una redirección podría llevar la contraseña o el token a otro destino: se trata como error."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        raise ErrorToken(f"Respuesta con una redirección inesperada (HTTP {code}).")


# Sin proxies (las peticiones nunca salen de localhost) y sin redirecciones.
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _SinRedirecciones())


def comprobar_destino(url: str) -> None:
    """Rechaza cualquier URL que no sea un servicio de la pila aislada (defensa adicional a las URL fijas)."""
    partes = urllib.parse.urlsplit(url)
    if partes.scheme != "http" or (partes.hostname, partes.port) not in DESTINOS_PERMITIDOS:
        raise ErrorToken("Destino no permitido: el script solo consulta la pila aislada sio-it.")


def solicitar_token(usuario: str, contrasena: str, abrir=_OPENER.open) -> dict:
    """Respuesta de Keycloak para `grant_type=password`; los errores no incluyen el cuerpo enviado."""
    comprobar_destino(TOKEN_URL)
    datos = urllib.parse.urlencode(
        {"grant_type": "password", "client_id": CLIENT_ID, "username": usuario, "password": contrasena,
         "scope": "openid"}
    ).encode()
    peticion = urllib.request.Request(
        TOKEN_URL, data=datos, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    try:
        with abrir(peticion, timeout=TIMEOUT_SEGUNDOS) as respuesta:
            cuerpo = respuesta.read()
    except urllib.error.HTTPError as error:
        codigo = error.code
        try:
            rechazo = json.loads(error.read() or b"{}").get("error")
        except (ValueError, AttributeError, OSError):
            rechazo = None
        finally:
            error.close()
        if codigo in (400, 401) and rechazo == "invalid_grant":
            raise ErrorToken(f"Keycloak rechazó las credenciales de {usuario} (contraseña incorrecta o usuario "
                             f"deshabilitado). Revise {PASSWORD_VARIABLE} en {ISOLATED_ENV}.") from None
        detalle = f", {rechazo}" if isinstance(rechazo, str) else ""
        raise ErrorToken(f"Keycloak respondió HTTP {codigo}{detalle}.") from None
    except urllib.error.URLError as error:
        raise ErrorToken(f"Keycloak de {AMBIENTE} no disponible en {KEYCLOAK_URL} ({error.reason}). "
                         "Compruebe la pila: bash validation/isolated-stack/stack.sh estado") from None
    except (TimeoutError, ConnectionError, OSError) as error:
        raise ErrorToken(f"Error de conexión con {KEYCLOAK_URL} ({type(error).__name__}).") from None
    try:
        respuesta_json = json.loads(cuerpo)
    except ValueError:
        raise ErrorToken("Keycloak devolvió una respuesta que no es JSON.") from None
    if not isinstance(respuesta_json, dict) or not isinstance(respuesta_json.get("access_token"), str):
        raise ErrorToken("La respuesta de Keycloak no contiene access_token.")
    return respuesta_json


def reclamaciones(token: str) -> dict:
    """Carga útil del JWT, sin verificar la firma (solo para mostrar datos y comprobar el emisor)."""
    try:
        carga = token.split(".")[1]
        carga += "=" * (-len(carga) % 4)
        datos = json.loads(base64.urlsafe_b64decode(carga))
    except (IndexError, ValueError):
        raise ErrorToken("El access_token recibido no es un JWT válido.") from None
    if not isinstance(datos, dict):
        raise ErrorToken("El access_token recibido no es un JWT válido.")
    return datos


def comprobar_emisor(datos: dict) -> None:
    if datos.get("iss") != ISSUER:
        raise ErrorToken(f"El token no es del ambiente {AMBIENTE} (emisor inesperado); se descarta.")


# --- Empresas del usuario (solo lecturas con su propio token) ---


class LecturaFallida(Exception):
    """Una lectura de la pila no se pudo completar; `motivo` nunca contiene el token."""

    def __init__(self, motivo: str) -> None:
        super().__init__(motivo)
        self.motivo = motivo


def leer_json(url: str, token: str, abrir=_OPENER.open):
    """`GET` autenticado a un servicio de la pila; cualquier fallo es `LecturaFallida`."""
    comprobar_destino(url)
    peticion = urllib.request.Request(
        url, method="GET", headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}
    )
    try:
        with abrir(peticion, timeout=TIMEOUT_SEGUNDOS) as respuesta:
            return json.loads(respuesta.read())
    except urllib.error.HTTPError as error:
        error.close()
        raise LecturaFallida(f"HTTP {error.code}") from None
    except urllib.error.URLError as error:
        raise LecturaFallida(f"servicio no disponible ({error.reason})") from None
    except (TimeoutError, ConnectionError, OSError) as error:
        raise LecturaFallida(f"error de conexión ({type(error).__name__})") from None
    except ValueError:
        raise LecturaFallida("respuesta que no es JSON") from None


@dataclass
class Sucursal:
    branch_id: str
    nombre: str
    asignada: bool


@dataclass
class Empresa:
    company_id: str
    nombre: str
    referencia: str | None
    sucursales: list[Sucursal] = field(default_factory=list)
    sucursales_confirmadas: bool = True
    aviso: str | None = None


def _sucursales(company_id: str, asignadas: set[str], token: str, abrir) -> list[Sucursal]:
    """Todas las sucursales `ACTIVE` de la empresa (lectura multisucursal con membresía), página a página."""
    sucursales: list[Sucursal] = []
    pagina = 1
    while True:
        url = f"{OPERATIONAL_CONTEXT_URL}/companies/{company_id}/branches?page={pagina}&page_size=100"
        datos = leer_json(url, token, abrir)
        for item in datos.get("items", []):
            nombre = " ".join(filter(None, (item.get("code"), item.get("name")))) or "sin nombre"
            sucursales.append(Sucursal(str(item["id"]), nombre, str(item["id"]) in asignadas))
        if pagina >= int(datos.get("total_pages") or 1):
            return sucursales
        pagina += 1


def _nombre_empresa(company_id: str, token: str, abrir) -> str:
    empresa = leer_json(f"{OPERATIONAL_CONTEXT_URL}/companies/{company_id}", token, abrir)
    organizacion = empresa.get("organization_identity_id")
    if not organizacion:
        return NO_CONFIRMADO
    try:
        identidad = leer_json(f"{PARTY_IDENTITY_URL}/organization-identities/{organizacion}", token, abrir)
    except LecturaFallida as error:
        raise LecturaFallida(f"Party Identity respondió {error.motivo} a este usuario") from None
    return identidad.get("trade_name") or identidad.get("legal_name") or NO_CONFIRMADO


def empresas_del_usuario(token: str, abrir=_OPENER.open) -> list[Empresa]:
    """Empresas con membresía `ACTIVE` del usuario del token, según Operational Context.

    `LecturaFallida` si no se pudieron leer las membresías: en ese caso ninguna empresa está confirmada.
    """
    contexto = leer_json(f"{OPERATIONAL_CONTEXT_URL}/me/operational-context", token, abrir)
    empresas: list[Empresa] = []
    for membresia in contexto.get("memberships", []):
        if membresia.get("status") != "ACTIVE" or membresia.get("company_status") != "ACTIVE":
            continue
        company_id = str(membresia["company_id"])
        asignadas = {str(b["branch_id"]) for b in membresia.get("branches", []) if b.get("allowed")}
        empresa = Empresa(company_id, NO_CONFIRMADO, EMPRESAS_CONOCIDAS.get(company_id))
        try:
            empresa.nombre = _nombre_empresa(company_id, token, abrir)
        except LecturaFallida as error:
            empresa.aviso = f"nombre no confirmado: {error.motivo}"
        try:
            empresa.sucursales = _sucursales(company_id, asignadas, token, abrir)
        except LecturaFallida as error:
            # Sin permiso para listar sucursales: solo las asignadas que informa la membresía.
            empresa.sucursales = [Sucursal(b, NO_CONFIRMADO, True) for b in sorted(asignadas)]
            empresa.sucursales_confirmadas = False
            empresa.aviso = ", ".join(filter(None, (empresa.aviso, f"sucursales no listadas: {error.motivo}")))
        empresas.append(empresa)
    orden = list(EMPRESAS_CONOCIDAS)
    empresas.sort(key=lambda e: (orden.index(e.company_id) if e.company_id in orden else len(orden), e.nombre))
    return empresas


def mostrar_empresas(usuario: str, token: str, abrir=_OPENER.open) -> None:
    mensaje(f"\nEmpresas de {usuario} (Operational Context de {AMBIENTE}, solo lectura):")
    try:
        empresas = empresas_del_usuario(token, abrir)
    except LecturaFallida as error:
        mensaje(f"  No se pudieron leer las membresías ({error.motivo}): empresas NO confirmadas.")
        return
    if not empresas:
        mensaje("  El usuario no tiene membresías ACTIVE en ninguna empresa.")
        return
    for numero, empresa in enumerate(empresas, start=1):
        etiqueta = f" [{empresa.referencia}]" if empresa.referencia else ""
        mensaje(f"\n  {numero}. {empresa.nombre}{etiqueta}")
        mensaje(f"     company_id: {empresa.company_id}")
        if empresa.aviso:
            mensaje(f"     Aviso: {empresa.aviso}")
        if not empresa.sucursales:
            mensaje("     Sucursales: ninguna" + ("" if empresa.sucursales_confirmadas else " confirmada"))
        for sucursal in empresa.sucursales:
            marca = " (asignada)" if sucursal.asignada else ""
            mensaje(f"     - {sucursal.nombre}{marca}: {sucursal.branch_id}")


# --- Portapapeles, menú y salida ---


def copiar(token: str) -> str:
    """Copia el token al portapapeles con wl-copy o xclip; devuelve la herramienta usada."""
    for herramienta, comando in (("wl-copy", ["wl-copy"]), ("xclip", ["xclip", "-selection", "clipboard"])):
        if shutil.which(herramienta) is None:
            continue
        try:
            subprocess.run(comando, input=token.encode(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           check=True, timeout=5)
            return herramienta
        except (subprocess.SubprocessError, OSError):
            continue
    raise ErrorToken("No se pudo copiar: instale wl-copy (Wayland) o xclip (X11). El token no se imprimió.")


def menu(leer=input) -> str | None:
    """Usuario elegido en el menú (número o nombre); `None` con `0`, `salir` o fin de entrada."""
    mensaje("==========================================")
    mensaje("    SIO - AMBIENTE DE INTEGRACIÓN")
    mensaje("==========================================")
    while True:
        mensaje("\nSelecciona el usuario:\n")
        for numero, usuario in enumerate(USUARIOS, start=1):
            mensaje(f"{numero}. {usuario}")
        mensaje("0. Salir")
        print("\nOpción: ", end="", file=sys.stderr, flush=True)
        try:
            opcion = leer().strip()
        except EOFError:
            return None
        if opcion.lower() in ("0", "salir", "exit"):
            return None
        if opcion.isdigit() and 1 <= int(opcion) <= len(USUARIOS):
            return USUARIOS[int(opcion) - 1]
        try:
            return normalizar_usuario(opcion)
        except ErrorToken:
            mensaje("Opción no válida. Intente nuevamente.")


def argumentos(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=f"Token de un usuario de prueba del Keycloak aislado {AMBIENTE} ({KEYCLOAK_URL}).",
    )
    parser.add_argument("usuario", nargs="?", help="Usuario de prueba (sin él: menú, o inventario.test sin teclado).")
    parser.add_argument("--user", dest="opcion_usuario", help="Usuario de prueba (alternativa al posicional).")
    parser.add_argument("--copy", action="store_true", help="Copia el token al portapapeles sin imprimirlo.")
    parser.add_argument("--empresas", action="store_true", help="Muestra también las empresas del usuario (stderr).")
    return parser.parse_args(argv)


def elegir_usuario(args: argparse.Namespace) -> str | None:
    """Usuario de los argumentos; `None` si no se indicó."""
    if args.usuario and args.opcion_usuario and normalizar_usuario(args.usuario) != normalizar_usuario(
        args.opcion_usuario
    ):
        raise ErrorToken("Indique el usuario una sola vez (posicional o --user).")
    indicado = args.usuario or args.opcion_usuario
    return normalizar_usuario(indicado) if indicado else None


def obtener(usuario: str) -> tuple[str, dict, dict]:
    respuesta = solicitar_token(usuario, leer_contrasena())
    token = respuesta["access_token"]
    datos = reclamaciones(token)
    comprobar_emisor(datos)
    return token, respuesta, datos


def mostrar_informacion(usuario: str, respuesta: dict, datos: dict) -> None:
    segundos = respuesta.get("expires_in")
    mensaje(f"\nUsuario:  {datos.get('preferred_username', usuario)}")
    mensaje(f"Ambiente: {AMBIENTE}")
    mensaje(f"Realm:    {REALM}")
    if isinstance(segundos, int):
        vence = (datetime.now() + timedelta(seconds=segundos)).strftime("%H:%M:%S")
        mensaje(f"Vence en: {segundos} s (a las {vence})")
    mensaje(f"Keycloak: {KEYCLOAK_URL} (emisor {ISSUER})")
    mensaje(f"Swagger:  {SWAGGER_URL}  →  Authorize, pegue el token sin anteponer 'Bearer'")


def es_terminal(flujo) -> bool:
    try:
        return flujo.isatty()
    except (AttributeError, ValueError):
        return False


def main(argv: list[str] | None = None, leer=input) -> int:
    args = argumentos(argv)
    try:
        usuario = elegir_usuario(args)
        interactivo = usuario is None and es_terminal(sys.stdin)
        if interactivo:
            usuario = menu(leer)
            if usuario is None:
                mensaje("Saliendo...")
                return 0
        usuario = usuario or USUARIO_PREDETERMINADO
        token, respuesta, datos = obtener(usuario)
        # En el menú se copia automáticamente, salvo que la salida se capture con $(...).
        copiar_token = args.copy or (interactivo and es_terminal(sys.stdout))
        herramienta = None
        sin_portapapeles = None
        if copiar_token:
            try:
                herramienta = copiar(token)
            except ErrorToken as error:
                if args.copy:
                    raise
                sin_portapapeles = error
    except ErrorToken as error:
        mensaje(f"Error: {error}")
        return 1

    mostrar_informacion(usuario, respuesta, datos)
    if interactivo or args.empresas:
        mostrar_empresas(usuario, token)
    mensaje()
    if herramienta:
        mensaje(f"Token copiado al portapapeles con {herramienta} (no se imprimió).")
        return 0
    if sin_portapapeles:
        mensaje("No hay portapapeles disponible (wl-copy o xclip); el token no se imprimió. Para obtenerlo:")
        mensaje(f"  TOKEN=$(python services/get_token_pruebas_it.py {usuario})")
        mensaje(f"  python services/get_token_pruebas_it.py {usuario}      # lo imprime para copiarlo")
        return 0
    mensaje("Token de acceso:")
    print(token, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
