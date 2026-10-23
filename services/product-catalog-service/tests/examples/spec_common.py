"""Constructores comunes de los ejercicios de docs/ejemplo/ (Principio XXII).

Cada ejercicio es una lista de pasos y cada paso una lista de llamadas. La prueba
`test_examples.py` las ejecuta contra la API y `render.py` genera la documentación.
"""

from __future__ import annotations

API = "/api/v1"
PARTY = "http://localhost:8002"


def call(
    title,
    method,
    path,
    body=None,
    why=(),
    save=None,
    expect=None,
    show=None,
    cond=None,
    external=False,
    note=None,
    sample=None,
    sample_note=None,
    sample_status=200,
    cond_text=None,
    perm=None,
    upload=None,
):
    """Una llamada a la API.

    - `save`: {"NOMBRE": "ruta.en.respuesta"}; el valor se usa luego como `<NOMBRE>`.
    - `expect`: código HTTP esperado (None = 200 o 201).
    - `show`: claves de la respuesta que se muestran en el documento.
    - `cond`: nombre de la variable de una consulta previa; la llamada solo se hace
      si esa consulta devolvió `items` vacío.
    - `external`: llamada a otro servicio (no se ejecuta en la validación).
    - `upload`: carga multipart (spec 024): {"file_name": ..., "content": "png"|"jpeg"|"webp", "color": (r, g, b)};
      la validación envía una imagen real generada (ficticia) en el campo `file`.
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
        cond=cond,
        external=external,
        note=note,
        sample=sample,
        sample_note=sample_note,
        sample_status=sample_status,
        cond_text=cond_text,
        perm=perm,
        upload=upload,
    )


def step(file, title, goal, calls, intro=None, after=None, needs=()):
    return dict(file=file, title=title, goal=goal, calls=calls, intro=intro, after=after, needs=list(needs))


# ------------------------------------------------------------------ bloques comunes

def get_unit(code, var, why):
    return call(
        f"Consultar la unidad `{code}`",
        "GET",
        f"{API}/units-of-measure?code={code}",
        why=why,
        save={var: "items[0].id"},
        show=["items[].id", "items[].code", "items[].name", "items[].measurement_type", "items[].allows_decimals", "total_records"],
    )


def get_packaging(code, var, why):
    return call(
        f"Consultar el tipo de empaque `{code}`",
        "GET",
        f"{API}/packaging-types?code={code}",
        why=why,
        save={var: "items[0].id"},
        show=["items[].id", "items[].code", "items[].name", "total_records"],
    )


def get_group_type(number):
    return call(
        f"Consultar el tipo de grupo `GROUP_{number}`",
        "GET",
        f"{API}/group-types?code=GROUP_{number}",
        why=[
            f"La columna `Grupo {number}` del Excel se guarda en el tipo de grupo `GROUP_{number}`, "
            "que la carga inicial ya creó. Se necesita su `id` para crear y consultar sus grupos.",
        ],
        save={f"GT_GROUP_{number}": "items[0].id"},
        show=["items[].id", "items[].code", "items[].allows_multiple", "total_records"],
    )


GEOGRAPHY = "http://localhost:8000"
COLOMBIA_ID = "cf160c2d-b6de-4ef5-9257-a0a8539058d9"


def get_manufacturer(search, var, label, trade_name):
    """Busca el fabricante; si no existe, consulta el país y lo crea en Party Identity."""
    q = f"Q_{var}"
    data = var.replace("FABRICANTE_", "")
    return [
        call(
            f"Buscar el fabricante {label} en Party Identity Service",
            "GET",
            f"{PARTY}/organization-identities?search={search}",
            external=True,
            perm="perm:party-identity:organization_identities:read",
            why=[
                "El catálogo no guarda fabricantes: solo guarda el `id` de la organización registrada en "
                "Party Identity Service (puerto `8002`). Por eso esta consulta va a otro servicio.",
                "`search` busca parcialmente en la razón social, el nombre comercial y el número de identificación.",
                "Al crear el producto, el catálogo vuelve a preguntar a Party Identity si esa organización "
                "existe; si no existe responde `422 MANUFACTURER_NOT_FOUND`.",
            ],
            save={q: "items"},
            sample={"items": [], "page": 1, "page_size": 20, "total_records": 0, "total_pages": 0},
            sample_note="en una base donde el fabricante todavía no existe",
            note=f"**Si `items` trae la organización:** guarde `items[0].id` → `<{var}>` y **salte** las llamadas 2 y 3. "
                 "Si trae varias, elija la correcta por `legal_name` e `identification_number`.\n\n"
                 "**Si viene vacío** (como arriba): el fabricante no está registrado; haga las llamadas 2 y 3 para crearlo.",
        ),
        call(
            "Consultar el país Colombia en Geography Service (solo si el fabricante no existe)",
            "GET",
            f"{GEOGRAPHY}/global-countries?iso2_code=CO",
            external=True,
            perm="perm:geography:global_countries:read",
            cond=q,
            cond_text="**Solo si la búsqueda anterior devolvió `\"items\": []`.** Si el fabricante ya existía, omita esta llamada y la siguiente.",
            why=[
                "Party Identity exige el `country_id` del país que emitió la identificación; los países los administra "
                "**Geography Service** (puerto `8000`).",
                "Se filtra por `iso2_code` (código ISO de 2 letras), que es fijo, en vez de por nombre.",
                f"En su entorno actual el `id` de Colombia es `{COLOMBIA_ID}`; se consulta igual porque en otra base puede cambiar.",
            ],
            save={"PAIS_CO": "items[0].id"},
            sample={"items": [{"id": "<PAIS_CO>", "iso2_code": "CO", "iso3_code": "COL", "name": "Colombia",
                               "phone_prefix": "+57", "status": "ACTIVE"}],
                    "page": 1, "page_size": 20, "total_records": 1, "total_pages": 1},
        ),
        call(
            f"Crear el fabricante {label} (solo si no existe)",
            "POST",
            f"{PARTY}/organization-identities",
            perm="perm:party-identity:organization_identities:create",
            body={
                "country_id": "<PAIS_CO>",
                "identification_type": "NIT",
                "identification_number": f"<DATO_NIT_{data}>",
                "legal_name": f"<DATO_RAZON_SOCIAL_{data}>",
                "trade_name": trade_name,
                "registration_status": "ACTIVE",
            },
            external=True,
            cond=q,
            cond_text="**Solo si la búsqueda del fabricante devolvió `\"items\": []`.**",
            why=[
                f"`<DATO_NIT_{data}>` y `<DATO_RAZON_SOCIAL_{data}>` **no salen del Excel**: son datos legales reales de la empresa. "
                "Tómelos del RUT del proveedor, de una factura suya o del registro mercantil (RUES). "
                "No invente un NIT: el registro es global y lo usarán todas las empresas.",
                "`identification_type: NIT` es la **sigla** del documento. Su entorno tiene una regla activa para Colombia que exige "
                "el formato `^[A-Z0-9]{4,11}-[0-9]$`: número, **guion** y dígito de verificación (ejemplo `900123456-7`). "
                "Si no lo cumple responde `422` \"El número de identificación no cumple ninguna regla activa para la sigla indicada\".",
                "`legal_name` es la razón social exacta (con `S.A.S.`, `S.A.`, etc.); `trade_name`, el nombre por el que se conoce.",
                "`registration_status: ACTIVE` igual que las organizaciones ya registradas. `organization_type` (p. ej. `SAS`) y "
                "`website` son opcionales: se omiten si no se conocen.",
                "Si esa combinación país + tipo + número ya existe responde `409`: vuelva a buscar por el NIT "
                f"(`?search=<DATO_NIT_{data}>`) y use ese `id`.",
                "El usuario necesita el permiso `perm:party-identity:organization_identities:create` (o `perm:party-identity:all:all`).",
            ],
            save={var: "id"},
            sample={"id": f"<{var}>", "country_id": "<PAIS_CO>", "identification_type": "NIT",
                    "identification_number": f"<DATO_NIT_{data}>", "legal_name": f"<DATO_RAZON_SOCIAL_{data}>",
                    "trade_name": trade_name, "organization_type": None, "registration_status": "ACTIVE",
                    "website": None, "version": 1},
            sample_status=201,
        ),
    ]


def group_block(number, code, name, gt_var=None):
    """Consulta el grupo, lo crea si no existe y lo asigna al producto."""
    gt = gt_var or f"GT_GROUP_{number}"
    var = f"GRUPO{number}_{code}"
    q = f"Q_{var}"
    return [
        call(
            f"Grupo {number} `{code}` — consultar si ya existe",
            "GET",
            f"{API}/group-types/<{gt}>/groups?code={code}",
            why=[
                "Los grupos son compartidos por muchos productos: `"
                + code
                + "` puede existir porque otro producto (u otro ejercicio) ya lo creó. "
                "Se consulta primero para **reutilizarlo** y no intentar duplicarlo "
                "(un segundo `POST` con el mismo código responde `409 DUPLICATE_CODE`).",
            ],
            save={q: "items"},
            show=["items[].id", "items[].code", "items[].name", "total_records"],
            note=f"**Si `items` trae el grupo:** guarde `items[0].id` → `<{var}>` y **salte** la llamada siguiente (crear). "
                 f"**Si viene vacío** (como en la respuesta de arriba, en una base nueva): haga la llamada siguiente.",
        ),
        call(
            f"Grupo {number} `{code}` — crearlo (solo si la consulta vino vacía)",
            "POST",
            f"{API}/group-types/<{gt}>/groups",
            body={"code": code, "name": name},
            cond=q,
            why=[
                f"`code` conserva el código del Excel (`{code}`) para poder rastrear el origen del dato.",
                f"`name` es el nombre del Excel escrito de forma legible.",
                "No se envía `parent_group_id`: en el Excel los grupos no tienen jerarquía.",
            ],
            save={var: "id"},
            show=["id", "group_type_id", "code", "name", "status"],
        ),
        call(
            f"Grupo {number} `{code}` — asignarlo al producto",
            "POST",
            f"{API}/products/<PRODUCTO>/group-assignments",
            body={"global_product_group_id": f"<{var}>"},
            why=[
                f"`<{var}>` es el `id` del grupo: el de la consulta si ya existía, o el del `POST` si se acaba de crear.",
                f"`GROUP_{number}` no admite varios grupos (`allows_multiple: false`): el producto queda "
                f"con un solo grupo de este tipo; un segundo daría `422 GROUP_TYPE_SINGLE_VALUE`.",
            ],
            save={f"ASIG_GRUPO{number}": "id"},
            show=["id", "global_product_group_id", "group_type_id", "status"],
        ),
    ]
