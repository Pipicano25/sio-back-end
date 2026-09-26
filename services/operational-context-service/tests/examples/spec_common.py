"""Constructores y datos comunes de los ejercicios de docs/ejemplo/ (Principio XXII).

Cada ejercicio es una lista de pasos y cada paso una lista de llamadas. La prueba
`test_examples.py` las ejecuta contra la API y `render.py` genera la documentación.

Las llamadas a Party Identity y Geography (clase C) no se ejecutan: son
**externas** y sus resultados se simulan con los UUID ficticios de este módulo,
que la prueba registra en los dobles de los puertos (Principio IV).
"""

from __future__ import annotations

API = "/api/v1"
# Alcance de plataforma (Fase B, DS-05): registrar, inactivar y reactivar empresas.
PLATFORM = ["perm:operational-context:platform:administer"]
PARTY_IDENTITY = "http://localhost:8002/api/v1"
GEOGRAPHY = "http://localhost:8000"

# ---- Identificadores ficticios que los dobles de Party Identity y Geography conocen ----
ORG_EJ1 = "7a1c0f10-0000-4000-8000-000000000e01"
ORG_EJ2 = "7a1c0f10-0000-4000-8000-000000000e02"
ORG_EJ3 = "7a1c0f10-0000-4000-8000-000000000e03"
UNKNOWN_ORGANIZATION = "7a1c0f10-0000-4000-8000-00000000dead"

PAIS_CO = "c0c0c0c0-0000-4000-8000-000000000057"
DIV_ANTIOQUIA = "d1d1d1d1-0000-4000-8000-000000000005"
DIV_CUNDINAMARCA = "d1d1d1d1-0000-4000-8000-000000000025"
CIU_MEDELLIN = "e2e2e2e2-0000-4000-8000-000000005001"
CIU_BOGOTA = "e2e2e2e2-0000-4000-8000-000000011001"

ORGANIZATIONS = {ORG_EJ1: "ACTIVE", ORG_EJ2: "ACTIVE", ORG_EJ3: "ACTIVE"}
COUNTRIES = {PAIS_CO: "ACTIVE"}
DIVISIONS = {DIV_ANTIOQUIA: ("ACTIVE", PAIS_CO), DIV_CUNDINAMARCA: ("ACTIVE", PAIS_CO)}
CITIES = {
    CIU_MEDELLIN: ("ACTIVE", PAIS_CO, DIV_ANTIOQUIA),
    CIU_BOGOTA: ("ACTIVE", PAIS_CO, DIV_CUNDINAMARCA),
}


def call(
    title,
    method,
    path,
    body=None,
    why=(),
    save=None,
    expect=None,
    show=None,
    external=None,
    note=None,
    sample=None,
    sample_status=200,
    perm=None,
    fake=None,
    also=(),
):
    """Una llamada a la API.

    - `save`: {"NOMBRE": "ruta.en.respuesta"}; el valor se usa luego como `<NOMBRE>`.
    - `expect`: código HTTP esperado (None = 200 o 201).
    - `show`: claves de la respuesta que se muestran en el documento.
    - `external`: nombre del otro servicio (Party Identity o Geography): la llamada no
      se ejecuta en la validación y `fake` indica el valor simulado de cada variable.
    - `also`: permisos adicionales que exige la URL además del que indica el `403`
      (p. ej. `perm:operational-context:platform:administer`, Fase B).
    """
    return dict(
        title=title,
        method=method,
        path=path,
        body=body,
        why=list(why),
        save=save or {},
        expect=expect,
        show=show,
        external=external,
        note=note,
        sample=sample,
        sample_status=sample_status,
        perm=perm,
        fake=fake or {},
        also=list(also),
    )


def step(file, title, goal, calls, intro=None, after=None):
    return dict(file=file, title=title, goal=goal, calls=calls, intro=intro, after=after)


def get_organization(variable, organization_id, legal_name):
    """Busca la organización en Party Identity y guarda su `id`."""
    return call(
        f"Consultar la organización {legal_name} en Party Identity Service",
        "GET",
        f"{PARTY_IDENTITY}/organization-identities?search=900",
        external="Party Identity Service",
        perm="perm:party-identity:organization_identities:read",
        why=[
            "Operational Context **no guarda** la razón social, el nombre comercial ni el NIT de la empresa: "
            "solo el `id` de su identidad legal en **Party Identity Service** (DS-01, DS-13).",
            "Si la organización todavía no existe, se registra primero en Party Identity "
            "(`POST /api/v1/organization-identities`) con sus datos legales oficiales.",
        ],
        save={variable: "items[0].id"},
        fake={variable: organization_id},
        sample={
            "items": [{
                "id": f"<{variable}>",
                "identification_type": "NIT",
                "identification_number": "<NIT obtenido del RUT; dato ficticio aquí>",
                "legal_name": legal_name,
                "status": "ACTIVE",
            }],
            "page": 1, "page_size": 20, "total_records": 1, "total_pages": 1,
        },
    )


