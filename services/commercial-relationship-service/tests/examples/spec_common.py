"""Constructores y datos comunes de los ejercicios de docs/ejemplo/ (Principio XXII).

Cada ejercicio es una lista de pasos y cada paso una lista de llamadas. La prueba
`test_examples.py` las ejecuta contra la API y `render.py` genera la documentación.

Las llamadas a Operational Context, Product Catalog, Party Identity y Payment Reference (clase C) no se
ejecutan: son **externas** y sus resultados se simulan con los UUID ficticios de este
módulo, que la prueba registra en los dobles de los puertos (Principio IV).
"""

from __future__ import annotations

API = "/api/v1"
OPERATIONAL_CONTEXT = "http://localhost:8004/api/v1"
PRODUCT_CATALOG = "http://localhost:8003/api/v1"
PARTY_IDENTITY = "http://localhost:8002/api/v1"

# ---- Empresas ficticias (Operational Context) y su organización en Party Identity ----
EMPRESA_EJ1 = "c0a1c0a1-0000-4000-8000-000000000e01"
EMPRESA_EJ2 = "c0a1c0a1-0000-4000-8000-000000000e02"
EMPRESA_EJ3 = "c0a1c0a1-0000-4000-8000-000000000e03"
ORG_EMPRESA_EJ1 = "7a1c0f10-0000-4000-8000-0000000c0e01"
ORG_EMPRESA_EJ2 = "7a1c0f10-0000-4000-8000-0000000c0e02"
ORG_EMPRESA_EJ3 = "7a1c0f10-0000-4000-8000-0000000c0e03"
COMPANIES = {EMPRESA_EJ1: ORG_EMPRESA_EJ1, EMPRESA_EJ2: ORG_EMPRESA_EJ2, EMPRESA_EJ3: ORG_EMPRESA_EJ3}
# Razón social ficticia de cada organización de empresa (resumen de empresas, FR-046)
COMPANY_NAMES = {
    ORG_EMPRESA_EJ1: "DROGUERÍA EJEMPLO FICTICIA S.A.S.",
    ORG_EMPRESA_EJ2: "COMERCIALIZADORA CLIENTES FICTICIA S.A.S.",
    ORG_EMPRESA_EJ3: "DISTRIBUIDORA PROVEEDORES FICTICIA S.A.S.",
}

# ---- Productos globales (Product Catalog) de las filas reales del Excel ----
GP_ACETAMINOFEN = "9a9a9a9a-0000-4000-8000-000000000045"   # Código 000045, fila 40
GP_AGUJA = "9a9a9a9a-0000-4000-8000-000000000537"          # Código 000537, fila 413
GP_WINNY = "9a9a9a9a-0000-4000-8000-000000015721"          # Código 015721, fila 11499
GP_CEPILLO = "9a9a9a9a-0000-4000-8000-000000022348"        # Código 022348, fila 16610 (inactivo)
GP_INCOMPLETO = "9a9a9a9a-0000-4000-8000-00000000f1c0"     # ficticio: producto global sin completar
# id -> (status, elegible para adopción)
GLOBAL_PRODUCTS = {
    GP_ACETAMINOFEN: ("ACTIVE", True),
    GP_AGUJA: ("ACTIVE", True),
    GP_WINNY: ("ACTIVE", True),
    GP_CEPILLO: ("INACTIVE", False),
    GP_INCOMPLETO: ("ACTIVE", False),
}

# ---- Identidades ficticias (Party Identity) ----
PER_CLIENTE = "5e5e5e5e-0000-4000-8000-000000000001"
ORG_CLIENTE = "6f6f6f6f-0000-4000-8000-000000000001"
ORG_PROVEEDOR = "6f6f6f6f-0000-4000-8000-000000000002"
ORG_PROVEEDOR_2 = "6f6f6f6f-0000-4000-8000-000000000003"
ORG_OTRA = "6f6f6f6f-0000-4000-8000-000000000009"
CONTACTO_CLIENTE = "4d4d4d4d-0000-4000-8000-000000000001"
CONTACTO_OTRA_ORG = "4d4d4d4d-0000-4000-8000-000000000009"
PERSONS = {PER_CLIENTE: "ACTIVE"}
ORGANIZATIONS = {
    ORG_CLIENTE: "ACTIVE",
    ORG_PROVEEDOR: "ACTIVE",
    ORG_PROVEEDOR_2: "ACTIVE",
    ORG_OTRA: "ACTIVE",
    ORG_EMPRESA_EJ2: "ACTIVE",
}
# contacto -> (organización, activo)
CONTACTS = {CONTACTO_CLIENTE: (ORG_CLIENTE, True), CONTACTO_OTRA_ORG: (ORG_OTRA, True)}


