"""Constructores comunes de los ejercicios de docs/ejemplo/ (Principio XXII).

Cada ejercicio es una lista de pasos y cada paso una lista de llamadas. La prueba
`test_examples.py` las ejecuta contra la API y `render.py` genera la documentación.
"""

from __future__ import annotations

from tests.conftest import COLOMBIA_ID

API = "/api/v1"
GEOGRAPHY = "http://localhost:8000"

# País inexistente (ficticio) que el doble de Geography responde con 404.
UNKNOWN_COUNTRY_ID = "5e0c0f6e-0000-4000-8000-00000000dead"


def call(
    title,
    method,
    path,
    body=None,
    why=(),
    save=None,
    expect=None,
    show=None,
    external=False,
    note=None,
    sample=None,
    sample_status=200,
    perm=None,
    fake=None,
):
    """Una llamada a la API.

    - `save`: {"NOMBRE": "ruta.en.respuesta"}; el valor se usa luego como `<NOMBRE>`.
    - `expect`: código HTTP esperado (None = 200 o 201).
    - `show`: claves de la respuesta que se muestran en el documento.
    - `external`: llamada a otro servicio (Geography): no se ejecuta en la validación;
      `fake` indica el valor simulado de cada variable guardada.
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
    )


def step(file, title, goal, calls, intro=None, after=None):
    return dict(file=file, title=title, goal=goal, calls=calls, intro=intro, after=after)


def get_colombia():
    """Consulta Colombia en Geography (otro servicio) y guarda su `id` como `<PAIS_CO>`."""
    return call(
        "Consultar el país Colombia en Geography Service",
        "GET",
        f"{GEOGRAPHY}/global-countries?iso3_code=COL",
        external=True,
        perm="perm:geography:global_countries:read",
        why=[
            "Party Identity no guarda países: solo guarda el `id` del país registrado en **Geography Service** "
            "(puerto `8000`) y lo valida contra él al crear o al cambiar la identificación.",
            "Se filtra por `iso3_code`, que es estable entre entornos; el `id` puede cambiar de una base a otra.",
        ],
        save={"PAIS_CO": "items[0].id"},
        fake={"PAIS_CO": str(COLOMBIA_ID)},
        sample={
            "items": [{"id": "<PAIS_CO>", "iso2_code": "CO", "iso3_code": "COL", "name": "Colombia", "status": "ACTIVE"}],
            "page": 1, "page_size": 20, "total_records": 1, "total_pages": 1,
        },
    )


# --------------------------------------------------------------------------
# Fase B: llamadas externas simuladas (Principio IV)
# --------------------------------------------------------------------------

OPERATIONAL_CONTEXT = "http://localhost:8004"


def get_company():
    """Consulta la empresa en Operational Context (otro servicio) y guarda su `id` como `<EMPRESA>`."""
    from tests.conftest import COMPANY_ID

    return call(
        "Consultar la empresa desde la que se confirma en Operational Context",
        "GET",
        f"{OPERATIONAL_CONTEXT}/api/v1/companies?status=ACTIVE",
        external=True,
        perm="perm:operational-context:companies:read",
        why=[
            "El perfil de contacto se confirma **desde una empresa**: Party Identity guarda solo el `id` de la empresa "
            "(`confirmed_by_company_id`) y el del usuario operativo que confirmó (`confirmed_by_user_id`).",
            "Para confirmar, el usuario debe tener una **membresía `ACTIVE`** en esa empresa (Operational Context, "
            "ejercicio 4 de su `docs/ejemplo/`). Party Identity la comprueba con su propio cliente técnico; el usuario "
            "**no** necesita permisos de Operational Context para confirmar.",
        ],
        save={"EMPRESA": "items[0].id"},
        fake={"EMPRESA": str(COMPANY_ID)},
        sample={"items": [{"id": "<EMPRESA>", "status": "ACTIVE"}], "page": 1, "page_size": 20,
                "total_records": 1, "total_pages": 1},
    )


def get_city():
    """Consulta la ciudad en Geography y guarda `<DIVISION>` y `<CIUDAD>` (coherentes con `<PAIS_CO>`)."""
    from tests.conftest import CITY_ID, DIVISION_ID

    return call(
        "Consultar la ciudad y su división en Geography Service",
        "GET",
        f"{GEOGRAPHY}/global-cities?country_id=<PAIS_CO>&search=BOGOTA",
        external=True,
        perm="perm:geography:global_cities:read",
        why=[
            "La dirección del perfil usa `country_id`, `administrative_division_id` y `city_id` de Geography; Party "
            "Identity valida que existan, estén `ACTIVE` y sean coherentes entre sí (ciudad de esa división y país).",
        ],
        save={"DIVISION": "items[0].administrative_division_id", "CIUDAD": "items[0].id"},
        fake={"DIVISION": str(DIVISION_ID), "CIUDAD": str(CITY_ID)},
        sample={"items": [{"id": "<CIUDAD>", "name": "BOGOTA, D.C.", "country_id": "<PAIS_CO>",
                           "administrative_division_id": "<DIVISION>", "status": "ACTIVE"}],
                "page": 1, "page_size": 20, "total_records": 1, "total_pages": 1},
    )
