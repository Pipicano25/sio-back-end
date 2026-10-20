# Errores y diagnóstico

[← Volver al índice](../index.md) · [Primeros pasos](primeros-pasos.md) · [Autenticación](autenticacion.md) · [Permisos](permisos.md)

Esta guía describe los formatos de error que devuelven las API de SIO, qué significa cada código HTTP y cómo debe reaccionar el frontend. Los códigos de aplicación (`code`) propios de cada operación se detallan en la ficha de cada servicio; aquí están las reglas comunes, verificadas en el código de los 12 servicios.

## 1. Dos formatos según el servicio

| Formato | Servicios | Content-Type | Cuerpo |
|---|---|---|---|
| **Problem Details** (RFC 9457) con `code` y `trace_id` | Party Identity, Product Catalog, Operational Context, Commercial Relationship, Purchase, Sales, Inventory, Audit, Product Inventory Query, Business Reporting | `application/problem+json` | Objeto con `type`, `title`, `status`, `detail`, `instance`, `code`, `trace_id` y extensiones |
| **Básico** (FastAPI) | Geography, Payment Reference | `application/json` | `{"detail": ...}`; Payment Reference añade `code` en dos conflictos |

Comprueba `Content-Type` o la presencia de `code` para distinguirlos. En ambos, los `401` emitidos por la librería de autenticación llevan `WWW-Authenticate: Bearer`.

### 1.1. Problem Details

```json
{
  "type": "https://sio/errors/sales/validation-error",
  "title": "Solicitud inválida",
  "status": 422,
  "detail": "La solicitud contiene datos inválidos.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales",
  "code": "SALES.VALIDATION_ERROR",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "lines.0.quantity",
      "message": "La cantidad debe ser mayor que cero.",
      "code": "QUANTITY_NOT_POSITIVE"
    }
  ]
}
```

| Campo | Tipo | Significado |
|---|---|---|
| `type` | string (URI) | `https://sio/errors/{servicio}/{code en kebab-case}`. Identificador estable del tipo de error; no es una página navegable |
| `title` | string | Título corto en español |
| `status` | integer | Mismo valor que el código HTTP |
| `detail` | string | Mensaje en español apto para mostrar al usuario |
| `instance` | string | Ruta de la solicitud |
| `code` | string | `{PREFIJO}.{CODIGO}`; el prefijo identifica al servicio (tabla siguiente). Es el valor que debe usar el frontend para decidir |
| `trace_id` | string | Identificador de la solicitud; también va en la cabecera `X-Trace-Id`. Pídelo al usuario al reportar un problema |
| `errors[]` | array, opcional | Solo en `400`/`422` de validación: lista de `{field, message, code}` |
| `dependency` | string, opcional | Solo en `503`: dependencia caída (`database`, u otro servicio) |
| Otras extensiones | según el error | Algunos `409` añaden campos (por ejemplo la versión esperada). Se documentan en cada ficha |

Prefijos de `code` y base de `type` por servicio:

| Servicio | Prefijo de `code` | Base de `type` |
|---|---|---|
| Party Identity | `PARTY_IDENTITY.` | `https://sio/errors/party-identity/` |
| Product Catalog | `PRODUCT_CATALOG.` | `https://sio/errors/product-catalog/` |
| Operational Context | `OPERATIONAL_CONTEXT.` | `https://sio/errors/operational-context/` |
| Commercial Relationship | `COMMERCIAL_RELATIONSHIP.` | `https://sio/errors/commercial-relationship/` |
| Purchase | `PURCHASE.` | `https://sio/errors/purchase/` |
| Sales | `SALES.` | `https://sio/errors/sales/` |
| Inventory | `INVENTORY.` | `https://sio/errors/inventory/` |
| Audit | `AUDIT.` | `https://sio/errors/audit/` |
| Product Inventory Query | `PRODUCT_INVENTORY_QUERY.` | `https://sio/errors/product-inventory-query/` |
| Business Reporting | `BUSINESS_REPORTING.` | `https://sio/errors/business-reporting/` |

### 1.2. Formato básico (Geography y Payment Reference)

```json
{
  "detail": "El país solicitado no existe."
}
```

