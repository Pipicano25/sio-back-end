"""Pasos del recorrido del MVP como datos (research R-12) y su ejecutor.

Cada `Step` describe una petición: identificador (`C-03.A`, familia `C-03` de
`contracts/e2e-scenarios.md` §2), ejercicio de la guía, ítems de la FASE 10, usuario, permiso, método,
servicio, ruta y cuerpo con marcadores estables (`{empresa_a}`, `{compra_1}`), estado esperado, valores
que se guardan de la respuesta y auditoría esperada. La misma definición la ejecuta la suite contra los
servicios reales y la renderiza la guía `docs/validacion-mvp/`; nada se duplica.

Marcadores: `{nombre}` se reemplaza por la variable de la corrida; un valor que es exactamente
`"{nombre}"` conserva el tipo de la variable (p. ej. `version` entera). `{run}` es el RUN_ID.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from sio_mvp.auth import ApiResponse, Clients
from sio_mvp.journal import ExpectedAudit, Journal
from sio_mvp.run_context import RunContext

MARKER = re.compile(r"\{([a-z0-9_]+)\}")
COMPANY, PLATFORM = "COMPANY", "PLATFORM"
CR_ACTOR = "service-account-commercial-relationship-service"

# Variables con datos protegidos (FR-013): nunca se escriben en informes ni en world.json.
PROTECTED_PREFIXES = ("nit_", "cc_")


class StepFailed(AssertionError):
    pass


@dataclass(frozen=True)
class AuditSpec:
    service: str
    action: str
    entity_type: str
    entity: str  # marcador del id de la entidad
    scope: str = COMPANY
    company: str | None = "{empresa_a}"
    actor: str | None = None  # por defecto, el usuario del paso
    correlated: bool = False  # se localiza también por correlation_id
    result: str = "SUCCESS"


@dataclass(frozen=True)
class Step:
    id: str
    title: str
    exercise: str
    items: tuple[int, ...]
    user: str
    permission: str
    service: str
    method: str
    path: str
    expect: int
    body: Any = None
    params: Mapping[str, Any] | None = None
    save: Mapping[str, str] = field(default_factory=dict)
    audit: tuple[AuditSpec, ...] = ()
    idempotent: bool = False  # Idempotency-Key y X-Correlation-Id
    why: str = ""
    expected_note: str = ""
    root: bool = False

    @property
    def family(self) -> str:
        return self.id.split(".")[0]


# --- marcadores ---------------------------------------------------------------------------------
def resolve(value: Any, variables: Mapping[str, Any]) -> Any:
    if isinstance(value, str):
        whole = MARKER.fullmatch(value)
        if whole:
            return variables[whole.group(1)]
        return MARKER.sub(lambda match: str(variables[match.group(1)]), value)
    if isinstance(value, dict):
        return {key: resolve(item, variables) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [resolve(item, variables) for item in value]
    return value


def extract(body: Any, path: str) -> Any:
    """Ruta simple sobre la respuesta: `id`, `item.id`, `lines.0.id`, `items[code=UND].id`."""
    current = body
    for segment in path.split("."):
        match = re.fullmatch(r"([a-z_]+)\[([a-z_]+)=([^\]]+)\]", segment)
        if match:
            name, key, wanted = match.groups()
            current = next(item for item in current[name] if str(item.get(key)) == wanted)
        elif segment.isdigit():
            current = current[int(segment)]
        else:
            current = current[segment]
    return current


def is_protected(name: str) -> bool:
    return name.startswith(PROTECTED_PREFIXES)


# --- catálogo de pasos ---------------------------------------------------------------------------
def _pi(perm: str) -> str:
    return f"perm:party-identity:{perm}"


def _oc(perm: str) -> str:
    return f"perm:operational-context:{perm}"


def _cr(perm: str) -> str:
    return f"perm:commercial-relationship:{perm}"


def _pc(perm: str) -> str:
    return f"perm:product-catalog:{perm}"


EX1 = "1-configuracion"
EX2 = "2-relacion-comercial-y-precios"
EX3 = "3-compras-e-inventario"
EX4 = "4-ventas"
EX5 = "5-anulaciones"
EX6 = "6-auditoria"
EX7 = "7-seguridad"

EXERCISES = {
    EX1: "Configuración de la empresa: organizaciones, personas, empresas, sucursales y usuarios operativos",
    EX2: "Relación comercial y precios: proveedor, cliente, productos, adopción, presentaciones y listas",
    EX3: "Compras e inventario: secuencias, compras, confirmación, entradas, saldos, kardex y capas",
    EX4: "Ventas con precio por presentación (lista indicada y predeterminada), rechazos, costo FIFO y margen",
    EX5: "Anulaciones y reversos",
    EX6: "Auditoría del recorrido",
    EX7: "Seguridad entre empresas y permisos",
}

# Usuarios operativos por empresa (P-02): (variable, usuario, empresa, sucursal o None).
OPERATIONAL_USERS = (
    ("admin", "admin.test", "a", "a1"),
    ("compras", "compras.test", "a", "a1"),
    ("ventas", "ventas.test", "a", "a1"),
    ("supervisor", "supervisor.test", "a", "a1"),
    ("consulta", "consulta.test", "a", None),
    ("reportes", "reportes.test", "b", None),
    ("inventario", "inventario.test", "b", "b1"),
)
PERSONS = ("cliente",) + tuple(name for name, *_ in OPERATIONAL_USERS)
ORGANIZATIONS = (("empresa_a", "EMPRESA A"), ("empresa_b", "EMPRESA B"), ("proveedor", "PROVEEDOR"))


def reference_steps() -> list[Step]:
    return [
        Step(
            "C-00.1", "Consultar el país Colombia en Geography", EX1, (1,), "admin.test",
            "perm:geography:global_countries:read", "geography", "GET", "/global-countries", 200,
            params={"iso3_code": "COL"}, save={"pais_co": "items.0.id"},
            why="Las identidades, empresas y sucursales guardan solo el id del país de Geography.",
        ),
        Step(
            "C-00.2", "Consultar una ciudad de Colombia en Geography", EX1, (2,), "admin.test",
            "perm:geography:global_cities:read", "geography", "GET", "/global-cities", 200,
            params={"country_id": "{pais_co}", "search": "Bogot"},
            save={"ciudad": "items.0.id", "departamento": "items.0.administrative_division_id"},
            why="La sucursal se ubica en una ciudad del seed de Geography (ubicación coherente país–departamento–ciudad).",
        ),
        Step(
            "C-00.3", "Consultar la regla de identificación NIT de Colombia", EX1, (1,), "admin.test",
            _pi("identification_type_rules:read"), "party-identity", "GET", "/identification-type-rules", 200,
            params={"party_kind": "ORGANIZATION", "country_id": "{pais_co}", "sigla": "NIT", "is_active": "true"},
            save={"patron_nit": "items.0.number_pattern"},
            why="Los NIT ficticios se generan con el patrón de la regla vigente (nunca identificaciones reales).",
        ),
        Step(
            "C-00.4", "Consultar la regla de identificación CC de Colombia", EX1, (3, 5), "admin.test",
            _pi("identification_type_rules:read"), "party-identity", "GET", "/identification-type-rules", 200,
            params={"party_kind": "PERSON", "country_id": "{pais_co}", "sigla": "CC", "is_active": "true"},
            save={"patron_cc": "items.0.number_pattern"},
        ),
        Step(
            "C-00.5", "Consultar la unidad de medida UND en Product Catalog", EX2, (6,), "admin.test",
            _pc("units-of-measure:read"), "product-catalog", "GET", "/units-of-measure", 200,
            params={"status": "ACTIVE", "page_size": 100}, save={"unidad_und": "items[code=UND].id"},
        ),
        Step(
            "C-00.6", "Consultar el tipo de condición de pago CREDIT en Payment Reference", EX2, (4,), "admin.test",
            "perm:payment-reference:global_payment_condition_types:read", "payment-reference", "GET",
            "/global-payment-condition-types", 200, params={"page_size": 100},
            save={"tipo_credito": "items[code=CREDIT].id"},
        ),
    ]


def identity_steps() -> list[Step]:
    steps = []
    for name, label in ORGANIZATIONS:
        steps.append(
            Step(
                f"C-01.{name}", f"Registrar la organización {label.lower()}", EX1, (1, 4) if name == "proveedor" else (1,),
                "admin.test", _pi("organization_identities:create"), "party-identity", "POST", "/organization-identities", 201,
                body={
                    "country_id": "{pais_co}",
                    "identification_type": "NIT",
                    "identification_number": f"{{nit_{name}}}",
                    "legal_name": f"{label} SIO MVP {{run}} (DATO FICTICIO)",
                },
                save={f"org_{name}": "id"},
                audit=(AuditSpec("party-identity", "CREATE_ORGANIZATION_IDENTITY", "OrganizationIdentity", f"{{org_{name}}}", PLATFORM, None),),
                why="La razón social y el NIT pertenecen a Party Identity; la empresa y el proveedor solo guardan el id.",
            )
        )
    for name in PERSONS:
        steps.append(
            Step(
                f"C-02.{name}", f"Registrar la persona {name}", EX1, (5,) if name == "cliente" else (3,),
                "admin.test", _pi("person_identities:create"), "party-identity", "POST", "/person-identities", 201,
                body={
                    "identification_country_id": "{pais_co}",
                    "identification_type": "CC",
                    "identification_number": f"{{cc_{name}}}",
                    "first_name": f"{name.upper()}MVP{{run}}",
                    "last_name": "DATO FICTICIO DE VALIDACION",
                    "birth_date": "1990-01-01",
                },
                save={f"persona_{name}": "id"},
                audit=(AuditSpec("party-identity", "CREATE_PERSON_IDENTITY", "PersonIdentity", f"{{persona_{name}}}", PLATFORM, None),),
                why="Cada usuario operativo y el cliente persona se vinculan a una persona de Party Identity.",
            )
        )
    return steps


def company_steps() -> list[Step]:
    steps = []
    for letter in ("a", "b"):
        steps.append(
            Step(
                f"C-03.{letter}", f"Registrar la empresa {letter.upper()}", EX1, (1,), "admin.test",
                f"{_oc('companies:create')} + {_oc('platform:administer')}", "operational-context", "POST", "/companies", 201,
                body={"organization_identity_id": f"{{org_empresa_{letter}}}"},
                save={f"empresa_{letter}": "id"},
                audit=(AuditSpec("operational-context", "CREATE_COMPANY", "Company", f"{{empresa_{letter}}}", COMPANY, f"{{empresa_{letter}}}"),),
                why="La moneda por defecto de la empresa es COP; la empresa no guarda NIT ni razón social.",
                expected_note="`default_currency` = `COP`, `status` = `ACTIVE`",
            )
        )
    for letter, branch in (("a", "a1"), ("b", "b1")):
        steps.append(
            Step(
                f"C-04.{branch}", f"Registrar la sucursal {branch.upper()}", EX1, (2,), "admin.test",
                _oc("branches:create"), "operational-context", "POST", f"/companies/{{empresa_{letter}}}/branches", 201,
                body={
                    "code": f"{branch.upper()}{{run}}",
                    "name": f"Sucursal {branch.upper()} {{run}} (dato ficticio)",
                    "country_id": "{pais_co}",
                    "administrative_division_id": "{departamento}",
                    "city_id": "{ciudad}",
                },
                save={f"sucursal_{branch}": "id", f"zona_{branch}": "effective_timezone"},
                audit=(AuditSpec("operational-context", "CREATE_BRANCH", "Branch", f"{{sucursal_{branch}}}", COMPANY, f"{{empresa_{letter}}}"),),
                why="La zona horaria efectiva de la sucursal define la fecha de negocio de compras y ventas.",
            )
        )
    for name, username, letter, _ in OPERATIONAL_USERS:
        steps.append(
            Step(
                f"C-05.{name}", f"Registrar a {username} como usuario operativo de la empresa {letter.upper()}", EX1, (3,),
                "admin.test", _oc("application_users:create"), "operational-context", "POST",
                f"/companies/{{empresa_{letter}}}/application-users", 201,
                body={
                    "username": username,
                    "person_identity_id": f"{{persona_{name}}}",
                    "display_name": f"{username} MVP {{run}} (dato ficticio)",
                },
                save={f"usuario_{name}": "id"},
                audit=(AuditSpec("operational-context", "CREATE_APPLICATION_USER", "ApplicationUser", f"{{usuario_{name}}}", COMPANY, f"{{empresa_{letter}}}"),),
                why="\"Crear usuario\" registra el usuario operativo de una cuenta existente de Keycloak (C-01 de la Spec).",
            )
        )
    for name, username, letter, branch in OPERATIONAL_USERS:
        if branch is None:
            continue
        steps.append(
            Step(
                f"C-06.{name}", f"Asignar a {username} la sucursal {branch.upper()}", EX1, (3,), "admin.test",
                _oc("user_branches:create"), "operational-context", "POST", f"/application-users/{{usuario_{name}}}/user-branches", 201,
                body={"branch_id": f"{{sucursal_{branch}}}"},
                save={f"asignacion_{name}": "id"},
                audit=(AuditSpec("operational-context", "ASSIGN_USER_BRANCH", "UserBranch", f"{{asignacion_{name}}}", COMPANY, f"{{empresa_{letter}}}"),),
            )
        )
    for name, username, letter, _ in OPERATIONAL_USERS:
        if letter != "a":
            continue
        steps.append(
            Step(
                f"C-07.{name}", f"Consultar el contexto operativo de {username}", EX1, (3,), username,
                _oc("application_users:read"), "operational-context", "GET", "/me/operational-context", 200,
                why="Cada usuario de A ve su membresía en A y, si está asignado, la sucursal A1 permitida.",
            )
        )
    return steps


def commercial_steps() -> list[Step]:
    cr = "commercial-relationship"
    pc = "product-catalog"
    steps = [
        Step(
            "C-08.proveedor", "Seleccionar el proveedor de la empresa A", EX2, (4,), "admin.test",
            _cr("company_suppliers:create"), cr, "POST", "/companies/{empresa_a}/company-suppliers", 201,
            body={"organization_identity_id": "{org_proveedor}", "internal_code": "PRV-{run}", "display_name": "Proveedor MVP {run} (dato ficticio)"},
            save={"proveedor": "id"},
            audit=(AuditSpec(cr, "CREATE_COMPANY_SUPPLIER", "CompanySupplier", "{proveedor}"),),
        ),
        Step(
            "C-08.condicion", "Registrar la condición de pago a crédito del proveedor", EX2, (4,), "admin.test",
            _cr("supplier_payment_conditions:create"), cr, "POST", "/companies/{empresa_a}/supplier-payment-conditions", 201,
            body={
                "company_supplier_id": "{proveedor}",
                "payment_condition_type_id": "{tipo_credito}",
                "currency_code": "COP",
                "payment_terms_days": 30,
                "is_default": True,
            },
            save={"condicion_credito": "id"},
            audit=(AuditSpec(cr, "CREATE_SUPPLIER_PAYMENT_CONDITION", "SupplierPaymentCondition", "{condicion_credito}"),),
            why="El tipo CREDIT de Payment Reference exige plazo mayor que 0.",
        ),
        Step(
            "C-09.cliente", "Incorporar el cliente persona de la empresa A", EX2, (5,), "admin.test",
            _cr("company_customers:create"), cr, "POST", "/companies/{empresa_a}/company-customers", 201,
            body={"customer_kind": "PERSON", "person_identity_id": "{persona_cliente}", "internal_code": "CLI-{run}", "display_name": "Cliente MVP {run} (dato ficticio)"},
            save={"cliente": "id"},
            audit=(AuditSpec(cr, "CREATE_COMPANY_CUSTOMER", "CompanyCustomer", "{cliente}"),),
        ),
        Step(
            "C-10.categoria", "Crear la categoría global de los productos", EX2, (6,), "admin.test",
            _pc("categories:create"), pc, "POST", "/categories", 201,
            body={"code": "MVP-{run}", "name": "Categoría MVP {run} (dato ficticio)"},
            save={"categoria": "id"},
            audit=(AuditSpec(pc, "CREATE_CATEGORY", "Category", "{categoria}", PLATFORM, None),),
            why="Un producto necesita una categoría vigente y una presentación activa para ser elegible para adopción.",
        ),
    ]
    for letter, with_box in (("a", True), ("b", False)):
        steps += [
            Step(
                f"C-10.producto_{letter}", f"Crear el producto global {letter.upper()}", EX2, (6,), "admin.test",
                _pc("products:create"), pc, "POST", "/products", 201,
                body={"product_type": "GOOD", "canonical_name": f"Producto {letter.upper()} MVP {{run}} (dato ficticio)", "base_unit_id": "{unidad_und}"},
                save={f"producto_{letter}": "id"},
                audit=(AuditSpec(pc, "CREATE_PRODUCT", "Product", f"{{producto_{letter}}}", PLATFORM, None),),
            ),
            Step(
                f"C-10.categoria_{letter}", f"Clasificar el producto {letter.upper()}", EX2, (6,), "admin.test",
                _pc("products:update"), pc, "POST", f"/products/{{producto_{letter}}}/categories", 201,
                body={"global_category_id": "{categoria}"},
                save={f"categoria_producto_{letter}": "id"},
                audit=(AuditSpec(pc, "ADD_PRODUCT_CATEGORY", "ProductCategory", f"{{categoria_producto_{letter}}}", PLATFORM, None),),
            ),
            Step(
                f"C-10.base_{letter}", f"Crear la presentación base (unidad) del producto {letter.upper()}", EX2, (7,), "admin.test",
                _pc("products:update"), pc, "POST", f"/products/{{producto_{letter}}}/presentations", 201,
                body={"code": f"UND-{letter.upper()}-{{run}}", "name": "Unidad (dato ficticio)", "base_quantity": "1", "display_order": 1, "is_base": True},
                save={f"presentacion_base_{letter}": "id"},
                audit=(AuditSpec(pc, "CREATE_PRODUCT_PRESENTATION", "ProductPresentation", f"{{presentacion_base_{letter}}}", PLATFORM, None),),
            ),
        ]
        if with_box:
            steps.append(
                Step(
                    "C-10.caja_a", "Crear la presentación \"Caja × 12\" del producto A", EX2, (7,), "admin.test",
                    _pc("products:update"), pc, "POST", "/products/{producto_a}/presentations", 201,
                    body={"code": "CJ12-A-{run}", "name": "Caja x12 (dato ficticio)", "base_quantity": "12", "display_order": 2, "is_base": False},
                    save={"presentacion_caja_a": "id"},
                    audit=(AuditSpec(pc, "CREATE_PRODUCT_PRESENTATION", "ProductPresentation", "{presentacion_caja_a}", PLATFORM, None),),
                    why="`base_quantity = 12`: una caja equivale a 12 unidades base (compras y ventas convierten con este factor).",
                )
            )
    for letter in ("a", "b"):
        steps.append(
            Step(
                f"C-11.producto_{letter}", f"Adoptar el producto {letter.upper()} en la empresa A", EX2, (6, 8), "admin.test",
                _cr("company_products:create"), cr, "POST", "/companies/{empresa_a}/company-products", 201,
                body={
                    "global_product_id": f"{{producto_{letter}}}",
                    "internal_code": f"MVP-{letter.upper()}-{{run}}",
                    "display_name": f"Producto {letter.upper()} MVP {{run}} (dato ficticio)",
                    "currency_code": "COP",
                    "inventory_control_enabled": True,
                },
                save={f"producto_empresa_{letter}": "id", f"producto_empresa_{letter}_version": "version"},
                audit=(
                    AuditSpec(cr, "ADOPT_COMPANY_PRODUCT", "CompanyProduct", f"{{producto_empresa_{letter}}}"),
                    AuditSpec(pc, "REGISTER_PRODUCT_FIRST_USE", "Product", f"{{producto_{letter}}}", PLATFORM, None, actor=CR_ACTOR),
                ),
                why="La adopción registra el primer uso del producto global en Product Catalog con la identidad técnica de Commercial Relationship. El producto de la empresa no tiene precio ni costo (spec 019): el precio se registra por presentación en las listas.",
            )
        )
    for letter in ("a", "b"):
        steps.append(
            Step(
                f"C-11.base_{letter}", f"Adoptar la presentación base (unidad) del producto {letter.upper()}", EX2, (7,), "admin.test",
                _cr("company_product_presentations:create"), cr, "POST", "/companies/{empresa_a}/company-product-presentations", 201,
                body={"company_product_id": f"{{producto_empresa_{letter}}}", "global_product_presentation_id": f"{{presentacion_base_{letter}}}", "sku": f"SKU-UND-{letter.upper()}-{{run}}"},
                save={f"presentacion_base_empresa_{letter}": "id"},
                audit=(
                    AuditSpec(cr, "CREATE_COMPANY_PRODUCT_PRESENTATION", "CompanyProductPresentation", f"{{presentacion_base_empresa_{letter}}}"),
                    AuditSpec(pc, "REGISTER_PRODUCT_FIRST_USE", "Product", f"{{producto_{letter}}}", PLATFORM, None, actor=CR_ACTOR),
                ),
                why="Toda venta indica una presentación (spec 019): la unidad base se vende con su presentación de factor 1.",
            )
        )
    steps.append(
        Step(
            "C-11.caja_a", "Adoptar la presentación \"Caja × 12\" del producto A", EX2, (7,), "admin.test",
            _cr("company_product_presentations:create"), cr, "POST", "/companies/{empresa_a}/company-product-presentations", 201,
            body={"company_product_id": "{producto_empresa_a}", "global_product_presentation_id": "{presentacion_caja_a}", "sku": "SKU-CJ12-{run}"},
            save={"presentacion_caja_empresa_a": "id"},
            audit=(
                AuditSpec(cr, "CREATE_COMPANY_PRODUCT_PRESENTATION", "CompanyProductPresentation", "{presentacion_caja_empresa_a}"),
                AuditSpec(pc, "REGISTER_PRODUCT_FIRST_USE", "Product", "{producto_a}", PLATFORM, None, actor=CR_ACTOR),
            ),
            why="La adopción de la presentación registra también su primer uso (la presentación queda bloqueada para cambios materiales).",
        )
    )
    for name, code, default in (("general", "GENERAL", True), ("mayorista", "MAYORISTA", False)):
        steps.append(
            Step(
                f"C-12.lista_{name}", f"Crear la lista de precios {code}", EX2, (8,), "admin.test",
                _cr("price_lists:create"), cr, "POST", "/companies/{empresa_a}/price-lists", 201,
                body={"code": f"{code}-{{run}}", "name": f"Lista {code} MVP {{run}} (dato ficticio)", "currency_code": "COP", "is_default": default},
                save={f"lista_{name}": "id"},
                audit=(AuditSpec(cr, "CREATE_PRICE_LIST", "PriceList", f"{{lista_{name}}}"),),
                why="GENERAL es la predeterminada: se aplica cuando la venta no indica lista." if default else "MAYORISTA solo se aplica si la línea la indica.",
            )
        )
    steps += [
        Step(
            "C-12.item_general", "Precio de la unidad del producto A en GENERAL", EX2, (8,), "admin.test",
            _cr("price_list_items:create"), cr, "POST", "/companies/{empresa_a}/price-list-items", 201,
            body={"price_list_id": "{lista_general}", "company_product_id": "{producto_empresa_a}", "company_product_presentation_id": "{presentacion_base_empresa_a}", "unit_price": "1500.00"},
            save={"item_general": "id", "item_general_version": "version"},
            audit=(AuditSpec(cr, "CREATE_PRICE_LIST_ITEM", "PriceListItem", "{item_general}"),),
            why="Cada presentación vendible tiene su precio explícito (spec 019); no hay precios generales por producto.",
        ),
        Step(
            "C-12.item_b", "Precio de la unidad del producto B en GENERAL", EX2, (8,), "admin.test",
            _cr("price_list_items:create"), cr, "POST", "/companies/{empresa_a}/price-list-items", 201,
            body={"price_list_id": "{lista_general}", "company_product_id": "{producto_empresa_b}", "company_product_presentation_id": "{presentacion_base_empresa_b}", "unit_price": "7000.00"},
            save={"item_b": "id"},
            audit=(AuditSpec(cr, "CREATE_PRICE_LIST_ITEM", "PriceListItem", "{item_b}"),),
        ),
        Step(
            "C-12.item_mayorista", "Precio de la caja del producto A en MAYORISTA", EX2, (8,), "admin.test",
            _cr("price_list_items:create"), cr, "POST", "/companies/{empresa_a}/price-list-items", 201,
            body={"price_list_id": "{lista_mayorista}", "company_product_id": "{producto_empresa_a}", "company_product_presentation_id": "{presentacion_caja_empresa_a}", "unit_price": "16000.00"},
            save={"item_mayorista": "id"},
            audit=(AuditSpec(cr, "CREATE_PRICE_LIST_ITEM", "PriceListItem", "{item_mayorista}"),),
        ),
        Step(
            "C-13.compras", "Crear la secuencia de numeración de compras", EX3, (10,), "admin.test",
            "perm:purchase:purchase_sequences:create", "purchase", "POST", "/companies/{empresa_a}/purchase-sequences", 201,
            body={"series_code": "MVP", "prefix": "CP", "separator": "-", "initial_number": 1, "number_length": 6, "reset_policy": "NEVER"},
            save={"secuencia_compras": "id"},
            audit=(AuditSpec("purchase", "CREATE_PURCHASE_SEQUENCE", "PurchaseSequence", "{secuencia_compras}"),),
            why="La compra recibe su número oficial al confirmarse.",
        ),
        Step(
            "C-13.ventas", "Crear la secuencia de numeración de ventas", EX3, (15,), "admin.test",
            "perm:sales:sale_sequences:create", "sales", "POST", "/companies/{empresa_a}/sale-sequences", 201,
            body={"series_code": "MVP", "prefix": "FV", "separator": "-", "initial_number": 1, "number_length": 6, "reset_policy": "NEVER"},
            save={"secuencia_ventas": "id"},
            audit=(AuditSpec("sales", "CREATE_SALE_SEQUENCE", "SaleSequence", "{secuencia_ventas}"),),
        ),
    ]
    return steps


CONFIGURATION = reference_steps() + identity_steps() + company_steps() + commercial_steps()

# --- compras (data-model §3.2) -------------------------------------------------------------------
PURCHASE_LINES = {
    "1": [
        {"company_product_id": "{producto_empresa_a}", "company_product_presentation_id": "{presentacion_caja_empresa_a}", "quantity": "2", "unit_cost": "12000"},
        {"company_product_id": "{producto_empresa_b}", "quantity": "10", "unit_cost": "5000"},
    ],
    "2": [{"company_product_id": "{producto_empresa_a}", "quantity": "26", "unit_cost": "1200"}],
    "3": [{"company_product_id": "{producto_empresa_a}", "quantity": "5", "unit_cost": "1300"}],
    "4": [{"company_product_id": "{producto_empresa_a}", "quantity": "1", "unit_cost": "1000"}],
}


def purchase_create(number: str) -> Step:
    return Step(
        f"P-01.P{number}", f"Registrar la compra P{number} en borrador", EX3, (9,), "compras.test",
        "perm:purchase:purchases:create + perm:purchase:purchase_details:create", "purchase", "POST",
        "/companies/{empresa_a}/purchases", 201,
        body={
            "branch_id": "{sucursal_a1}",
            "company_supplier_id": "{proveedor}",
            "operation_date": "{fecha_negocio}",
            "supplier_document_number": f"FP{number}-{{run}}",
            "lines": PURCHASE_LINES[number],
        },
        save={f"compra_{number}": "id", f"compra_{number}_version": "version"},
        audit=(AuditSpec("purchase", "CREATE_PURCHASE", "Purchase", f"{{compra_{number}}}"),),
        why="`unit_cost` es por unidad de la línea (caja en P1); Inventory recibe la cantidad y el costo en unidad base.",
    )


def purchase_confirm(number: str) -> Step:
    return Step(
        f"P-02.P{number}", f"Confirmar la compra P{number}", EX3, (10,), "compras.test",
        "perm:purchase:purchases:update", "purchase", "POST", f"/companies/{{empresa_a}}/purchases/{{compra_{number}}}/confirmation", 200,
        body={"version": f"{{compra_{number}_version}}"},
        save={f"compra_{number}_version": "version", f"compra_{number}_numero": "number", f"compra_{number}_operacion": "inventory_operation_id"},
        audit=(
            AuditSpec("purchase", "CONFIRM_PURCHASE", "Purchase", f"{{compra_{number}}}", correlated=True),
            AuditSpec("inventory", "APPLY_INVENTORY_ENTRY", "InventoryOperation", f"{{compra_{number}_operacion}}", correlated=True),
        ),
        idempotent=True,
        why="La confirmación asigna el número oficial y registra la entrada en Inventory una sola vez (Idempotency-Key).",
        expected_note="`status` = `CONFIRMED`, `number` asignado, `inventory_operation_id`",
    )


PURCHASES = [purchase_create(number) for number in ("1", "2", "3", "4")] + [purchase_confirm(number) for number in ("1", "2", "3")]

INVENTORY_READS = [
    Step(
        "P-03.saldo_a", "Consultar el saldo del producto A en A1", EX3, (11, 12), "supervisor.test",
        "perm:inventory:balances:read", "inventory", "GET", "/companies/{empresa_a}/branches/{sucursal_a1}/balances/{producto_empresa_a}", 200,
        expected_note="`quantity` = `55.0000` tras las compras",
    ),
    Step(
        "P-03.saldo_b", "Consultar el saldo del producto B en A1", EX3, (11, 12), "supervisor.test",
        "perm:inventory:balances:read", "inventory", "GET", "/companies/{empresa_a}/branches/{sucursal_a1}/balances/{producto_empresa_b}", 200,
        expected_note="`quantity` = `10.0000`",
    ),
    Step(
        "P-03.kardex_a", "Consultar el kardex del producto A", EX3, (11, 18), "supervisor.test",
        "perm:inventory:movements:read", "inventory", "GET", "/companies/{empresa_a}/branches/{sucursal_a1}/kardex/{producto_empresa_a}", 200,
        params={"page_size": 100},
    ),
    Step(
        "P-03.capas_a", "Consultar las capas FIFO del producto A", EX3, (11, 12), "supervisor.test",
        "perm:inventory:valuation:read", "inventory", "GET", "/companies/{empresa_a}/branches/{sucursal_a1}/valuation/{producto_empresa_a}/layers", 200,
        params={"include_closed": "true"},
    ),
    Step(
        "P-03.capas_b", "Consultar las capas FIFO del producto B", EX3, (11, 12), "supervisor.test",
        "perm:inventory:valuation:read", "inventory", "GET", "/companies/{empresa_a}/branches/{sucursal_a1}/valuation/{producto_empresa_b}/layers", 200,
        params={"include_closed": "true"},
    ),
]

# --- ventas (data-model §3.3) --------------------------------------------------------------------
SALE_LINES = {
    "1": [{"company_product_id": "{producto_empresa_a}", "company_product_presentation_id": "{presentacion_caja_empresa_a}", "price_list_id": "{lista_mayorista}", "quantity": "1"}],
    "2": [{"company_product_id": "{producto_empresa_a}", "company_product_presentation_id": "{presentacion_base_empresa_a}", "quantity": "20"}],
    "3": [{"company_product_id": "{producto_empresa_b}", "company_product_presentation_id": "{presentacion_base_empresa_b}", "quantity": "4"}],
    "4": [{"company_product_id": "{producto_empresa_a}", "company_product_presentation_id": "{presentacion_base_empresa_a}", "quantity": "100"}],
    "5": [{"company_product_id": "{producto_empresa_a}", "company_product_presentation_id": "{presentacion_base_empresa_a}", "quantity": "1"}],
    "6": [{"company_product_id": "{producto_empresa_a}", "company_product_presentation_id": "{presentacion_base_empresa_a}", "quantity": "1"}],
    "7": [{"company_product_id": "{producto_empresa_b}", "company_product_presentation_id": "{presentacion_base_empresa_b}", "quantity": "1"}],
}
SALE_PRICE_NOTES = {
    "1": "Lista indicada MAYORISTA: precio de la caja 16 000",
    "2": "Sin lista: se aplica la predeterminada GENERAL, 1 500 la unidad",
    "3": "Producto B: precio de su unidad en la lista predeterminada GENERAL, 7 000",
    "4": "100 unidades (más de las existentes)",
    "5": "Lista predeterminada; su precio cambiará antes de confirmar",
    "6": "Borrador que se anulará",
    "7": "Producto B; se inactivará antes de confirmar",
}


def sale_create(number: str) -> Step:
    return Step(
        f"V-01.V{number}", f"Registrar la venta V{number} en borrador", EX4, (13,), "ventas.test",
        "perm:sales:sales:create + perm:sales:sale_details:create", "sales", "POST", "/companies/{empresa_a}/sales", 201,
        body={"branch_id": "{sucursal_a1}", "company_customer_id": "{cliente}", "lines": SALE_LINES[number]},
        save={f"venta_{number}": "id", f"venta_{number}_version": "version"},
        audit=(AuditSpec("sales", "CREATE_SALE", "Sale", f"{{venta_{number}}}"),),
        why=SALE_PRICE_NOTES[number],
    )


def sale_confirm(number: str, expect: int = 200, items: tuple[int, ...] = (15,), family: str = "V-03") -> Step:
    confirmed = expect == 200
    return Step(
        f"{family}.V{number}",
        f"Confirmar la venta V{number}" + ("" if confirmed else " (rechazada)"), EX4, items, "ventas.test",
        "perm:sales:sales:update", "sales", "POST", f"/companies/{{empresa_a}}/sales/{{venta_{number}}}/confirmation", expect,
        body={"version": f"{{venta_{number}_version}}"},
        save={f"venta_{number}_version": "version", f"venta_{number}_numero": "number", f"venta_{number}_operacion": "inventory_operation_id"} if confirmed else {},
        audit=(
            AuditSpec("sales", "CONFIRM_SALE", "Sale", f"{{venta_{number}}}", correlated=True),
            AuditSpec("inventory", "APPLY_INVENTORY_OUTPUT", "InventoryOperation", f"{{venta_{number}_operacion}}", correlated=True),
        ) if confirmed else (),
        idempotent=True,
    )


SALES_DRAFTS = [sale_create(number) for number in ("1", "2", "3", "4", "5", "6", "7")]
SALES_CONFIRMATIONS = [sale_confirm(number) for number in ("1", "2", "3")]
SALE_AVAILABILITY = [
    Step(
        f"V-02.V{number}", f"Consultar la disponibilidad de la venta V{number}", EX4, (14,), "ventas.test",
        "perm:sales:sales:read", "sales", "GET", f"/companies/{{empresa_a}}/sales/{{venta_{number}}}/availability", 200,
        expected_note="`all_available` = `true`" if number == "2" else "`all_available` = `false`",
    )
    for number in ("2", "4")
]
V4_REJECTED = sale_confirm("4", expect=409, items=(14,), family="V-04")
V5_CHANGE_PRICE = Step(
    "V-05.cambio", "Cambiar el precio de la unidad del producto A en GENERAL (1 500 → 1 550)", EX4, (15,), "admin.test",
    _cr("price_list_items:update"), "commercial-relationship", "POST", "/price-list-items/{item_general}/change-price", 201,
    body={"unit_price": "1550.00", "version": "{item_general_version}"},
    save={"item_general_nuevo": "item.id"},
    audit=(AuditSpec("commercial-relationship", "CHANGE_PRICE_LIST_ITEM_PRICE", "PriceListItem", "{item_general_nuevo}"),),
    why="El precio vigente cambia entre el borrador de V5 y su confirmación.",
)
V5_REJECTED = sale_confirm("5", expect=409, items=(15,), family="V-05")
V7_DEACTIVATE = Step(
    "V-05b.inactivar", "Inactivar el producto B de la empresa A", EX4, (15,), "admin.test",
    _cr("company_products:delete"), "commercial-relationship", "POST", "/company-products/{producto_empresa_b}/deactivate", 200,
    body={"version": "{producto_empresa_b_version}"},
    save={"producto_empresa_b_version": "version"},
    audit=(AuditSpec("commercial-relationship", "DEACTIVATE_COMPANY_PRODUCT", "CompanyProduct", "{producto_empresa_b}"),),
)
V7_REJECTED = Step(
    "V-05b.V7", "Confirmar la venta V7 con el producto inactivo (rechazada)", EX4, (15,), "ventas.test",
    "perm:sales:sales:update", "sales", "POST", "/companies/{empresa_a}/sales/{venta_7}/confirmation", 409,
    body={"version": "{venta_7_version}"}, idempotent=True,
)
V7_REACTIVATE = Step(
    "V-05b.reactivar", "Reactivar el producto B de la empresa A", EX4, (15,), "admin.test",
    _cr("company_products:update"), "commercial-relationship", "POST", "/company-products/{producto_empresa_b}/reactivate", 200,
    body={"version": "{producto_empresa_b_version}"},
    save={"producto_empresa_b_version": "version"},
    audit=(AuditSpec("commercial-relationship", "REACTIVATE_COMPANY_PRODUCT", "CompanyProduct", "{producto_empresa_b}"),),
)
SALE_PROFITABILITY = [
    Step(
        "V-06.vendedor", "Consultar la venta V2 como vendedor (sin costo ni margen)", EX4, (16,), "ventas.test",
        "perm:sales:sales:read", "sales", "GET", "/companies/{empresa_a}/sales/{venta_2}", 200,
        expected_note="Sin `unit_cost_snapshot`, `cost_total`, `cost_known`, `gross_margin_amount` ni `gross_margin_percentage`",
    ),
    Step(
        "V-06.supervisor", "Consultar la venta V2 como supervisor (con costo y margen)", EX4, (16,), "supervisor.test",
        "perm:sales:sales:read + perm:sales:sales:read-profitability", "sales", "GET", "/companies/{empresa_a}/sales/{venta_2}", 200,
        expected_note="`cost_total` = `21600.00`, `gross_margin_amount` = `8400.00`",
    ),
]
OUTPUT_READS = [
    Step(
        "V-07.saldo_a", "Saldo del producto A tras las ventas", EX4, (16, 17), "supervisor.test",
        "perm:inventory:balances:read", "inventory", "GET", "/companies/{empresa_a}/branches/{sucursal_a1}/balances/{producto_empresa_a}", 200,
        expected_note="`quantity` = `23.0000`",
    ),
    Step(
        "V-07.saldo_b", "Saldo del producto B tras las ventas", EX4, (16, 17), "supervisor.test",
        "perm:inventory:balances:read", "inventory", "GET", "/companies/{empresa_a}/branches/{sucursal_a1}/balances/{producto_empresa_b}", 200,
        expected_note="`quantity` = `6.0000`",
    ),
    Step(
        "V-07.kardex_a", "Kardex del producto A con las salidas", EX4, (16, 18), "supervisor.test",
        "perm:inventory:movements:read", "inventory", "GET", "/companies/{empresa_a}/branches/{sucursal_a1}/kardex/{producto_empresa_a}", 200,
        params={"page_size": 100},
    ),
    Step(
        "V-07.kardex_b", "Kardex del producto B con la salida", EX4, (16, 18), "supervisor.test",
        "perm:inventory:movements:read", "inventory", "GET", "/companies/{empresa_a}/branches/{sucursal_a1}/kardex/{producto_empresa_b}", 200,
        params={"page_size": 100},
    ),
    Step(
        "V-07.capas_a", "Capas FIFO del producto A tras las ventas", EX4, (16, 17), "supervisor.test",
        "perm:inventory:valuation:read", "inventory", "GET", "/companies/{empresa_a}/branches/{sucursal_a1}/valuation/{producto_empresa_a}/layers", 200,
        params={"include_closed": "true"},
    ),
    Step(
        "V-07.capas_b", "Capas FIFO del producto B tras las ventas", EX4, (16, 17), "supervisor.test",
        "perm:inventory:valuation:read", "inventory", "GET", "/companies/{empresa_a}/branches/{sucursal_a1}/valuation/{producto_empresa_b}/layers", 200,
        params={"include_closed": "true"},
    ),
]


def consumptions_step(name: str) -> Step:
    return Step(
        f"V-07.consumos_{name}", f"Consumos de costo de la salida de {name.upper()}", EX4, (16,), "supervisor.test",
        "perm:inventory:valuation:read", "inventory", "GET", f"/companies/{{empresa_a}}/inventory-movements/{{movimiento_{name}}}/cost-consumptions", 200,
    )


CONSUMPTIONS = [consumptions_step(name) for name in ("v1", "v2", "v3")]

# --- anulaciones (data-model §3.4) ---------------------------------------------------------------
def cancel_step(kind: str, number: str, expect: int = 200, family: str = "A-01") -> Step:
    is_purchase = kind == "compra"
    user = "compras.test" if is_purchase else "ventas.test"
    service = "purchase" if is_purchase else "sales"
    resource = "purchases" if is_purchase else "sales"
    prefix = "P" if is_purchase else "V"
    audit: tuple[AuditSpec, ...] = ()
    if expect == 409 and is_purchase:
        # El rechazo de Inventory con la operación registrada deja CANCEL_PURCHASE con FAILURE (R-13 de la 014).
        audit = (AuditSpec(service, "CANCEL_PURCHASE", "Purchase", f"{{{kind}_{number}}}", correlated=True, result="FAILURE"),)
    if expect == 200:
        audit = (
            AuditSpec(service, "CANCEL_PURCHASE" if is_purchase else "CANCEL_SALE", "Purchase" if is_purchase else "Sale", f"{{{kind}_{number}}}", correlated=True),
        )
    return Step(
        f"{family}.{prefix}{number}", f"Anular la {kind} {prefix}{number}" + ("" if expect == 200 else " (rechazada)"), EX5, (20,), user,
        f"perm:{service}:{resource}:delete", service, "POST", f"/companies/{{empresa_a}}/{resource}/{{{kind}_{number}}}/cancellation", expect,
        body={"version": f"{{{kind}_{number}_version}}", "reason": f"Anulación de validación MVP {{run}} (dato ficticio)"},
        save={f"{kind}_{number}_version": "version"} if expect == 200 else {},
        audit=audit,
        idempotent=True,
    )


CANCELLATIONS = [
    cancel_step("compra", "4"),
    cancel_step("venta", "6"),
    cancel_step("venta", "3"),
    cancel_step("compra", "3"),
]
P1_CANCEL_REJECTED = cancel_step("compra", "1", expect=409, family="A-02")


def reversal_lookup(kind: str, number: str) -> Step:
    is_purchase = kind == "compra"
    service = "purchase" if is_purchase else "sales"
    resource = "purchases" if is_purchase else "sales"
    return Step(
        f"A-01.operaciones_{'P' if is_purchase else 'V'}{number}", f"Consultar las operaciones de la {kind} anulada", EX5, (20,),
        "compras.test" if is_purchase else "ventas.test",
        f"perm:{service}:{'purchase' if is_purchase else 'sale'}_operations:read", service, "GET",
        f"/companies/{{empresa_a}}/{resource}/{{{kind}_{number}}}/operations", 200,
        why="La operación de anulación guarda el id de la operación de reverso de Inventory.",
    )


REVERSAL_LOOKUPS = [reversal_lookup("venta", "3"), reversal_lookup("compra", "3")]
FINAL_READS = [
    Step(
        "A-03.saldo_a", "Saldo final del producto A", EX5, (17, 20), "supervisor.test",
        "perm:inventory:balances:read", "inventory", "GET", "/companies/{empresa_a}/branches/{sucursal_a1}/balances/{producto_empresa_a}", 200,
        expected_note="`quantity` = `18.0000`",
    ),
    Step(
        "A-03.saldo_b", "Saldo final del producto B", EX5, (17, 20), "supervisor.test",
        "perm:inventory:balances:read", "inventory", "GET", "/companies/{empresa_a}/branches/{sucursal_a1}/balances/{producto_empresa_b}", 200,
        expected_note="`quantity` = `10.0000`",
    ),
    Step(
        "A-03.kardex_a", "Kardex final del producto A", EX5, (18, 20), "supervisor.test",
        "perm:inventory:movements:read", "inventory", "GET", "/companies/{empresa_a}/branches/{sucursal_a1}/kardex/{producto_empresa_a}", 200,
        params={"page_size": 100},
    ),
    Step(
        "A-03.kardex_b", "Kardex final del producto B", EX5, (18, 20), "supervisor.test",
        "perm:inventory:movements:read", "inventory", "GET", "/companies/{empresa_a}/branches/{sucursal_a1}/kardex/{producto_empresa_b}", 200,
        params={"page_size": 100},
    ),
    Step(
        "A-03.capas_a", "Capas finales del producto A", EX5, (17, 20), "supervisor.test",
        "perm:inventory:valuation:read", "inventory", "GET", "/companies/{empresa_a}/branches/{sucursal_a1}/valuation/{producto_empresa_a}/layers", 200,
        params={"include_closed": "true"},
    ),
    Step(
        "A-03.capas_b", "Capas finales del producto B", EX5, (17, 20), "supervisor.test",
        "perm:inventory:valuation:read", "inventory", "GET", "/companies/{empresa_a}/branches/{sucursal_a1}/valuation/{producto_empresa_b}/layers", 200,
        params={"include_closed": "true"},
    ),
    Step(
        "A-03.valoracion", "Valoración final de la sucursal A1", EX5, (17, 20), "supervisor.test",
        "perm:inventory:valuation:read", "inventory", "GET", "/companies/{empresa_a}/branches/{sucursal_a1}/valuation", 200,
        params={"page_size": 100},
    ),
]

# --- auditoría (U-01, U-02) ----------------------------------------------------------------------
AUDIT_STEPS = [
    Step(
        "U-01.empresa", "Historial de auditoría de una entidad de la empresa A", EX6, (19,), "admin.test",
        "perm:audit:audit-events:read", "audit", "GET", "/companies/{empresa_a}/entity-history/{tipo_entidad}/{id_entidad}", 200,
        why="Cada acción esperada aparece exactamente una vez, con su autor y en orden por `occurred_at`.",
    ),
    Step(
        "U-01.plataforma", "Historial de auditoría de una entidad de plataforma", EX6, (19,), "admin.test",
        "perm:audit:platform-events:read", "audit", "GET", "/platform-entity-history/{tipo_entidad}/{id_entidad}", 200,
        why="Identidades y productos globales generan eventos de plataforma (sin empresa).",
    ),
    Step(
        "U-02.vendedor", "Consultar la auditoría como vendedor (rechazado)", EX6, (19,), "ventas.test",
        "perm:audit:audit-events:read", "audit", "GET", "/companies/{empresa_a}/audit-events", 403,
        why="`ventas.test` no tiene permiso de lectura de auditoría.",
    ),
]

RECORRIDO = (
    CONFIGURATION
    + PURCHASES
    + INVENTORY_READS
    + SALES_DRAFTS
    + SALE_AVAILABILITY
    + SALES_CONFIRMATIONS
    + [V4_REJECTED, V5_CHANGE_PRICE, V5_REJECTED, V7_DEACTIVATE, V7_REJECTED, V7_REACTIVATE]
    + SALE_PROFITABILITY
    + OUTPUT_READS
    + CONSUMPTIONS
    + CANCELLATIONS
    + REVERSAL_LOOKUPS
    + [P1_CANCEL_REJECTED]
    + FINAL_READS
    + AUDIT_STEPS
)


def by_id(steps: list[Step] | None = None) -> dict[str, Step]:
    catalogue: dict[str, Step] = {}
    for step in steps or all_steps():
        if step.id in catalogue:
            raise ValueError(f"Paso duplicado: {step.id}")
        catalogue[step.id] = step
    return catalogue


def all_steps() -> list[Step]:
    from scenario import security  # pasos de la etapa seguridad (T043, T044)

    return list(RECORRIDO) + list(security.SECURITY_STEPS)


# --- ejecutor ------------------------------------------------------------------------------------
class Runner:
    """Ejecuta pasos contra los servicios reales y registra resultados y auditoría esperada."""

    def __init__(self, clients: Clients, context: RunContext, journal: Journal, variables: dict[str, Any]) -> None:
        self.clients = clients
        self.context = context
        self.journal = journal
        self.vars = variables
        self.vars.setdefault("run", context.run_id)
        self.responses: dict[str, ApiResponse] = {}

    def resolved(self, step: Step, overrides: Mapping[str, Any] | None = None) -> tuple[str, Any, Any]:
        variables = {**self.vars, **(overrides or {})}
        return resolve(step.path, variables), resolve(copy.deepcopy(step.body), variables), resolve(dict(step.params or {}), variables) or None

    def run(
        self,
        step: Step,
        *,
        expect: int | set[int] | None = None,
        attempt: int = 1,
        overrides: Mapping[str, Any] | None = None,
        user: str | None = None,
        idempotency_key: str | None = None,
        record_audit: bool = True,
    ) -> ApiResponse:
        path, body, params = self.resolved(step, overrides)
        client = self.client_for(user or step.user)
        key = correlation = None
        if step.idempotent:
            key = idempotency_key or self.context.idempotency_key(step.id, attempt)
            correlation = self.context.correlation_id(step.id)
        response = client.request(
            step.method,
            step.service,
            path,
            step_id=step.id,
            json_body=body,
            params=params,
            idempotency_key=key,
            correlation_id=correlation,
            path_template=step.path,
            root=step.root,
        )
        self.responses[step.id] = response
        allowed = {step.expect} if expect is None else ({expect} if isinstance(expect, int) else set(expect))
        if response.status not in allowed:
            raise StepFailed(
                f"{step.id} ({step.title}): se esperaba {sorted(allowed)} y se obtuvo {response.status}: "
                + self.journal.safe_text(response.body)
            )
        if response.status == step.expect:
            for name, source in step.save.items():
                value = extract(response.body, source)
                self.vars[name] = value
                if not is_protected(name) and isinstance(value, str) and len(value) == 36:
                    self.journal.created(step.id, name, value)
            if record_audit:
                for spec in step.audit:
                    self.expect_audit(step, spec, correlation)
        return response

    def client_for(self, identity: str):
        if identity == "sin-token":
            return self.clients.anonymous()
        if identity == "token-invalido":
            return self.clients.invalid_token()
        if identity.startswith("service-account-"):
            client_id = identity[len("service-account-") :]
            return self.clients.service_account(client_id, client_id.upper().replace("-", "_") + "_CLIENT_SECRET")
        return self.clients.user(identity)

    def expect_audit(self, step: Step, spec: AuditSpec, correlation: str | None) -> None:
        self.journal.expect_audit(
            ExpectedAudit(
                step_id=step.id,
                service=spec.service,
                action=spec.action,
                entity_type=spec.entity_type,
                entity_id=str(resolve(spec.entity, self.vars)),
                scope=spec.scope,
                company_id=str(resolve(spec.company, self.vars)) if spec.company else None,
                actor=spec.actor or step.user,
                correlation_id=correlation if spec.correlated else None,
                result=spec.result,
            )
        )
