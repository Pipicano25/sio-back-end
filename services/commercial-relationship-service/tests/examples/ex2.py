"""Ejercicio 2 de docs/ejemplo/: clientes (FR-020 a FR-028; DS-08, DS-14, DS-15, DS-17)."""

from tests.examples.spec_common import (
    API,
    CONTACTO_CLIENTE,
    CONTACTO_OTRA_ORG,
    EMPRESA_EJ2,
    ORG_CLIENTE,
    ORG_EMPRESA_EJ2,
    ORG_OTRA,
    PER_CLIENTE,
    call,
    get_company,
    get_contact,
    get_organization,
    get_person,
    step,
)

CUSTOMER_SHOW = [
    "id", "customer_kind", "person_identity_id", "organization_identity_id", "internal_code", "display_name",
    "preferred_contact_person_id", "status", "version",
]
ERROR_SHOW = ["status", "code", "detail", "errors"]

EX2 = dict(
    folder="2-clientes",
    title="Ejercicio 2 — Clientes persona y organización",
    data_file="00-datos-ficticios.md",
    focus=(
        "Incorporar un **cliente persona** y un **cliente organización con persona de contacto preferida**, ver los "
        "rechazos de un contacto de otra organización y de la **propia empresa como cliente**, modificar el cliente y "
        "**inactivarlo y reactivarlo**."
    ),
    data=[
        ("Empresa", "COMERCIALIZADORA CLIENTES FICTICIA S.A.S. (**ficticia**)"),
        ("Cliente persona", "Persona **ficticia** registrada en Party Identity (documento ficticio)"),
        ("Cliente organización", "MINIMARKET EJEMPLO FICTICIO S.A.S. (**ficticio**, NIT ficticio)"),
        ("Contacto preferido", "Persona de contacto **ficticia** de esa organización"),
        ("Otra organización", "DISTRIBUIDORA AJENA FICTICIA S.A.S. (**ficticia**) con su propio contacto"),
    ],
    interpretation=[
        ("Fuente", "No existe una fuente del sistema anterior para clientes: todos los datos son **ficticios**. Ningún "
         "NIT, razón social ni documento se presenta como real."),
        ("Qué se guarda", "Solo el `id` de la identidad en Party Identity, el código interno y el nombre visible de la "
         "empresa. Nombre legal, documento y contacto se consultan en Party Identity (Principio III)."),
        ("Tipo", "`PERSON` exige `person_identity_id`; `ORGANIZATION` exige `organization_identity_id`; nunca ambos."),
        ("Contacto", "Solo organizaciones; debe ser de la misma organización y estar activo al asignarlo."),
        ("Propia empresa", "Una empresa no puede ser cliente de sí misma (DS-15)."),
    ],
    order_rules=[
        ("Identidades primero", "El cliente referencia identidades que ya existen en Party Identity."),
        ("Alta antes de cambios", "La modificación y los estados se aplican sobre un cliente existente."),
    ],
    steps=[
        step("01-consultar-identidades.md", "Consultar la empresa y las identidades",
             "Obtener `<EMPRESA>`, la persona, las organizaciones y los contactos.", [
                 get_company("EMPRESA", EMPRESA_EJ2, "COMERCIALIZADORA CLIENTES FICTICIA S.A.S."),
                 get_organization("ORG_EMPRESA", ORG_EMPRESA_EJ2, "COMERCIALIZADORA CLIENTES FICTICIA S.A.S."),
                 get_person("PERSONA", PER_CLIENTE, "cliente (ficticia)"),
                 get_organization("ORG_CLIENTE", ORG_CLIENTE, "MINIMARKET EJEMPLO FICTICIO S.A.S."),
                 get_contact("CONTACTO", CONTACTO_CLIENTE, "ORG_CLIENTE", "del minimarket (ficticia)"),
                 get_organization("ORG_OTRA", ORG_OTRA, "DISTRIBUIDORA AJENA FICTICIA S.A.S."),
                 get_contact("CONTACTO_OTRA", CONTACTO_OTRA_ORG, "ORG_OTRA", "de la distribuidora (ficticia)"),
             ]),
        step("02-cliente-persona.md", "Incorporar un cliente persona",
             "Registrar a la persona como cliente.", [
                 call("Incorporar el cliente persona", "POST", f"{API}/companies/<EMPRESA>/company-customers",
                      body={"customer_kind": "PERSON", "person_identity_id": "<PERSONA>",
                            "internal_code": "CLI-0001", "display_name": "Cliente persona (ficticio)"},
                      why=["El servicio valida en Party Identity, **con el token del usuario**, que la persona exista y "
                           "esté `ACTIVE`; si el usuario no puede leer personas, responde `403 PARTY_IDENTITY_ACCESS_DENIED`.",
                           "`display_name` es obligatorio: lo escribe el usuario (DS-14)."],
                      save={"CLIENTE_PERSONA": "id"}, show=CUSTOMER_SHOW),
                 call("Indicar un contacto preferido para una persona (rechazado)", "POST",
                      f"{API}/companies/<EMPRESA>/company-customers",
                      body={"customer_kind": "PERSON", "person_identity_id": "<PERSONA>", "internal_code": "CLI-0002",
                            "display_name": "Otro", "preferred_contact_person_id": "<CONTACTO>"},
                      why=["Solo los clientes `ORGANIZATION` admiten persona de contacto: `422 CONTACT_PERSON_NOT_ALLOWED`."],
                      expect=422, show=ERROR_SHOW),
             ]),
        step("03-cliente-organizacion.md", "Incorporar un cliente organización",
             "Registrar la organización con su contacto y ver los rechazos.", [
                 call("Indicar el contacto de otra organización (rechazado)", "POST",
                      f"{API}/companies/<EMPRESA>/company-customers",
                      body={"customer_kind": "ORGANIZATION", "organization_identity_id": "<ORG_CLIENTE>",
                            "internal_code": "CLI-0100", "display_name": "Minimarket (ficticio)",
                            "preferred_contact_person_id": "<CONTACTO_OTRA>"},
                      why=["El contacto debe pertenecer a la **misma** organización: `422 CONTACT_PERSON_INVALID`."],
                      expect=422, show=ERROR_SHOW),
                 call("Incorporar el cliente organización con su contacto", "POST",
                      f"{API}/companies/<EMPRESA>/company-customers",
                      body={"customer_kind": "ORGANIZATION", "organization_identity_id": "<ORG_CLIENTE>",
                            "internal_code": "CLI-0100", "display_name": "Minimarket (ficticio)",
                            "preferred_contact_person_id": "<CONTACTO>"},
                      why=["Antes de Party Identity, el servicio consulta la empresa en Operational Context para "
                           "comprobar que la organización no sea la de la propia empresa (DS-15)."],
                      save={"CLIENTE_ORG": "id"}, show=CUSTOMER_SHOW),
                 call("Incorporar la propia empresa como cliente (rechazado)", "POST",
                      f"{API}/companies/<EMPRESA>/company-customers",
                      body={"customer_kind": "ORGANIZATION", "organization_identity_id": "<ORG_EMPRESA>",
                            "internal_code": "CLI-YO", "display_name": "La propia empresa"},
                      why=["Una empresa nunca es cliente de sí misma: `422 SELF_RELATIONSHIP_NOT_ALLOWED`."],
                      expect=422, show=ERROR_SHOW),
             ]),
        step("04-modificar-y-estados.md", "Modificar, inactivar y reactivar",
             "Cambiar el nombre visible y el ciclo de vida del cliente.", [
                 call("Cambiar el nombre visible y quitar el contacto", "PUT", f"{API}/company-customers/<CLIENTE_ORG>",
                      body={"internal_code": "CLI-0100", "display_name": "Minimarket Centro (ficticio)",
                            "preferred_contact_person_id": None, "version": 1},
                      why=["El `PUT` cambia código interno, nombre visible y contacto; tipo e identidad son inmutables.",
                           "Quitar el contacto no consulta Party Identity."],
                      show=["id", "display_name", "preferred_contact_person_id", "version"]),
                 call("Inactivar el cliente persona", "POST", f"{API}/company-customers/<CLIENTE_PERSONA>/deactivate",
                      body={"version": 1}, why=["Inactivar exige `delete`; no borra nada."],
                      show=["id", "status", "version"]),
                 call("Reactivar el cliente persona", "POST", f"{API}/company-customers/<CLIENTE_PERSONA>/reactivate",
                      body={"version": 2},
                      why=["Reactivar vuelve a validar que la persona siga `ACTIVE` en Party Identity."],
                      show=["id", "status", "version"]),
                 call("Listar los clientes organización", "GET",
                      f"{API}/companies/<EMPRESA>/company-customers?customer_kind=ORGANIZATION",
                      why=["Filtros por tipo, identidad, estado y búsqueda en código y nombre."],
                      show=["items[].internal_code", "items[].display_name", "total_records"]),
             ]),
    ],
)
