"""Ejercicio 4 de docs/ejemplo/: usuarios operativos (Fase B; FR-010 a FR-019, DS-01, DS-03, DS-16)."""

from tests.examples.spec_common import (
    API,
    ORG_EJ4,
    ORG_EJ4B,
    PER_COMPRAS,
    PER_SUPERVISOR,
    PLATFORM,
    TECHNICAL_ACCOUNT,
    call,
    get_organization,
    get_person,
    step,
)

USER_SHOW = ["id", "company_id", "keycloak_user_id", "person_identity_id", "display_name", "status", "version"]

EX4 = dict(
    folder="4-usuarios-operativos",
    title="Ejercicio 4 — Usuarios operativos de una empresa",
    focus=(
        "Registrar **usuarios operativos** (membresías): la cuenta de Keycloak por `username` o `sub`, la persona en "
        "Party Identity, una sola membresía `ACTIVE` por empresa, la **misma persona en dos empresas**, el rechazo de "
        "una **cuenta técnica** y la inactivación y reactivación sin afectar la otra empresa."
    ),
    data=[
        ("Empresa A", "COMERCIALIZADORA USUARIOS FICTICIA S.A.S. (**ficticia**)"),
        ("Empresa B", "ALIADO USUARIOS FICTICIO S.A.S. (**ficticia**)"),
        ("Persona 1", "Supervisora ficticia; cuenta de Keycloak `supervisor.test`"),
        ("Persona 2", "Comprador ficticio; cuenta de Keycloak `compras.test`"),
        ("Cuenta técnica", f"`{TECHNICAL_ACCOUNT}` (cuenta de servicio de un cliente `client_credentials`)"),
    ],
    interpretation=[
        ("Membresía", "Un usuario operativo es la pertenencia de **una persona humana** (cuenta de Keycloak + "
         "`PersonIdentity`) a **una** empresa. La misma persona puede estar en varias empresas."),
        ("Cuenta", "Se indica por `username` o por `keycloak_user_id` (`sub`); el servicio la verifica en Keycloak y "
         "guarda solo el `sub` (DS-03)."),
        ("Persona", "`person_identity_id` es obligatorio y debe estar `ACTIVE` en Party Identity (DS-16)."),
        ("Unicidad", "Como máximo una membresía `ACTIVE` por empresa y persona, y por empresa y cuenta; el historial se "
         "conserva (DS-01)."),
        ("Aislamiento", "Desde que `supervisor.test` es miembro de la empresa A, puede consultarla; los demás usuarios "
         "sin membresía reciben `404`."),
    ],
    order_rules=[
        ("Persona y empresas primero", "La membresía une una empresa existente con una persona de Party Identity."),
        ("Registrar antes de inactivar", "La reactivación vuelve a validar la cuenta y la persona."),
    ],
    steps=[
        step("01-consultar-personas.md", "Consultar las personas en Party Identity",
             "Obtener `<PERSONA_SUPERVISORA>` y `<PERSONA_COMPRADOR>`.", [
                 get_person("PERSONA_SUPERVISORA", PER_SUPERVISOR, "de la supervisora (ficticia)"),
                 get_person("PERSONA_COMPRADOR", PER_COMPRAS, "del comprador (ficticio)"),
             ]),
        step("02-registrar-empresas.md", "Registrar las dos empresas",
             "Crear las empresas A y B (solo el administrador de plataforma).", [
                 get_organization("ORG_A", ORG_EJ4, "COMERCIALIZADORA USUARIOS FICTICIA S.A.S."),
                 get_organization("ORG_B", ORG_EJ4B, "ALIADO USUARIOS FICTICIO S.A.S."),
                 call("Registrar la empresa A", "POST", f"{API}/companies", also=PLATFORM,
                      body={"organization_identity_id": "<ORG_A>"},
                      why=["Registrar empresas exige `platform:administer` (Fase B): solo `admin.test`."],
                      save={"EMPRESA_A": "id"}, show=["id", "status"]),
                 call("Registrar la empresa B", "POST", f"{API}/companies", also=PLATFORM,
                      body={"organization_identity_id": "<ORG_B>"},
                      why=["Segunda empresa para mostrar la misma persona en dos empresas."],
                      save={"EMPRESA_B": "id"}, show=["id", "status"]),
             ]),
        step(
            "03-registrar-usuarios.md",
            "Registrar los usuarios operativos de la empresa A",
            "Registrar a la supervisora por `username` y comprobar los rechazos.",
            [
                call("Registrar a supervisor.test por nombre de usuario", "POST",
                     f"{API}/companies/<EMPRESA_A>/application-users",
                     body={"username": "supervisor.test", "person_identity_id": "<PERSONA_SUPERVISORA>",
                           "display_name": "Supervisora (ficticia)", "reference_email": "supervisora@ficticia.co"},
                     why=["El servicio busca la cuenta `supervisor.test` en Keycloak (solo lectura, con su propia "
                          "identidad técnica) y guarda su `sub`; el `username` no se guarda.",
                          "La persona se valida en Party Identity con el token de quien registra."],
                     save={"USR_SUPERVISORA": "id"}, show=USER_SHOW),
                call("Intentar registrarla otra vez (rechazado)", "POST",
                     f"{API}/companies/<EMPRESA_A>/application-users",
                     body={"username": "supervisor.test", "person_identity_id": "<PERSONA_SUPERVISORA>",
                           "display_name": "Duplicada"},
                     why=["Ya existe una membresía `ACTIVE` de esa persona en la empresa: `409 DUPLICATE_MEMBERSHIP`."],
                     expect=409, show=["status", "code", "detail", "errors"]),
                call("Intentar registrar una cuenta técnica (rechazado)", "POST",
                     f"{API}/companies/<EMPRESA_A>/application-users",
                     body={"keycloak_user_id": TECHNICAL_ACCOUNT, "person_identity_id": "<PERSONA_COMPRADOR>",
                           "display_name": "Servicio"},
                     why=["Las cuentas de servicio (`client_credentials`) no son usuarios operativos: "
                          "`422 TECHNICAL_ACCOUNT_NOT_ALLOWED` (FR-019)."],
                     expect=422, show=["status", "code", "detail"]),
                call("Registrar a compras.test", "POST", f"{API}/companies/<EMPRESA_A>/application-users",
                     body={"username": "compras.test", "person_identity_id": "<PERSONA_COMPRADOR>",
                           "display_name": "Comprador (ficticio)"},
                     why=["Usuario operativo de solo lectura en Operational Context."],
                     save={"USR_COMPRADOR_A": "id"}, show=USER_SHOW),
            ],
        ),
        step(
            "04-consultar-usuarios.md",
            "Consultar los usuarios de la empresa A",
            "Listar las membresías y consultar una por su `id`.",
            [
                call("Listar los usuarios activos de la empresa A", "GET",
                     f"{API}/companies/<EMPRESA_A>/application-users",
                     why=["Solo los miembros de la empresa A (o el administrador de plataforma) la ven: "
                          "`supervisor.test` y `compras.test` responden `200`; los demás, `404`."],
                     show=["items[].keycloak_user_id", "items[].display_name", "total_records"]),
                call("Consultar la supervisora por su `id`", "GET", f"{API}/application-users/<USR_SUPERVISORA>",
                     why=["Es la consulta que usan los demás servicios para el usuario operativo de un documento."],
                     show=USER_SHOW),
            ],
        ),
        step(
            "05-misma-persona-otra-empresa.md",
            "La misma persona en otra empresa",
            "Registrar a `compras.test` también en la empresa B y retirarlo solo de esa empresa.",
            [
                call("Registrar a compras.test en la empresa B", "POST",
                     f"{API}/companies/<EMPRESA_B>/application-users",
                     body={"username": "compras.test", "person_identity_id": "<PERSONA_COMPRADOR>",
                           "display_name": "Comprador (ficticio)"},
                     why=["Ni la persona ni la cuenta son únicas globalmente: son dos membresías independientes."],
                     save={"USR_COMPRADOR_B": "id"}, show=USER_SHOW),
                call("Inactivar la membresía de la empresa B", "POST",
                     f"{API}/application-users/<USR_COMPRADOR_B>/deactivate", body={"version": 1},
                     why=["Solo termina la relación con la empresa B: la membresía de A, la cuenta de Keycloak y la "
                          "`PersonIdentity` no cambian (DS-11)."],
                     show=["status", "version"]),
                call("Consultar la membresía de la empresa A", "GET", f"{API}/application-users/<USR_COMPRADOR_A>",
                     why=["Sigue `ACTIVE`."],
                     show=["company_id", "status", "version"]),
                call("Reactivar la membresía de la empresa B", "POST",
                     f"{API}/application-users/<USR_COMPRADOR_B>/reactivate", body={"version": 2},
                     why=["Reactivar vuelve a validar la cuenta en Keycloak y la persona en Party Identity."],
                     show=["status", "version"]),
            ],
        ),
    ],
)
