"""Ejercicio 6 de docs/ejemplo/: personas de contacto de una organización (Fase B; FR-040–FR-047)."""

from tests.examples.spec_common import API, call, get_colombia, step

CONTACT_SHOW = ["id", "organization_identity_id", "person_identity_id", "position", "phone", "is_primary",
                "is_active", "version"]

ORGANIZATION = {
    "country_id": "<PAIS_CO>",
    "identification_type": "NIT",
    "identification_number": "900000006-6",
    "legal_name": "LABORATORIO CONTACTOS FICTICIO S.A.S.",
}

PERSON = {
    "identification_country_id": "<PAIS_CO>",
    "identification_type": "CC",
    "identification_number": "1000000006",
    "first_name": "MARTA",
    "last_name": "COMERCIAL",
    "second_last_name": "FICTICIA",
    "birth_date": "1988-07-01",
}

EX6 = dict(
    folder="6-personas-de-contacto",
    title="Ejercicio 6 — Personas de contacto: principal, set-primary e inactivación",
    focus=(
        "Registrar el contacto comercial (vinculado a una persona identificada) como **principal** y el de cartera, "
        "ver el `409` al crear un segundo principal, cambiarlo con **`set-primary`** (atómico) y **inactivar** un "
        "contacto sin afectar a los demás. El `GET` por `id` es el contrato Provider que usará Commercial Relationship "
        "para validar el contacto preferido de un cliente o proveedor."
    ),
    data=[
        ("Organización", "LABORATORIO CONTACTOS FICTICIO S.A.S. — NIT `900000006-6` (**ficticios**)"),
        ("Contacto comercial", "MARTA COMERCIAL FICTICIA — `CC 1000000006` (**ficticia**)"),
        ("Contacto de cartera", "Teléfono `+57 601 555 0166` (**ficticio**), sin persona identificada"),
    ],
    interpretation=[
        ("Principal único", "Como máximo un contacto activo principal por organización; puede no haber ninguno."),
        ("Cambio de principal", "Solo con `:set-primary` (desmarca el anterior y marca el nuevo en una operación); "
         "`is_primary` no se cambia con `PUT` (`422 IMMUTABLE_FIELD`)."),
        ("Inactivar", "Quita la marca de principal solo de ese contacto; los demás no cambian."),
    ],
    order_rules=[
        ("Identidades primero", "La organización y la persona vinculada deben existir y estar `ACTIVE`."),
        ("Principal antes de cambiarlo", "El `409` y el `set-primary` se ven después de tener un principal."),
    ],
    steps=[
        step("01-consultar-pais.md", "Consultar el país", "Obtener `<PAIS_CO>`.", [get_colombia()]),
        step(
            "02-registrar-identidades.md", "Registrar la organización y la persona", "Crear las identidades globales.",
            [
                call("Registrar la organización", "POST", f"{API}/organization-identities", body=ORGANIZATION,
                     why=["Las personas de contacto, sectores y representantes cuelgan de una organización `ACTIVE` de Party Identity; se registra primero con datos **ficticios** (NIT que cumple la regla `NIT`, no es real)."],
                     save={"ORG_LAB": "id"}, show=["id", "legal_name", "status"]),
                call("Registrar la persona de contacto", "POST", f"{API}/person-identities", body=PERSON,
                     why=["Un contacto puede vincular una `PersonIdentity` existente y `ACTIVE`; Party Identity no copia su nombre ni su documento en el contacto."],
                     save={"PERSONA_MARTA": "id"}, show=["id", "first_name", "last_name", "status"]),
            ],
        ),
        step(
            "03-registrar-contactos.md", "Registrar contactos", "Crear el principal y el de cartera.",
            [
                call("Registrar el contacto comercial como principal", "POST",
                     f"{API}/organization-identities/<ORG_LAB>/contact-persons",
                     body={"person_identity_id": "<PERSONA_MARTA>", "position": "Comercial", "is_primary": True},
                     why=["Vincula una `PersonIdentity`; con ella no hace falta correo ni teléfono."],
                     save={"CONTACTO_COMERCIAL": "id"}, show=CONTACT_SHOW),
                call("Registrar el contacto de cartera", "POST",
                     f"{API}/organization-identities/<ORG_LAB>/contact-persons",
                     body={"position": "Cartera", "phone": "+57 601 555 0166"},
                     why=["Contacto sin persona vinculada: basta un medio de contacto (aquí el teléfono).",
                          "Se crea como no principal (`is_primary` por defecto `false`): ya hay un principal y solo puede haber uno."],
                     save={"CONTACTO_CARTERA": "id"}, show=CONTACT_SHOW),
                call("Intentar crear un segundo principal (rechazado)", "POST",
                     f"{API}/organization-identities/<ORG_LAB>/contact-persons",
                     body={"position": "Logística", "phone": "+57 601 555 0167", "is_primary": True},
                     why=["Ya hay un principal: `409 PRIMARY_CONTACT_CONFLICT`. Para cambiarlo se usa `set-primary`."],
                     expect=409, show=["status", "code"]),
            ],
        ),
        step(
            "04-set-primary-e-inactivar.md", "Cambiar el principal e inactivar", "Usar set-primary y retirar un contacto.",
            [
                call("Establecer el contacto de cartera como principal", "POST",
                     f"{API}/organization-contact-persons/<CONTACTO_CARTERA>:set-primary", body={"version": 1},
                     why=["Exige `update`. En una sola operación el comercial deja de ser principal."],
                     show=CONTACT_SHOW),
                call("Consultar el contacto comercial por `id` (contrato Provider)", "GET",
                     f"{API}/organization-contact-persons/<CONTACTO_COMERCIAL>",
                     why=["Commercial Relationship comprueba `organization_identity_id` e `is_active` con esta consulta."],
                     show=CONTACT_SHOW),
                call("Inactivar el contacto de cartera", "POST",
                     f"{API}/organization-contact-persons/<CONTACTO_CARTERA>:deactivate", body={"version": 2},
                     why=["Exige `delete`; no elimina. Deja de ser principal; la organización queda sin principal."],
                     show=CONTACT_SHOW),
                call("Listar los contactos vigentes", "GET", f"{API}/organization-identities/<ORG_LAB>/contact-persons",
                     why=["Por defecto solo los activos; `?is_active=false` muestra los inactivos."],
                     show=["total_records"]),
            ],
        ),
    ],
)