def call(
    title,
    method,
    path,
    body=None,
    why=(),
    save=None,
    expect=None,
    show=None,
    external=None,
    note=None,
    sample=None,
    sample_status=200,
    perm=None,
    fake=None,
    also=(),
):
    """Una llamada a la API.

    - `save`: {"NOMBRE": "ruta.en.respuesta"}; el valor se usa luego como `<NOMBRE>`.
    - `expect`: código HTTP esperado (None = 200 o 201).
    - `show`: claves de la respuesta que se muestran en el documento.
    - `external`: nombre del otro servicio: la llamada no se ejecuta en la validación y
      `fake` indica el valor simulado de cada variable.
    """
    return dict(
        title=title,
        method=method,
        path=path,
        body=body,
        why=list(why),
        save=save or {},
        expect=expect,
        show=show,
        external=external,
        note=note,
        sample=sample,
        sample_status=sample_status,
        perm=perm,
        fake=fake or {},
        also=list(also),
    )


def process(title, name, params=None, why=(), save=None, show=None, note=None):
    """Un proceso automático (no es una llamada del usuario): lo ejecuta la prueba con `processes[name](**params)`.

    Sirve para lo que en un entorno real hacen otros procesos, por ejemplo la entrega de Purchase al registrar una
    recepción física y el `commercial-relationship-price-worker` (spec 021). No exige permisos de usuario.
    """
    return dict(
        title=title, method="PROCESO", path="", body=None, why=list(why), save=save or {}, expect=None, show=show,
        external=None, note=note, sample=None, sample_status=200, perm=None, fake={}, also=[],
        process=name, params=dict(params or {}),
    )


def step(file, title, goal, calls, intro=None, after=None):
    return dict(file=file, title=title, goal=goal, calls=calls, intro=intro, after=after)


def get_company(variable, company_id, legal_name):
    """Consulta la empresa en Operational Context (donde el usuario debe ser miembro)."""
    return call(
        f"Consultar la empresa {legal_name} en Operational Context",
        "GET",
        f"{OPERATIONAL_CONTEXT}/me/operational-context",
        external="Operational Context Service",
        perm="perm:operational-context:application_users:read",
        why=[
            "Commercial Relationship **no guarda** empresas: usa el `company_id` de Operational Context y, en cada "
            "solicitud, le pregunta si el usuario tiene membresía `ACTIVE` en ella (DS-02).",
            "`me/operational-context` lista las empresas donde el usuario es miembro: de ahí se toma el `id`.",
        ],
        save={variable: "memberships[0].company_id"},
        fake={variable: company_id},
        sample={"keycloak_user_id": "<sub del usuario>", "memberships": [{
            "application_user_id": "<id generado>", "company_id": f"<{variable}>",
            "company_status": "ACTIVE", "status": "ACTIVE", "branches": [],
        }]},
    )


