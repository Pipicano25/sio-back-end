"""Prueba de provision.py contra un contenedor de PRUEBA (spec 025, T008).

Crea una base propia ``contract_provision_test`` en el servidor de la base de pruebas de Operational Context, con
una tabla, tres vistas de contrato y dos consumidores; aplica dos veces, verifica las cuatro comprobaciones y lo
borra todo al terminar (base y roles). No toca las tablas de las pruebas de OC.

URL de administrador: ``CONTRACT_PROVISION_TEST_ADMIN_URL`` o, si falta, ``OPERATIONAL_CONTEXT_TEST_DATABASE_URL``
cargada del ``.env`` de operational-context-service, igual que su ``conftest.py``. Solo se aceptan bases cuyo nombre
contiene "test".

    services/operational-context-service/.venv/bin/pytest infrastructure/scripts/contract-readers/tests -q
"""

from __future__ import annotations

import importlib.util
import os
import secrets
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
SCRIPT = HERE.parent / "provision.py"
DB = "contract_provision_test"
ROLES = ("alp_contract_reader", "bet_contract_reader", "contract_dmo__alp", "contract_dmo__bet")


def _load_script():
    spec = importlib.util.spec_from_file_location("provision", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


provision = _load_script()


def _server_admin_url() -> str:
    url = os.environ.get("CONTRACT_PROVISION_TEST_ADMIN_URL", "").strip()
    if not url:
        try:
            from dotenv import load_dotenv
        except ModuleNotFoundError:
            pytest.skip("Sin CONTRACT_PROVISION_TEST_ADMIN_URL ni python-dotenv.")
        load_dotenv(REPO / "services" / "operational-context-service" / ".env", override=False)
        url = os.environ.get("OPERATIONAL_CONTEXT_TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("Sin URL de una base de pruebas.")
    if "test" not in (make_url(url).database or "").lower():
        pytest.fail("La URL de administrador debe ser de una base de pruebas.")
    return url


def _cleanup(server):
    with server.connect() as connection:
        connection.execute(text(f"DROP DATABASE IF EXISTS {DB} WITH (FORCE)"))
        for role in ROLES:
            connection.execute(text(f"DROP ROLE IF EXISTS {role}"))


@pytest.fixture(scope="module")
def admin_url():
    base = _server_admin_url()
    server = create_engine(base, isolation_level="AUTOCOMMIT")
    try:
        with server.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        server.dispose()
        pytest.skip("La base de pruebas de Operational Context no responde (docker start sio-operational-context-test-db).")
    _cleanup(server)
    with server.connect() as connection:
        connection.execute(text(f"CREATE DATABASE {DB}"))
    url = make_url(base).set(database=DB).render_as_string(hide_password=False)
    owner = create_engine(url)
    with owner.begin() as connection:
        connection.execute(text("CREATE TABLE public.secret_table (id int, name text)"))
        connection.execute(text("INSERT INTO public.secret_table VALUES (1, 'x')"))
        connection.execute(text("CREATE SCHEMA contract"))
        for view in ("v1_a", "v1_b", "v1_c"):
            connection.execute(text(f"CREATE VIEW contract.{view} AS SELECT id FROM public.secret_table"))
    owner.dispose()
    yield url
    _cleanup(server)
    server.dispose()


def _grants(tmp_path: Path, alpha_views: str) -> Path:
    services = tmp_path / "services"
    path = services / "demo-owner-service" / "contract" / "grants.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "owner: demo-owner\n"
        "abbreviation: dmo\n"
        "consumers:\n"
        f"  alpha:\n    abbreviation: alp\n    views: [{alpha_views}]\n"
        "  beta:\n    abbreviation: bet\n    views: [v1_c]\n",
        encoding="utf-8",
    )
    return services


@pytest.fixture
def env(monkeypatch, admin_url):
    passwords = {"ALPHA": secrets.token_urlsafe(24), "BETA": secrets.token_urlsafe(24)}
    monkeypatch.setenv("CONTRACT_ADMIN_URL_DEMO_OWNER", admin_url)
    for name, value in passwords.items():
        monkeypatch.setenv(f"CONTRACT_READER_PASSWORD_{name}", value)
    return passwords


def _run(command, services, capsys):
    code = provision.main([command, "--entorno", "local", "--services-dir", str(services)])
    return code, capsys.readouterr()


def _assert_no_secrets(output, admin_url, passwords):
    text_out = output.out + output.err
    assert make_url(admin_url).password not in text_out
    for value in passwords.values():
        assert value not in text_out


def test_apply_is_idempotent_and_verify_passes(tmp_path, env, admin_url, capsys):
    services = _grants(tmp_path, "v1_a, v1_b")
    for _ in range(2):
        code, output = _run("aplicar", services, capsys)
        assert code == 0, output.err
        assert "demo-owner → alpha: 2 vistas" in output.out
        _assert_no_secrets(output, admin_url, env)

    code, output = _run("verificar", services, capsys)
    assert code == 0, output.out
    lines = [line for line in output.out.splitlines() if line.startswith(("OK", "FALLA"))]
    assert all(line.startswith("OK") for line in lines)
    for expected in (
        "dmo→alp: lee contract.v1_a",
        "dmo→alp: lee contract.v1_b",
        "dmo→alp: no lee public.secret_table",
        "dmo→alp: no escribe",
        "dmo→alp: no lee contract.v1_c",
        "dmo→bet: no lee contract.v1_a",
    ):
        assert any(expected in line for line in lines), expected
    _assert_no_secrets(output, admin_url, env)


def test_removing_a_view_revokes_it(tmp_path, env, admin_url, capsys):
    assert _run("aplicar", _grants(tmp_path, "v1_a, v1_b"), capsys)[0] == 0
    services = _grants(tmp_path, "v1_a")
    assert _run("aplicar", services, capsys)[0] == 0
    reader = provision.prov.reader_url(admin_url, "alp_contract_reader", env["ALPHA"])
    engine = create_engine(reader)
    try:
        with pytest.raises(Exception, match="permission denied"):
            with engine.connect() as connection:
                connection.execute(text("SELECT 1 FROM contract.v1_b"))
    finally:
        engine.dispose()


def test_verify_fails_when_a_table_is_readable(tmp_path, env, admin_url, capsys):
    services = _grants(tmp_path, "v1_a")
    assert _run("aplicar", services, capsys)[0] == 0
    owner = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with owner.connect() as connection:
        connection.execute(text("GRANT SELECT ON public.secret_table TO contract_dmo__alp"))
    try:
        code, output = _run("verificar", services, capsys)
        assert code == 1
        assert "FALLA dmo→alp: no lee public.secret_table" in output.out
    finally:
        with owner.connect() as connection:
            connection.execute(text("REVOKE SELECT ON public.secret_table FROM contract_dmo__alp"))
        owner.dispose()


def test_missing_password_is_reported_without_secrets(tmp_path, env, admin_url, monkeypatch, capsys):
    monkeypatch.delenv("CONTRACT_READER_PASSWORD_BETA")
    code, output = _run("aplicar", _grants(tmp_path, "v1_a"), capsys)
    assert code == 2
    assert "CONTRACT_READER_PASSWORD_BETA" in output.err
    _assert_no_secrets(output, admin_url, env)


def test_undeclared_view_is_rejected(tmp_path, env, capsys):
    code, output = _run("aplicar", _grants(tmp_path, "v1_a, v1_zz"), capsys)
    assert code == 2
    assert "v1_zz" in output.err
