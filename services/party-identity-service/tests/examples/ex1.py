"""Ejercicio 1 de docs/ejemplo/: reglas de identificación (DS-07, FR-010–FR-014)."""

from tests.examples.spec_common import API, call, get_colombia, step

RULE_SHOW = ["id", "party_kind", "identification_type", "sigla", "number_pattern", "min_age_years",
             "max_age_years", "is_active", "valid_to", "version"]

EX1 = dict(
    folder="1-reglas-de-identificacion",
    title="Ejercicio 1 — Reglas de identificación: crear, versionar y retirar",
    focus=(
        "Cómo se administra una regla de validación sin cambiar código: consultar las reglas de Colombia que dejó "
        "la carga inicial, crear una regla nueva, ver los rechazos (`409` duplicada, `422` patrón inválido), "
        "corregir su descripción, **crear una nueva versión** cuando cambia el patrón y **retirarla** sin borrarla."
    ),
    data=[
        ("País", "Colombia (`COL`), consultado en Geography Service"),
        ("Tipo de parte", "`PERSON`"),
        ("Tipo de identificación nuevo", "`PASSPORT` con sigla `PA` (la carga inicial no trae pasaporte)"),
        ("Patrón inicial", "`^[A-Z0-9]{6,9}$`: 6 a 9 letras o dígitos"),
        ("Patrón corregido", "`^[A-Z]{2}[0-9]{6,7}$`: 2 letras y 6 o 7 dígitos"),
        ("Ejemplos", "`AB123456` (**ficticio**; no corresponde a ningún pasaporte real)"),
    ],
    interpretation=[
        ("Reglas de Colombia", "La carga inicial (`python -m party_identity_service.seed load`) deja 8 reglas activas; "
         "se consultan sin modificarlas."),
        ("Pasaporte", "No existe regla `PA`: sin regla, una persona con esa sigla solo tiene validaciones base (DS-03). "
         "Crear la regla hace que se valide el formato."),
        ("Cambio de patrón", "No se hace con `PUT`: se crea una **nueva versión** (`POST .../versions`). La anterior queda "
         "histórica (`is_active: false`, `valid_to` informado) para conservar con qué regla se validó cada dato."),
        ("Retiro", "`POST .../deactivate` deja la regla histórica; nunca se elimina (D7). Una regla histórica no admite cambios."),
    ],
    order_rules=[
        ("País primero", "Toda regla lleva el `id` del país, que se obtiene de Geography."),
        ("Crear antes de versionar", "Solo una regla activa puede tener una nueva versión."),
        ("Versión antes de retirar", "Se retira la versión vigente; la anterior ya quedó histórica al versionar."),
    ],
    steps=[
        step(
            "01-consultar-pais-y-reglas.md",
            "Consultar el país y las reglas de Colombia",
            "Obtener `<PAIS_CO>` y ver las reglas `CC` que dejó la carga inicial.",
            [
                get_colombia(),
                call(
                    "Consultar las reglas activas de cédula (`CC`) de Colombia",
                    "GET",
                    f"{API}/identification-type-rules?country_id=<PAIS_CO>&sigla=CC&is_active=true",
                    why=[
                        "Hay dos reglas `CC`: la cédula moderna (10 dígitos) y la antigua (3 a 8). Un número es válido si cumple "
                        "**al menos una** de las reglas activas de la sigla.",
                        "`is_active=true` excluye las reglas históricas.",
                    ],
                    show=["items[].identification_type", "items[].sigla", "items[].number_pattern",
                          "items[].min_age_years", "items[].is_active", "total_records"],
                ),
            ],
        ),
        step(
            "02-crear-regla.md",
            "Crear la regla de pasaporte",
            "Crear la regla `PASSPORT` / `PA` y comprobar los rechazos.",
            [
                call(
                    "Crear la regla `PASSPORT` (`PA`)",
                    "POST",
                    f"{API}/identification-type-rules",
                    body={
                        "party_kind": "PERSON",
                        "country_id": "<PAIS_CO>",
                        "identification_type": "PASSPORT",
                        "sigla": "PA",
                        "number_pattern": "^[A-Z0-9]{6,9}$",
                        "number_pattern_description": "Pasaporte: 6 a 9 letras o dígitos.",
                        "example_value": "AB123456",
                    },
                    why=[
                        "`identification_type` es el formato concreto; `sigla` es lo que se escribe al registrar la persona.",
                        "`example_value` debe cumplir el patrón: si no, responde `422 EXAMPLE_DOES_NOT_MATCH_PATTERN`.",
                        "No se envían edades: el pasaporte no restringe la edad.",
                        "El servicio valida `<PAIS_CO>` contra Geography antes de guardar.",
                    ],
                    save={"REGLA_PA": "id"},
                    show=RULE_SHOW,
                ),
                call(
                    "Intentar crear otra regla activa igual (rechazado)",
                    "POST",
                    f"{API}/identification-type-rules",
                    body={
                        "party_kind": "PERSON",
                        "country_id": "<PAIS_CO>",
                        "identification_type": "PASSPORT",
                        "sigla": "PA",
                        "number_pattern": "^[A-Z0-9]{6,9}$",
                        "number_pattern_description": "Duplicado.",
                    },
                    why=["Solo puede haber **una** regla activa por tipo de parte + país + tipo de identificación."],
                    expect=409,
                    show=["status", "code", "detail"],
                ),
                call(
                    "Intentar crear una regla con un patrón inválido (rechazado)",
                    "POST",
                    f"{API}/identification-type-rules",
                    body={
                        "party_kind": "PERSON",
                        "country_id": "<PAIS_CO>",
                        "identification_type": "DIPLOMATIC_ID",
                        "sigla": "CD",
                        "number_pattern": "^[0-9{5}$",
                        "number_pattern_description": "Patrón mal escrito.",
                    },
                    why=["El patrón es una expresión regular; si no compila responde `422 INVALID_NUMBER_PATTERN`."],
                    expect=422,
                    show=["status", "code"],
                ),
            ],
        ),
        step(
            "03-corregir-descripcion.md",
            "Corregir la descripción",
            "Modificar en sitio lo que no cambia la validación.",
            [
                call(
                    "Corregir la descripción y el ejemplo",
                    "PUT",
                    f"{API}/identification-type-rules/<REGLA_PA>",
                    body={
                        "number_pattern_description": "Pasaporte colombiano: 6 a 9 letras o dígitos, sin espacios.",
                        "example_value": "AB123456",
                        "version": 1,
                    },
                    why=[
                        "El `PUT` solo cambia la descripción y el ejemplo. Enviar otro `number_pattern` o edades responde "
                        "`422 RULE_CHANGE_REQUIRES_NEW_VERSION`, y cambiar país, tipo o sigla `422 IMMUTABLE_FIELD`.",
                        "`version` es la que se leyó; si otro usuario la cambió antes, responde `409 VERSION_CONFLICT`.",
                    ],
                    show=["id", "number_pattern_description", "version", "is_active"],
                ),
                call(
                    "Intentar cambiar el patrón con `PUT` (rechazado)",
                    "PUT",
                    f"{API}/identification-type-rules/<REGLA_PA>",
                    body={
                        "number_pattern_description": "Pasaporte colombiano: 6 a 9 letras o dígitos, sin espacios.",
                        "example_value": "AB123456",
                        "number_pattern": "^[A-Z]{2}[0-9]{6,7}$",
                        "version": 2,
                    },
                    why=["Cambiar el patrón exige una nueva versión (paso siguiente)."],
                    expect=422,
                    show=["status", "code"],
                ),
            ],
        ),
        step(
            "04-nueva-version.md",
            "Crear una nueva versión de la regla",
            "Cambiar el patrón conservando la regla anterior como histórica.",
            [
                call(
                    "Crear la nueva versión con el patrón corregido",
                    "POST",
                    f"{API}/identification-type-rules/<REGLA_PA>/versions",
                    body={
                        "number_pattern": "^[A-Z]{2}[0-9]{6,7}$",
                        "number_pattern_description": "Pasaporte: 2 letras y 6 o 7 dígitos.",
                        "example_value": "AB123456",
                        "version": 2,
                    },
                    why=[
                        "En una sola transacción la regla actual queda histórica y se crea la nueva, activa.",
                        "La nueva regla conserva país, tipo y sigla; tiene su propio `id`.",
                        "Exige `create` sobre `identification_type_rules` (es una regla nueva), no `update`.",
                    ],
                    save={"REGLA_PA_V2": "id"},
                    show=RULE_SHOW,
                ),
                call(
                    "Consultar la regla anterior",
                    "GET",
                    f"{API}/identification-type-rules/<REGLA_PA>",
                    why=["Sigue existiendo, ahora histórica: `is_active: false` y `valid_to` con la fecha del cambio."],
                    show=["id", "number_pattern", "is_active", "version"],
                ),
            ],
        ),
        step(
            "05-retirar-regla.md",
            "Retirar la regla",
            "Dejar histórica la versión vigente, sin borrarla.",
            [
                call(
                    "Retirar la versión vigente",
                    "POST",
                    f"{API}/identification-type-rules/<REGLA_PA_V2>/deactivate",
                    body={"version": 1},
                    why=[
                        "Retirar exige `delete` sobre `identification_type_rules`; la regla no se elimina (D7).",
                        "Sin regla activa `PA`, las personas con esa sigla vuelven a validarse solo con las reglas base.",
                    ],
                    show=["id", "is_active", "version"],
                ),
                call(
                    "Intentar retirarla otra vez (rechazado)",
                    "POST",
                    f"{API}/identification-type-rules/<REGLA_PA_V2>/deactivate",
                    body={"version": 2},
                    why=["Una regla histórica no admite cambios: responde `409 INVALID_STATUS_TRANSITION`."],
                    expect=409,
                    show=["status", "code"],
                ),
            ],
        ),
    ],
)
