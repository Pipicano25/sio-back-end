"""Ejercicio 5 de docs/ejemplo/: sucursales asignadas y acceso operativo (Fase B; FR-020 a FR-025, FR-070, FR-071)."""

from tests.examples.spec_common import (
    API,
    ORG_EJ5,
    PER_COMPRAS,
    PLATFORM,
    call,
    get_organization,
    get_person,
    step,
)

LOOKUP = ["perm:operational-context:platform:lookup"]
ACCESS_SHOW = ["allowed", "reason", "keycloak_user_id", "application_user_id", "permission"]
ASSIGNMENT_SHOW = ["id", "branch_id", "status", "assigned_by", "operational_access"]

EX5 = dict(
    folder="5-sucursales-y-acceso",
    title="Ejercicio 5 — Sucursales asignadas y acceso operativo",
    focus=(
        "Asignar sucursales a un usuario operativo y comprobar su **acceso operativo** con "
        "`GET /api/v1/operational-access`: permitido, cada **causa estable** de denegación y la **vía técnica** que "
        "evalúa el permiso con los roles del usuario objetivo."
    ),
    data=[
        ("Empresa", "LOGÍSTICA ACCESO FICTICIA S.A.S. (**ficticia**)"),
        ("Sucursales", "`PRI-01` Principal y `SEC-01` Secundaria (**ficticias**)"),
        ("Usuario", "`compras.test` (grupo `compras`: `perm:purchase:all:all`, lecturas)"),
    ],
    interpretation=[
        ("Acceso efectivo", "Se calcula en cada consulta: membresía, empresa, sucursal y asignación `ACTIVE` y, si se "
         "indica, el permiso de la operación. Una sola condición fallida niega el acceso (DS-07)."),
        ("Respuesta", "Siempre `200` con `allowed` y una causa estable (`reason`); `4xx`/`5xx` solo para errores de "
         "contrato (DS-08)."),
        ("Vía técnica", "Con `keycloak_user_id` exige `platform:lookup`; el permiso se evalúa con los roles del usuario "
         "leídos de Keycloak, nunca con los del token que consulta (R-11)."),
        ("Autor", "`assigned_by` es siempre el `sub` de quien asigna (DS-10)."),
    ],
    order_rules=[
        ("Membresía antes de asignar", "Solo se asignan sucursales de la empresa de la membresía."),
        ("Asignar antes de consultar el acceso", "Sin asignación la causa es `BRANCH_NOT_ASSIGNED`."),
    ],
    steps=[
        step("01-consultar-datos.md", "Consultar la organización y la persona",
             "Obtener `<ORG_EMPRESA>` y `<PERSONA_COMPRADOR>`.", [
                 get_organization("ORG_EMPRESA", ORG_EJ5, "LOGÍSTICA ACCESO FICTICIA S.A.S."),
                 get_person("PERSONA_COMPRADOR", PER_COMPRAS, "del comprador (ficticio)"),
             ]),
        step("02-empresa-y-sucursales.md", "Registrar la empresa, sus sucursales y el usuario",
             "Crear la empresa, dos sucursales y la membresía de `compras.test`.", [
                 call("Registrar la empresa", "POST", f"{API}/companies", also=PLATFORM,
                      body={"organization_identity_id": "<ORG_EMPRESA>"},
                      why=["Solo el administrador de plataforma registra empresas."],
                      save={"EMPRESA": "id"}, show=["id", "status"]),
                 call("Registrar la sucursal principal", "POST", f"{API}/companies/<EMPRESA>/branches",
                      body={"code": "PRI-01", "name": "Principal (ficticia)"},
                      why=["Sucursal a la que se asignará el usuario."],
                      save={"SUC_PRINCIPAL": "id"}, show=["id", "code", "status"]),
                 call("Registrar la sucursal secundaria", "POST", f"{API}/companies/<EMPRESA>/branches",
                      body={"code": "SEC-01", "name": "Secundaria (ficticia)"},
                      why=["Sucursal sin asignar, para ver `BRANCH_NOT_ASSIGNED`."],
                      save={"SUC_SECUNDARIA": "id"}, show=["id", "code", "status"]),
                 call("Registrar a compras.test como usuario operativo", "POST",
                      f"{API}/companies/<EMPRESA>/application-users",
                      body={"username": "compras.test", "person_identity_id": "<PERSONA_COMPRADOR>",
                            "display_name": "Comprador (ficticio)"},
                      why=["La membresía es requisito del acceso operativo."],
                      save={"USR_COMPRADOR": "id"}, show=["id", "keycloak_user_id", "status"]),
             ]),
        step(
            "03-asignar-sucursal.md",
            "Asignar la sucursal principal",
            "Asignar `PRI-01` al usuario y ver su acceso calculado.",
            [
                call("Asignar la sucursal principal", "POST",
                     f"{API}/application-users/<USR_COMPRADOR>/user-branches",
                     body={"branch_id": "<SUC_PRINCIPAL>"},
                     why=["El cuerpo solo lleva la sucursal; el usuario viene de la ruta y el autor del token."],
                     save={"ASIGNACION": "id"}, show=ASSIGNMENT_SHOW),
                call("Intentar asignarla otra vez (rechazado)", "POST",
                     f"{API}/application-users/<USR_COMPRADOR>/user-branches",
                     body={"branch_id": "<SUC_PRINCIPAL>"},
                     why=["La pareja usuario + sucursal es única: `409 DUPLICATE_USER_BRANCH` (se reactiva, no se duplica)."],
                     expect=409, show=["status", "code", "detail"]),
                call("Listar las sucursales asignadas al usuario", "GET",
                     f"{API}/application-users/<USR_COMPRADOR>/user-branches",
                     why=["Cada asignación informa su acceso operativo calculado (sin permiso concreto)."],
                     show=["items[].branch_id", "items[].status", "items[].operational_access", "total_records"]),
            ],
        ),
        step(
            "04-comprobar-acceso.md",
            "Comprobar el acceso operativo (vía técnica)",
            "Consultar el acceso de `compras.test` como lo haría Purchase con su identidad técnica.",
            [
                call("Acceso a la sucursal principal para crear compras", "GET",
                     f"{API}/operational-access?branch_id=<SUC_PRINCIPAL>&keycloak_user_id=compras.test"
                     "&permission=perm:purchase:purchases:create", also=LOOKUP,
                     why=["`compras.test` es miembro, tiene la sucursal asignada y su grupo tiene `perm:purchase:all:all`: "
                          "`allowed: true`.",
                          "El permiso se evalúa con los roles de `compras.test` leídos de Keycloak, no con los del token "
                          "que consulta."],
                     show=ACCESS_SHOW),
                call("Acceso para crear ventas (denegado)", "GET",
                     f"{API}/operational-access?branch_id=<SUC_PRINCIPAL>&keycloak_user_id=compras.test"
                     "&permission=perm:sales:sales:create", also=LOOKUP,
                     why=["El grupo `compras` no tiene permisos de ventas: `allowed: false`, `PERMISSION_DENIED`, "
                          "con `200` (no es un error del contrato)."],
                     show=ACCESS_SHOW),
                call("Acceso a la sucursal secundaria (denegado)", "GET",
                     f"{API}/operational-access?branch_id=<SUC_SECUNDARIA>&keycloak_user_id=compras.test",
                     also=LOOKUP,
                     why=["Sin asignación a esa sucursal: `BRANCH_NOT_ASSIGNED`."],
                     show=ACCESS_SHOW),
            ],
        ),
        step(
            "05-efecto-de-inactivar.md",
            "Efecto de inactivar la asignación y la sucursal",
            "Retirar la asignación, inactivar la sucursal y volver a comprobar.",
            [
                call("Retirar la asignación", "POST", f"{API}/user-branches/<ASIGNACION>/deactivate",
                     body={"version": 1},
                     why=["No se elimina: queda `INACTIVE` con su fecha de retiro."],
                     show=["status", "version", "operational_access"]),
                call("Acceso tras retirar la asignación (denegado)", "GET",
                     f"{API}/operational-access?branch_id=<SUC_PRINCIPAL>&keycloak_user_id=compras.test",
                     also=LOOKUP,
                     why=["La asignación existe pero está inactiva: `USER_BRANCH_INACTIVE`."],
                     show=ACCESS_SHOW),
                call("Inactivar la sucursal principal", "POST", f"{API}/branches/<SUC_PRINCIPAL>/deactivate",
                     body={"version": 1},
                     why=["Inactivar la sucursal no modifica las asignaciones (DS-11)."],
                     show=["status", "version"]),
                call("Acceso a la sucursal inactiva (denegado)", "GET",
                     f"{API}/operational-access?branch_id=<SUC_PRINCIPAL>&keycloak_user_id=compras.test",
                     also=LOOKUP,
                     why=["En la vía técnica se evalúa primero la empresa y luego la sucursal: `BRANCH_INACTIVE`."],
                     show=ACCESS_SHOW),
            ],
        ),
    ],
)
