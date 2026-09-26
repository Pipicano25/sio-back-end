"""Ejercicio 2 de docs/ejemplo/: sucursales (FR-020 a FR-025, DS-05, DS-08, DS-10)."""

from tests.examples.spec_common import (
    API,
    PLATFORM,
    CIU_BOGOTA,
    CIU_MEDELLIN,
    DIV_ANTIOQUIA,
    DIV_CUNDINAMARCA,
    ORG_EJ2,
    call,
    get_city,
    get_country,
    get_division,
    get_organization,
    step,
)

BRANCH_SHOW = ["id", "company_id", "company_status", "code", "name", "city_id", "timezone",
               "effective_timezone", "status", "version"]

MEDELLIN_BRANCH = {
    "code": " med-01 ",
    "name": "Tienda El Poblado (ficticia)",
    "country_id": "<PAIS_CO>",
    "administrative_division_id": "<DIV_ANT>",
    "city_id": "<CIU_MED>",
}
BOGOTA_BRANCH = {
    "code": "BOG-01",
    "name": "Bodega Norte (ficticia)",
    "country_id": "<PAIS_CO>",
    "administrative_division_id": "<DIV_CUN>",
    "city_id": "<CIU_BOG>",
    "timezone": "America/Bogota",
}

EX2 = dict(
    folder="2-sucursales",
    title="Ejercicio 2 — Sucursales de una empresa",
    focus=(
        "Registrar sucursales con **código único por empresa**, la **zona horaria heredada** frente a la propia, "
        "los rechazos por **código duplicado** y por **ubicación incoherente**, y el **cambio de código** "
        "(las referencias usan el `id`, no el código)."
    ),
    data=[
        ("Organización", "DISTRIBUIDORA EJEMPLO FICTICIA S.A.S. (**ficticia**)"),
        ("Sucursal 1", "`MED-01` Tienda El Poblado, Medellín (**ficticia**), sin zona horaria propia"),
        ("Sucursal 2", "`BOG-01` Bodega Norte, Bogotá (**ficticia**), con zona horaria propia `America/Bogota`"),
        ("Rechazo por incoherencia", "Medellín enviada con el departamento de Cundinamarca"),
    ],
    interpretation=[
        ("Código", "Se recortan los espacios y se pasa a mayúsculas: ` med-01 ` queda `MED-01`. Es único dentro de la empresa, "
         "también frente a sucursales inactivas."),
        ("Zona horaria", "Si la sucursal no tiene zona propia, `effective_timezone` es la de su empresa, calculada en cada "
         "consulta; nunca se copia (DS-08)."),
        ("Coherencia", "La ciudad debe pertenecer al país **y** exactamente a la división enviada (DS-05)."),
        ("Cambio de código", "Está permitido: los demás servicios guardan el `id` de la sucursal (DS-10)."),
    ],
    order_rules=[
        ("Empresa primero", "Las sucursales se crean bajo `/api/v1/companies/<EMPRESA>/branches`."),
        ("Ubicación antes de las sucursales", "Se consultan en Geography los `id` que se envían."),
    ],
    steps=[
        step("01-consultar-organizacion.md", "Consultar la organización", "Obtener `<ORG_EMPRESA>`.",
             [get_organization("ORG_EMPRESA", ORG_EJ2, "DISTRIBUIDORA EJEMPLO FICTICIA S.A.S.")]),
        step("02-consultar-ubicacion.md", "Consultar las ubicaciones",
             "Obtener `<PAIS_CO>`, `<DIV_ANT>`, `<CIU_MED>`, `<DIV_CUN>` y `<CIU_BOG>`.",
             [get_country(),
              get_division("DIV_ANT", DIV_ANTIOQUIA, "Antioquia"),
              get_city("CIU_MED", CIU_MEDELLIN, "Medellín", "DIV_ANT"),
              get_division("DIV_CUN", DIV_CUNDINAMARCA, "Cundinamarca"),
              get_city("CIU_BOG", CIU_BOGOTA, "Bogotá", "DIV_CUN")]),
        step("03-registrar-empresa.md", "Registrar la empresa", "Crear la empresa que tendrá las sucursales.", [
            call("Registrar la empresa", "POST", f"{API}/companies", also=PLATFORM,
                 body={"organization_identity_id": "<ORG_EMPRESA>", "country_id": "<PAIS_CO>"},
                 why=["Solo la organización es obligatoria; la ubicación de la sede puede completarse después."],
                 save={"EMPRESA": "id"}, show=["id", "timezone", "status", "version"]),
        ]),
        step(
            "04-registrar-sucursales.md",
            "Registrar las sucursales",
            "Crear dos sucursales y comprobar los rechazos.",
            [
                call("Registrar la sucursal de Medellín sin zona horaria propia", "POST",
                     f"{API}/companies/<EMPRESA>/branches", body=MEDELLIN_BRANCH,
                     why=["El código ` med-01 ` se normaliza a `MED-01`.",
                          "Sin `timezone`, la sucursal usa la de la empresa (`effective_timezone`)."],
                     save={"SUC_MED": "id"}, show=BRANCH_SHOW),
                call("Registrar la bodega de Bogotá con zona horaria propia", "POST",
                     f"{API}/companies/<EMPRESA>/branches", body=BOGOTA_BRANCH,
                     why=["Con `timezone` propia, esa prevalece sobre la de la empresa."],
                     save={"SUC_BOG": "id"}, show=BRANCH_SHOW),
                call("Intentar repetir el código MED-01 (rechazado)", "POST",
                     f"{API}/companies/<EMPRESA>/branches",
                     body={"code": "MED-01", "name": "Otra tienda (ficticia)"},
                     why=["El código ya existe en la empresa: `409 DUPLICATE_BRANCH_CODE`."],
                     expect=409, show=["status", "code", "detail"]),
                call("Intentar Medellín con el departamento de Cundinamarca (rechazado)", "POST",
                     f"{API}/companies/<EMPRESA>/branches",
                     body={**MEDELLIN_BRANCH, "code": "MED-02", "administrative_division_id": "<DIV_CUN>"},
                     why=["La ciudad no pertenece a la división enviada: `422 GEOGRAPHY_INCOHERENT` en `city_id`."],
                     expect=422, show=["status", "code", "detail", "errors"]),
            ],
        ),
        step(
            "05-consultar-y-cambiar-codigo.md",
            "Consultar las sucursales y cambiar un código",
            "Listar las sucursales de la empresa y cambiar el código de la bodega.",
            [
                call("Listar las sucursales activas de la empresa", "GET", f"{API}/companies/<EMPRESA>/branches",
                     why=["Por defecto solo aparecen las sucursales `ACTIVE`."],
                     show=["items[].code", "items[].effective_timezone", "total_records"]),
                call("Cambiar el código de la bodega", "PUT", f"{API}/branches/<SUC_BOG>",
                     body={**BOGOTA_BRANCH, "code": "BOD-NORTE", "version": 1},
                     why=["El código puede cambiar respetando la unicidad; el `id` no cambia (DS-10).",
                          "No cambia la ubicación: no se consulta Geography."],
                     show=["id", "code", "version"]),
                call("Consultar la bodega por su `id`", "GET", f"{API}/branches/<SUC_BOG>",
                     why=["Es la consulta que usan Inventory, Purchase y Sales (contrato Provider)."],
                     show=BRANCH_SHOW),
            ],
        ),
    ],
)
