"""T057 — Renderizado de la guía docs/validacion-mvp/ desde los pasos (sio_mvp.guide)."""

import pytest

from scenario.steps import AuditSpec, Step
from sio_mvp import guide

pytestmark = pytest.mark.unit

STEP = Step(
    "P-02.P1", "Confirmar la compra P1", "3-compras-e-inventario", (10,), "compras.test",
    "perm:purchase:purchases:update", "purchase", "POST", "/companies/{empresa_a}/purchases/{compra_1}/confirmation", 200,
    body={"version": "{compra_1_version}", "nota": "Compra {run}"},
    save={"compra_1_numero": "number"},
    audit=(AuditSpec("purchase", "CONFIRM_PURCHASE", "Purchase", "{compra_1}"),),
    idempotent=True, why="Asigna el número oficial.", expected_note="`status` = `CONFIRMED`",
)


class FakeRealm:
    PERMS = {"admin.test": {"perm:all:all:all"}, "compras.test": {"perm:purchase:all:all"}}
    users = {name: {"groups": [f"/{name.split('.')[0]}"]} for name in (
        "admin.test", "compras.test", "ventas.test", "supervisor.test", "consulta.test", "reportes.test", "inventario.test")}

    def user_permissions(self, user):
        return set(self.PERMS.get(user, set()))

    def has_permission(self, user, permission):
        from sio_mvp.realm import Realm

        return any(Realm.grants(role, permission) for role in self.PERMS.get(user, set()))

    def granting_role(self, user, permission):
        from sio_mvp.realm import Realm

        return next((role for role in sorted(self.PERMS.get(user, set())) if Realm.grants(role, permission)), None)


def test_step_render_contains_user_permission_method_path_body_and_expected():
    text = guide.render_call(STEP, FakeRealm(), number=1)
    assert "`compras.test`" in text
    assert "`perm:purchase:purchases:update`" in text
    assert "POST http://127.0.0.1:8107/api/v1/companies/<EMPRESA_A>/purchases/<COMPRA_1>/confirmation" in text
    assert '"version": "<COMPRA_1_VERSION>"' in text
    assert "Idempotency-Key" in text and "X-Correlation-Id" in text
    assert "`200`" in text and "`status` = `CONFIRMED`" in text
    assert "`number` → `<COMPRA_1_NUMERO>`" in text
    assert "`CONFIRM_PURCHASE`" in text
    assert "Asigna el número oficial." in text


def test_markers_do_not_depend_on_run_id():
    text = guide.render_call(STEP, FakeRealm(), number=1)
    assert "<RUN_ID>" in text
    assert "{run}" not in text and "{empresa_a}" not in text


def test_who_can_lists_users_with_the_permission():
    text = guide.render_call(STEP, FakeRealm(), number=1)
    assert "`admin.test`" in text and "`compras.test`" in text


def test_render_has_no_secrets():
    pages = guide.render([STEP], FakeRealm())
    import re

    for content in pages.values():
        # Solo se nombra la variable; nunca un valor literal, un token ni un secreto de cliente.
        assert re.search(r"password=(?!\$KEYCLOAK_TEST_USER_PASSWORD)", content) is None
        assert "Bearer ey" not in content and "client_secret" not in content


def test_render_produces_index_exercises_and_users_pages():
    pages = guide.render([STEP], FakeRealm())
    assert "README.md" in pages
    assert "usuarios-y-permisos.md" in pages
    assert "3-compras-e-inventario/ORDEN.md" in pages
    assert "3-compras-e-inventario/USUARIOS.md" in pages
    assert any(path.startswith("3-compras-e-inventario/0") for path in pages)


def test_render_is_deterministic():
    assert guide.render([STEP], FakeRealm()) == guide.render([STEP], FakeRealm())
