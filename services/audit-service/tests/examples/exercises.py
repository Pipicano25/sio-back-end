"""Ejercicios de `docs/ejemplo/` como datos estructurados (Principio XXII).

Datos **ficticios** (no existe una fuente del sistema anterior para eventos de auditoría):
identificadores fijos y fechas pasadas para que la documentación generada sea estable.

Cada paso:

- `actor`: `"emisor"` (cuenta de servicio `audit-test-emitter`) o un usuario de prueba;
- `kind`: `"registro"` (solo cuentas de servicio) o `"consulta"` (permiso + alcance);
- `save`: variables `<NOMBRE>` que se guardan de la respuesta y se usan en pasos posteriores.
"""

from __future__ import annotations

COMPANY = "a11d0000-0000-4000-8000-000000000001"
OTHER_COMPANY = "a11d0000-0000-4000-8000-000000000099"
PRICE_ITEM = "b22e0000-0000-4000-8000-000000000010"
SUPPLIER = "b22e0000-0000-4000-8000-000000000020"
GLOBAL_PRODUCT = "b22e0000-0000-4000-8000-000000000030"
ADMIN_SUB = "13fb7acf-dac0-4fba-ae39-6759c77c3f97"


def ev(number: int) -> str:
    return f"c33f0000-0000-4000-8000-{number:012d}"


def event(number: int, **fields) -> dict:
    body = {
        "event_id": ev(number),
        "company_id": COMPANY,
        "keycloak_user_id": ADMIN_SUB,
        "username_snapshot": "admin.test",
        "action": "CHANGE_PRICE",
        "entity_type": "PriceListItem",
        "entity_id": PRICE_ITEM,
        "previous_values": {"unit_price": "2000.00"},
        "new_values": {"unit_price": "2100.00"},
        "result": "SUCCESS",
        "occurred_at": "2026-09-15T14:00:00-05:00",
    }
    body.update(fields)
    return {key: value for key, value in body.items() if value is not None}


REGISTRO = "registro"
CONSULTA = "consulta"

