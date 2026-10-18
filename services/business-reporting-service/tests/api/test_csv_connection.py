"""Garantía real del CSV ante un error a mitad de la transmisión, con un servidor Uvicorn local (sin contenedores).

Con codificación `chunked`, al relanzarse la excepción después de enviar datos, Uvicorn cierra la conexión **sin**
el bloque final `0\\r\\n\\r\\n`. Un cliente HTTP lo detecta como cuerpo incompleto (`httpx.RemoteProtocolError`;
`curl` termina con el código 18). Es lo que se documenta como garantía del lado del transporte; la garantía que no
depende del cliente es la ausencia de la fila `TOTAL FILAS`.
"""

from __future__ import annotations

import socket
import threading
import time

import httpx
import pytest
import uvicorn

from business_reporting_service.main import create_app
from tests.api.support import PERIOD, branch_base, seed_evolution
from tests.conftest import NOW, build_test_settings
from tests.fakes import build_fakes


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def server(test_auth, user_token):
    fakes = build_fakes()
    seed_evolution(fakes, 250)
    fakes.fail_inventory_pages.add(2)
    app = create_app(build_test_settings(), auth=test_auth, jwks_probe=lambda: True, ports_factory=fakes.ports_for,
                     clock=lambda: NOW)
    port = free_port()
    instance = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="critical"))
    thread = threading.Thread(target=instance.run, daemon=True)
    thread.start()
    for _ in range(100):
        if instance.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}", fakes, user_token("inventario.test")
    instance.should_exit = True
    thread.join(timeout=5)


def test_interrupted_csv_is_an_incomplete_http_body(server) -> None:
    url, fakes, token = server
    received = bytearray()
    with pytest.raises(httpx.RemoteProtocolError):
        with httpx.stream("GET", url + branch_base(fakes) + "/stock-evolution",
                          params={**PERIOD, "format": "csv"}, headers={"Authorization": f"Bearer {token}"},
                          timeout=10) as response:
            assert response.status_code == 200
            assert response.headers.get("transfer-encoding") == "chunked"
            for chunk in response.iter_bytes():
                received.extend(chunk)
    text = received.decode("utf-8")
    assert "#ERROR: reporte incompleto, trace_id=" in text
    assert "TOTAL FILAS" not in text


def test_complete_csv_ends_cleanly(server) -> None:
    url, fakes, token = server
    fakes.fail_inventory_pages.clear()
    response = httpx.get(url + branch_base(fakes) + "/stock-evolution", params={**PERIOD, "format": "csv"},
                         headers={"Authorization": f"Bearer {token}"}, timeout=10)
    assert response.status_code == 200
    assert response.text.rstrip("\r\n").endswith("TOTAL FILAS,250")