def get_global_product(variable, product_id, identifier, name, status="ACTIVE", eligible=True, search=None):
    """Busca el producto global en Product Catalog por su código de barras (o por nombre si no tiene)."""
    path = (
        f"{PRODUCT_CATALOG}/products/by-identifier/{identifier}"
        if search is None
        else f"{PRODUCT_CATALOG}/products?search={search}&status=ALL"
    )
    sample = (
        {"product": {"id": f"<{variable}>", "canonical_name": name, "status": status,
                     "eligible_for_adoption": eligible}, "identifier": identifier, "is_current": True}
        if search is None
        else {"items": [{"id": f"<{variable}>", "canonical_name": name, "status": status,
                         "eligible_for_adoption": eligible}], "page": 1, "page_size": 20,
              "total_records": 1, "total_pages": 1}
    )
    return call(
        f"Consultar el producto global {name} en Product Catalog",
        "GET",
        path,
        external="Product Catalog Service",
        perm="perm:product-catalog:products:read",
        why=[
            "Commercial Relationship **no copia** el nombre canónico, la marca ni la unidad del producto global: "
            "solo guarda su `id` (`global_product_id`, FR-018).",
            "Al adoptar, el servicio vuelve a comprobar en Product Catalog que esté `ACTIVE` y completo, con su "
            "propia identidad técnica.",
        ],
        save={variable: "product.id" if search is None else "items[0].id"},
        fake={variable: product_id},
        sample=sample,
    )


def get_person(variable, person_id, description):
    return call(
        f"Consultar la persona {description} en Party Identity",
        "GET",
        f"{PARTY_IDENTITY}/person-identities?search=<documento>",
        external="Party Identity Service",
        perm="perm:party-identity:person_identities:read",
        why=["Commercial Relationship **no guarda** nombres ni documentos: solo el `id` de la `PersonIdentity` "
             "(Principio III). Si la persona no existe, se registra primero en Party Identity."],
        save={variable: "items[0].id"},
        fake={variable: person_id},
        sample={"items": [{"id": f"<{variable}>", "identification_type": "CC",
                           "identification_number": "<documento oficial; dato ficticio aquí>",
                           "first_name": "<nombre ficticio>", "status": "ACTIVE"}],
                "page": 1, "page_size": 20, "total_records": 1, "total_pages": 1},
    )


def get_organization(variable, organization_id, legal_name):
    return call(
        f"Consultar la organización {legal_name} en Party Identity",
        "GET",
        f"{PARTY_IDENTITY}/organization-identities?search=<NIT>",
        external="Party Identity Service",
        perm="perm:party-identity:organization_identities:read",
        why=["Commercial Relationship **no guarda** la razón social ni el NIT: solo el `id` de la "
             "`OrganizationIdentity` (Principio III). El NIT real se toma de una fuente oficial (RUT, RUES)."],
        save={variable: "items[0].id"},
        fake={variable: organization_id},
        sample={"items": [{"id": f"<{variable}>", "identification_type": "NIT",
                           "identification_number": "<NIT obtenido del RUT; dato ficticio aquí>",
                           "legal_name": legal_name, "status": "ACTIVE"}],
                "page": 1, "page_size": 20, "total_records": 1, "total_pages": 1},
    )


def get_contact(variable, contact_id, organization_variable, description):
    return call(
        f"Consultar la persona de contacto {description} en Party Identity",
        "GET",
        f"{PARTY_IDENTITY}/organization-identities/<{organization_variable}>/contact-persons",
        external="Party Identity Service",
        perm="perm:party-identity:organization_contact_persons:read",
        why=["El contacto preferido debe pertenecer a la misma organización y estar activo; el servicio lo valida "
             "en Party Identity al asignarlo (FR-022)."],
        save={variable: "items[0].id"},
        fake={variable: contact_id},
        sample={"items": [{"id": f"<{variable}>", "organization_identity_id": f"<{organization_variable}>",
                           "is_active": True, "position": "<cargo ficticio>"}],
                "page": 1, "page_size": 20, "total_records": 1, "total_pages": 1},
    )


# --------------------------------------------------------------------------
# Fase B (specs/010-commercial-relationship-commercial-product): ejercicios 4–6
# --------------------------------------------------------------------------

PAYMENT_REFERENCE = "http://localhost:8105"

