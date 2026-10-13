"""Pruebas sin red de la obtención de tokens (services/get_token.py y su uso desde sio_query.py).

    tools/data-migration/.venv/bin/python -m pytest tools/data-migration/ia-tools/test_tokens.py -q
"""

from __future__ import annotations

import importlib.util

import pytest

import sio_query

SECRETO = "secreto-sintetico-de-prueba"


class Respuesta:
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