def get_country():
    return call(
        "Consultar el país Colombia en Geography Service",
        "GET",
        f"{GEOGRAPHY}/global-countries?iso3_code=COL",
        external="Geography Service",
        perm="perm:geography:global_countries:read",
        why=[
            "Operational Context no guarda países: guarda el `id` de Geography y lo valida al asignarlo.",
            "Se filtra por `iso3_code`, estable entre entornos; el `id` puede cambiar de una base a otra.",
        ],
        save={"PAIS_CO": "items[0].id"},
        fake={"PAIS_CO": PAIS_CO},
        sample={"items": [{"id": "<PAIS_CO>", "iso3_code": "COL", "name": "Colombia", "status": "ACTIVE"}],
                "page": 1, "page_size": 20, "total_records": 1, "total_pages": 1},
    )


def get_division(variable, division_id, name):
    return call(
        f"Consultar el departamento {name} en Geography Service",
        "GET",
        f"{GEOGRAPHY}/global-administrative-divisions?country_id=<PAIS_CO>&search={name}",
        external="Geography Service",
        perm="perm:geography:global_administrative_divisions:read",
        why=["La división administrativa debe pertenecer al país indicado (coherencia estricta, DS-05)."],
        save={variable: "items[0].id"},
        fake={variable: division_id},
        sample={"items": [{"id": f"<{variable}>", "country_id": "<PAIS_CO>", "name": name, "status": "ACTIVE"}],
                "page": 1, "page_size": 20, "total_records": 1, "total_pages": 1},
    )


def get_city(variable, city_id, name, division_variable):
    return call(
        f"Consultar la ciudad {name} en Geography Service",
        "GET",
        f"{GEOGRAPHY}/global-cities?administrative_division_id=<{division_variable}>&search={name}",
        external="Geography Service",
        perm="perm:geography:global_cities:read",
        why=["La ciudad debe pertenecer al país y exactamente a la división enviada."],
        save={variable: "items[0].id"},
        fake={variable: city_id},
        sample={"items": [{
            "id": f"<{variable}>", "country_id": "<PAIS_CO>",
            "administrative_division_id": f"<{division_variable}>", "name": name, "status": "ACTIVE",
        }], "page": 1, "page_size": 20, "total_records": 1, "total_pages": 1},
    )


# ---- Fase B: organizaciones, personas y cuentas ficticias de los ejercicios 4 a 6 ----
ORG_EJ4 = "7a1c0f10-0000-4000-8000-000000000e04"
ORG_EJ4B = "7a1c0f10-0000-4000-8000-000000000e4b"
ORG_EJ5 = "7a1c0f10-0000-4000-8000-000000000e05"
ORG_EJ6 = "7a1c0f10-0000-4000-8000-000000000e06"
ORGANIZATIONS.update({ORG_EJ4: "ACTIVE", ORG_EJ4B: "ACTIVE", ORG_EJ5: "ACTIVE", ORG_EJ6: "ACTIVE"})

PER_SUPERVISOR = "9e9e9e9e-0000-4000-8000-000000000001"
PER_COMPRAS = "9e9e9e9e-0000-4000-8000-000000000002"
PER_ASESOR_1 = "9e9e9e9e-0000-4000-8000-000000000011"
PER_ASESOR_2 = "9e9e9e9e-0000-4000-8000-000000000012"
PER_ASESOR_3 = "9e9e9e9e-0000-4000-8000-000000000013"
PERSONS = {
    PER_SUPERVISOR: "ACTIVE",
    PER_COMPRAS: "ACTIVE",
    PER_ASESOR_1: "ACTIVE",
    PER_ASESOR_2: "ACTIVE",
    PER_ASESOR_3: "ACTIVE",
}

# Cuenta técnica de un cliente `client_credentials` (no puede ser usuario operativo, FR-019).
TECHNICAL_ACCOUNT = "service-account-inventory-service"


def get_person(variable, person_id, description):
    """Busca la persona en Party Identity y guarda su `id` (FR-016)."""
    return call(
        f"Consultar la persona {description} en Party Identity Service",
        "GET",
        f"{PARTY_IDENTITY}/person-identities?search=<documento>",
        external="Party Identity Service",
        perm="perm:party-identity:person_identities:read",
        why=[
            "Operational Context **no guarda** nombres ni documentos de las personas: solo el `id` de su "
            "`PersonIdentity` en **Party Identity Service** (DS-16, Principio III).",
            "Si la persona no existe, se registra primero en Party Identity con sus datos oficiales.",
        ],
        save={variable: "items[0].id"},
        fake={variable: person_id},
        sample={
            "items": [{
                "id": f"<{variable}>",
                "identification_type": "CC",
                "identification_number": "<documento oficial; dato ficticio aquí>",
                "first_name": "<nombre ficticio>",
                "status": "ACTIVE",
            }],
            "page": 1, "page_size": 20, "total_records": 1, "total_pages": 1,
        },
    )
