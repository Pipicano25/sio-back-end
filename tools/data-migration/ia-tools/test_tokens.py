"""Pruebas sin red de la obtención de tokens (services/get_token.py y su uso desde sio_query.py).

    tools/data-migration/.venv/bin/python -m pytest tools/data-migration/ia-tools/test_tokens.py -q
"""

from __future__ import annotations

import importlib.util
import json

import pytest

import sio_query

SECRETO = "secreto-sintetico-de-prueba"


class Respuesta:
    status_code = 200

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return {"access_token": "token-sintetico"}


@pytest.fixture
def get_token(monkeypatch):
    spec = importlib.util.spec_from_file_location("get_token_prueba", sio_query.TOKEN_SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    enviados: list[dict] = []
    monkeypatch.setattr(modulo.requests, "post", lambda url, data, timeout: enviados.append(data) or Respuesta())
    modulo.enviados = enviados
    return modulo


def test_usuario_de_prueba_sigue_usando_password(get_token, monkeypatch, capsys) -> None:
    monkeypatch.setenv("KEYCLOAK_TEST_USER_PASSWORD", SECRETO)
    assert get_token.obtener_token("consulta") == "token-sintetico"
    enviado = get_token.enviados[0]
    assert enviado["grant_type"] == "password" and enviado["client_id"] == "sio-web"
    assert enviado["username"] == "consulta.test"
    assert SECRETO not in capsys.readouterr().err


def test_cliente_tecnico_usa_client_credentials_y_no_muestra_el_secreto(get_token, monkeypatch, capsys) -> None:
    monkeypatch.setenv("SIO_DATA_IMPORTER_CLIENT_SECRET", SECRETO)
    assert get_token.obtener_token_cliente("sio-data-importer") == "token-sintetico"
    enviado = get_token.enviados[0]
    assert enviado == {"grant_type": "client_credentials", "client_id": "sio-data-importer", "client_secret": SECRETO}
    salida = capsys.readouterr()
    assert SECRETO not in salida.err and SECRETO not in salida.out


def test_cliente_sin_secreto_se_detiene_sin_solicitar_token(get_token, monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("CLIENTE_INEXISTENTE_CLIENT_SECRET", raising=False)
    monkeypatch.setattr(get_token, "INFRASTRUCTURE_ENV", tmp_path / "no-existe.env")
    with pytest.raises(SystemExit, match="CLIENTE_INEXISTENTE_CLIENT_SECRET"):
        get_token.obtener_token_cliente("cliente-inexistente")
    assert get_token.enviados == []


def test_main_con_cliente(get_token, monkeypatch, capsys) -> None:
    monkeypatch.setenv("SIO_DATA_IMPORTER_CLIENT_SECRET", SECRETO)
    monkeypatch.setattr(get_token.sys, "argv", ["get_token.py", "--cliente", "sio-data-importer"])
    assert get_token.main() == 0
    assert capsys.readouterr().out.strip() == "token-sintetico"
    monkeypatch.setattr(get_token.sys, "argv", ["get_token.py", "--cliente"])
    assert get_token.main() == 1


def test_sio_query_elige_la_funcion_segun_el_rol(monkeypatch) -> None:
    llamadas: list[tuple[str, str]] = []

    class Modulo:
        @staticmethod
        def obtener_token(rol):
            llamadas.append(("usuario", rol))
            return "t-usuario"

        @staticmethod
        def obtener_token_cliente(client_id):
            llamadas.append(("cliente", client_id))
            return "t-cliente"

    class Spec:
        loader = type("L", (), {"exec_module": staticmethod(lambda m: None)})()

    monkeypatch.setattr(sio_query.importlib.util, "spec_from_file_location", lambda *a: Spec())
    monkeypatch.setattr(sio_query.importlib.util, "module_from_spec", lambda spec: Modulo)
    assert sio_query.SioQuery("consulta")._authorization() == {"Authorization": "Bearer t-usuario"}
    assert sio_query.SioQuery("cliente:sio-data-importer")._authorization() == {"Authorization": "Bearer t-cliente"}
    assert llamadas == [("usuario", "consulta"), ("cliente", "sio-data-importer")]


def test_usuario_nominal_usa_su_contrasena_del_entorno(get_token, monkeypatch, capsys) -> None:
    monkeypatch.setenv("SANTIAGO_RODRIGUEZ_PASSWORD", SECRETO)
    assert get_token.obtener_token_usuario("santiago.rodriguez") == "token-sintetico"
    enviado = get_token.enviados[0]
    assert enviado["grant_type"] == "password" and enviado["username"] == "santiago.rodriguez"
    assert enviado["password"] == SECRETO and SECRETO not in capsys.readouterr().err
    monkeypatch.setattr(get_token.sys, "argv", ["get_token.py", "--usuario", "santiago.rodriguez"])
    assert get_token.main() == 0


def test_sio_query_rol_usuario(monkeypatch) -> None:
    class Modulo:
        obtener_token = staticmethod(lambda rol: "t-test")
        obtener_token_cliente = staticmethod(lambda c: "t-cliente")
        obtener_token_usuario = staticmethod(lambda u: f"t-{u}")

    class Spec:
        loader = type("L", (), {"exec_module": staticmethod(lambda m: None)})()

    monkeypatch.setattr(sio_query.importlib.util, "spec_from_file_location", lambda *a: Spec())
    monkeypatch.setattr(sio_query.importlib.util, "module_from_spec", lambda spec: Modulo)
    assert sio_query.SioQuery("usuario:santiago.rodriguez")._authorization() == {"Authorization": "Bearer t-santiago.rodriguez"}


# ----------------------------------------------- opción 8: usuarios de empresas (menú interactivo)

CONTRASENA = "contrasena-sintetica-de-prueba"
TOKEN = "token-sintetico-de-empresa"


class Keycloak:
    """Keycloak simulado: solo acepta `CONTRASENA`; registra los envíos."""

    def __init__(self) -> None:
        self.enviados: list[dict] = []

    def __call__(self, url, data, timeout):
        self.enviados.append(data)
        valido = data.get("grant_type") != "password" or data.get("password") in (CONTRASENA, SECRETO)
        return RespuestaKeycloak(200 if valido else 401, {"access_token": TOKEN, "expires_in": 300,
                                                            "refresh_token": "refresh-sintetico"} if valido
                                 else {"error": "invalid_grant", "error_description": "Invalid user credentials"})


class RespuestaKeycloak:
    def __init__(self, status_code: int, cuerpo: dict) -> None:
        self.status_code, self._cuerpo = status_code, cuerpo

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"{self.status_code} Client Error")

    def json(self) -> dict:
        return self._cuerpo


@pytest.fixture
def menu(get_token, monkeypatch, tmp_path):
    """Menú con entradas guionizadas, contraseña por `getpass` simulada y Keycloak simulado."""
    keycloak = Keycloak()
    monkeypatch.setattr(get_token.requests, "post", keycloak)

    # nunca el archivo real: por omisión, uno inexistente (contraseña manual)
    monkeypatch.setattr(get_token, "CREDENCIALES_LOCALES", tmp_path / "sin-credenciales.txt")

    def ejecutar(entradas: list[str], contrasenas: list[str] = (), empresas=None, credenciales=None, modo=0o600):
        if credenciales is not None:
            archivo_credenciales = tmp_path / "credenciales.txt"
            archivo_credenciales.write_text(credenciales, encoding="utf-8")
            archivo_credenciales.chmod(modo)
            monkeypatch.setattr(get_token, "CREDENCIALES_LOCALES", archivo_credenciales)
        if empresas is not None:
            archivo = tmp_path / "empresas.json"
            archivo.write_text(json.dumps(empresas), encoding="utf-8")
            monkeypatch.setattr(get_token, "EMPRESAS_FILE", archivo)
        pendientes, claves = iter(entradas), iter(contrasenas)
        monkeypatch.setattr("builtins.input", lambda *a: next(pendientes))
        pedidas: list[dict] = []

        def getpass(prompt, stream=None):
            pedidas.append({"prompt": prompt, "stream": stream})
            return next(claves)

        monkeypatch.setattr(get_token.getpass, "getpass", getpass)
        monkeypatch.setattr(get_token.sys, "argv", ["get_token.py"])
        codigo = get_token.main()
        return codigo, keycloak.enviados, pedidas

    return ejecutar


def test_configuracion_versionada_tiene_los_siete_usuarios_reales_de_dao(get_token) -> None:
    [dao] = get_token.cargar_empresas()
    assert dao["nombre"] == "GRUPO DAO S.A.S." and dao["company_id"] == "eede165e-71e7-430f-b126-d3899cd36398"
    assert [(u["usuario"], u["grupo"]) for u in dao["usuarios"]] == [
        ("santiago.rodriguez", "supervisores"), ("laura.martinez", "ventas"), ("andres.ramirez", "ventas"),
        ("valentina.gomez", "consulta"), ("juan.castro", "consulta"), ("daniela.herrera", "consulta"),
        ("nicolas.vargas", "consulta"),
    ]
    texto = get_token.EMPRESAS_FILE.read_text(encoding="utf-8").lower()
    assert "password" not in texto.replace("nunca contraseñas", "") and "secret" not in texto and "token\"" not in texto


def test_roles_actuales_siguen_igual(menu, monkeypatch, capsys) -> None:
    monkeypatch.setenv("KEYCLOAK_TEST_USER_PASSWORD", SECRETO)
    codigo, enviados, pedidas = menu(["4"])
    assert codigo == 0 and enviados[0]["username"] == "ventas.test" and pedidas == []
    salida = capsys.readouterr()
    assert salida.out.strip() == TOKEN
    for linea in ("1. Admin", "7. Consulta", "8. Usuarios de empresas", "0. Salir"):
        assert linea in salida.err


def test_dao_muestra_sus_usuarios_y_entrega_el_token_del_elegido(menu, capsys) -> None:
    codigo, enviados, pedidas = menu(["8", "1", "2", "n"], [CONTRASENA])
    assert codigo == 0
    assert enviados == [{"grant_type": "password", "client_id": "sio-web", "username": "laura.martinez",
                         "password": CONTRASENA, "scope": "openid"}]
    assert pedidas[0]["stream"] is not None and "laura.martinez" in pedidas[0]["prompt"]  # getpass: sin eco
    salida = capsys.readouterr()
    assert salida.out.strip() == TOKEN  # solo el token en la salida estándar
    assert "1. GRUPO DAO S.A.S." in salida.err and "0. Volver" in salida.err
    assert "Usuarios de GRUPO DAO S.A.S." in salida.err
    assert "1. santiago.rodriguez" in salida.err and "Supervisores" in salida.err and "3. andres.ramirez" in salida.err
    assert "vence en 300 segundos" in salida.err and "Usuario: laura.martinez" in salida.err
    for secreto in (CONTRASENA, "refresh-sintetico"):
        assert secreto not in salida.err and secreto not in salida.out


def test_contrasena_incorrecta_da_mensaje_controlado_y_permite_reintentar(menu, capsys) -> None:
    codigo, enviados, _ = menu(["8", "1", "1", "1", "1", "n"], ["incorrecta-sintetica", CONTRASENA])
    assert codigo == 0 and [e["password"] for e in enviados] == ["incorrecta-sintetica", CONTRASENA]
    salida = capsys.readouterr()
    assert "Usuario o contraseña incorrectos" in salida.err
    assert "incorrecta-sintetica" not in salida.err + salida.out and "Invalid user credentials" not in salida.err
    assert salida.out.strip() == TOKEN


def test_contrasena_vacia_no_llama_a_keycloak(menu, capsys) -> None:
    codigo, enviados, _ = menu(["8", "1", "1", "0", "0", "0"], [""])
    assert codigo == 0 and enviados == [] and capsys.readouterr().out == ""


def test_volver_y_salir(menu, capsys) -> None:
    # usuarios → Volver → empresas → Volver → menú principal → Salir: sin token ni llamadas
    codigo, enviados, pedidas = menu(["8", "1", "0", "0", "0"])
    assert codigo == 0 and enviados == [] and pedidas == []
    salida = capsys.readouterr()
    assert salida.out == "" and "Saliendo..." in salida.err
    assert salida.err.count("Seleccione un rol:") == 2 and salida.err.count("Seleccione una empresa:") == 2


def test_opcion_invalida_en_submenus(menu, capsys) -> None:
    codigo, enviados, _ = menu(["8", "9", "x", "0", "0"])
    assert codigo == 0 and enviados == []
    assert capsys.readouterr().err.count("Opción no válida") == 2


def test_otra_empresa_sin_cambiar_el_codigo(menu, capsys) -> None:
    empresas = {"empresas": [
        {"nombre": "GRUPO DAO S.A.S.", "usuarios": [{"usuario": "santiago.rodriguez", "grupo": "supervisores"}]},
        {"nombre": "EMPRESA FICTICIA S.A.S.", "usuarios": [{"usuario": "usuario.ficticio", "grupo": "compras"}]},
    ]}
    codigo, enviados, _ = menu(["8", "2", "1", "n"], [CONTRASENA], empresas=empresas)
    assert codigo == 0 and enviados[0]["username"] == "usuario.ficticio"
    assert "2. EMPRESA FICTICIA S.A.S." in capsys.readouterr().err


def test_configuracion_invalida_se_detiene_sin_llamar_a_keycloak(menu, get_token, monkeypatch, tmp_path) -> None:
    for contenido in ("{no es json", json.dumps({"empresas": [{"nombre": "X", "usuarios": [{"usuario": " "}]}]})):
        archivo = tmp_path / "rota.json"
        archivo.write_text(contenido, encoding="utf-8")
        monkeypatch.setattr(get_token, "EMPRESAS_FILE", archivo)
        with pytest.raises(SystemExit, match="configuración de empresas"):
            menu(["8"])


def test_usuario_nominal_por_argumento_con_contrasena_incorrecta_no_revela_secretos(get_token, monkeypatch, capsys) -> None:
    keycloak = Keycloak()
    monkeypatch.setattr(get_token.requests, "post", keycloak)
    monkeypatch.setenv("SANTIAGO_RODRIGUEZ_PASSWORD", "incorrecta-sintetica")
    with pytest.raises(SystemExit) as error:
        get_token.obtener_token_usuario("santiago.rodriguez")
    assert "usuario o contraseña incorrectos" in str(error.value) and "incorrecta-sintetica" not in str(error.value)


# ----------------------------------------------- credenciales del archivo local de desarrollo

CREDENCIALES = (
    "# archivo sintético de prueba\n"
    "santiago.rodriguez=" + CONTRASENA + "\n"
    "laura.martinez=otra-contrasena-sintetica\n"
)


def test_credencial_local_sin_teclear_y_otro_usuario(menu, capsys) -> None:
    """Santiago con la contraseña del archivo; luego se vuelve y se elige a Laura (rechazada → manual)."""
    codigo, enviados, pedidas = menu(["8", "1", "1", "s", "1", "2", "n"], [CONTRASENA], credenciales=CREDENCIALES)
    assert codigo == 0
    assert [(e["username"], e["password"]) for e in enviados] == [
        ("santiago.rodriguez", CONTRASENA),
        ("laura.martinez", "otra-contrasena-sintetica"),  # del archivo; Keycloak simulado la rechaza
        ("laura.martinez", CONTRASENA),  # la escrita a mano
    ]
    assert len(pedidas) == 1 and "laura.martinez" in pedidas[0]["prompt"]  # solo se tecleó la de Laura
    salida = capsys.readouterr()
    assert salida.out.split() == [TOKEN, TOKEN]
    assert "tomada del archivo local" in salida.err and "Keycloak rechazó la contraseña de laura.martinez" in salida.err
    for secreto in (CONTRASENA, "otra-contrasena-sintetica", "refresh-sintetico"):
        assert secreto not in salida.err and secreto not in salida.out


def test_solo_se_lee_la_linea_del_usuario(get_token, monkeypatch, tmp_path) -> None:
    archivo = tmp_path / "c.txt"
    archivo.write_text(CREDENCIALES + "  # comentario\n\nsin-separador\nvacio=\n", encoding="utf-8")
    archivo.chmod(0o600)
    monkeypatch.setattr(get_token, "CREDENCIALES_LOCALES", archivo)
    assert get_token.contrasena_local("santiago.rodriguez") == CONTRASENA
    for ausente in ("santiago", "vacio", "sin-separador", "nicolas.vargas"):
        with pytest.raises(get_token.CredencialLocalNoDisponible) as error:
            get_token.contrasena_local(ausente)
        assert CONTRASENA not in str(error.value) and "otra-contrasena" not in str(error.value)


@pytest.mark.parametrize("modo", [0o644, 0o640, 0o604, 0o660])
def test_permisos_inseguros_obligan_a_escribirla(menu, capsys, modo) -> None:
    codigo, enviados, pedidas = menu(["8", "1", "1", "n"], [CONTRASENA], credenciales=CREDENCIALES, modo=modo)
    assert codigo == 0 and len(pedidas) == 1 and enviados[0]["password"] == CONTRASENA
    err = capsys.readouterr().err
    assert "permisos inseguros" in err and "chmod 600" in err and "otra-contrasena" not in err


def test_archivo_ausente_o_usuario_sin_credencial_pide_la_contrasena(menu, capsys) -> None:
    codigo, _, pedidas = menu(["8", "1", "1", "n"], [CONTRASENA])  # archivo inexistente
    assert codigo == 0 and len(pedidas) == 1 and "no existe el archivo" in capsys.readouterr().err
    codigo, _, pedidas = menu(["8", "1", "7", "n"], [CONTRASENA], credenciales=CREDENCIALES)  # nicolas.vargas
    assert codigo == 0 and len(pedidas) == 1 and "nicolas.vargas no tiene credenciales" in capsys.readouterr().err


def test_keycloak_remoto_nunca_usa_el_archivo(menu, get_token, monkeypatch, capsys) -> None:
    monkeypatch.setattr(get_token, "TOKEN_URL", "https://keycloak.ejemplo.invalid/realms/sio/protocol/openid-connect/token")
    codigo, enviados, pedidas = menu(["8", "1", "1", "n"], [CONTRASENA], credenciales=CREDENCIALES)
    assert codigo == 0 and len(pedidas) == 1 and enviados[0]["password"] == CONTRASENA
    assert "Keycloak no es local" in capsys.readouterr().err


def test_contrasena_rechazada_y_manual_vacia_vuelve_a_la_lista(menu, capsys) -> None:
    codigo, enviados, _ = menu(["8", "1", "2", "0", "0", "0"], [""], credenciales=CREDENCIALES)
    assert codigo == 0 and [e["username"] for e in enviados] == ["laura.martinez"]  # la vacía no se envía
    salida = capsys.readouterr()
    assert salida.out == "" and "Usuario o contraseña incorrectos" in salida.err
