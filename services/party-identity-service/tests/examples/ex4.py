"""Ejercicio 4 de docs/ejemplo/: perfil de contacto de una organización (Fase B; FR-010–FR-031)."""

from tests.conftest import NON_MEMBER_COMPANY_ID, UNAVAILABLE_COMPANY_ID
from tests.examples.spec_common import API, UNKNOWN_COUNTRY_ID, call, get_city, get_colombia, get_company, step

PROFILE_SHOW = ["id", "email", "phone", "city_id", "is_active", "confirmed_by_company_id",
                "confirmed_by_user_id", "version"]

ORGANIZATION = {
    "country_id": "<PAIS_CO>",
    "identification_type": "NIT",
    "identification_number": "900000004-4",
    "legal_name": "DISTRIBUIDORA CONTACTO FICTICIA S.A.S.",
}

PROFILE = {
    "email": "compras@distribuidora-ficticia.co",
    "phone": "+57 601 555 0104",
    "address_line": "Calle 00 # 00-04 (ficticia)",
    "country_id": "<PAIS_CO>",
    "administrative_division_id": "<DIVISION>",
    "city_id": "<CIUDAD>",
    "postal_code": "110111",
    "confirmed_by_company_id": "<EMPRESA>",
}

EX4 = dict(
    folder="4-perfil-de-organizacion",
    title="Ejercicio 4 — Perfil de contacto de una organización: versiones, no-op y cierre",
    focus=(
        "Registrar el contacto vigente de un proveedor **confirmado desde una empresa**, ver que una solicitud "
        "idéntica no crea versión, **reemplazarlo** (se cierra la versión anterior y se crea otra), consultar el "
        "**historial**, los rechazos por **geografía incoherente**, por **usuario sin membresía** y por "
        "**dependencia caída**, y **cerrar** el perfil sin reemplazo (y el `409` al repetirlo). Muestra además que "
        "`compras.test` lee el contacto y `reportes.test`/`consulta.test` no."
    ),
    data=[
        ("Organización", "DISTRIBUIDORA CONTACTO FICTICIA S.A.S. — NIT `900000004-4` (**ficticios**)"),
        ("Correo y teléfono", "`compras@distribuidora-ficticia.co`, `+57 601 555 0104` (**ficticios**)"),
        ("Dirección", "Calle 00 # 00-04, Bogotá (**ficticia**)"),
        ("Empresa confirmante", "La empresa de Operational Context en la que el usuario tiene membresía `ACTIVE`"),
        ("Empresa sin membresía (rechazo)", f"`{NON_MEMBER_COMPANY_ID}` (**ficticia**; el usuario no es miembro)"),
        ("Empresa con Operational Context caído (rechazo)", f"`{UNAVAILABLE_COMPANY_ID}` (**simulación** de indisponibilidad)"),
    ],
    interpretation=[
        ("Perfil global", "El perfil pertenece a la organización, no a la empresa: cualquier empresa reutiliza la versión "
         "vigente. Empresa y usuario confirmantes son **trazabilidad** de la versión, no propiedad exclusiva."),
        ("Versionado", "Nunca se sobrescribe: un cambio cierra la vigente (`valid_to`) y crea otra en la misma operación; "
         "`version` crece por organización y se envía para reemplazar o cerrar."),
        ("Confirmante", "`confirmed_by_user_id` nunca se envía: lo resuelve Party Identity con Operational Context "
         "(membresía `ACTIVE`). Un administrador de plataforma sin membresía recibe `422`."),
        ("Datos sensibles", "Correo, teléfono y dirección se leen con el permiso específico "
         "`organization_contact_profiles:read`; en logs y errores se enmascaran."),
    ],
    order_rules=[
        ("Referencias primero", "País, ciudad y empresa son de otros servicios: se consultan para conocer sus `id`."),
        ("Organización antes que su perfil", "El perfil se registra sobre una organización `ACTIVE`."),
        ("Versión vigente para reemplazar y cerrar", "Cada reemplazo o cierre envía la `version` de la vigente."),
    ],
    steps=[
        step("01-consultar-referencias.md", "Consultar referencias externas",
             "Obtener `<PAIS_CO>`, `<DIVISION>`, `<CIUDAD>` y `<EMPRESA>`.",
             [get_colombia(), get_city(), get_company()]),
        step(
            "02-registrar-organizacion.md", "Registrar la organización", "Crear el proveedor (identidad global).",
            [call("Registrar la organización", "POST", f"{API}/organization-identities", body=ORGANIZATION,
                  why=["Es la identidad global a la que pertenece el perfil de contacto."],
                  save={"ORG_PROVEEDOR": "id"}, show=["id", "legal_name", "status", "version"])],
        ),
        step(
            "03-registrar-perfil.md", "Registrar el perfil y repetirlo", "Crear la versión vigente; la repetición no cambia nada.",
            [
                call("Registrar el perfil de contacto (confirmado desde la empresa)", "POST",
                     f"{API}/organization-identities/<ORG_PROVEEDOR>/contact-profile", body=PROFILE,
                     why=["Al menos uno de correo, teléfono o dirección es obligatorio.",
                          "La geografía se valida contra Geography; la empresa y la membresía, contra Operational Context.",
                          "La respuesta trae `confirmed_by_user_id`: el usuario operativo resuelto, nunca enviado."],
                     expect=201, save={"PERFIL_1": "id"}, show=PROFILE_SHOW),
                call("Repetir exactamente la misma solicitud (sin cambios)", "POST",
                     f"{API}/organization-identities/<ORG_PROVEEDOR>/contact-profile", body={**PROFILE, "version": 1},
                     why=["Es semánticamente idéntica a la vigente: responde `200` con la misma versión, sin crear "
                          "otra, sin tocar `updated_at` ni consultar otros servicios."],
                     expect=200, show=PROFILE_SHOW),
                call("Consultar el perfil vigente", "GET",
                     f"{API}/organization-identities/<ORG_PROVEEDOR>/contact-profile",
                     why=["Es el contrato que usan Commercial Relationship, Purchase y Sales para mostrar el contacto."],
                     show=PROFILE_SHOW),
            ],
        ),
        step(
            "04-reemplazar-y-rechazos.md", "Reemplazar el perfil y rechazos",
            "Crear una versión nueva y ver los rechazos.",
            [
                call("Reemplazar el teléfono (nueva versión)", "POST",
                     f"{API}/organization-identities/<ORG_PROVEEDOR>/contact-profile",
                     body={**PROFILE, "phone": "+57 601 555 0144", "version": 1},
                     why=["Se envía el conjunto completo y la `version` de la vigente. La versión 1 queda cerrada con "
                          "`valid_to` y se crea otra vigente."],
                     expect=201, save={"PERFIL_2": "id"}, show=PROFILE_SHOW),
                call("Intentar una división administrativa inexistente (rechazado)", "POST",
                     f"{API}/organization-identities/<ORG_PROVEEDOR>/contact-profile",
                     body={**PROFILE, "administrative_division_id": UNKNOWN_COUNTRY_ID, "version": 3},
                     why=["La división enviada no existe en Geography: `422 ADMINISTRATIVE_DIVISION_NOT_FOUND`; no se guarda nada."],
                     expect=422, show=["status", "code", "detail"]),
                call("Intentar confirmar desde una empresa sin membresía (rechazado)", "POST",
                     f"{API}/organization-identities/<ORG_PROVEEDOR>/contact-profile",
                     body={**PROFILE, "phone": "+57 601 555 0145", "confirmed_by_company_id": str(NON_MEMBER_COMPANY_ID),
                           "version": 3},
                     why=["El usuario no es miembro de esa empresa: `422 CONFIRMATION_MEMBERSHIP_INVALID` con "
                          "`reason: USER_NOT_MEMBER`. Ser administrador no basta."],
                     expect=422, show=["status", "code", "reason"]),
                call("Intentar con Operational Context no disponible (simulado, rechazado)", "POST",
                     f"{API}/organization-identities/<ORG_PROVEEDOR>/contact-profile",
                     body={**PROFILE, "phone": "+57 601 555 0146", "confirmed_by_company_id": str(UNAVAILABLE_COMPANY_ID),
                           "version": 3},
                     why=["Responde `503 DEPENDENCY_UNAVAILABLE` con `dependency: operational-context`; no se guarda nada."],
                     expect=503, show=["status", "code", "dependency"]),
                call("Consultar el historial de versiones", "GET",
                     f"{API}/organization-identities/<ORG_PROVEEDOR>/contact-profile/versions",
                     why=["Las versiones se conservan, de la más reciente a la más antigua, con quién y desde qué "
                          "empresa se confirmó cada una."],
                     show=["total_records"]),
            ],
        ),
        step(
            "05-cerrar-perfil.md", "Cerrar el perfil sin reemplazo", "Dejar la organización sin perfil vigente.",
            [
                call("Cerrar el perfil vigente", "POST",
                     f"{API}/organization-identities/<ORG_PROVEEDOR>/contact-profile:close", body={"version": 3},
                     why=["Exige `delete` sobre `organization_contact_profiles`, aunque no borra: la versión queda en el historial."],
                     show=PROFILE_SHOW),
                call("Repetir el cierre (rechazado)", "POST",
                     f"{API}/organization-identities/<ORG_PROVEEDOR>/contact-profile:close", body={"version": 4},
                     why=["Ya no hay vigente pero sí historia: `409 CONTACT_PROFILE_ALREADY_CLOSED` (si nunca hubiera "
                          "tenido perfil sería `404 CONTACT_PROFILE_NOT_FOUND`)."],
                     expect=409, show=["status", "code"]),
                call("Consultar el perfil vigente (ya no hay)", "GET",
                     f"{API}/organization-identities/<ORG_PROVEEDOR>/contact-profile",
                     why=["`404 CONTACT_PROFILE_NOT_FOUND`: la organización existe, pero no tiene perfil vigente."],
                     expect=404, show=["status", "code"]),
            ],
        ),
    ],
)
