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
