"""Ejercicio 5 de docs/ejemplo/: proveedores por producto y condiciones de pago (FR-020 a FR-038; aclaración 3).

Producto real de `docs/CAMPOS PRODUCTOS.xlsx` (fila 40, con su `Nombre Proveedor`); proveedor, costos y
condiciones ficticios.
"""

from tests.examples.spec_common import (
    API,
    EMPRESA_EJ5,
    GP_ACETAMINOFEN,
    GPRES_ACETA_CAJA,
    ORG_PROVEEDOR_EJ5,
    TIPO_CASH,
    TIPO_CREDIT,
    UNIDAD_CAJA,
    UNIDAD_OTRA,
    call,
    get_base_unit,
    get_company,
    get_condition_type,
    get_global_presentation,
    get_global_product,
    get_organization,
    step,
)

SUPPLIER_PRODUCT_SHOW = [
    "id", "company_supplier_id", "company_product_id", "company_product_presentation_id", "supplier_product_code",
    "purchase_unit_id", "minimum_order_quantity", "pack_quantity", "negotiated_unit_cost", "currency_code",
    "is_preferred", "status", "version",
]
CONDITION_SHOW = [
    "id", "company_supplier_id", "payment_condition_type_id", "currency_code", "payment_terms_days", "credit_limit",
    "cash_discount_percentage", "is_default", "status", "version",
]
ERROR_SHOW = ["status", "code", "detail", "errors"]

