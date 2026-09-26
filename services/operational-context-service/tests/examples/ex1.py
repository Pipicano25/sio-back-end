"""Ejercicio 1 de docs/ejemplo/: empresa con sede operativa principal (FR-010 a FR-016, DS-01, DS-13)."""

from tests.examples.spec_common import (
    API,
    CIU_MEDELLIN,
    DIV_ANTIOQUIA,
    ORG_EJ1,
    UNKNOWN_ORGANIZATION,
    call,
    get_city,
    get_country,
    get_division,
    get_organization,
    step,
)

COMPANY_SHOW = ["id", "organization_identity_id", "email", "phone", "country_id", "administrative_division_id",
                "city_id", "latitude", "longitude", "timezone", "default_currency", "status", "version"]

COMPANY = {
    "organization_identity_id": "<ORG_EMPRESA>",
    "email": "contacto@comercializadora-ficticia.co",
    "phone": "+57 604 000 0001",
    "address_line": "Carrera Ficticia 43A # 1-50",
    "country_id": "<PAIS_CO>",
    "administrative_division_id": "<DIV_ANT>",
    "city_id": "<CIU_MED>",
    "postal_code": "050021",
    "latitude": "6.208000",
    "longitude": "-75.567000",
}

EX1 = dict(
    folder="1-empresa-con-sede",
    title="Ejercicio 1 — Empresa con su sede operativa principal",
    focus=(
        "Registrar una empresa **vinculada a su identidad legal** de Party Identity, con la ubicación coherente "
        "de su **sede operativa principal**; consultarla y modificarla con control de **versión**; y el rechazo "
        "cuando la organización no existe."
    ),
    data=[
        ("Organización", "COMERCIALIZADORA EJEMPLO FICTICIA S.A.S. (**ficticia**), ya registrada en Party Identity"),
        ("Correo y teléfono de la sede", "`contacto@comercializadora-ficticia.co`, `+57 604 000 0001` (**ficticios**)"),
        ("Dirección de la sede", "Carrera Ficticia 43A # 1-50, Medellín (**ficticia**)"),
        ("Coordenadas", "`6.208000`, `-75.567000` (aproximadas, ilustrativas)"),
        ("Organización inexistente (rechazo)", f"`{UNKNOWN_ORGANIZATION}` (UUID que Party Identity no conoce)"),
    ],
    interpretation=[
        ("Identidad legal", "La empresa **no guarda** NIT, razón social ni nombre comercial: se consultan en Party "
         "Identity con `organization_identity_id` (DS-01, DS-13)."),
        ("Contacto", "Correo, teléfono y dirección son de la **sede operativa principal** en SIO; no son el contacto "
         "global de la organización (DS-14)."),
        ("Ubicación", "País, departamento y ciudad son `id` de Geography; se validan juntos y deben ser coherentes."),
        ("Zona horaria y moneda", "Si no se envían, la empresa queda con `America/Bogota` y `COP`."),
    ],
    order_rules=[
        ("Organización primero", "La empresa exige el `id` de una organización `ACTIVE` de Party Identity."),
        ("Ubicación antes de la empresa", "País → departamento → ciudad: cada consulta usa el `id` anterior."),
        ("Versión", "Para modificar se envía la `version` leída; la respuesta trae la nueva."),
    ],
    steps=[
        step("01-consultar-organizacion.md", "Consultar la organización", "Obtener `<ORG_EMPRESA>`.",
             [get_organization("ORG_EMPRESA", ORG_EJ1, "COMERCIALIZADORA EJEMPLO FICTICIA S.A.S.")]),
        step("02-consultar-ubicacion.md", "Consultar la ubicación de la sede",
             "Obtener `<PAIS_CO>`, `<DIV_ANT>` y `<CIU_MED>`.",
             [get_country(), get_division("DIV_ANT", DIV_ANTIOQUIA, "Antioquia"),
              get_city("CIU_MED", CIU_MEDELLIN, "Medellín", "DIV_ANT")]),
        step(
            "03-registrar-empresa.md",
            "Registrar la empresa",
            "Crear la empresa y comprobar el rechazo por organización inexistente.",
            [
                call(
                    "Registrar la empresa con su sede operativa principal",
                    "POST",
                    f"{API}/companies",
                    body=COMPANY,
                    why=[
                        "`organization_identity_id` es **obligatorio**: la empresa se identifica por su organización.",
                        "No se envían `timezone` ni `default_currency`: quedan `America/Bogota` y `COP`.",
                        "Las coordenadas se envían como texto decimal (hasta 6 decimales, sin redondeo).",
                    ],
                    save={"EMPRESA": "id"},
                    show=COMPANY_SHOW,
                ),
                call(
                    "Intentar registrar una empresa con una organización inexistente (rechazado)",
                    "POST",
                    f"{API}/companies",
                    body={"organization_identity_id": UNKNOWN_ORGANIZATION},
                    why=["Party Identity responde `404`: la API responde `422 ORGANIZATION_IDENTITY_NOT_FOUND` y no guarda nada."],
                    expect=422,
                    show=["status", "code", "detail", "errors"],
                ),
            ],
        ),
        step(
            "04-consultar-y-modificar.md",
            "Consultar y modificar la empresa",
            "Leer la empresa, cambiar el teléfono con la versión vigente y buscarla por su organización.",
            [
                call("Consultar la empresa por su `id`", "GET", f"{API}/companies/<EMPRESA>",
                     why=["Es la consulta que usan los demás servicios (contrato Provider)."], show=COMPANY_SHOW),
                call(
                    "Modificar el teléfono con la versión vigente",
                    "PUT",
                    f"{API}/companies/<EMPRESA>",
                    body={**COMPANY, "phone": "+57 604 000 0002", "timezone": "America/Bogota",
                          "default_currency": "COP", "version": 1},
                    why=[
                        "`PUT` reemplaza todos los campos: se envían de nuevo los que no cambian.",
                        "No cambia la organización ni la ubicación: el servicio no vuelve a consultar Party Identity ni Geography.",
                    ],
                    show=["phone", "version"],
                ),
                call(
                    "Buscar la empresa por su organización",
                    "GET",
                    f"{API}/companies?organization_identity_id=<ORG_EMPRESA>",
                    why=["Para buscar por NIT o razón social se busca primero la organización en Party Identity (FR-054)."],
                    show=["items[].id", "items[].status", "total_records"],
                ),
            ],
        ),
    ],
)
