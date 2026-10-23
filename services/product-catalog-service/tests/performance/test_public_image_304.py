"""`304` de la ruta pública de imágenes en ≤ 100 ms sin cargar el objeto (spec 022, T143; RNF-022-6).

Solo en la pila aislada `sio-it-*`: `SIO_TEST_TARGET=isolated` y `validation/isolation_guard.py`. La URL se obtiene
de PC-3 (spec 024) para la presentación con imagen del manifiesto de `validation/isolated-stack/seed.py`. Para demostrar que el
`304` no lee el almacenamiento, se repite con el almacenamiento aislado **congelado** (`docker pause`; sus datos
están en `tmpfs` y un `stop` los borraría): el `304` sigue respondiendo y un `200` ya no puede.
"""

from __future__ import annotations

import importlib.util
import json
import os
import statistics
import subprocess
import time
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.performance

REPO = Path(__file__).resolve().parents[4]
PC = os.environ.get("PRODUCT_CATALOG_INTEGRATION_BASE_URL", "http://127.0.0.1:18103/api/v1").rstrip("/")
TOKEN_URL = os.environ.get("KEYCLOAK_TOKEN_URL", "http://127.0.0.1:18081/realms/sio/protocol/openid-connect/token")
STORAGE = "sio-it-object-storage"


def guard():
    spec = importlib.util.spec_from_file_location("sio_isolation_guard", REPO / "validation" / "isolation_guard.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def isolated_password() -> str:
    path = Path(os.environ.get("SIO_IT_ENV_FILE", REPO / "validation" / "isolated-stack" / ".env"))
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("KEYCLOAK_TEST_USER_PASSWORD="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("sin contraseña de la pila aislada")


@pytest.fixture(scope="module")
def image_url() -> str:
    guard().check_targets({"product_catalog": PC, "keycloak": TOKEN_URL})
    state = Path(os.environ.get("SIO_IT_STATE_DIR", "/tmp/sio-it-state")) / "seed.json"
    seed = json.loads(state.read_text(encoding="utf-8"))
    presentation = next(p["image_presentation_id"] for p in seed["products"].values() if p["image"])
    token = httpx.post(TOKEN_URL, data={"grant_type": "password", "client_id": "sio-web", "scope": "openid",
                                        "username": "ventas.test", "password": isolated_password()}).raise_for_status()
    # Spec 024: la URL es de la imagen principal de la presentación (PC-3).
    response = httpx.post(f"{PC}/presentations/batch-lookup", json={"ids": [presentation]},
                          headers={"Authorization": f"Bearer {token.json()['access_token']}"}).raise_for_status()
    url = response.json()["items"][0]["image_url"]
    assert url
    return url


def test_304_within_100_ms(image_url) -> None:
    with httpx.Client() as browser:
        etag = browser.get(image_url).raise_for_status().headers["etag"]
        for _ in range(5):
            browser.get(image_url, headers={"If-None-Match": etag})
        durations = []
        for _ in range(50):
            started = time.perf_counter()
            response = browser.get(image_url, headers={"If-None-Match": etag})
            durations.append(time.perf_counter() - started)
            assert response.status_code == 304 and response.content == b""
    durations.sort()
    p95 = durations[int(0.95 * len(durations)) - 1]
    print(f"304: p50={statistics.median(durations) * 1000:.1f} ms p95={p95 * 1000:.1f} ms")
    assert p95 <= 0.100


def test_304_does_not_read_the_object(image_url) -> None:
    with httpx.Client() as browser:
        etag = browser.get(image_url).raise_for_status().headers["etag"]
        guard().check_container(STORAGE)
        subprocess.run(["docker", "pause", STORAGE], check=True, capture_output=True, timeout=60)
        try:
            started = time.perf_counter()
            assert browser.get(image_url, headers={"If-None-Match": etag}).status_code == 304
            assert time.perf_counter() - started <= 0.100
            # Sin almacenamiento, el contenido no se puede servir: `503` o tiempo agotado, nunca la imagen.
            try:
                response = browser.get(image_url, timeout=15)
                assert response.status_code != 200
            except httpx.TimeoutException:
                pass
        finally:
            guard().check_container(STORAGE)
            subprocess.run(["docker", "unpause", STORAGE], check=True, capture_output=True, timeout=60)
            for _ in range(60):
                if browser.get(image_url).status_code == 200:
                    break
                time.sleep(1)
        assert browser.get(image_url).status_code == 200
