"""Ejercicio 3 de docs/ejemplo/: organizaciones (FR-030–FR-035, DS-11)."""

from tests.examples.spec_common import API, UNKNOWN_COUNTRY_ID, call, get_colombia, step

ORG_SHOW = ["id", "identification_type", "identification_number", "legal_name", "registration_status",
            "status", "version"]

ORGANIZATION = {
    "country_id": "<PAIS_CO>",
    "identification_type": "NIT",
    "identification_number": "900000001-1",
    "legal_name": "COMERCIALIZADORA EJEMPLO FICTICIA S.A.S.",
    "trade_name": "EJEMPLO FICTICIO",
    "organization_type": "SAS",
    "registration_status": "ACTIVA",
}

EX3 = dict(
    folder="3-organizaciones",
    title="Ejercicio 3 — Organizaciones: registrar, rechazos, inactivar y reactivar",
    focus=(
        "Registrar una organización con NIT, los rechazos por **formato** (regla `NIT`) y por **país inexistente**, "
        "y el ciclo **inactivar → reactivar**, incluido el rechazo de una transición repetida y quién puede hacer "
        "cada acción (`supervisor.test` reactiva pero no inactiva)."
    ),
    data=[
        ("Razón social", "COMERCIALIZADORA EJEMPLO FICTICIA S.A.S. (**ficticia**)"),
        ("NIT", "`900000001-1` (**ficticio**; cumple el formato número-guion-dígito, no es un NIT real)"),
        ("NIT mal escrito (rechazo)", "`900000001` sin guion ni dígito de verificación"),
        ("País inexistente (rechazo)", f"`{UNKNOWN_COUNTRY_ID}` (UUID ficticio que Geography no conoce)"),
    ],
    interpretation=[
        ("Regla aplicada", "La regla `NIT` de organizaciones exige `^[A-Z0-9]{4,11}-[0-9]$`."),
        ("País", "Se valida contra Geography: si no existe responde `422 COUNTRY_NOT_FOUND`; si Geography no responde, `503`."),
        ("`registration_status`", "Es el estado legal informativo; **no** controla el uso. El uso lo controla `status`."),
        ("Datos legales", "En un entorno real el NIT y la razón social se toman del RUT o del registro mercantil (RUES); "
         "nunca se inventan: el registro es global."),
    ],
    order_rules=[
        ("País primero", "La organización lleva el `id` del país de registro."),
        ("Inactivar antes de reactivar", "Reactivar una organización activa responde `409 INVALID_STATUS_TRANSITION`."),
    ],
    steps=[
        step(
            "01-consultar-pais.md",
            "Consultar el país",
            "Obtener `<PAIS_CO>`.",
            [get_colombia()],
        ),
        step(
            "02-registrar-organizacion.md",
            "Registrar la organización",
            "Crear la organización y comprobar los rechazos.",
            [
                call(
                    "Registrar la organización con NIT",
                    "POST",
                    f"{API}/organization-identities",
                    body=ORGANIZATION,
                    why=[
                        "`identification_type: NIT` es la sigla; el número va con guion y dígito de verificación.",
                        "`trade_name`, `organization_type`, `registration_status` y `website` son opcionales.",
                    ],
                    save={"ORG_EJEMPLO": "id"},
                    show=ORG_SHOW,
                ),
                call(
                    "Intentar registrar un NIT sin dígito de verificación (rechazado)",
                    "POST",
                    f"{API}/organization-identities",
                    body={**ORGANIZATION, "identification_number": "900000001"},
                    why=["No cumple la regla `NIT`: responde `422 INVALID_IDENTIFICATION_NUMBER` con la descripción de la regla."],
                    expect=422,
                    show=["status", "code", "detail"],
                ),
                call(
                    "Intentar registrar con un país inexistente (rechazado)",
                    "POST",
                    f"{API}/organization-identities",
                    body={**ORGANIZATION, "country_id": UNKNOWN_COUNTRY_ID, "identification_number": "900000002-2"},
                    why=["Geography responde que el país no existe: `422 COUNTRY_NOT_FOUND`; no se guarda nada."],
                    expect=422,
                    show=["status", "code"],
                ),
            ],
        ),
        step(
            "03-inactivar-y-reactivar.md",
            "Inactivar y reactivar",
            "Retirar la organización de uso y volver a activarla.",
            [
                call(
                    "Inactivar la organización",
                    "POST",
                    f"{API}/organization-identities/<ORG_EJEMPLO>/deactivate",
                    body={"version": 1},
                    why=[
                        "Exige `delete` sobre `organization_identities`. No se borra: sigue consultable por `id` con "
                        "`status: INACTIVE`, y los servicios que ya la referencian no se ven afectados.",
                    ],
                    show=ORG_SHOW,
                ),
                call(
                    "Intentar inactivarla otra vez (rechazado)",
                    "POST",
                    f"{API}/organization-identities/<ORG_EJEMPLO>/deactivate",
                    body={"version": 2},
                    why=["Ya está inactiva: `409 INVALID_STATUS_TRANSITION` y la versión no cambia."],
                    expect=409,
                    show=["status", "code"],
                ),
                call(
                    "Reactivar la organización",
                    "POST",
                    f"{API}/organization-identities/<ORG_EJEMPLO>/reactivate",
                    body={"version": 2},
                    why=["Reactivar exige `update`: por eso `supervisor.test` puede reactivar aunque no pueda inactivar."],
                    show=ORG_SHOW,
                ),
                call(
                    "Consultar la organización por `id`",
                    "GET",
                    f"{API}/organization-identities/<ORG_EJEMPLO>",
                    why=["Es la consulta que usan los demás servicios para validar la referencia (contrato Provider)."],
                    show=ORG_SHOW,
                ),
            ],
        ),
    ],
)