EMPRESA_EJ4 = "c0a1c0a1-0000-4000-8000-000000000e04"
EMPRESA_EJ5 = "c0a1c0a1-0000-4000-8000-000000000e05"
EMPRESA_EJ6 = "c0a1c0a1-0000-4000-8000-000000000e06"
EMPRESA_EJ7 = "c0a1c0a1-0000-4000-8000-000000000e07"  # spec 021
EMPRESA_EJ8 = "c0a1c0a1-0000-4000-8000-000000000e08"  # spec 021
EMPRESA_EJ9 = "c0a1c0a1-0000-4000-8000-000000000e09"  # spec 021
ORG_EMPRESA_EJ4 = "7a1c0f10-0000-4000-8000-0000000c0e04"
ORG_EMPRESA_EJ5 = "7a1c0f10-0000-4000-8000-0000000c0e05"
ORG_EMPRESA_EJ6 = "7a1c0f10-0000-4000-8000-0000000c0e06"
ORG_EMPRESA_EJ7 = "7a1c0f10-0000-4000-8000-0000000c0e07"
ORG_EMPRESA_EJ8 = "7a1c0f10-0000-4000-8000-0000000c0e08"
ORG_EMPRESA_EJ9 = "7a1c0f10-0000-4000-8000-0000000c0e09"
COMPANIES.update({
    EMPRESA_EJ4: ORG_EMPRESA_EJ4, EMPRESA_EJ5: ORG_EMPRESA_EJ5, EMPRESA_EJ6: ORG_EMPRESA_EJ6, EMPRESA_EJ7: ORG_EMPRESA_EJ7,
    EMPRESA_EJ8: ORG_EMPRESA_EJ8, EMPRESA_EJ9: ORG_EMPRESA_EJ9,
})
COMPANY_NAMES.update({
    ORG_EMPRESA_EJ4: "DROGUERÍA PRESENTACIONES FICTICIA S.A.S.",
    ORG_EMPRESA_EJ5: "DROGUERÍA COMPRAS FICTICIA S.A.S.",
    ORG_EMPRESA_EJ6: "DROGUERÍA PRECIOS FICTICIA S.A.S.",
    ORG_EMPRESA_EJ7: "DROGUERÍA POLÍTICAS FICTICIA S.A.S.",
    ORG_EMPRESA_EJ8: "DROGUERÍA IMPUESTOS FICTICIA S.A.S.",
    ORG_EMPRESA_EJ9: "DROGUERÍA ACTUALIZACIONES FICTICIA S.A.S.",
})

# Producto real de la fila 16577 (único con `Precio Lista` en la fuente).
GP_IRBESARTAN = "9a9a9a9a-0000-4000-8000-000000022315"     # Código 022315, fila 16577
GLOBAL_PRODUCTS[GP_IRBESARTAN] = ("ACTIVE", True)

# Presentaciones globales (Product Catalog). Sus nombres viven en Product Catalog; aquí son **ficticias**.
GPRES_ACETA_CAJA = "8b8b8b8b-0000-4000-8000-000000000451"   # Caja x100 (presentación base del producto)
GPRES_ACETA_SOBRE = "8b8b8b8b-0000-4000-8000-000000000452"  # Sobre x10
GPRES_AGUJA_CAJA = "8b8b8b8b-0000-4000-8000-000000005371"   # Caja x100 de la aguja (otro producto)
GPRES_IRBE_CAJA = "8b8b8b8b-0000-4000-8000-000000223151"    # Caja x30 del irbesartán
# presentación -> (producto global, estado, elegible)
GLOBAL_PRESENTATIONS = {
    GPRES_ACETA_CAJA: (GP_ACETAMINOFEN, "ACTIVE", True),
    GPRES_ACETA_SOBRE: (GP_ACETAMINOFEN, "ACTIVE", True),
    GPRES_AGUJA_CAJA: (GP_AGUJA, "ACTIVE", True),
    GPRES_IRBE_CAJA: (GP_IRBESARTAN, "ACTIVE", True),
}

# Unidad base de cada producto global (Product Catalog, `base_unit_id`).
UNIDAD_CAJA = "7c7c7c7c-0000-4000-8000-00000000ca1a"
UNIDAD_OTRA = "7c7c7c7c-0000-4000-8000-00000000ffff"
BASE_UNITS = {GP_ACETAMINOFEN: UNIDAD_CAJA, GP_AGUJA: UNIDAD_CAJA, GP_IRBESARTAN: UNIDAD_CAJA}

