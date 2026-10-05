"""Pruebas reales de permisos de sio-auth contra Keycloak.

La contraseña del usuario de prueba (`KEYCLOAK_TEST_USER_PASSWORD`) y la URL y el realm de
Keycloak (`KEYCLOAK_PUBLIC_URL`, `KEYCLOAK_REALM`) se leen de la variable de entorno o, si no
existe, de `infrastructure/.env`; la contraseña no tiene valor por defecto y, si falta, las
pruebas se omiten. Ejecución: `pytest tests/validar_token_env.py`.

Validan:
1. Que Keycloak esté disponible.
2. Que sea posible obtener un Access Token real.
3. Que sio-auth valide ese token contra el JWKS real.
4. Que los permisos provengan dinámicamente de resource_access.sio-api.roles.
5. Que los permisos tengan la estructura perm:{servicio}:{recurso}:{accion}.
6. Que los wildcards `all` funcionen sin mantener catálogos locales de permisos.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import requests

from sio_auth import AuthSettings, SioPermission
from sio_auth.jwks import JWKSClient
from sio_auth.models import SioGrant
from sio_auth.permissions import (
    has_permission,
    parse_permission_grant,
)
from sio_auth.tokens import AccessTokenDecoder, TokenClaims


# =====================================================================
# CONFIGURACIÓN EXCLUSIVA DE ESTA PRUEBA
# =====================================================================
#
# Estos valores pertenecen al escenario de prueba; ninguno es una credencial.
# NO forman parte de la configuración interna de sio-auth.
# NO se empaquetan dentro de la librería instalada porque están fuera de src/.
#

# Mismo criterio que `services/get_token.py` y las pruebas de integración de los
# servicios: primero la variable de entorno y, si no existe, `infrastructure/.env`
# (no versionado; `infrastructure/.env.example` documenta las variables con
# valores ficticios).
INFRASTRUCTURE_ENV = Path(__file__).resolve().parents[3] / "infrastructure" / ".env"


def _setting(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    if not value and INFRASTRUCTURE_ENV.is_file():
        for line in INFRASTRUCTURE_ENV.read_text(encoding="utf-8").splitlines():
            key, separator, content = line.partition("=")
            if separator and key.strip() == name:
                value = content.strip().strip('"').strip("'")
    return value or None


KEYCLOAK_BASE_URL = (_setting("KEYCLOAK_PUBLIC_URL") or "http://localhost:8081").rstrip("/")
KEYCLOAK_REALM = _setting("KEYCLOAK_REALM") or "sio"

KEYCLOAK_TEST_CLIENT_ID = "sio-web"
KEYCLOAK_TEST_USERNAME = "admin.test"

# La contraseña NUNCA se escribe en el código ni tiene valor por defecto
# (Constitución, Principio IX).
PASSWORD_VARIABLE = "KEYCLOAK_TEST_USER_PASSWORD"
KEYCLOAK_TEST_PASSWORD = _setting(PASSWORD_VARIABLE)

SIO_AUTH_AUDIENCE = "sio-api"

if not KEYCLOAK_TEST_PASSWORD:
    pytest.skip(
        f"Defina {PASSWORD_VARIABLE} (variable de entorno o infrastructure/.env) para "
        "ejecutar las pruebas reales contra Keycloak.",
        allow_module_level=True,
    )


ISSUER = f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}"

TOKEN_URL = (
    f"{ISSUER}/protocol/openid-connect/token"
)

OPENID_CONFIGURATION_URL = (
    f"{ISSUER}/.well-known/openid-configuration"
)


# =====================================================================
# FIXTURES
# =====================================================================

@pytest.fixture(scope="session")
def token_keycloak() -> str:
    """Solicita un Access Token real al Keycloak de pruebas."""

    payload = {
        "grant_type": "password",
        "client_id": KEYCLOAK_TEST_CLIENT_ID,
        "username": KEYCLOAK_TEST_USERNAME,
        "password": KEYCLOAK_TEST_PASSWORD,
        "scope": "openid",
    }

    try:
        respuesta = requests.post(
            TOKEN_URL,
            data=payload,
            timeout=5,
        )
    except requests.exceptions.ConnectionError:
        pytest.fail(
            "No se pudo conectar a Keycloak. "
            "Verifica que el servicio esté ejecutándose."
        )

    if respuesta.status_code != 200:
        pytest.fail(
            "Keycloak no pudo generar el Access Token. "
            f"HTTP {respuesta.status_code}: {respuesta.text}"
        )

    datos = respuesta.json()

    assert "access_token" in datos, (
        "Keycloak no devolvió access_token"
    )

    assert datos.get("token_type", "").lower() == "bearer", (
        "Keycloak no devolvió un token de tipo Bearer"
    )

    return datos["access_token"]


@pytest.fixture(scope="session")
def claims_keycloak(token_keycloak: str) -> TokenClaims:
    """Valida el token real utilizando sio-auth y devuelve sus claims."""

    # No usamos AuthSettings.from_env().
    # La configuración se entrega explícitamente a la librería.
    settings = AuthSettings(
        issuer=ISSUER,
        audience=SIO_AUTH_AUDIENCE,
    )

    with JWKSClient(settings) as jwks_client:
        decoder = AccessTokenDecoder(
            settings,
            jwks_client,
        )

        return decoder.decode(token_keycloak)


# =====================================================================
# 1. KEYCLOAK DISPONIBLE
# =====================================================================

def test_keycloak_esta_disponible():
    """Verifica que Keycloak y el realm configurado respondan."""

    try:
        respuesta = requests.get(
            OPENID_CONFIGURATION_URL,
            timeout=5,
        )
    except requests.exceptions.ConnectionError:
        pytest.fail(
            "No se pudo conectar a Keycloak. "
            "Verifica que el servicio esté ejecutándose."
        )

    assert respuesta.status_code == 200, (
        "Keycloak respondió con código "
        f"{respuesta.status_code}"
    )

    datos = respuesta.json()

    assert datos.get("issuer") == ISSUER, (
        "El issuer publicado por Keycloak no coincide "
        "con el issuer esperado"
    )


# =====================================================================
# 2. TOKEN REAL VÁLIDO
# =====================================================================

def test_token_es_validado_por_sio_auth(
    claims_keycloak: TokenClaims,
):
    """Comprueba que sio-auth acepte el Access Token real."""

    assert claims_keycloak.subject
    assert claims_keycloak.issuer == ISSUER
    assert SIO_AUTH_AUDIENCE in claims_keycloak.audiences

    print("\nTOKEN VALIDADO")
    print(f"sub: {claims_keycloak.subject}")
    print(
        "username: "
        f"{claims_keycloak.preferred_username or 'No informado'}"
    )


# =====================================================================
# 3. ESTRUCTURA DE LOS PERMISOS QUE VIENEN DE KEYCLOAK
# =====================================================================

def test_permisos_keycloak_tienen_estructura_correcta(
    claims_keycloak: TokenClaims,
):
    """Valida todos los roles `perm:` recibidos desde Keycloak.

    No se compara contra una lista fija de permisos.
    Se inspecciona dinámicamente lo que realmente llegó en el JWT.
    """

    roles_permiso = sorted(
        role
        for role in claims_keycloak.roles
        if role.startswith("perm:")
    )

    assert roles_permiso, (
        "El usuario autenticado no recibió ningún role con prefijo 'perm:'. "
        "Revisa los roles de resource_access.sio-api.roles en Keycloak."
    )

    print("\nPERMISOS RECIBIDOS DESDE KEYCLOAK")

    for role in roles_permiso:
        print(f"- {role}")

        partes = role.split(":")

        assert len(partes) == 4, (
            f"El permiso '{role}' no cumple "
            "perm:{servicio}:{recurso}:{accion}"
        )

        assert partes[0] == "perm"

        assert partes[1], (
            f"El permiso '{role}' no contiene servicio"
        )
        assert partes[2], (
            f"El permiso '{role}' no contiene recurso"
        )
        assert partes[3], (
            f"El permiso '{role}' no contiene acción"
        )

        grant = parse_permission_grant(role)

        assert grant is not None, (
            f"sio-auth no pudo interpretar el permiso '{role}'"
        )


# =====================================================================
# 4. LOS PERMISOS DE TokenClaims DEBEN SALIR DE LOS ROLES DE KEYCLOAK
# =====================================================================

def test_permissions_se_extraen_de_roles_keycloak(
    claims_keycloak: TokenClaims,
):
    """Comprueba que sio-auth no invente ni mantenga permisos locales."""

    esperados = {
        role
        for role in claims_keycloak.roles
        if parse_permission_grant(role) is not None
    }

    detectados = {
        str(permission)
        for permission in claims_keycloak.permissions
    }

    assert detectados == esperados, (
        "Los permisos detectados por sio-auth no coinciden exactamente "
        "con los roles de permisos recibidos desde Keycloak."
    )

    print("\nPERMISOS INTERPRETADOS POR SIO-AUTH")

    for permission in sorted(detectados):
        print(f"- {permission}")


# =====================================================================
# 5. UN GRANT REAL DEL TOKEN DEBE CONCEDER UN PERMISO COMPATIBLE
# =====================================================================

def test_un_grant_real_concede_permiso(
    claims_keycloak: TokenClaims,
):
    """Toma un grant real del JWT y comprueba la resolución de wildcards."""

    assert claims_keycloak.permissions, (
        "El token no contiene permisos que sio-auth pueda evaluar"
    )

    grant = next(iter(claims_keycloak.permissions))

    # Si un segmento contiene `all`, usamos un nombre ficticio para demostrar
    # que realmente funciona como wildcard.
    required = SioPermission(
        service=(
            "servicio_prueba"
            if grant.service == "all"
            else grant.service
        ),
        resource=(
            "recurso_prueba"
            if grant.resource == "all"
            else grant.resource
        ),
        action=(
            "accion_prueba"
            if grant.action == "all"
            else grant.action
        ),
    )

    assert has_permission(
        claims_keycloak.permissions,
        required,
    ), (
        f"El grant real '{grant}' debería permitir '{required}'"
    )

    print("\nVALIDACIÓN DE GRANT REAL")
    print(f"Grant recibido : {grant}")
    print(f"Permiso pedido : {required}")
    print("Resultado       : PERMITIDO")


# =====================================================================
# 6. REGLA GENÉRICA DE WILDCARD GLOBAL
# =====================================================================

def test_wildcard_global_all():
    """Comprueba perm:all:all:all sin depender de permisos reales de SIO."""

    grants = {
        SioGrant(
            service="all",
            resource="all",
            action="all",
        )
    }

    required = SioPermission(
        service="servicio_prueba",
        resource="recurso_prueba",
        action="accion_prueba",
    )

    assert has_permission(grants, required) is True


# =====================================================================
# 7. UN PERMISO CON ACCIÓN DIFERENTE DEBE SER RECHAZADO
# =====================================================================

def test_accion_diferente_no_concede_permiso():
    """Comprueba que un grant concreto no autorice otra acción."""

    grants = {
        SioGrant(
            service="servicio_prueba",
            resource="recurso_prueba",
            action="leer",
        )
    }

    required = SioPermission(
        service="servicio_prueba",
        resource="recurso_prueba",
        action="actualizar",
    )

    assert has_permission(grants, required) is False
