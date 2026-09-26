"""Ejercicio 6 de docs/ejemplo/: asesores de la empresa (Fase B; FR-050 a FR-058, DS-13, DS-15)."""

from tests.examples.spec_common import (
    API,
    ORG_EJ6,
    PER_ASESOR_1,
    PER_ASESOR_2,
    PER_ASESOR_3,
    PLATFORM,
    call,
    get_organization,
    get_person,
    step,
)

DELETE = ["perm:operational-context:company_advisor_assignments:delete"]
ADVISOR_SHOW = ["id", "person_identity_id", "is_primary", "status", "assigned_by", "version"]

EX6 = dict(
    folder="6-asesores",
    title="Ejercicio 6 — Asesores de la empresa",
    focus=(
        "Registrar el **asesor principal**, rechazar un segundo principal, agregar un asesor no principal, "
        "**cambiar el asesor principal** en una sola operación y consultar el **historial**."
    ),
    data=[
        ("Empresa", "ASESORADA EJEMPLO FICTICIA S.A.S. (**ficticia**)"),
        ("Asesor 1", "Primer asesor principal (persona **ficticia**)"),
        ("Asesor 2", "Nuevo asesor principal (persona **ficticia**)"),
        ("Asesor 3", "Asesor no principal (persona **ficticia**)"),
        ("Vigencias", "Fechas pasadas fijas, para que el historial sea reproducible"),
    ],
    interpretation=[
        ("Asesor", "Persona de Party Identity relacionada con la empresa con vigencia; no exige cuenta en SIO."),
        ("Principal", "Como máximo un asesor principal vigente por empresa; puede haber varios no principales."),
        ("Cambio", "`change-primary` cierra la asignación vigente y crea la nueva en una sola transacción; nunca "
         "sobrescribe la persona de una asignación (DS-13)."),
        ("Validación", "La persona se valida en Party Identity al crear y en el cambio, antes de escribir (DS-15)."),
    ],
    order_rules=[
        ("Principal antes del cambio", "Sin asesor principal vigente, el cambio responde `409 NO_ACTIVE_PRIMARY_ADVISOR`."),
        ("Cerrar no reabre", "Una asignación cerrada es inmutable: el historial solo crece."),
    ],
    steps=[
        step("01-consultar-datos.md", "Consultar la organización y las personas",
             "Obtener `<ORG_EMPRESA>` y las tres personas.", [
                 get_organization("ORG_EMPRESA", ORG_EJ6, "ASESORADA EJEMPLO FICTICIA S.A.S."),
                 get_person("PERSONA_ASESOR_1", PER_ASESOR_1, "del primer asesor (ficticio)"),
                 get_person("PERSONA_ASESOR_2", PER_ASESOR_2, "del nuevo asesor (ficticio)"),
                 get_person("PERSONA_ASESOR_3", PER_ASESOR_3, "del asesor no principal (ficticio)"),
             ]),
        step("02-registrar-empresa.md", "Registrar la empresa", "Crear la empresa asesorada.", [
            call("Registrar la empresa", "POST", f"{API}/companies", also=PLATFORM,
                 body={"organization_identity_id": "<ORG_EMPRESA>"},
                 why=["Solo el administrador de plataforma registra empresas."],
                 save={"EMPRESA": "id"}, show=["id", "status"]),
        ]),
        step(
            "03-registrar-asesores.md",
            "Registrar los asesores",
            "Registrar el asesor principal y uno no principal.",
            [
                call("Registrar el asesor principal", "POST", f"{API}/companies/<EMPRESA>/advisor-assignments",
                     body={"person_identity_id": "<PERSONA_ASESOR_1>", "valid_from": "2026-01-01T00:00:00-05:00"},
                     why=["`is_primary` es `true` por defecto; `valid_from` puede ser pasada, nunca futura."],
                     save={"ASESORIA_1": "id"}, show=ADVISOR_SHOW),
                call("Intentar un segundo asesor principal (rechazado)", "POST",
                     f"{API}/companies/<EMPRESA>/advisor-assignments",
                     body={"person_identity_id": "<PERSONA_ASESOR_2>"},
                     why=["Ya hay un principal vigente: `409 PRIMARY_ADVISOR_EXISTS`; para reemplazarlo se usa "
                          "`change-primary`."],
                     expect=409, show=["status", "code", "detail"]),
                call("Registrar un asesor no principal", "POST", f"{API}/companies/<EMPRESA>/advisor-assignments",
                     body={"person_identity_id": "<PERSONA_ASESOR_3>", "is_primary": False,
                           "valid_from": "2026-02-01T00:00:00-05:00"},
                     why=["Puede haber varios asesores vigentes; solo uno principal."],
                     save={"ASESORIA_3": "id"}, show=ADVISOR_SHOW),
            ],
        ),
        step(
            "04-cambiar-asesor-principal.md",
            "Cambiar el asesor principal",
            "Reemplazar al asesor 1 por el asesor 2 en una sola operación.",
            [
                call("Cambiar el asesor principal", "POST",
                     f"{API}/companies/<EMPRESA>/advisor-assignments/change-primary", also=DELETE,
                     body={"current_assignment_id": "<ASESORIA_1>", "version": 1,
                           "person_identity_id": "<PERSONA_ASESOR_2>", "effective_at": "2026-06-01T00:00:00-05:00"},
                     why=["Exige `create` **y** `delete` de asesores: `supervisor.test` no puede.",
                          "Cierra la asignación 1 (`valid_to` = `effective_at`) y crea la 2 en la misma transacción."],
                     save={"ASESORIA_2": "created.id"},
                     show=["closed.id", "closed.status", "created.id", "created.person_identity_id",
                           "created.is_primary", "created.status"]),
            ],
        ),
        step(
            "05-historial-y-cierre.md",
            "Consultar el historial y cerrar un asesor",
            "Ver el historial completo y cerrar al asesor no principal.",
            [
                call("Consultar el historial de asesores", "GET", f"{API}/companies/<EMPRESA>/advisor-assignments",
                     why=["Sin filtro de estado devuelve vigentes y cerradas, de la vigencia más reciente a la más antigua."],
                     show=["items[].person_identity_id", "items[].is_primary", "items[].status", "total_records"]),
                call("Cerrar la asignación del asesor no principal", "POST",
                     f"{API}/advisor-assignments/<ASESORIA_3>/close",
                     body={"version": 1, "valid_to": "2026-07-01T00:00:00-05:00"},
                     why=["Exige `delete`; no elimina: fija `valid_to` y la deja `INACTIVE`."],
                     show=["id", "status", "version"]),
                call("Intentar cerrarla otra vez (rechazado)", "POST", f"{API}/advisor-assignments/<ASESORIA_3>/close",
                     body={"version": 2},
                     why=["Una asignación cerrada es inmutable: `409 INVALID_STATUS_TRANSITION`."],
                     expect=409, show=["status", "code", "detail"]),
            ],
        ),
    ],
)