- `404` y `409`: `detail` con un mensaje en español. Payment Reference añade `code` en dos `409`: `PAYMENT_REFERENCE.VERSION_CONFLICT` y `PAYMENT_REFERENCE.INVALID_STATUS_TRANSITION`.
- `422`: formato estándar de FastAPI, con `detail` como **lista** de errores de validación:

```json
{
  "detail": [
    {
      "type": "string_too_long",
      "loc": ["body", "name"],
      "msg": "String should have at most 100 characters",
      "input": "…",
      "ctx": {"max_length": 100}
    }
  ]
}
```

- `503`: `{"detail": "..."}` cuando la base de datos no está disponible, sin `code` ni `trace_id`.
- No envían `X-Trace-Id`.

## 2. Códigos HTTP y qué hacer

| HTTP | Cuándo ocurre | `code` habitual (servicios con Problem Details) | Qué hacer en el frontend |
|---|---|---|---|
| `200` | Consulta o modificación satisfactoria | — | Procesar el cuerpo |
| `201` | Recurso creado | — | Leer el identificador generado por el servidor en el cuerpo |
| `204` | Operación sin cuerpo de respuesta (algunas eliminaciones y cierres) | — | No intentar leer JSON |
| `304` | Solo con `If-None-Match` en la lectura de imagen de Product Catalog | — | Usar la copia en caché |
| `400` | Cuerpo que no es JSON válido; en Product Catalog también parámetros de ruta o consulta no interpretables | `MALFORMED_REQUEST` (`MALFORMED_BODY` en Purchase y Sales) | Error de programación del cliente; revisar la serialización |
| `401` | Token ausente, mal formado, vencido, con `iss` o `aud` incorrectos | `UNAUTHENTICATED` | Renovar el token una vez y reintentar una vez; si persiste, volver al login |
| `403` | Token válido sin el permiso de la operación; o acceso operativo denegado en Purchase, Sales, Inventory, Commercial Relationship y Audit | `FORBIDDEN`, `OPERATIONAL_ACCESS_DENIED`, `BRANCH_ACCESS_DENIED` | Mostrar el `detail` y el `trace_id`. No reintentar. Recalcular los permisos de la interfaz |
| `404` | El recurso de la ruta no existe **o está fuera del alcance** del usuario (empresa o sucursal sin membresía) | `NOT_FOUND` | Revisar el identificador y el contexto operativo ([Permisos §5](permisos.md#5-alcance-de-datos-plataforma-empresa-y-sucursal)) |
| `405` | Método no permitido en la ruta | `METHOD_NOT_ALLOWED` | Error de programación del cliente |
| `409` | Conflicto de estado: duplicado, versión desactualizada, transición no permitida, secuencia no configurada, clave de idempotencia reutilizada con otro cuerpo | `VERSION_CONFLICT`, `INVALID_STATUS_TRANSITION`, `DUPLICATE_*`, `IDEMPOTENCY_KEY_CONFLICT`, otros por servicio | Mostrar el `detail`; recargar el recurso y repetir la acción con la versión actual si procede |
| `422` | Validación de campos o de reglas de negocio de la entrada, incluidas referencias a recursos inexistentes o inactivos | `VALIDATION_ERROR`, `IMMUTABLE_FIELD`, otros por servicio | Mostrar `errors[].message` junto al campo `errors[].field` |
| `500` | Error no controlado | `INTERNAL_ERROR` | Mostrar mensaje genérico y el `trace_id`; reportar |
| `503` | Base de datos del servicio o un servicio dependiente no disponible | `DEPENDENCY_UNAVAILABLE` con `dependency` | Mostrar estado temporal y permitir reintentar tras unos segundos |

Reglas generales (comunes a los servicios con Problem Details):

- `400` solo si el JSON no se puede interpretar; `422` para toda validación de entrada y de dominio.
- `409` para unicidad, versión y transiciones de estado.
- `404` tanto para «no existe» como para «fuera de alcance», a propósito, para no revelar la existencia de datos de otras empresas.
- `503` solo por pérdida de conexión con la base de datos o indisponibilidad de otro servicio; otros errores de base de datos se reportan como `500`.

## 3. Errores de validación en detalle

En los servicios con Problem Details, `422` incluye `errors[]` con un elemento por campo inválido:

| Campo | Significado |
|---|---|
| `field` | Ruta del campo en notación de puntos, sin el prefijo `body` (por ejemplo `lines.0.quantity`, `name`) |
| `message` | Mensaje en español o el mensaje de Pydantic |
| `code` | Causa. En la mayoría de los servicios es siempre `VALIDATION_ERROR` (o `IMMUTABLE_FIELD` en Product Catalog). Purchase y Sales usan causas específicas |

Causas de `errors[].code` en Purchase y Sales: `REQUIRED`, `INVALID_FORMAT`, `UNKNOWN_FIELD`, `LINES_LIMIT_EXCEEDED`, `QUANTITY_NOT_POSITIVE`, `TOO_MANY_DECIMALS`, `AMOUNT_OUT_OF_RANGE`, `REASON_REQUIRED`, `IDEMPOTENCY_KEY_REQUIRED`, `PAGE_SIZE_OUT_OF_RANGE`, `INVALID_DATE_RANGE`.

Un campo desconocido en el cuerpo produce `422` en los servicios que rechazan campos extra (Purchase y Sales lo reportan como `UNKNOWN_FIELD`). **NO VERIFICADO** para cada modelo de los demás servicios; las fichas indican cuándo un modelo rechaza campos adicionales.

## 4. Concurrencia y versiones

Varios recursos llevan un campo `version` (entero) que debe enviarse al modificar. Si el recurso cambió desde que se leyó, el servicio responde `409` `VERSION_CONFLICT`. El frontend debe recargar el recurso, mostrar los cambios y repetir la acción con la nueva versión. Las fichas indican qué operaciones exigen `version` y en qué campo (cuerpo o cabecera).

## 5. Trazabilidad

- Los 10 servicios con Problem Details devuelven la cabecera `X-Trace-Id` en **todas** las respuestas, correctas o no, y el mismo valor en el campo `trace_id` de los errores.
- Si el cliente envía una cabecera `traceparent` válida (W3C Trace Context), el servicio reutiliza su trace-id; si no, genera uno.
- Los `403` por permiso no indican qué permiso faltó; esa información está solo en el log del servidor, asociada al `trace_id`. Por eso el frontend debe mostrarlo al usuario.
- Geography y Payment Reference no devuelven `X-Trace-Id`.

## 6. Manejo recomendado en el cliente

```ts
type ProblemDetails = {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance: string;
  code: string;
  trace_id: string;
  errors?: { field: string; message: string; code: string }[];
  dependency?: string;
};

type ErrorBasico = { detail: string | unknown[]; code?: string };

export function describirError(status: number, body: unknown, traceId: string | null) {
  const problem = body as Partial<ProblemDetails> | undefined;
  const code = problem?.code ?? null;
  const detail =
    typeof problem?.detail === "string" ? problem.detail : "La solicitud no pudo completarse.";

  switch (status) {
    case 401:
      return { accion: "renovar-y-reintentar", mensaje: detail };
    case 403:
      return { accion: "mostrar", mensaje: `${detail} (trace_id: ${traceId ?? problem?.trace_id ?? "n/d"})` };
    case 404:
      return { accion: "revisar-contexto", mensaje: detail };
    case 409:
      return { accion: "recargar", mensaje: detail, code };
    case 422:
      return {
        accion: "marcar-campos",
        mensaje: detail,
        campos: problem?.errors ?? [],
      };
    case 503:
      return { accion: "reintentar-luego", mensaje: detail };
    default:
      return { accion: "reportar", mensaje: `${detail} (trace_id: ${traceId ?? "n/d"})` };
  }
}
```

Para Geography y Payment Reference, `body.detail` en `422` es una lista; conviértela a mensajes por campo usando `loc` y `msg`.

## 7. Errores de Keycloak

Los errores del token endpoint (`invalid_grant`, `unauthorized_client`, `invalid_client`) y del login se describen en [Autenticación §4.2 y §13](autenticacion.md#42-canje-del-código-por-tokens). No llegan desde las API de SIO sino desde Keycloak, con el formato OAuth 2.0 `{"error": "...", "error_description": "..."}`.

## 8. Información pendiente de verificar

| Punto | Estado |
|---|---|
| Comportamiento exacto de cada modelo ante campos desconocidos en el cuerpo | NO VERIFICADO de forma global; se indica por operación en las fichas |
| Lista completa de códigos `409` y `422` por servicio | Se documenta en cada ficha a medida que se completa |
