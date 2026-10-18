"""Pruebas unitarias de `services/get_token_pruebas_it.py` (sin red ni Keycloak).

Ejecución (biblioteca estándar):
    python -m unittest services/test_get_token_pruebas_it.py
"""

from __future__ import annotations

import base64
import io
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import get_token_pruebas_it as it  # noqa: E402

SECRETO = "contrasena-de-prueba-que-no-debe-aparecer"


def jwt(**claims) -> str:
    carga = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"cabecera.{carga}.firma"


TOKEN_IT = jwt(iss=it.ISSUER, preferred_username="inventario.test")


class Respuesta(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def abrir_con(cuerpo: dict | bytes):
    datos = cuerpo if isinstance(cuerpo, bytes) else json.dumps(cuerpo).encode()
    peticiones = []

    def abrir(peticion, timeout):
        peticiones.append((peticion, timeout))
        return Respuesta(datos)

    abrir.peticiones = peticiones
    return abrir


def abrir_con_error(codigo: int, cuerpo: dict):
    def abrir(peticion, timeout):
        raise urllib.error.HTTPError(peticion.full_url, codigo, "error", {}, io.BytesIO(json.dumps(cuerpo).encode()))

    return abrir


class ConfiguracionFija(unittest.TestCase):
    def test_solo_destinos_de_la_pila(self):
        for url in (it.TOKEN_URL, f"{it.OPERATIONAL_CONTEXT_URL}/me/operational-context",
                    f"{it.PARTY_IDENTITY_URL}/organization-identities/x"):
            it.comprobar_destino(url)
        for url in ("http://localhost:8081/realms/sio/protocol/openid-connect/token",  # Keycloak habitual
                    "http://localhost:8104/api/v1/me/operational-context",            # OC habitual
                    "http://127.0.0.1:18104/api/v1/x", "https://localhost:18081/x", "http://otro:18081/x"):
            with self.assertRaises(it.ErrorToken, msg=url):
                it.comprobar_destino(url)

    def test_solo_keycloak_aislado(self):
        self.assertEqual(it.TOKEN_URL, "http://localhost:18081/realms/sio/protocol/openid-connect/token")
        self.assertEqual(it.ISSUER, "http://localhost:18081/realms/sio")
        self.assertEqual(it.CLIENT_ID, "sio-web")
        self.assertEqual(it.ISOLATED_ENV.parts[-3:], ("validation", "isolated-stack", ".env"))

    def test_la_url_no_depende_del_entorno(self):
        with mock.patch.dict("os.environ", {"KEYCLOAK_TOKEN_URL": "http://localhost:8081/x"}):
            import importlib

            recargado = importlib.reload(it)
            self.assertEqual(recargado.TOKEN_URL, "http://localhost:18081/realms/sio/protocol/openid-connect/token")


class Usuarios(unittest.TestCase):
    def test_predeterminado_es_inventario(self):
        self.assertIsNone(it.elegir_usuario(it.argumentos([])))  # sin usuario: menú o el predeterminado
        self.assertEqual(it.USUARIO_PREDETERMINADO, "inventario.test")

    def test_posicional_y_opcion(self):
        self.assertEqual(it.elegir_usuario(it.argumentos(["ventas.test"])), "ventas.test")
        self.assertEqual(it.elegir_usuario(it.argumentos(["--user", "supervisor.test"])), "supervisor.test")
        self.assertEqual(it.elegir_usuario(it.argumentos(["admin"])), "admin.test")

    def test_usuario_invalido(self):
        with self.assertRaises(it.ErrorToken):
            it.normalizar_usuario("santiago.rodriguez")

    def test_usuario_duplicado_distinto(self):
        with self.assertRaises(it.ErrorToken):
            it.elegir_usuario(it.argumentos(["ventas.test", "--user", "admin.test"]))


class Contrasena(unittest.TestCase):
    def escribir(self, texto: str) -> Path:
        carpeta = tempfile.mkdtemp()
        archivo = Path(carpeta) / ".env"
        archivo.write_text(texto, encoding="utf-8")
        return archivo

    def test_lee_solo_la_variable(self):
        archivo = self.escribir(f"# comentario\nOTRA=1\nKEYCLOAK_TEST_USER_PASSWORD={SECRETO}\n")
        self.assertEqual(it.leer_contrasena(archivo), SECRETO)

    def test_archivo_inexistente(self):
        with self.assertRaises(it.ErrorToken) as error:
            it.leer_contrasena(Path(tempfile.mkdtemp()) / ".env")
        self.assertIn("No existe", str(error.exception))

    def test_variable_ausente_o_vacia(self):
        for texto in ("OTRA=1\n", "KEYCLOAK_TEST_USER_PASSWORD=\n"):
            with self.assertRaises(it.ErrorToken) as error:
                it.leer_contrasena(self.escribir(texto))
            self.assertIn("no está definida", str(error.exception))


class Solicitud(unittest.TestCase):
    def test_peticion_correcta(self):
        abrir = abrir_con({"access_token": TOKEN_IT, "expires_in": 300})
        respuesta = it.solicitar_token("inventario.test", SECRETO, abrir=abrir)
        self.assertEqual(respuesta["access_token"], TOKEN_IT)
        [(peticion, timeout)] = abrir.peticiones
        self.assertEqual(peticion.full_url, it.TOKEN_URL)
        self.assertEqual(peticion.get_method(), "POST")
        self.assertIn(b"grant_type=password", peticion.data)
        self.assertIn(b"client_id=sio-web", peticion.data)
        self.assertNotIn(b"client_secret", peticion.data)
        self.assertEqual(timeout, it.TIMEOUT_SEGUNDOS)

    def test_contrasena_incorrecta(self):
        with self.assertRaises(it.ErrorToken) as error:
            it.solicitar_token("ventas.test", SECRETO, abrir=abrir_con_error(401, {"error": "invalid_grant"}))
        self.assertIn("rechazó las credenciales", str(error.exception))
        self.assertNotIn(SECRETO, str(error.exception))

    def test_respuesta_http_incorrecta(self):
        with self.assertRaises(it.ErrorToken) as error:
            it.solicitar_token("ventas.test", SECRETO, abrir=abrir_con_error(503, {}))
        self.assertIn("HTTP 503", str(error.exception))

    def test_keycloak_no_disponible(self):
        def abrir(peticion, timeout):
            raise urllib.error.URLError(ConnectionRefusedError(111, "Connection refused"))

        with self.assertRaises(it.ErrorToken) as error:
            it.solicitar_token("ventas.test", SECRETO, abrir=abrir)
        self.assertIn("no disponible", str(error.exception))

    def test_error_de_conexion(self):
        def abrir(peticion, timeout):
            raise TimeoutError

        with self.assertRaises(it.ErrorToken) as error:
            it.solicitar_token("ventas.test", SECRETO, abrir=abrir)
        self.assertIn("Error de conexión", str(error.exception))

    def test_respuesta_no_json_o_sin_token(self):
        for cuerpo in (b"<html>", {"token_type": "Bearer"}):
            with self.assertRaises(it.ErrorToken):
                it.solicitar_token("ventas.test", SECRETO, abrir=abrir_con(cuerpo))

    def test_redireccion_es_error(self):
        manejador = it._SinRedirecciones()
        with self.assertRaises(it.ErrorToken):
            manejador.redirect_request(None, None, 302, "Found", {}, "http://otro/")


class Emisor(unittest.TestCase):
    def test_acepta_sio_it(self):
        it.comprobar_emisor(it.reclamaciones(TOKEN_IT))

    def test_rechaza_keycloak_habitual(self):
        with self.assertRaises(it.ErrorToken):
            it.comprobar_emisor(it.reclamaciones(jwt(iss="http://localhost:8081/realms/sio")))

    def test_jwt_invalido(self):
        with self.assertRaises(it.ErrorToken):
            it.reclamaciones("no-es-un-jwt")


class Main(unittest.TestCase):
    def ejecutar(self, argv, terminal=(False, False), entradas=(), **parches):
        """`terminal` = (stdin es teclado, stdout es pantalla); `entradas`, lo que se escribe en el menú."""
        salida, errores = io.StringIO(), io.StringIO()
        respuestas = iter(entradas)

        def leer():
            try:
                return next(respuestas)
            except StopIteration:
                raise EOFError from None

        def es_terminal(flujo):
            return terminal[0] if flujo is sys.stdin else terminal[1]

        parches.setdefault("mostrar_empresas", mock.Mock())
        with mock.patch.object(it, "leer_contrasena", return_value=SECRETO), \
                mock.patch.object(it, "solicitar_token", return_value={"access_token": TOKEN_IT, "expires_in": 300}), \
                mock.patch.object(it, "es_terminal", es_terminal), \
                mock.patch("sys.stdout", salida), mock.patch("sys.stderr", errores):
            for nombre, valor in parches.items():
                mock.patch.object(it, nombre, valor).start()
            try:
                codigo = it.main(argv, leer=leer)
            finally:
                mock.patch.stopall()
        self.empresas = parches["mostrar_empresas"]
        return codigo, salida.getvalue(), errores.getvalue()

    def test_imprime_solo_el_token_en_stdout(self):
        codigo, salida, errores = self.ejecutar([])
        self.assertEqual(codigo, 0)
        self.assertEqual(salida.strip(), TOKEN_IT)
        self.assertIn("inventario.test", errores)
        self.assertIn("sio-it", errores)
        self.assertIn("300 s", errores)
        self.assertIn(it.SWAGGER_URL, errores)
        self.assertNotIn(SECRETO, salida + errores)

    def test_copy_no_imprime_el_token(self):
        copiado = mock.Mock(return_value="xclip")
        codigo, salida, errores = self.ejecutar(["ventas.test", "--copy"], copiar=copiado)
        self.assertEqual(codigo, 0)
        self.assertEqual(salida, "")
        self.assertNotIn(TOKEN_IT, errores)
        copiado.assert_called_once_with(TOKEN_IT)

    def test_copy_sin_herramienta(self):
        with mock.patch.object(it.shutil, "which", return_value=None):
            with self.assertRaises(it.ErrorToken):
                it.copiar(TOKEN_IT)

    def test_error_devuelve_1_sin_secretos(self):
        falla = mock.Mock(side_effect=it.ErrorToken("Keycloak respondió HTTP 503."))
        codigo, salida, errores = self.ejecutar(["ventas.test"], solicitar_token=falla)
        self.assertEqual(codigo, 1)
        self.assertEqual(salida, "")
        self.assertIn("HTTP 503", errores)
        self.assertNotIn(SECRETO, errores)

    def test_usuario_invalido_devuelve_1(self):
        codigo, salida, errores = self.ejecutar(["otro.usuario"])
        self.assertEqual((codigo, salida), (1, ""))
        self.assertIn("Usuario no válido", errores)


class Menu(unittest.TestCase):
    def setUp(self):
        self.errores = io.StringIO()
        parche = mock.patch("sys.stderr", self.errores)
        parche.start()
        self.addCleanup(parche.stop)

    def test_muestra_el_encabezado_y_los_siete_usuarios(self):
        self.assertEqual(it.menu(iter(["5"]).__next__), "inventario.test")
        texto = self.errores.getvalue()
        self.assertIn("SIO - AMBIENTE DE INTEGRACIÓN", texto)
        self.assertIn("Selecciona el usuario:", texto)
        for numero, usuario in enumerate(it.USUARIOS, start=1):
            self.assertIn(f"{numero}. {usuario}", texto)
        self.assertIn("Opción:", texto)

    def test_seleccion_por_numero_y_por_nombre(self):
        self.assertEqual(it.menu(iter(["1"]).__next__), "admin.test")
        self.assertEqual(it.menu(iter(["ventas"]).__next__), "ventas.test")

    def test_opcion_invalida_vuelve_a_preguntar(self):
        self.assertEqual(it.menu(iter(["9", "abc", "4"]).__next__), "ventas.test")
        self.assertEqual(self.errores.getvalue().count("Opción no válida"), 2)

    def test_salir(self):
        self.assertIsNone(it.menu(iter(["0"]).__next__))

        def fin():
            raise EOFError

        self.assertIsNone(it.menu(fin))


def respuestas_pila(rutas: dict):
    """`abrir` simulado para lecturas: ruta → JSON, o un código HTTP de error; registra las URL pedidas."""
    pedidas = []

    def abrir(peticion, timeout):
        pedidas.append(peticion.full_url)
        assert peticion.get_method() == "GET"
        assert peticion.headers["Authorization"] == f"Bearer {TOKEN_IT}"
        for ruta, valor in rutas.items():
            if peticion.full_url.endswith(ruta) or ruta + "?" in peticion.full_url:
                if isinstance(valor, int):
                    raise urllib.error.HTTPError(peticion.full_url, valor, "error", {}, io.BytesIO(b"{}"))
                return Respuesta(json.dumps(valor).encode())
        raise urllib.error.HTTPError(peticion.full_url, 404, "error", {}, io.BytesIO(b"{}"))

    abrir.pedidas = pedidas
    return abrir


DAO = "4e0f8c4a-f357-49fc-8b2b-d62c985e1ab2"
OTRA = "11111111-1111-4111-8111-111111111111"


def membresia(company_id, status="ACTIVE", asignadas=()):
    return {"company_id": company_id, "status": status, "company_status": "ACTIVE",
            "branches": [{"branch_id": b, "allowed": True} for b in asignadas]}


class Empresas(unittest.TestCase):
    def pila(self, memberships, **extra):
        rutas = {
            "/me/operational-context": {"memberships": memberships},
            f"/companies/{DAO}": {"id": DAO, "organization_identity_id": "org-dao"},
            f"/companies/{OTRA}": {"id": OTRA, "organization_identity_id": "org-otra"},
            "/organization-identities/org-dao": {"legal_name": "EMPRESA DAO", "trade_name": None},
            "/organization-identities/org-otra": {"legal_name": "OTRA S.A.S.", "trade_name": "Otra"},
            f"/companies/{DAO}/branches": {"items": [{"id": "b1", "code": "S1", "name": "Sucursal 1"},
                                                     {"id": "b2", "code": "S2", "name": "Sucursal 2"}],
                                           "total_pages": 1},
            f"/companies/{OTRA}/branches": {"items": [], "total_pages": 1},
        }
        rutas.update(extra)
        return respuestas_pila(rutas)

    def test_solo_membresias_activas_con_nombre_y_sucursales(self):
        abrir = self.pila([membresia(OTRA), membresia(DAO, asignadas=["b2"]), membresia("inactiva", "INACTIVE")])
        empresas = it.empresas_del_usuario(TOKEN_IT, abrir)
        self.assertEqual([e.company_id for e in empresas], [DAO, OTRA])  # conocidas primero
        dao = empresas[0]
        self.assertEqual((dao.nombre, dao.referencia), ("EMPRESA DAO", "empresa tipo DAO"))
        self.assertEqual([(s.branch_id, s.asignada) for s in dao.sucursales], [("b1", False), ("b2", True)])
        self.assertEqual(empresas[1].nombre, "Otra")
        self.assertFalse(any("inactiva" in url for url in abrir.pedidas))

    def test_las_empresas_conocidas_no_crean_membresias(self):
        empresas = it.empresas_del_usuario(TOKEN_IT, self.pila([membresia(OTRA)]))
        self.assertEqual([e.company_id for e in empresas], [OTRA])

    def test_usuario_sin_membresias(self):
        abrir = self.pila([])
        self.assertEqual(it.empresas_del_usuario(TOKEN_IT, abrir), [])
        errores = io.StringIO()
        with mock.patch("sys.stderr", errores):
            it.mostrar_empresas("consulta.test", TOKEN_IT, abrir)
        self.assertIn("no tiene membresías ACTIVE", errores.getvalue())

    def test_membresias_no_legibles_no_se_confirman(self):
        abrir = respuestas_pila({"/me/operational-context": 503})
        errores = io.StringIO()
        with mock.patch("sys.stderr", errores):
            it.mostrar_empresas("ventas.test", TOKEN_IT, abrir)
        self.assertIn("NO confirmadas", errores.getvalue())
        self.assertIn("HTTP 503", errores.getvalue())
        self.assertNotIn(TOKEN_IT, errores.getvalue())

    def test_sin_permiso_de_sucursales_usa_las_asignadas_y_lo_avisa(self):
        abrir = self.pila([membresia(DAO, asignadas=["b2"])], **{f"/companies/{DAO}/branches": 403})
        [dao] = it.empresas_del_usuario(TOKEN_IT, abrir)
        self.assertFalse(dao.sucursales_confirmadas)
        self.assertEqual([s.branch_id for s in dao.sucursales], ["b2"])
        self.assertIn("HTTP 403", dao.aviso)

    def test_solo_lecturas_en_la_pila(self):
        abrir = self.pila([membresia(DAO), membresia(OTRA)])
        it.empresas_del_usuario(TOKEN_IT, abrir)
        self.assertTrue(abrir.pedidas)
        for url in abrir.pedidas:
            self.assertTrue(url.startswith(("http://localhost:18104/", "http://localhost:18101/")), url)

    def test_un_destino_ajeno_no_se_consulta(self):
        abrir = mock.Mock()
        with self.assertRaises(it.ErrorToken):
            it.leer_json("http://localhost:8104/api/v1/me/operational-context", TOKEN_IT, abrir)
        abrir.assert_not_called()


class Interactivo(unittest.TestCase):
    ejecutar = Main.ejecutar

    def test_menu_obtiene_copia_y_no_imprime(self):
        copiado = mock.Mock(return_value="wl-copy")
        codigo, salida, errores = self.ejecutar([], terminal=(True, True), entradas=["4"], copiar=copiado)
        self.assertEqual((codigo, salida), (0, ""))
        copiado.assert_called_once_with(TOKEN_IT)
        self.assertIn("SIO - AMBIENTE DE INTEGRACIÓN", errores)
        for dato in ("Realm:    sio", "Ambiente: sio-it", "http://localhost:18081", it.SWAGGER_URL, "300 s"):
            self.assertIn(dato, errores)
        self.assertIn("copiado al portapapeles", errores)
        self.assertNotIn(TOKEN_IT, errores)
        self.assertNotIn(SECRETO, errores)
        self.empresas.assert_called_once()

    def test_menu_sin_portapapeles_explica_como_obtenerlo(self):
        falla = mock.Mock(side_effect=it.ErrorToken("sin portapapeles"))
        codigo, salida, errores = self.ejecutar([], terminal=(True, True), entradas=["4"], copiar=falla)
        self.assertEqual((codigo, salida), (0, ""))
        self.assertIn("TOKEN=$(python services/get_token_pruebas_it.py ventas.test)", errores)
        self.assertNotIn(TOKEN_IT, errores)

    def test_menu_con_salida_capturada_entrega_el_token_en_stdout(self):
        copiado = mock.Mock()
        codigo, salida, _ = self.ejecutar([], terminal=(True, False), entradas=["2"], copiar=copiado)
        self.assertEqual((codigo, salida.strip()), (0, TOKEN_IT))
        copiado.assert_not_called()

    def test_menu_salir(self):
        codigo, salida, errores = self.ejecutar([], terminal=(True, True), entradas=["0"])
        self.assertEqual((codigo, salida), (0, ""))
        self.assertIn("Saliendo", errores)

    def test_sin_teclado_usa_inventario_sin_menu(self):
        codigo, salida, errores = self.ejecutar([], terminal=(False, False))
        self.assertEqual((codigo, salida.strip()), (0, TOKEN_IT))
        self.assertNotIn("Selecciona el usuario", errores)
        self.empresas.assert_not_called()

    def test_comandos_existentes_no_muestran_menu(self):
        for argv in (["ventas.test"], ["--user", "ventas.test"]):
            codigo, salida, errores = self.ejecutar(argv, terminal=(True, True))
            self.assertEqual((codigo, salida.strip()), (0, TOKEN_IT))
            self.assertNotIn("Selecciona el usuario", errores)
            self.empresas.assert_not_called()

    def test_opcion_empresas_en_modo_no_interactivo(self):
        codigo, salida, _ = self.ejecutar(["ventas.test", "--empresas"])
        self.assertEqual((codigo, salida.strip()), (0, TOKEN_IT))
        self.empresas.assert_called_once()


if __name__ == "__main__":
    unittest.main()
