"""Grupos de usuario del realm: superadmin, admin, Compras, Ventas e Inventario (spec 026, versión del servidor OCI).

Lee la plantilla versionada del realm y la compara con las listas exactas del contrato de la spec
(`specs/026-three-permission-groups/contracts/realm-groups.md`, copiadas aquí porque `specs/` no está en
Git). Evalúa los permisos con `sio-auth`, incluidos los comodines, igual que lo hace cada servicio.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sio_auth.models import SioPermission
from sio_auth.permissions import evaluate_permission

REALM = (
    Path(__file__).resolve().parents[4]
    / "infrastructure" / "keycloak" / "realm-template" / "sio-realm.template.json"
)
DATA = json.loads(REALM.read_text(encoding="utf-8"))
GROUPS = {group["name"]: group["clientRoles"]["sio-api"] for group in DATA["groups"]}
CATALOG = [role["name"] for role in DATA["roles"]["client"]["sio-api"]]
HUMANS = {user["username"]: user for user in DATA["users"] if "serviceAccountClientId" not in user}

SUPERADMIN = frozenset({"superadmin", "perm:all:all:all"})

ADMIN = frozenset({
    "admin",
    "perm:audit:audit-events:read",
    "perm:business-reporting:purchases:read",
    "perm:business-reporting:sales_by_branch:read",
    "perm:business-reporting:stock_evolution:read",
    "perm:business-reporting:top_selling_products:read",
    "perm:commercial-relationship:all:create",
    "perm:commercial-relationship:all:delete",
    "perm:commercial-relationship:all:read",
    "perm:commercial-relationship:all:update",
    "perm:commercial-relationship:automatic_price_applications:resolve",
    "perm:geography:all:create",
    "perm:geography:all:read",
    "perm:geography:all:update",
    "perm:inventory:adjustments:create",
    "perm:inventory:adjustments:read",
    "perm:inventory:balances:read",
    "perm:inventory:company-policies:read",
    "perm:inventory:company-policies:update",
    "perm:inventory:counts:create",
    "perm:inventory:counts:read",
    "perm:inventory:movements:read",
    "perm:inventory:product-policies:read",
    "perm:inventory:product-policies:update",
    "perm:inventory:stock_evolution:read",
    "perm:inventory:valuation:read",
    "perm:operational-context:all:create",
    "perm:operational-context:all:delete",
    "perm:operational-context:all:read",
    "perm:operational-context:all:update",
    "perm:party-identity:all:create",
    "perm:party-identity:all:read",
    "perm:party-identity:all:update",
    "perm:payment-reference:all:create",
    "perm:payment-reference:all:read",
    "perm:payment-reference:all:update",
    "perm:payment_reference:global_payment_condition_types:read",
    "perm:payment_reference:global_payment_methods:read",
    "perm:product-catalog:all:create",
    "perm:product-catalog:all:read",
    "perm:product-catalog:all:update",
    "perm:product-catalog:first-use:register-manual",
    "perm:product-inventory-query:inventory_overviews:read",
    "perm:product-inventory-query:inventory_summary:read",
    "perm:product-inventory-query:inventory_valuation:read",
    "perm:product-inventory-query:low_stock_products:read",
    "perm:product-inventory-query:product_overviews:read",
    "perm:product-inventory-query:stock:read",
    "perm:purchase:all:all",
    "perm:sales:all:all",
})

# Grupo `empleado` del cierre anterior de la 026: referencia de equivalencia de las tres áreas juntas.
EMPLEADO_ANTERIOR = frozenset({
    "empleado",
    "perm:business-reporting:purchases:read",
    "perm:business-reporting:stock_evolution:read",
    "perm:business-reporting:top_selling_products:read",
    "perm:commercial-relationship:company_customers:create",
    "perm:commercial-relationship:company_customers:read",
    "perm:commercial-relationship:company_product_presentations:read",
    "perm:commercial-relationship:company_products:read",
    "perm:commercial-relationship:company_suppliers:read",
    "perm:commercial-relationship:customer_credit_profiles:read",
    "perm:commercial-relationship:customer_payment_conditions:read",
    "perm:commercial-relationship:customer_segments:read",
    "perm:commercial-relationship:price_list_items:read",
    "perm:commercial-relationship:price_lists:read",
    "perm:commercial-relationship:product_pricing_policies:read",
    "perm:commercial-relationship:supplier_commercial_conditions:read",
    "perm:commercial-relationship:supplier_evaluations:read",
    "perm:commercial-relationship:supplier_payment_conditions:read",
    "perm:commercial-relationship:supplier_products:read",
    "perm:geography:all:read",
    "perm:inventory:adjustments:create",
    "perm:inventory:adjustments:read",
    "perm:inventory:balances:read",
    "perm:inventory:company-policies:read",
    "perm:inventory:counts:create",
    "perm:inventory:counts:read",
    "perm:inventory:movements:read",
    "perm:inventory:product-policies:read",
    "perm:inventory:stock_evolution:read",
    "perm:inventory:valuation:read",
    "perm:operational-context:all:read",
    "perm:party-identity:global_business_sectors:read",
    "perm:party-identity:identification_type_rules:read",
    "perm:party-identity:organization_business_sectors:read",
    "perm:party-identity:organization_contact_persons:create",
    "perm:party-identity:organization_contact_persons:read",
    "perm:party-identity:organization_contact_persons:update",
    "perm:party-identity:organization_contact_profiles:create",
    "perm:party-identity:organization_contact_profiles:read",
    "perm:party-identity:organization_contact_profiles:update",
    "perm:party-identity:organization_identities:create",
    "perm:party-identity:organization_identities:read",
    "perm:party-identity:organization_identities:update",
    "perm:party-identity:organization_legal_representatives:read",
    "perm:party-identity:person_contact_profiles:create",
    "perm:party-identity:person_contact_profiles:read",
    "perm:party-identity:person_contact_profiles:update",
    "perm:party-identity:person_identities:create",
    "perm:party-identity:person_identities:read",
    "perm:party-identity:person_identities:update",
    "perm:payment-reference:all:read",
    "perm:product-catalog:all:read",
    "perm:product-inventory-query:inventory_overviews:read",
    "perm:product-inventory-query:inventory_summary:read",
    "perm:product-inventory-query:low_stock_products:read",
    "perm:product-inventory-query:product_overviews:read",
    "perm:product-inventory-query:stock:read",
    "perm:purchase:purchase_details:create",
    "perm:purchase:purchase_details:delete",
    "perm:purchase:purchase_details:read",
    "perm:purchase:purchase_details:update",
    "perm:purchase:purchase_lifecycle_events:create",
    "perm:purchase:purchase_lifecycle_events:delete",
    "perm:purchase:purchase_lifecycle_events:read",
    "perm:purchase:purchase_lifecycle_events:update",
    "perm:purchase:purchase_operations:create",
    "perm:purchase:purchase_operations:delete",
    "perm:purchase:purchase_operations:read",
    "perm:purchase:purchase_operations:update",
    "perm:purchase:purchase_sequences:create",
    "perm:purchase:purchase_sequences:delete",
    "perm:purchase:purchase_sequences:read",
    "perm:purchase:purchase_sequences:update",
    "perm:purchase:purchases:create",
    "perm:purchase:purchases:delete",
    "perm:purchase:purchases:read",
    "perm:purchase:purchases:update",
    "perm:sales:all:create",
    "perm:sales:all:delete",
    "perm:sales:all:read",
    "perm:sales:all:update",
})

COMPRAS = frozenset({
    "perm:business-reporting:purchases:read",
    "perm:commercial-relationship:company_customers:read",
    "perm:commercial-relationship:company_product_presentations:read",
    "perm:commercial-relationship:company_products:read",
    "perm:commercial-relationship:company_suppliers:read",
    "perm:commercial-relationship:customer_credit_profiles:read",
    "perm:commercial-relationship:customer_payment_conditions:read",
    "perm:commercial-relationship:customer_segments:read",
    "perm:commercial-relationship:price_list_items:read",
    "perm:commercial-relationship:price_lists:read",
    "perm:commercial-relationship:product_pricing_policies:read",
    "perm:commercial-relationship:supplier_commercial_conditions:read",
    "perm:commercial-relationship:supplier_evaluations:read",
    "perm:commercial-relationship:supplier_payment_conditions:read",
    "perm:commercial-relationship:supplier_products:read",
    "perm:geography:all:read",
    "perm:operational-context:all:read",
    "perm:party-identity:global_business_sectors:read",
    "perm:party-identity:identification_type_rules:read",
    "perm:party-identity:organization_business_sectors:read",
    "perm:party-identity:organization_contact_persons:create",
    "perm:party-identity:organization_contact_persons:read",
    "perm:party-identity:organization_contact_persons:update",
    "perm:party-identity:organization_contact_profiles:create",
    "perm:party-identity:organization_contact_profiles:read",
    "perm:party-identity:organization_contact_profiles:update",
    "perm:party-identity:organization_identities:create",
    "perm:party-identity:organization_identities:read",
    "perm:party-identity:organization_identities:update",
    "perm:party-identity:organization_legal_representatives:read",
    "perm:party-identity:person_contact_profiles:create",
    "perm:party-identity:person_contact_profiles:read",
    "perm:party-identity:person_contact_profiles:update",
    "perm:party-identity:person_identities:create",
    "perm:party-identity:person_identities:read",
    "perm:party-identity:person_identities:update",
    "perm:payment-reference:all:read",
    "perm:product-catalog:all:read",
    "perm:purchase:purchase_details:create",
    "perm:purchase:purchase_details:delete",
    "perm:purchase:purchase_details:read",
    "perm:purchase:purchase_details:update",
    "perm:purchase:purchase_lifecycle_events:create",
    "perm:purchase:purchase_lifecycle_events:delete",
    "perm:purchase:purchase_lifecycle_events:read",
    "perm:purchase:purchase_lifecycle_events:update",
    "perm:purchase:purchase_operations:create",
    "perm:purchase:purchase_operations:delete",
    "perm:purchase:purchase_operations:read",
    "perm:purchase:purchase_operations:update",
    "perm:purchase:purchase_sequences:create",
    "perm:purchase:purchase_sequences:delete",
    "perm:purchase:purchase_sequences:read",
    "perm:purchase:purchase_sequences:update",
    "perm:purchase:purchases:create",
    "perm:purchase:purchases:delete",
    "perm:purchase:purchases:read",
    "perm:purchase:purchases:update",
})

VENTAS = frozenset({
    "perm:business-reporting:top_selling_products:read",
    "perm:commercial-relationship:company_customers:create",
    "perm:commercial-relationship:company_customers:read",
    "perm:commercial-relationship:company_product_presentations:read",
    "perm:commercial-relationship:company_products:read",
    "perm:commercial-relationship:company_suppliers:read",
    "perm:commercial-relationship:customer_credit_profiles:read",
    "perm:commercial-relationship:customer_payment_conditions:read",
    "perm:commercial-relationship:customer_segments:read",
    "perm:commercial-relationship:price_list_items:read",
    "perm:commercial-relationship:price_lists:read",
    "perm:commercial-relationship:product_pricing_policies:read",
    "perm:commercial-relationship:supplier_commercial_conditions:read",
    "perm:commercial-relationship:supplier_evaluations:read",
    "perm:commercial-relationship:supplier_payment_conditions:read",
    "perm:commercial-relationship:supplier_products:read",
    "perm:geography:all:read",
    "perm:operational-context:all:read",
    "perm:party-identity:global_business_sectors:read",
    "perm:party-identity:identification_type_rules:read",
    "perm:party-identity:organization_business_sectors:read",
    "perm:party-identity:organization_contact_persons:create",
    "perm:party-identity:organization_contact_persons:read",
    "perm:party-identity:organization_contact_persons:update",
    "perm:party-identity:organization_contact_profiles:create",
    "perm:party-identity:organization_contact_profiles:read",
    "perm:party-identity:organization_contact_profiles:update",
    "perm:party-identity:organization_identities:create",
    "perm:party-identity:organization_identities:read",
    "perm:party-identity:organization_identities:update",
    "perm:party-identity:organization_legal_representatives:read",
    "perm:party-identity:person_contact_profiles:create",
    "perm:party-identity:person_contact_profiles:read",
    "perm:party-identity:person_contact_profiles:update",
    "perm:party-identity:person_identities:create",
    "perm:party-identity:person_identities:read",
    "perm:party-identity:person_identities:update",
    "perm:payment-reference:all:read",
    "perm:product-catalog:all:read",
    "perm:product-inventory-query:inventory_overviews:read",
    "perm:product-inventory-query:product_overviews:read",
    "perm:product-inventory-query:stock:read",
    "perm:sales:all:create",
    "perm:sales:all:delete",
    "perm:sales:all:read",
    "perm:sales:all:update",
})

INVENTARIO = frozenset({
    "perm:business-reporting:stock_evolution:read",
    "perm:commercial-relationship:company_products:read",
    "perm:geography:all:read",
    "perm:inventory:adjustments:create",
    "perm:inventory:adjustments:read",
    "perm:inventory:balances:read",
    "perm:inventory:company-policies:read",
    "perm:inventory:counts:create",
    "perm:inventory:counts:read",
    "perm:inventory:movements:read",
    "perm:inventory:product-policies:read",
    "perm:inventory:stock_evolution:read",
    "perm:inventory:valuation:read",
    "perm:operational-context:all:read",
    "perm:product-catalog:all:read",
    "perm:product-inventory-query:inventory_overviews:read",
    "perm:product-inventory-query:inventory_summary:read",
    "perm:product-inventory-query:low_stock_products:read",
    "perm:product-inventory-query:product_overviews:read",
    "perm:product-inventory-query:stock:read",
})

OPERARIO = COMPRAS | VENTAS | INVENTARIO

UNION_VENTAS_COMPRAS_INVENTARIO = frozenset({
    "perm:business-reporting:purchases:read",
    "perm:business-reporting:stock_evolution:read",
    "perm:business-reporting:top_selling_products:read",
    "perm:commercial-relationship:company_customers:create",
    "perm:commercial-relationship:company_customers:read",
    "perm:commercial-relationship:company_product_presentations:read",
    "perm:commercial-relationship:company_products:read",
    "perm:commercial-relationship:company_suppliers:read",
    "perm:commercial-relationship:customer_credit_profiles:read",
    "perm:commercial-relationship:customer_payment_conditions:read",
    "perm:commercial-relationship:customer_segments:read",
    "perm:commercial-relationship:price_list_items:read",
    "perm:commercial-relationship:price_lists:read",
    "perm:commercial-relationship:product_pricing_policies:read",
    "perm:commercial-relationship:supplier_commercial_conditions:read",
    "perm:commercial-relationship:supplier_evaluations:read",
    "perm:commercial-relationship:supplier_payment_conditions:read",
    "perm:commercial-relationship:supplier_products:read",
    "perm:geography:all:read",
    "perm:inventory:adjustments:create",
    "perm:inventory:adjustments:read",
    "perm:inventory:balances:read",
    "perm:inventory:company-policies:read",
    "perm:inventory:counts:create",
    "perm:inventory:counts:read",
    "perm:inventory:movements:read",
    "perm:inventory:product-policies:read",
    "perm:inventory:stock_evolution:read",
    "perm:inventory:valuation:read",
    "perm:operational-context:all:read",
    "perm:party-identity:global_business_sectors:read",
    "perm:party-identity:identification_type_rules:read",
    "perm:party-identity:organization_business_sectors:read",
    "perm:party-identity:organization_contact_persons:read",
    "perm:party-identity:organization_contact_profiles:read",
    "perm:party-identity:organization_identities:read",
    "perm:party-identity:person_contact_profiles:read",
    "perm:party-identity:person_identities:create",
    "perm:party-identity:person_identities:read",
    "perm:payment-reference:all:read",
    "perm:product-catalog:all:read",
    "perm:product-inventory-query:inventory_overviews:read",
    "perm:product-inventory-query:inventory_summary:read",
    "perm:product-inventory-query:low_stock_products:read",
    "perm:product-inventory-query:product_overviews:read",
    "perm:product-inventory-query:stock:read",
    "perm:purchase:purchase_details:create",
    "perm:purchase:purchase_details:delete",
    "perm:purchase:purchase_details:read",
    "perm:purchase:purchase_details:update",
    "perm:purchase:purchase_lifecycle_events:create",
    "perm:purchase:purchase_lifecycle_events:delete",
    "perm:purchase:purchase_lifecycle_events:read",
    "perm:purchase:purchase_lifecycle_events:update",
    "perm:purchase:purchase_operations:create",
    "perm:purchase:purchase_operations:delete",
    "perm:purchase:purchase_operations:read",
    "perm:purchase:purchase_operations:update",
    "perm:purchase:purchase_sequences:create",
    "perm:purchase:purchase_sequences:delete",
    "perm:purchase:purchase_sequences:read",
    "perm:purchase:purchase_sequences:update",
    "perm:purchase:purchases:create",
    "perm:purchase:purchases:delete",
    "perm:purchase:purchases:read",
    "perm:purchase:purchases:update",
    "perm:sales:all:create",
    "perm:sales:all:delete",
    "perm:sales:all:read",
    "perm:sales:all:update",
})

SOLO_SUPERADMIN = (
    "perm:operational-context:platform:administer",
    "perm:operational-context:platform:lookup",
    "perm:commercial-relationship:platform:lookup",
    "perm:commercial-relationship:automatic_price_update_requests:submit",
    "perm:inventory:platform:lookup",
    "perm:inventory:entries:create",
    "perm:inventory:outputs:create",
    "perm:audit:audit-events:create",
    "perm:audit:platform-events:read",
    "perm:product-catalog:first-use:register",
)
GLOBAL_SERVICES = ("product-catalog", "geography", "payment-reference", "payment_reference", "party-identity")
PARTY_EDITABLE = (
    "person_identities",
    "organization_identities",
    "person_contact_profiles",
    "organization_contact_profiles",
    "organization_contact_persons",
)


def perm(text: str) -> SioPermission:
    _, service, resource, action = text.split(":")
    return SioPermission(service, resource, action)


def covers(group: str, permission: str) -> bool:
    """`operario` es la suma de las tres áreas (un usuario en `Compras`, `Ventas` e `Inventario`)."""
    roles = sorted(OPERARIO) if group == "operario" else GROUPS[group]
    return evaluate_permission(roles, perm(permission))


def catalog_perms(service: str, actions: set[str]) -> list[str]:
    return [
        name for name in CATALOG
        if name.startswith(f"perm:{service}:") and name.split(":")[2] != "all" and name.split(":")[3] in actions
    ]


# --- Estructura (FR-001 a FR-008) ------------------------------------------------------------------

GROUP_IDS = {
    "superadmin": "753f037b-7d06-4309-9166-1c6a4bc4ef04",
    "admin": "f08f068d-4001-468e-9246-8c6e47f5d630",
    "Compras": "f3c2df7b-c966-4c33-b824-6795b4a09a84",
    "Ventas": "d0ef048f-0161-4512-b4b8-91bbe585921e",
    "Inventario": "bb1fd9e5-ef48-4c1d-926c-a112758075bb",
}

USERS = {
    "admin.sio": ("13fb7acf-dac0-4fba-ae39-6759c77c3f97", ["/superadmin", "/admin", "/Compras", "/Ventas", "/Inventario"]),
    "admin.dao": ("c623059e-c281-4bfb-b8ad-e648f6daa104", ["/admin", "/Compras", "/Ventas", "/Inventario"]),
    "operario.dao": ("7a34c410-ce85-47d9-b897-8acb56e31449", ["/Compras", "/Ventas", "/Inventario"]),
    "alex": ("66730e09-9adf-4a5a-ad8e-f452f7af19fc", ["/Compras", "/Inventario", "/Ventas", "/admin", "/superadmin"]),
    "manuel": ("84a400d4-654f-4ebc-9d81-3dd4d1a567a5", ["/Compras", "/Inventario", "/Ventas", "/admin"]),
    "pedro": ("9ddeeeba-7e34-41e4-a960-5b6ef10fff25", ["/Compras", "/Inventario", "/Ventas", "/admin"]),
    "tomas": ("b1dd207f-361b-492c-9466-37e892e29a5e", ["/Compras", "/Inventario", "/Ventas"]),
}


def test_exactamente_cinco_grupos_con_ids_del_servidor() -> None:
    assert {group["name"]: group.get("id") for group in DATA["groups"]} == GROUP_IDS


@pytest.mark.parametrize(
    ("group", "expected"),
    [
        ("superadmin", SUPERADMIN),
        ("admin", ADMIN),
        ("Compras", COMPRAS),
        ("Ventas", VENTAS),
        ("Inventario", INVENTARIO),
    ],
)
def test_roles_exactos_del_contrato(group, expected) -> None:
    assert len(GROUPS[group]) == len(set(GROUPS[group])), "roles repetidos"
    assert set(GROUPS[group]) == expected


def test_las_tres_areas_juntas_son_el_antiguo_empleado() -> None:
    assert OPERARIO == EMPLEADO_ANTERIOR - {"empleado"}


def test_las_areas_no_traen_rol_de_nombre() -> None:
    for area in (COMPRAS, VENTAS, INVENTARIO):
        assert all(role.startswith("perm:") for role in area)


def test_todos_los_roles_existen_en_el_catalogo() -> None:
    for group, roles in GROUPS.items():
        assert set(roles) <= set(CATALOG), group


def test_catalogo_sin_cambios() -> None:
    assert len(CATALOG) == 319
    assert {"superadmin", "admin", "empleado"} <= set(CATALOG)


def test_roles_de_perfil_viejos_eliminados() -> None:
    old = {"administrador", "supervisor", "compras", "ventas", "inventario", "reportes", "consulta"}
    assert not old & set(CATALOG)


def test_usuarios_exactos() -> None:
    assert {name: (user["id"], user["groups"]) for name, user in HUMANS.items()} == {
        name: (user_id, groups) for name, (user_id, groups) in USERS.items()
    }


@pytest.mark.parametrize("username", sorted(USERS))
def test_usuarios_sin_roles_propios_y_con_contrasena_de_prueba(username) -> None:
    user = HUMANS[username]
    assert "sio-api" not in user.get("clientRoles", {})
    assert user["credentials"] == [
        {"type": "password", "value": "${KEYCLOAK_TEST_USER_PASSWORD}", "temporary": False}
    ]


def test_mapeadores_de_sio_web_sin_cambios() -> None:
    web = next(client for client in DATA["clients"] if client["clientId"] == "sio-web")
    assert sorted(mapper["name"] for mapper in web["protocolMappers"]) == ["sio-api-audience", "sio-groups-userinfo"]


# --- Admin (Historia 1; FR-005 a FR-008) -----------------------------------------------------------

@pytest.mark.parametrize(
    "permission",
    [
        "perm:sales:sales:read-profitability",
        "perm:sales:sales:delete",
        "perm:purchase:purchase_line_taxes:override",
        "perm:purchase:purchases:delete",
        "perm:commercial-relationship:automatic_price_applications:resolve",
        "perm:commercial-relationship:pricing_policies:delete",
        "perm:commercial-relationship:company_product_purchase_taxes:update",
        "perm:inventory:product-policies:update",
        "perm:inventory:company-policies:update",
        "perm:inventory:adjustments:create",
        "perm:inventory:counts:create",
        "perm:operational-context:application_users:delete",
        "perm:operational-context:user_branches:create",
        "perm:operational-context:companies:update",
        "perm:audit:audit-events:read",
        "perm:product-inventory-query:low_stock_products:read",
        "perm:business-reporting:sales_by_branch:read",
        "perm:product-catalog:first-use:register-manual",
        "perm:product-catalog:global_products:create",
        "perm:product-catalog:brands:update",
        "perm:geography:global_cities:create",
        "perm:payment-reference:global_payment_methods:update",
        "perm:party-identity:person_identities:update",
        "perm:party-identity:global_business_sectors:create",
    ],
)
def test_admin_puede(permission) -> None:
    assert covers("admin", permission)


@pytest.mark.parametrize("permission", SOLO_SUPERADMIN)
def test_admin_no_tiene_permisos_de_plataforma_ni_tecnicos(permission) -> None:
    assert not covers("admin", permission)


@pytest.mark.parametrize("service", GLOBAL_SERVICES)
def test_admin_no_elimina_ni_desactiva_lo_global(service) -> None:
    forbidden = catalog_perms(service, {"delete", "deactivate"})
    assert forbidden or service == "payment_reference"
    assert [name for name in forbidden if covers("admin", name)] == []


# --- Operario = Compras + Ventas + Inventario (Historia 2) --------------------------------------------------------

def test_empleado_conserva_ventas_compras_e_inventario() -> None:
    assert UNION_VENTAS_COMPRAS_INVENTARIO <= OPERARIO
    for permission in UNION_VENTAS_COMPRAS_INVENTARIO:
        if ":all:" not in permission:  # los comodines no son permisos concretos; ya están en el grupo
            assert covers("operario", permission), permission


@pytest.mark.parametrize("resource", PARTY_EDITABLE)
@pytest.mark.parametrize("action", ["create", "read", "update"])
def test_empleado_crea_lee_y_edita_personas(resource, action) -> None:
    assert covers("operario", f"perm:party-identity:{resource}:{action}")


def test_empleado_nunca_elimina_ni_desactiva_en_party_identity() -> None:
    assert [name for name in catalog_perms("party-identity", {"delete"}) if covers("operario", name)] == []


@pytest.mark.parametrize(
    "permission",
    [
        "perm:sales:sales:read-profitability",
        "perm:operational-context:application_users:create",
        "perm:operational-context:application_users:update",
        "perm:operational-context:application_users:delete",
        "perm:operational-context:user_branches:create",
        "perm:operational-context:companies:update",
        "perm:product-catalog:global_products:create",
        "perm:product-catalog:brands:update",
        "perm:geography:global_cities:create",
        "perm:payment-reference:global_payment_methods:update",
        "perm:party-identity:global_business_sectors:create",
        "perm:party-identity:organization_legal_representatives:create",
        "perm:inventory:product-policies:update",
        "perm:purchase:purchase_line_taxes:override",
        *SOLO_SUPERADMIN,
    ],
)
def test_empleado_no_puede(permission) -> None:
    assert not covers("operario", permission)


@pytest.mark.parametrize(
    "permission",
    [
        "perm:operational-context:application_users:read",
        "perm:operational-context:companies:read",
        "perm:product-catalog:global_products:read",
        "perm:geography:global_cities:read",
        "perm:party-identity:organization_legal_representatives:read",
        "perm:inventory:product-policies:read",
        "perm:product-inventory-query:low_stock_products:read",
    ],
)
def test_empleado_consulta(permission) -> None:
    assert covers("operario", permission)


# --- SuperAdmin (Historia 3; FR-004) ---------------------------------------------------------------

@pytest.mark.parametrize(
    "permission",
    [
        *SOLO_SUPERADMIN,
        "perm:operational-context:companies:create",
        "perm:product-catalog:products:deactivate",
        "perm:party-identity:person_identities:delete",
        "perm:sales:sales:read-profitability",
    ],
)
def test_superadmin_lo_puede_todo(permission) -> None:
    assert covers("superadmin", permission)


# --- Cada área opera solo lo suyo (Historia 2) -------------------------------------------------------

@pytest.mark.parametrize(
    ("area", "puede", "no_puede"),
    [
        ("Ventas", "perm:sales:sales:create", "perm:purchase:purchases:create"),
        ("Compras", "perm:purchase:purchases:create", "perm:inventory:adjustments:create"),
        ("Inventario", "perm:inventory:adjustments:create", "perm:sales:sales:create"),
        ("Inventario", "perm:inventory:counts:create", "perm:purchase:purchases:create"),
    ],
)
def test_cada_area_opera_lo_suyo(area, puede, no_puede) -> None:
    assert covers(area, puede)
    assert not covers(area, no_puede)
