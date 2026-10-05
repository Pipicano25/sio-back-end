"""Ejecución simultánea de solicitudes contra la base real de pruebas (pruebas de concurrencia).

Cada solicitud usa su propio `TestClient` (su propia conexión) y todas arrancan
juntas con una barrera, como en las pruebas de concurrencia de la Fase A.
"""

from __future__ import annotations

import threading
from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import ApiClient


def race(app, token: str, calls: list[tuple[str, str, Any]]):
    """Envía `(método, url, cuerpo)` en paralelo y devuelve las respuestas en el mismo orden."""
    barrier = threading.Barrier(len(calls))
    results: list[Any] = [None] * len(calls)

    def run(index: int, method: str, url: str, body: Any) -> None:
        with TestClient(app, raise_server_exceptions=False) as client:
            barrier.wait()
            results[index] = ApiClient(client, token).request(method, url, json=body)

    threads = [
        threading.Thread(target=run, args=(index, *call)) for index, call in enumerate(calls)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return results