EXERCISES = [
    {
        "number": 1,
        "folder": "1-registrar-eventos",
        "title": "Registrar eventos de auditoría",
        "purpose": (
            "Un microservicio emisor registra eventos con su identidad técnica: un evento, su reenvío "
            "idempotente, un conflicto de `event_id`, la redacción de un secreto, un lote atómico y "
            "los rechazos de validación."
        ),
        "data": [
            ("Empresa", COMPANY, "Empresa ficticia de los eventos."),
            ("Precio de lista", PRICE_ITEM, "Entidad afectada (`PriceListItem`)."),
            ("Actor", ADMIN_SUB, "`sub` de `admin.test`, el usuario que originó la acción en el emisor."),
            ("Emisor", "audit-test-emitter", "Cuenta de servicio de pruebas; Audit fija `source_service` con su `client_id`."),
        ],
        "steps": [
            {
                "file": "01-registrar-un-evento.md",
                "title": "Registrar un cambio de precio",
                "actor": "emisor",
                "kind": REGISTRO,
                "method": "POST",
                "path": "/api/v1/audit-events",
                "body": event(1),
                "expect": 201,
                "save": {"AUDIT_ID_CAMBIO": "id"},
                "why": [
                    "`event_id` lo genera el emisor al guardar en su outbox y lo conserva en los reintentos.",
                    "`occurred_at` lleva zona horaria; Audit guarda además `recorded_at` (momento de registro).",
                    "No se envían `source_service`, `created_by`, `recorded_at` ni `id`: los fija Audit.",
                ],
            },
            {
                "file": "02-reenviar-el-mismo-evento.md",
                "title": "Reenviar el mismo evento (respuesta perdida)",
                "actor": "emisor",
                "kind": REGISTRO,
                "method": "POST",
                "path": "/api/v1/audit-events",
                "body": event(1),
                "expect": 200,
                "why": [
                    "Mismo `event_id` y mismo contenido: Audit devuelve el evento original (`200`) sin duplicarlo.",
                    "Es lo que hace el `audit-outbox-worker` cuando no recibió la confirmación anterior.",
                ],
            },
            {
                "file": "03-conflicto-de-event-id.md",
                "title": "Mismo `event_id` con otro contenido",
                "actor": "emisor",
                "kind": REGISTRO,
                "method": "POST",
                "path": "/api/v1/audit-events",
                "body": event(1, new_values={"unit_price": "2500.00"}),
                "expect": 409,
                "why": [
                    "Un `event_id` identifica un único evento para siempre (RN-05): `409 AUDIT.EVENT_ID_CONFLICT`.",
                    "El evento original no cambia y la respuesta no revela su contenido.",
                ],
            },
            {
                "file": "04-redaccion-de-secretos.md",
                "title": "Evento con un valor sensible",
                "actor": "emisor",
                "kind": REGISTRO,
                "method": "POST",
                "path": "/api/v1/audit-events",
                "body": event(
                    2,
                    action="UPDATE",
                    entity_type="CompanySupplier",
                    entity_id=SUPPLIER,
                    previous_values={"portal": {"user": "proveedor", "api_key": "valor-ficticio-1"}},
                    new_values={"portal": {"user": "proveedor", "api_key": "valor-ficticio-2"}},
                ),
                "expect": 201,
                "why": [
                    "`api_key` está en la política de redacción: su valor se guarda como `\"***\"`.",
                    "Las rutas ocultadas quedan en `redacted_paths`; el evento no se rechaza.",
                    "Normalmente el emisor ya lo ocultó antes de su outbox; Audit lo repite como defensa.",
                ],
            },
            {
                "file": "05-registrar-un-lote.md",
                "title": "Registrar un lote de eventos",
                "actor": "emisor",
                "kind": REGISTRO,
                "method": "POST",
                "path": "/api/v1/audit-events/batch",
                "body": {
                    "events": [
                        event(1),
                        event(3, action="INACTIVATE", previous_values={"status": "ACTIVE"}, new_values={"status": "INACTIVE"}),
                        event(4, action="UPDATE", result="FAILURE", reason="Versión desactualizada", new_values=None),
                    ]
                },
                "expect": 200,
                "why": [
                    "Lote de 1 a 100 eventos; la respuesta indica `CREATED` o `ALREADY_EXISTS` por evento.",
                    "El primer evento ya existía (paso 1): cuenta como confirmado.",
                    "`FAILURE` sin cambios de valores es válido; `reason` es opcional.",
                ],
            },
            {
                "file": "06-lote-con-un-evento-invalido.md",
                "title": "Lote con un evento inválido",
                "actor": "emisor",
                "kind": REGISTRO,
                "method": "POST",
                "path": "/api/v1/audit-events/batch",
                "body": {"events": [event(5), event(6, action="cambiar-precio")]},
                "expect": 422,
                "why": [
                    "El lote es atómico: un evento inválido rechaza todo el lote y no se guarda ninguno.",
                    "El error indica el evento por su posición: `events[1].action`.",
                ],
            },
            {
                "file": "07-campos-que-fija-audit.md",
                "title": "Enviar un campo que fija Audit",
                "actor": "emisor",
                "kind": REGISTRO,
                "method": "POST",
                "path": "/api/v1/audit-events",
                "body": {**event(7), "source_service": "otro-servicio"},
                "expect": 422,
                "why": ["`source_service` sale del token, nunca del cuerpo (RC-03)."],
            },
        ],
    },
    {
        "number": 2,
        "folder": "2-consultar-auditoria-de-empresa",
        "title": "Consultar la auditoría de una empresa",
        "purpose": (
            "Un supervisor consulta qué se hizo en su empresa: listado con filtros, un evento por `id` "
            "e historial de una entidad. La consulta exige el permiso de lectura de auditoría y la "
            "membresía `ACTIVE` en la empresa (Operational Context)."
        ),
        "data": [
            ("Empresa", COMPANY, "Todos los usuarios de prueba son miembros (Operational Context simulado)."),
            ("Otra empresa", OTHER_COMPANY, "Ningún usuario de prueba es miembro."),
            ("Precio de lista", PRICE_ITEM, "Entidad con historial: creación, cambio y un intento fallido."),
        ],
        "steps": [
            {
                "file": "01-registrar-historial.md",
                "title": "El emisor registra el historial del precio",
                "actor": "emisor",
                "kind": REGISTRO,
                "method": "POST",
                "path": "/api/v1/audit-events/batch",
                "body": {
                    "events": [
                        event(11, action="CREATE", previous_values=None, new_values={"unit_price": "2000.00"}, occurred_at="2026-09-10T09:00:00-05:00"),
                        event(12, occurred_at="2026-09-15T14:00:00-05:00"),
                        event(13, result="FAILURE", reason="El precio en vigencia no se puede modificar", new_values={"unit_price": "1900.00"}, occurred_at="2026-09-16T08:30:00-05:00"),
                    ]
                },
                "expect": 200,
                "save": {"AUDIT_ID_CREACION": "items[0].id"},
                "why": ["Datos de partida de las consultas (tres eventos del mismo precio de lista)."],
            },
            {
                "file": "02-listar-eventos-de-la-empresa.md",
                "title": "Listar los eventos de la empresa",
                "actor": "supervisor.test",
                "kind": CONSULTA,
                "method": "GET",
                "path": f"/api/v1/companies/{COMPANY}/audit-events",
                "expect": 200,
                "why": [
                    "Orden del más reciente al más antiguo; paginado (`page_size` máximo 100).",
                    "Solo eventos de esta empresa; nunca eventos de plataforma.",
                ],
            },
            {
                "file": "03-filtrar-intentos-fallidos.md",
                "title": "Filtrar los intentos fallidos",
                "actor": "supervisor.test",
                "kind": CONSULTA,
                "method": "GET",
                "path": f"/api/v1/companies/{COMPANY}/audit-events?result=FAILURE&entity_type=PriceListItem",
                "expect": 200,
                "why": ["Los filtros se combinan; un parámetro desconocido responde `422`."],
            },
            {
                "file": "04-consultar-un-evento.md",
                "title": "Consultar un evento por `id`",
                "actor": "supervisor.test",
                "kind": CONSULTA,
                "method": "GET",
                "path": f"/api/v1/companies/{COMPANY}/audit-events/<AUDIT_ID_CREACION>",
                "expect": 200,
                "why": ["`id` es el identificador que asignó Audit (distinto de `event_id`)."],
            },
            {
                "file": "05-historial-de-la-entidad.md",
                "title": "Historial del precio de lista",
                "actor": "supervisor.test",
                "kind": CONSULTA,
                "method": "GET",
                "path": f"/api/v1/companies/{COMPANY}/entity-history/PriceListItem/{PRICE_ITEM}",
                "expect": 200,
                "why": ["Orden cronológico (del más antiguo al más reciente), incluidos los `FAILURE`."],
            },
            {
                "file": "06-empresa-sin-membresia.md",
                "title": "Consultar una empresa donde no es miembro",
                "actor": "supervisor.test",
                "kind": CONSULTA,
                "method": "GET",
                "path": f"/api/v1/companies/{OTHER_COMPANY}/audit-events",
                "expect": 404,
                "why": ["Fuera del alcance → `404`, sin revelar si la empresa tiene eventos."],
            },
        ],
    },
    {
        "number": 3,
        "folder": "3-eventos-de-plataforma",
        "title": "Eventos de plataforma (sin empresa)",
        "purpose": (
            "Un cambio en un catálogo global no pertenece a ninguna empresa: se consulta con el permiso "
            "independiente `perm:audit:platform-events:read`, sin membresía. El permiso de auditoría de "
            "empresa no da acceso a estos eventos."
        ),
        "data": [
            ("Producto global", GLOBAL_PRODUCT, "Entidad de Product Catalog afectada (evento ficticio)."),
            ("Empresa", COMPANY, "Solo para mostrar que la ruta de empresa no devuelve eventos de plataforma."),
        ],
        "steps": [
            {
                "file": "01-registrar-evento-de-plataforma.md",
                "title": "Registrar un evento sin empresa",
                "actor": "emisor",
                "kind": REGISTRO,
                "method": "POST",
                "path": "/api/v1/audit-events",
                "body": event(
                    21,
                    company_id=None,
                    action="UPDATE",
                    entity_type="GlobalProduct",
                    entity_id=GLOBAL_PRODUCT,
                    previous_values={"name": "Arroz 500 g (ficticio)"},
                    new_values={"name": "Arroz blanco 500 g (ficticio)"},
                ),
                "expect": 201,
                "save": {"AUDIT_ID_PLATAFORMA": "id"},
                "why": ["Sin `company_id` el evento es de plataforma; `branch_id` exigiría `company_id`."],
            },
            {
                "file": "02-listar-eventos-de-plataforma.md",
                "title": "Listar los eventos de plataforma",
                "actor": "supervisor.test",
                "kind": CONSULTA,
                "method": "GET",
                "path": "/api/v1/platform-audit-events",
                "expect": 200,
                "why": ["Solo eventos con `company_id` nulo; no consulta Operational Context."],
            },
            {
                "file": "03-historial-del-producto-global.md",
                "title": "Historial del producto global",
                "actor": "supervisor.test",
                "kind": CONSULTA,
                "method": "GET",
                "path": f"/api/v1/platform-entity-history/GlobalProduct/{GLOBAL_PRODUCT}",
                "expect": 200,
                "why": ["Mismo formato que el historial de empresa, en el alcance de plataforma."],
            },
            {
                "file": "04-evento-de-plataforma-por-ruta-de-empresa.md",
                "title": "Pedir el evento de plataforma por la ruta de empresa",
                "actor": "supervisor.test",
                "kind": CONSULTA,
                "method": "GET",
                "path": f"/api/v1/companies/{COMPANY}/audit-events/<AUDIT_ID_PLATAFORMA>",
                "expect": 404,
                "why": ["Los alcances están separados: la ruta de empresa nunca devuelve eventos de plataforma."],
            },
        ],
    },
]