# Proveedor ficticio de los ejercicios 5–6 y tipos de condición de pago (Payment Reference, `seed`).
ORG_PROVEEDOR_EJ5 = "6f6f6f6f-0000-4000-8000-000000000005"
ORGANIZATIONS[ORG_PROVEEDOR_EJ5] = "ACTIVE"
TIPO_CASH = "3c3c3c3c-0000-4000-8000-00000000ca5e"
TIPO_CREDIT = "3c3c3c3c-0000-4000-8000-00000000c2ed"
# tipo -> (código, estado)
CONDITION_TYPES = {TIPO_CASH: ("CASH", "ACTIVE"), TIPO_CREDIT: ("CREDIT", "ACTIVE")}


def get_global_presentation(variable, presentation_id, product_variable, description):
    return call(
        f"Consultar la presentación global {description} en Product Catalog",
        "GET",
        f"{PRODUCT_CATALOG}/products/<{product_variable}>/presentations",
        external="Product Catalog Service",
        perm="perm:product-catalog:products:read",
        why=[
            "Commercial Relationship **no copia** el nombre, la cantidad base ni el empaque de la presentación global: "
            "solo guarda su `id` (`global_product_presentation_id`, FR-017).",
            "Al adoptar, el servicio vuelve a comprobar en Product Catalog que esté `ACTIVE`, sea elegible y "
            "pertenezca al mismo producto global, y registra su **primer uso** con su identidad técnica.",
        ],
        save={variable: "[0].id"},
        fake={variable: presentation_id},
        sample=[{"id": f"<{variable}>", "global_product_id": f"<{product_variable}>",
                 "name": f"{description} (nombre en Product Catalog)", "status": "ACTIVE",
                 "eligible_for_adoption": True}],
    )


def get_base_unit(variable, unit_id, product_variable):
    return call(
        "Consultar la unidad base del producto global en Product Catalog",
        "GET",
        f"{PRODUCT_CATALOG}/products/<{product_variable}>",
        external="Product Catalog Service",
        perm="perm:product-catalog:products:read",
        why=["En el MVP no hay conversión de unidades (OP-01): la unidad de compra de un producto de proveedor es "
             "siempre la **unidad base** del producto global (DS-07). El servicio la verifica con su identidad técnica."],
        save={variable: "base_unit_id"},
        fake={variable: unit_id},
        sample={"id": f"<{product_variable}>", "base_unit_id": f"<{variable}>", "status": "ACTIVE"},
    )


def get_condition_type(variable, type_id, code):
    return call(
        f"Consultar el tipo de condición de pago {code} en Payment Reference",
        "GET",
        f"{PAYMENT_REFERENCE}/global-payment-condition-types?code={code}",
        external="Payment Reference Service",
        perm="perm:payment-reference:global_payment_condition_types:read",
        why=["Commercial Relationship **no guarda** el código ni el nombre del tipo: solo su `id`. Lo consulta con "
             "su identidad técnica para validar que esté `ACTIVE` y que el plazo corresponda (`CASH` → 0 días; "
             "`CREDIT` y `FINANCING` → más de 0, FR-033)."],
        save={variable: "items[0].id"},
        fake={variable: type_id},
        sample={"items": [{"id": f"<{variable}>", "code": code, "name": "<nombre del tipo>", "status": "ACTIVE"}]},
    )

# Spec 021, ejercicio 9: identificadores fijos de las recepciones que entrega Purchase (simuladas en la validación).
COMPRA_EJ9_1 = "5e5e5e5e-0000-4000-8000-000000000901"
COMPRA_EJ9_2 = "5e5e5e5e-0000-4000-8000-000000000902"
DETALLE_EJ9_1 = "5d5d5d5d-0000-4000-8000-000000000901"
DETALLE_EJ9_2 = "5d5d5d5d-0000-4000-8000-000000000902"
SEDE_EJ9 = "5b5b5b5b-0000-4000-8000-000000000909"
RECIBIO_EJ9 = "5a5a5a5a-0000-4000-8000-000000000909"
