"""Ejercicio 7 de docs/ejemplo/: sectores económicos con el árbol CIIU Rev. 5 A.C. (Fase B; FR-050–FR-065)."""

from tests.examples.spec_common import API, call, get_colombia, step

SECTOR_SHOW = ["id", "classification_system", "code", "name", "parent_sector_id", "status", "version"]
ASSIGNMENT_SHOW = ["id", "global_business_sector_id", "is_primary", "is_active", "valid_to", "version"]
CIIU = "classification_system=CIIU_REV5_AC"

ORGANIZATION = {
    "country_id": "<PAIS_CO>",
    "identification_type": "NIT",
    "identification_number": "900000007-7",
    "legal_name": "CAFE Y TIENDA FICTICIA S.A.S.",
}

EX7 = dict(
    folder="7-sectores-economicos",
    title="Ejercicio 7 — Sectores económicos: árbol CIIU, catálogo propio y sectores de una organización",
    focus=(
        "Recorrer el **árbol CIIU Rev. 5 A.C.** que carga el `seed` (sección → división → grupo → clase), crear un "
        "sector en una **clasificación propia** y ver por qué no se inactiva un sector con hijos activos, asignar dos "
        "sectores a una organización, **cambiar el principal** con `set-primary` y **cerrar** una asignación."
    ),
    data=[
        ("Catálogo CIIU", "Datos **oficiales** del DANE (CIIU Rev. 5 A.C.), cargados con "
         "`python -m party_identity_service.seed load-business-sectors`; no son ficticios"),
        ("Clasificación propia", "`EJEMPLO_INTERNO`, códigos `X` y `X1` (**ficticios**)"),
        ("Organización", "CAFE Y TIENDA FICTICIA S.A.S. — NIT `900000007-7` (**ficticios**)"),
        ("Sectores asignados", "Clase CIIU `0123` (Cultivo de café) y clase `4711` (comercio al por menor de alimentos)"),
    ],
    interpretation=[
        ("Árbol", "`parent_sector_id` une clase → grupo → división → sección; las secciones no tienen padre "
         "(`level_root=true`)."),
        ("Identidad del sector", "`classification_system` + `code` es única e inmutable; varias clasificaciones "
         "conviven en el mismo catálogo."),
        ("Inactivación", "Un sector con hijos `ACTIVE` no se inactiva (`409 SECTOR_HAS_ACTIVE_CHILDREN`): primero los "
         "hijos; no hay cascada."),
        ("Sector principal", "Como máximo uno vigente por organización; se cambia con `set-primary`."),
        ("Vigencia", "Las asignaciones usan `[valid_from, valid_to)`; cerradas no se reactivan: se crea una nueva."),
    ],
    order_rules=[
        ("Seed antes de asignar", "Los sectores CIIU deben existir; los carga el `seed`, no la API."),
        ("Padres antes que hijos", "Un sector nuevo exige padre existente, `ACTIVE` y de la misma clasificación."),
        ("Asignar antes de cambiar el principal", "`set-primary` actúa sobre una asignación vigente."),
    ],
    steps=[
        step(
            "01-recorrer-arbol-ciiu.md", "Recorrer el árbol CIIU", "Obtener las secciones y bajar hasta una clase.",
            [
                call("Listar las secciones CIIU (raíces del árbol)", "GET",
                     f"{API}/global-business-sectors?{CIIU}&level_root=true&page_size=5",
                     why=["`level_root=true` devuelve solo sectores sin padre: las 22 secciones de la CIIU Rev. 5 A.C."],
                     show=["total_records"]),
                call("Consultar la sección A", "GET", f"{API}/global-business-sectors?{CIIU}&code=A",
                     why=["`classification_system` + `code` identifican un sector; el `id` cambia entre entornos, el código no."],
                     save={"SECCION_A": "items[0].id"}, show=["total_records"]),
                call("Listar las divisiones de la sección A", "GET",
                     f"{API}/global-business-sectors?parent_sector_id=<SECCION_A>",
                     why=["Los hijos directos se filtran con `parent_sector_id`."], show=["total_records"]),
                call("Consultar la clase 0123 (Cultivo de café)", "GET", f"{API}/global-business-sectors?{CIIU}&code=0123",
                     why=["Se asignan **clases** (4 dígitos), el nivel más específico; el filtro `code` es exacto."],
                     save={"CLASE_CAFE": "items[0].id"}, show=["total_records"]),
                call("Consultar la clase 4711 por texto", "GET",
                     f"{API}/global-business-sectors?{CIIU}&search=4711",
                     why=["`search` busca en el código o en el nombre."],
                     save={"CLASE_TIENDA": "items[0].id"}, show=["total_records"]),
                call("Ver el detalle de la clase 0123", "GET", f"{API}/global-business-sectors/<CLASE_CAFE>",
                     why=["Su padre es el grupo `012` (Cultivos agrícolas permanentes)."], show=SECTOR_SHOW),
            ],
        ),
        step(
            "02-clasificacion-propia.md", "Crear sectores en una clasificación propia",
            "Crear un sector con un hijo y ver el rechazo al inactivar el padre.",
            [
                call("Crear el sector raíz X", "POST", f"{API}/global-business-sectors",
                     body={"classification_system": "ejemplo_interno", "code": " x ", "name": "Sector interno X"},
                     why=["`classification_system` y `code` se normalizan a mayúsculas sin espacios exteriores."],
                     save={"SECTOR_X": "id"}, show=SECTOR_SHOW),
                call("Crear el sector X1, hijo de X", "POST", f"{API}/global-business-sectors",
                     body={"classification_system": "EJEMPLO_INTERNO", "code": "X1", "name": "Subsector interno X1",
                           "parent_sector_id": "<SECTOR_X>"},
                     why=["El padre debe existir, estar `ACTIVE` y ser de la misma clasificación; no se permiten ciclos."],
                     save={"SECTOR_X1": "id"}, show=SECTOR_SHOW),
                call("Intentar colgar X1 de un sector CIIU (rechazado)", "PUT", f"{API}/global-business-sectors/<SECTOR_X1>",
                     body={"name": "Subsector interno X1", "parent_sector_id": "<SECCION_A>", "version": 1},
                     why=["El padre debe ser de la misma clasificación: `422 INVALID_SECTOR_HIERARCHY`."],
                     expect=422, show=["status", "code"]),
                call("Intentar inactivar X con un hijo activo (rechazado)", "POST",
                     f"{API}/global-business-sectors/<SECTOR_X>:deactivate", body={"version": 1},
                     why=["`409 SECTOR_HAS_ACTIVE_CHILDREN`: primero se inactiva X1; no hay cascada."],
                     expect=409, show=["status", "code"]),
                call("Inactivar X1", "POST", f"{API}/global-business-sectors/<SECTOR_X1>:deactivate", body={"version": 1},
                     why=["Se inactiva primero el hijo; exige `delete` y la versión vigente. Nunca se borra."],
                     show=SECTOR_SHOW),
                call("Inactivar X", "POST", f"{API}/global-business-sectors/<SECTOR_X>:deactivate", body={"version": 1},
                     why=["Ya no tiene hijos activos."], show=SECTOR_SHOW),
            ],
        ),
        step("03-consultar-pais.md", "Consultar el país", "Obtener `<PAIS_CO>`.", [get_colombia()]),
        step(
            "04-asignar-sectores.md", "Asignar sectores a una organización",
            "Registrar la organización, asignar dos sectores y cambiar el principal.",
            [
                call("Registrar la organización", "POST", f"{API}/organization-identities", body=ORGANIZATION,
                     why=["Las personas de contacto, sectores y representantes cuelgan de una organización `ACTIVE` de Party Identity; se registra primero con datos **ficticios** (NIT que cumple la regla `NIT`, no es real)."],
                     save={"ORG_CAFE": "id"}, show=["id", "legal_name", "status"]),
                call("Asignar la clase 0123 como sector principal", "POST",
                     f"{API}/organization-identities/<ORG_CAFE>/business-sectors",
                     body={"global_business_sector_id": "<CLASE_CAFE>", "is_primary": True},
                     why=["Sin `valid_from`, la vigencia empieza ahora."],
                     save={"ASIG_CAFE": "id"}, show=ASSIGNMENT_SHOW),
                call("Asignar la clase 4711 como sector secundario", "POST",
                     f"{API}/organization-identities/<ORG_CAFE>/business-sectors",
                     body={"global_business_sector_id": "<CLASE_TIENDA>", "is_primary": False},
                     why=["Una organización puede tener varios sectores vigentes; solo uno es principal."],
                     save={"ASIG_TIENDA": "id"}, show=ASSIGNMENT_SHOW),
                call("Intentar asignar otra vez la clase 4711 (rechazado)", "POST",
                     f"{API}/organization-identities/<ORG_CAFE>/business-sectors",
                     body={"global_business_sector_id": "<CLASE_TIENDA>", "is_primary": False},
                     why=["Ya hay una asignación vigente de ese sector: `409 DUPLICATE_ACTIVE_SECTOR_ASSIGNMENT`."],
                     expect=409, show=["status", "code"]),
                call("Cambiar el sector principal a 4711", "POST",
                     f"{API}/organization-business-sectors/<ASIG_TIENDA>:set-primary", body={"version": 1},
                     why=["Desmarca el principal anterior (su `version` también aumenta) en la misma transacción."],
                     show=ASSIGNMENT_SHOW),
            ],
        ),
        step(
            "05-cerrar-asignacion.md", "Cerrar una asignación y ver el historial",
            "Cerrar el sector 0123 y consultar las asignaciones.",
            [
                call("Cerrar la asignación de la clase 0123", "POST",
                     f"{API}/organization-business-sectors/<ASIG_CAFE>:close", body={"version": 2},
                     why=["Exige `delete`; no borra: guarda `valid_to`.",
                          "`version` es 2 porque `set-primary` la desmarcó como principal."],
                     show=ASSIGNMENT_SHOW),
                call("Consultar los sectores vigentes", "GET",
                     f"{API}/organization-identities/<ORG_CAFE>/business-sectors",
                     why=["`state` omitido equivale a `active`."], show=["total_records"]),
                call("Consultar el historial completo", "GET",
                     f"{API}/organization-identities/<ORG_CAFE>/business-sectors?state=all",
                     why=["`state=active`, `closed` o `all`. Una asignación cerrada no se reactiva."],
                     show=["total_records"]),
            ],
        ),
    ],
)