EX5 = dict(
    folder="5-proveedores-por-producto-y-condiciones",
    title="Ejercicio 5 — Proveedores por producto y condiciones de pago",
    data_file="00-datos-del-excel.md",
    real_data=True,
    focus=(
        "Registrar qué **proveedor suministra** un producto en general y en una **presentación** concreta (relaciones "
        "que coexisten), los rechazos de una **relación repetida** y de una **unidad distinta de la base**, y las "
        "**condiciones de pago**: contado con plazo (rechazado) y crédito predeterminado en pesos."
    ),
    data=[
        ("Fuente", "`docs/CAMPOS PRODUCTOS.xlsx`, hoja `Hoja1` (encabezados en la fila 2)"),
        ("Fila 40", "`Código` 000045 · `Nombre Proveedor` ACETAMINOFEN 500MG TABLETA CAJAX100 SIEGFRIED · "
         "`Unidad Medida` CAJA"),
        ("Proveedor", "LABORATORIO PROVEEDOR FICTICIO S.A.S. (**ficticio**, NIT ficticio)."),
        ("Costos, mínimos y condiciones", "**Ficticios**: costo negociado 12500.5000 COP, mínimo 10 cajas, crédito a "
         "30 días con cupo de 5 000 000 COP. La fuente no trae costos por proveedor (`Costo` vacío)."),
        ("Empresa", "DROGUERÍA COMPRAS FICTICIA S.A.S. (**ficticia**), registrada en Operational Context."),
    ],
    interpretation=[
        ("Código del proveedor", "`Nombre Proveedor` → `supplier_product_code`: así llama el proveedor al producto."),
        ("Unidad de compra", "Es siempre la **unidad base** del producto global (sin conversión de unidades en el MVP)."),
        ("Relación por presentación", "La relación general (sin presentación) y la de la caja x100 coexisten; se "
         "rechaza repetir la misma combinación proveedor + producto + presentación entre las `ACTIVE` (aclaración 3)."),
        ("Proveedor activo", "Solo un proveedor `ACTIVE` recibe productos y condiciones nuevos (FR-021, FR-031): si está "
         "inactivo o bloqueado se reactiva o desbloquea antes."),
        ("Tipo de condición", "Se lee de Payment Reference en cada validación y no se copia: contado exige 0 días; "
         "crédito y financiación, más de 0."),
    ],
    order_rules=[
        ("Producto, presentación y proveedor primero", "El producto de proveedor une los tres."),
        ("Unidad base antes de registrar", "El servicio la verifica en Product Catalog al registrar."),
    ],
    steps=[
        step("01-consultar-datos.md", "Consultar la empresa, el producto, la presentación, el proveedor y los tipos",
             "Obtener los identificadores de los otros servicios.", [
                 get_company("EMPRESA", EMPRESA_EJ5, "DROGUERÍA COMPRAS FICTICIA S.A.S."),
                 get_global_product("GP_ACETAMINOFEN", GP_ACETAMINOFEN, "7707355056876",
                                    "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED"),
                 get_global_presentation("GPRES_CAJA", GPRES_ACETA_CAJA, "GP_ACETAMINOFEN", "Caja x100"),
                 get_base_unit("UNIDAD_BASE", UNIDAD_CAJA, "GP_ACETAMINOFEN"),
                 get_organization("ORG_PROVEEDOR", ORG_PROVEEDOR_EJ5, "LABORATORIO PROVEEDOR FICTICIO S.A.S."),
                 get_condition_type("TIPO_CASH", TIPO_CASH, "CASH"),
                 get_condition_type("TIPO_CREDIT", TIPO_CREDIT, "CREDIT"),
             ]),
        step("02-preparar.md", "Adoptar el producto y la presentación y seleccionar el proveedor",
             "Crear lo que el producto de proveedor referencia.", [
                 call("Adoptar el acetaminofén (fila 40)", "POST", f"{API}/companies/<EMPRESA>/company-products",
                      body={"global_product_id": "<GP_ACETAMINOFEN>", "internal_code": "000045",
                            "display_name": "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED",
                            "currency_code": "COP"},
                      why=["Ejercicio 1."], save={"PRODUCTO": "id"}, show=["id", "status"]),
                 call("Adoptar la caja x100", "POST", f"{API}/companies/<EMPRESA>/company-product-presentations",
                      body={"company_product_id": "<PRODUCTO>", "global_product_presentation_id": "<GPRES_CAJA>"},
                      why=["Ejercicio 4. Es comprable por defecto."], save={"PRES_CAJA": "id"},
                      show=["id", "is_purchasable", "status"]),
                 call("Seleccionar el proveedor", "POST", f"{API}/companies/<EMPRESA>/company-suppliers",
                      body={"organization_identity_id": "<ORG_PROVEEDOR>", "internal_code": "PRV-0001",
                            "display_name": "Laboratorio proveedor (ficticio)"},
                      why=["Ejercicio 3."], save={"PROVEEDOR": "id"}, show=["id", "status"]),
             ]),
        step("03-productos-de-proveedor.md", "Registrar qué suministra el proveedor",
             "Relación general, rechazo por unidad, relación por presentación y rechazo por repetición.", [
                 call("Registrar la relación general", "POST", f"{API}/companies/<EMPRESA>/supplier-products",
                      body={"company_supplier_id": "<PROVEEDOR>", "company_product_id": "<PRODUCTO>",
                            "supplier_product_code": "ACETAMINOFEN 500MG TABLETA CAJAX100 SIEGFRIED",
                            "purchase_unit_id": "<UNIDAD_BASE>", "currency_code": "COP",
                            "negotiated_unit_cost": "12500.5000", "minimum_order_quantity": "10",
                            "is_preferred": True},
                      why=["El servicio exige proveedor y producto `ACTIVE` y comprueba en Product Catalog que la "
                           "unidad sea la base. Se marca como proveedor preferido del producto."],
                      save={"PRV_GENERAL": "id"}, show=SUPPLIER_PRODUCT_SHOW),
                 call("Registrar con otra unidad (rechazado)", "POST", f"{API}/companies/<EMPRESA>/supplier-products",
                      body={"company_supplier_id": "<PROVEEDOR>", "company_product_id": "<PRODUCTO>",
                            "company_product_presentation_id": "<PRES_CAJA>", "purchase_unit_id": UNIDAD_OTRA,
                            "currency_code": "COP"},
                      why=["Sin conversión de unidades en el MVP: `422 PURCHASE_UNIT_NOT_BASE_UNIT`."],
                      expect=422, show=ERROR_SHOW),
                 call("Registrar la relación de la caja x100", "POST", f"{API}/companies/<EMPRESA>/supplier-products",
                      body={"company_supplier_id": "<PROVEEDOR>", "company_product_id": "<PRODUCTO>",
                            "company_product_presentation_id": "<PRES_CAJA>", "purchase_unit_id": "<UNIDAD_BASE>",
                            "currency_code": "COP", "pack_quantity": "100"},
                      why=["Coexiste con la general: la presentación es parte de la combinación única (aclaración 3)."],
                      show=SUPPLIER_PRODUCT_SHOW),
                 call("Repetir la relación general (rechazado)", "POST", f"{API}/companies/<EMPRESA>/supplier-products",
                      body={"company_supplier_id": "<PROVEEDOR>", "company_product_id": "<PRODUCTO>",
                            "purchase_unit_id": "<UNIDAD_BASE>", "currency_code": "COP"},
                      why=["Ya hay una relación `ACTIVE` sin presentación: `409 DUPLICATE_SUPPLIER_PRODUCT`."],
                      expect=409, show=ERROR_SHOW),
             ]),
        step("04-condiciones-de-pago.md", "Registrar las condiciones de pago",
             "Contado con plazo (rechazado) y crédito predeterminado.", [
                 call("Registrar contado con 15 días (rechazado)", "POST",
                      f"{API}/companies/<EMPRESA>/supplier-payment-conditions",
                      body={"company_supplier_id": "<PROVEEDOR>", "payment_condition_type_id": "<TIPO_CASH>",
                            "currency_code": "COP", "payment_terms_days": 15},
                      why=["Contado exige 0 días: `422 PAYMENT_TERMS_INCONSISTENT` (FR-033)."],
                      expect=422, show=ERROR_SHOW),
                 call("Registrar contado con descuento por pronto pago", "POST",
                      f"{API}/companies/<EMPRESA>/supplier-payment-conditions",
                      body={"company_supplier_id": "<PROVEEDOR>", "payment_condition_type_id": "<TIPO_CASH>",
                            "currency_code": "COP", "payment_terms_days": 0, "cash_discount_percentage": "2.5"},
                      why=["Plazo 0 y descuento entre 0 y 100 con hasta 4 decimales."],
                      show=CONDITION_SHOW),
                 call("Registrar crédito a 30 días como predeterminado en COP", "POST",
                      f"{API}/companies/<EMPRESA>/supplier-payment-conditions",
                      body={"company_supplier_id": "<PROVEEDOR>", "payment_condition_type_id": "<TIPO_CREDIT>",
                            "currency_code": "COP", "payment_terms_days": 30, "credit_limit": "5000000.00",
                            "is_default": True},
                      why=["Una condición de crédito no crea deuda; la deuda nace en Finanzas con una compra "
                           "confirmada. Hay como máximo una predeterminada por proveedor y moneda."],
                      show=CONDITION_SHOW),
             ]),
    ],
)
