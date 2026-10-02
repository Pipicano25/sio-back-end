"""Ejercicio 5 de docs/ejemplo/: perfil de contacto de una persona (Fase B; FR-016, RN-12)."""

from tests.examples.spec_common import API, call, get_colombia, get_company, step

PROFILE_SHOW = ["id", "email", "phone", "is_active", "confirmed_by_company_id", "confirmed_by_user_id", "version"]

PERSON = {
    "identification_country_id": "<PAIS_CO>",
    "identification_type": "CC",
    "identification_number": "1000000005",
    "first_name": "LUIS",
    "last_name": "CLIENTE",
    "second_last_name": "FICTICIO",
    "birth_date": "1985-03-20",
}

PROFILE = {
    "email": "luis.cliente@correo-ficticio.co",
    "phone": "+57 300 555 0105",
    "confirmed_by_company_id": "<EMPRESA>",
}

EX5 = dict(
    folder="5-perfil-de-persona",
    title="Ejercicio 5 — Perfil de contacto de una persona: cliente persona natural e inactivación",
    focus=(
        "Registrar el contacto de un **cliente persona natural** (sin dirección, solo correo y teléfono), consultarlo, "
        "y ver que al **inactivar la persona** el perfil sigue consultable (sin cascadas) pero no se aceptan versiones "
        "nuevas (`422 PERSON_IDENTITY_INACTIVE`)."
    ),
    data=[
        ("Persona", "LUIS CLIENTE FICTICIO — `CC 1000000005` (**ficticios**), nacido en 1985"),
        ("Contacto", "`luis.cliente@correo-ficticio.co`, `+57 300 555 0105` (**ficticios**)"),
    ],
    interpretation=[
        ("Sin dirección", "Basta uno de correo, teléfono o dirección; sin geografía no se consulta Geography."),
        ("Sin cascadas", "Inactivar la persona no cierra su perfil: solo impide versiones nuevas (DS-07)."),
        ("Permiso específico", "Leer la persona (`person_identities:read`) **no** permite leer su contacto: hace falta "
         "`person_contact_profiles:read`."),
    ],
    order_rules=[
        ("Referencias primero", "País y empresa confirmante se consultan en sus servicios."),
        ("Persona activa", "El perfil se registra mientras la persona está `ACTIVE`; luego se inactiva para ver el efecto."),
    ],
    steps=[
        step("01-consultar-referencias.md", "Consultar referencias externas", "Obtener `<PAIS_CO>` y `<EMPRESA>`.",
             [get_colombia(), get_company()]),
        step(
            "02-registrar-persona-y-perfil.md", "Registrar la persona y su perfil", "Crear la persona y su contacto vigente.",
            [
                call("Registrar la persona", "POST", f"{API}/person-identities", body=PERSON,
                     why=["Cédula moderna de 10 dígitos y persona adulta: cumple las reglas de Colombia."],
                     save={"PERSONA_CLIENTE": "id"}, show=["id", "first_name", "last_name", "status", "version"]),
                call("Registrar el perfil de contacto", "POST",
                     f"{API}/person-identities/<PERSONA_CLIENTE>/contact-profile", body=PROFILE,
                     why=["Solo correo y teléfono; la empresa confirmante es obligatoria."],
                     expect=201, show=PROFILE_SHOW),
                call("Consultar el perfil vigente", "GET", f"{API}/person-identities/<PERSONA_CLIENTE>/contact-profile",
                     why=["Lo usará Sales para contactar al cliente persona."], show=PROFILE_SHOW),
            ],
        ),
        step(
            "03-inactivar-persona.md", "Inactivar la persona", "Ver el efecto sobre el perfil.",
            [
                call("Inactivar la persona", "POST", f"{API}/person-identities/<PERSONA_CLIENTE>/deactivate",
                     body={"version": 1}, why=["Exige `delete` sobre `person_identities`; no elimina."],
                     show=["id", "status", "version"]),
                call("Intentar una versión nueva del perfil (rechazado)", "POST",
                     f"{API}/person-identities/<PERSONA_CLIENTE>/contact-profile",
                     body={**PROFILE, "phone": "+57 300 555 0155", "version": 1},
                     why=["La persona está `INACTIVE`: `422 PERSON_IDENTITY_INACTIVE`."],
                     expect=422, show=["status", "code"]),
                call("Consultar el perfil (sigue vigente)", "GET",
                     f"{API}/person-identities/<PERSONA_CLIENTE>/contact-profile",
                     why=["Sin cascadas: el perfil vigente se conserva y sigue consultable."], show=PROFILE_SHOW),
            ],
        ),
    ],
)
