"""Ejercicio 2 de docs/ejemplo/: personas (FR-020–FR-029, DS-02, DS-06, DS-11)."""

from tests.examples.spec_common import API, call, get_colombia, step

PERSON_SHOW = ["id", "identification_type", "identification_number", "first_name", "last_name",
               "verification_status", "status", "version"]

PERSON = {
    "identification_country_id": "<PAIS_CO>",
    "identification_type": "CC",
    "identification_number": "1000000001",
    "first_name": "ANA",
    "middle_name": "MARIA",
    "last_name": "EJEMPLO",
    "second_last_name": "FICTICIA",
    "birth_date": "1990-05-10",
}

EX2 = dict(
    folder="2-personas",
    title="Ejercicio 2 — Personas: registrar, validar, verificar e inactivar",
    focus=(
        "Registrar una persona con cédula, ver cómo se aplican las reglas de Colombia (formato y **edad**), el "
        "rechazo por **duplicado**, el control de **versión** al modificar, el estado de verificación y la "
        "**inactivación** sin borrar (la persona deja de aparecer en la lista, pero sigue consultable por `id`)."
    ),
    data=[
        ("Nombre", "ANA MARIA EJEMPLO FICTICIA (**ficticio**)"),
        ("Documento", "`CC 1000000001` (**ficticio**; cumple el formato de 10 dígitos de la cédula moderna)"),
        ("Fecha de nacimiento", "1990-05-10 (adulta)"),
        ("Menor de edad (rechazo)", "`TI 1000000002` con la misma fecha de nacimiento (**ficticio**)"),
    ],
    interpretation=[
        ("Reglas aplicadas", "`CC` tiene dos reglas activas (moderna y antigua): el número debe cumplir al menos una; ambas "
         "exigen 18 años o más, así que `birth_date` es obligatoria."),
        ("Tarjeta de identidad", "`TI` exige de 7 a 17 años: una persona de 1990 responde `422 AGE_OUT_OF_RANGE`."),
        ("Estados", "`verification_status` (verificación) y `status` (uso) son independientes: inactivar no cambia la "
         "verificación."),
        ("Datos sensibles", "El número completo y la fecha solo se devuelven a quien tiene permiso de lectura; en logs y "
         "mensajes de error se enmascaran (`******0001`)."),
    ],
    order_rules=[
        ("País primero", "La persona lleva el `id` del país emisor, que se obtiene de Geography."),
        ("Registrar antes de modificar", "Cada modificación lleva la `version` leída."),
        ("Inactivar al final", "Una persona inactiva se sigue pudiendo consultar por `id`, pero no aparece en la lista por defecto."),
    ],
    steps=[
        step(
            "01-consultar-pais.md",
            "Consultar el país",
            "Obtener `<PAIS_CO>`.",
            [get_colombia()],
        ),
        step(
            "02-registrar-persona.md",
            "Registrar la persona",
            "Crear la persona y comprobar los rechazos por edad y por duplicado.",
            [
                call(
                    "Registrar a ANA MARIA con cédula",
                    "POST",
                    f"{API}/person-identities",
                    body=PERSON,
                    why=[
                        "`identification_type` es la **sigla** (`CC`); se normaliza a mayúsculas y el número sin espacios exteriores.",
                        "No se envía `verification_status`: queda `UNVERIFIED`. Tampoco `status` ni campos de auditoría "
                        "(`created_by` se toma del token); enviarlos responde `422`.",
                        "El servicio valida el país contra Geography y el número y la edad contra las reglas activas.",
                    ],
                    save={"PERSONA_ANA": "id"},
                    show=PERSON_SHOW,
                ),
                call(
                    "Intentar registrar con tarjeta de identidad (`TI`) a una persona adulta (rechazado)",
                    "POST",
                    f"{API}/person-identities",
                    body={**PERSON, "identification_type": "TI", "identification_number": "1000000002",
                          "first_name": "LUIS", "middle_name": None},
                    why=["La regla `TI` exige de 7 a 17 años; con nacimiento en 1990 responde `422 AGE_OUT_OF_RANGE`."],
                    expect=422,
                    show=["status", "code", "detail"],
                ),
                call(
                    "Intentar registrar otra vez la misma cédula (rechazado)",
                    "POST",
                    f"{API}/person-identities",
                    body={**PERSON, "first_name": "OTRA"},
                    why=["País + tipo + número es único, también frente a personas inactivas: responde `409`. El mensaje no "
                         "muestra el número completo."],
                    expect=409,
                    show=["status", "code", "detail"],
                ),
            ],
        ),
        step(
            "03-verificar-persona.md",
            "Marcar la persona como verificada",
            "Modificar con control de versión.",
            [
                call(
                    "Cambiar `verification_status` a `VERIFIED`",
                    "PUT",
                    f"{API}/person-identities/<PERSONA_ANA>",
                    body={**PERSON, "verification_status": "VERIFIED", "version": 1},
                    why=[
                        "El `PUT` envía la persona completa y la `version` leída (1).",
                        "Como no cambian país, tipo ni número, **no** se consulta Geography: la modificación funciona aunque "
                        "Geography no esté disponible (DS-06).",
                        "Si el cuerpo fuera idéntico al actual, respondería `200` sin cambiar la versión.",
                    ],
                    show=PERSON_SHOW,
                ),
                call(
                    "Repetir el cambio con la versión vieja (rechazado)",
                    "PUT",
                    f"{API}/person-identities/<PERSONA_ANA>",
                    body={**PERSON, "verification_status": "VERIFIED", "version": 1},
                    why=["La persona ya está en la versión 2: responde `409 VERSION_CONFLICT` y no cambia nada."],
                    expect=409,
                    show=["status", "code"],
                ),
            ],
        ),
        step(
            "04-inactivar-persona.md",
            "Inactivar la persona",
            "Retirarla de uso sin borrarla y consultarla con filtro explícito.",
            [
                call(
                    "Inactivar a ANA MARIA",
                    "POST",
                    f"{API}/person-identities/<PERSONA_ANA>/deactivate",
                    body={"version": 2},
                    why=[
                        "Inactivar exige `delete` sobre `person_identities`; reactivar (`/reactivate`) exige `update`.",
                        "`verification_status` sigue `VERIFIED`: son estados independientes.",
                    ],
                    show=["id", "verification_status", "status", "version"],
                ),
                call(
                    "Listar personas (por defecto solo `ACTIVE`)",
                    "GET",
                    f"{API}/person-identities",
                    why=["Sin filtro de estado la lista muestra solo personas activas: ANA MARIA ya no aparece."],
                    show=["total_records"],
                ),
                call(
                    "Listar personas inactivas",
                    "GET",
                    f"{API}/person-identities?status=INACTIVE",
                    why=["Las inactivas se consultan con `status=INACTIVE`. Por `id` se devuelve en cualquier estado."],
                    show=["items[].id", "items[].status", "total_records"],
                ),
            ],
        ),
    ],
)
