# Primeros pasos

[← Volver al índice](../index.md) · [Autenticación](autenticacion.md) · [Permisos](permisos.md) · [Errores](errores.md) · [Parámetros](../parametros/README.md)

Esta guía resume lo que un desarrollador frontend necesita para hacer la primera llamada correcta a SIO y entender las convenciones comunes a los 12 microservicios. Entorno: desarrollo `siodev`, servicios desplegados en Render.

## 1. Qué necesitas antes de empezar

| Elemento | Valor | Dónde se explica |
|---|---|---|
| Servidor Keycloak y realm | `https://fastapi-postgrest-online-keycloak.onrender.com`, realm `siodev` | [Autenticación](autenticacion.md) |
| Cliente público | `sio-web` (Authorization Code + PKCE S256) | [Autenticación](autenticacion.md) |
| Audiencia del token | `sio-api` | [Autenticación](autenticacion.md) |
| Usuario de prueba con membresía | Lo entrega el administrador. La contraseña no se publica | [Autenticación §12](autenticacion.md#12-usuarios-y-grupos-de-prueba-del-realm) |
| URL base de cada servicio | Tabla siguiente | Esta guía |
| Empresa y sucursal activas | Se obtienen de Operational Context después del login | [company_id](../parametros/company-id.md), [branch_id](../parametros/branch-id.md) |

## 2. URLs de los servicios en Render

| # | Servicio | URL base para el frontend | Swagger | OpenAPI |
|---|---|---|---|---|
| 1 | Geography | `https://sio-geography-dev.onrender.com` | [/docs](https://sio-geography-dev.onrender.com/docs) | [/openapi.json](https://sio-geography-dev.onrender.com/openapi.json) |
| 2 | Party Identity | `https://sio-party-identity-dev.onrender.com/api/v1` | [/docs](https://sio-party-identity-dev.onrender.com/docs) | [/openapi.json](https://sio-party-identity-dev.onrender.com/openapi.json) |
| 3 | Product Catalog | `https://sio-product-catalog-dev.onrender.com/api/v1` | [/docs](https://sio-product-catalog-dev.onrender.com/docs) | [/openapi.json](https://sio-product-catalog-dev.onrender.com/openapi.json) |
| 4 | Operational Context | `https://sio-operational-context-dev.onrender.com/api/v1` | [/docs](https://sio-operational-context-dev.onrender.com/docs) | [/openapi.json](https://sio-operational-context-dev.onrender.com/openapi.json) |
| 5 | Payment Reference | `https://sio-payment-reference-dev.onrender.com` | [/docs](https://sio-payment-reference-dev.onrender.com/docs) | [/openapi.json](https://sio-payment-reference-dev.onrender.com/openapi.json) |
| 6 | Commercial Relationship | `https://sio-commercial-relationship-dev.onrender.com/api/v1` | [/docs](https://sio-commercial-relationship-dev.onrender.com/docs) | [/openapi.json](https://sio-commercial-relationship-dev.onrender.com/openapi.json) |
| 7 | Purchase | `https://sio-purchase-dev.onrender.com/api/v1` | [/docs](https://sio-purchase-dev.onrender.com/docs) | [/openapi.json](https://sio-purchase-dev.onrender.com/openapi.json) |
| 8 | Sales | `https://sio-sales-dev.onrender.com/api/v1` | [/docs](https://sio-sales-dev.onrender.com/docs) | [/openapi.json](https://sio-sales-dev.onrender.com/openapi.json) |
| 9 | Inventory | `https://sio-inventory-dev.onrender.com/api/v1` | [/docs](https://sio-inventory-dev.onrender.com/docs) | [/openapi.json](https://sio-inventory-dev.onrender.com/openapi.json) |
| 10 | Audit | `https://sio-audit-dev.onrender.com/api/v1` | [/docs](https://sio-audit-dev.onrender.com/docs) | [/openapi.json](https://sio-audit-dev.onrender.com/openapi.json) |
| 11 | Product Inventory Query | `https://sio-product-inventory-query-dev.onrender.com/api/v1` | [/docs](https://sio-product-inventory-query-dev.onrender.com/docs) | [/openapi.json](https://sio-product-inventory-query-dev.onrender.com/openapi.json) |
| 12 | Business Reporting | `https://sio-business-reporting-dev.onrender.com/api/v1` | [/docs](https://sio-business-reporting-dev.onrender.com/docs) | [/openapi.json](https://sio-business-reporting-dev.onrender.com/openapi.json) |

- **Geography y Payment Reference no usan el prefijo `/api/v1`.** Los otros diez sí. En las fichas de servicio, la columna «Ruta relativa» se concatena a la URL base de esta tabla.
- `/docs`, `/openapi.json`, `/health/live` y `/health/ready` cuelgan siempre del dominio, sin prefijo, y no exigen token. El 2026-10-19 los 12 servicios respondieron `200` en `/openapi.json`.
- Swagger depende de `SIO_DOCS_ENABLED=true` en el servicio; si el administrador lo desactiva, `/docs` y `/openapi.json` dejan de existir.

### Comprobación de disponibilidad

```http
GET https://sio-operational-context-dev.onrender.com/health/live
```

| Ruta | Qué comprueba | Respuesta |
|---|---|---|
| `/health/live` | El proceso responde | `200` `{"status": "ok"}` |
| `/health/ready` | El proceso y su base de datos | `200` `{"status": "ok"}`; `503` `{"detail": "..."}` si la base de datos no está disponible |

Las dos rutas existen en los 12 servicios y cuentan dentro de las 411 operaciones de los contratos. Son las únicas rutas sin autenticación además de la documentación.

### Arranque en frío de Render

Los servicios de desarrollo corren en instancias que se suspenden tras un periodo sin tráfico. La primera llamada después de la pausa puede tardar varias decenas de segundos. Recomendaciones:

- Configura un `timeout` de al menos 60 s en el cliente HTTP durante el desarrollo.
- Muestra estados de carga y permite reintentar.
- Una respuesta `503` en `/health/ready` o en una operación indica base de datos no disponible, no arranque en frío: ver [Errores](errores.md).

## 3. Cabeceras comunes

| Cabecera | Cuándo | Valor |
|---|---|---|
| `Authorization` | Siempre, salvo rutas públicas | `Bearer <ACCESS_TOKEN>` ([Autenticación](autenticacion.md)) |
| `Accept` | Recomendado | `application/json`. Los reportes de Business Reporting admiten CSV por parámetro de consulta, no por `Accept` |
| `Content-Type` | En `POST`, `PUT` y `PATCH` con cuerpo | `application/json` |
| `Idempotency-Key` | Obligatoria en 5 operaciones de confirmación, recepción y anulación de Purchase y Sales | De 1 a 150 caracteres ASCII imprimibles sin espacios (patrón `^[\x21-\x7e]{1,150}$`). Ver §6 |
| `If-None-Match` | Opcional en una operación de Product Catalog (lectura de imagen) | ETag devuelto antes; permite `304` |
| `traceparent` | Opcional | Formato W3C; si es válido, el servicio reutiliza su trace-id |

Cabeceras de respuesta útiles:

| Cabecera | Quién la envía | Uso |
|---|---|---|
| `X-Trace-Id` | Los 10 servicios con Problem Details (todos salvo Geography y Payment Reference) | Identificador para soporte; también va en el cuerpo de los errores como `trace_id` |
| `WWW-Authenticate: Bearer` | Todos, en `401` | Indica que falta o falló el token |
| `Content-Disposition` | Business Reporting en formato CSV | Nombre del archivo descargable |

## 4. Flujo de integración recomendado

1. **Autenticar** al usuario con Keycloak (`sio-web`, PKCE). Guardar el Access Token en memoria.
2. **Leer el contexto operativo**: `GET /api/v1/me/operational-context` en Operational Context. De ahí salen las empresas (`company_id`) y sucursales (`branch_id`) a las que el usuario pertenece.
3. **Elegir empresa y sucursal activas** en la interfaz. No las escribas en el código: cambian por usuario y por entorno. Un usuario puede tener **varias membresías** (una por empresa) y, dentro de cada una, varias sucursales; la respuesta trae todas, incluidas las inactivas, con `allowed` y `reason`. Reglas de selección:
   - Ofrece solo las membresías con `status: ACTIVE` y `company_status: ACTIVE`, y solo las sucursales con `allowed: true`. Si una sola cumple, selecciónala sin preguntar; si hay varias, pide al usuario que elija y recuerda la elección por sesión.
   - No existe un selector de contexto en el backend: la empresa elegida viaja en la ruta (`/companies/{company_id}/…`) y la sucursal en el cuerpo o la consulta (`branch_id`) de cada llamada. Cambiar de empresa es simplemente usar otro `company_id`.
   - Si `memberships` llega vacío, el usuario está autenticado pero no pertenece a ninguna empresa: muestra ese mensaje y no llames a las API de empresa (responderían `404`).
   - El detalle de cada paso está en [Acceso y contexto operativo](../principales/acceso-y-contexto-operativo.md).
4. **Leer los permisos** de `resource_access["sio-api"].roles` del token para mostrar u ocultar módulos ([Permisos](permisos.md)).
5. **Llamar a las API** con `Authorization: Bearer` y los identificadores obtenidos. Cada ficha de servicio enlaza a la guía de cada parámetro en [parametros/](../parametros/README.md).
6. **Tratar los errores** de forma uniforme: `401` renovar y reintentar una vez; `403` mostrar mensaje y `trace_id`; `404` revisar empresa, sucursal o identificador; `409` y `422` mostrar el `detail` y los `errors[]` ([Errores](errores.md)).

### Primera llamada completa

```bash
curl -sS 'https://sio-operational-context-dev.onrender.com/api/v1/me/operational-context' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Accept: application/json'
```

Respuesta `200` (identificadores ilustrativos; estructura tomada del modelo del servicio):

```json
{
  "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "memberships": [
    {
      "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "company_status": "ACTIVE",
      "status": "ACTIVE",
      "branches": [
        {
          "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
          "user_branch_status": "ACTIVE",
          "branch_status": "ACTIVE",
          "allowed": true,
          "reason": null
        }
      ]
    }
  ]
}
```

`memberships[].company_id` es el `company_id` y `memberships[].branches[].branch_id` el `branch_id` que usarás en el resto de las API.

### Cliente HTTP de ejemplo (TypeScript)

```ts
import { obtenerAccessToken } from "./auth/keycloak";

export class SioApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: unknown,
    public readonly traceId: string | null,
  ) {
    super(`SIO API ${status}`);
  }
}

async function solicitar<T>(url: string, init: RequestInit = {}, reintentar = true): Promise<T> {
  const token = await obtenerAccessToken();
  const respuesta = await fetch(url, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(init.headers ?? {}),
      Authorization: `Bearer ${token}`,
    },
    signal: AbortSignal.timeout(60_000),
  });

  if (respuesta.status === 401 && reintentar) {
    // El token pudo vencer entre la lectura y el envío: renovar una vez y reintentar una vez.
    return solicitar<T>(url, init, false);
  }
  if (respuesta.status === 204) {
    return undefined as T;
  }
  const cuerpo = await respuesta.json().catch(() => null);
  if (!respuesta.ok) {
    throw new SioApiError(respuesta.status, cuerpo, respuesta.headers.get("X-Trace-Id"));
  }
  return cuerpo as T;
}

export const sio = {
  get: <T>(url: string) => solicitar<T>(url),
  post: <T>(url: string, body: unknown, headers?: Record<string, string>) =>
    solicitar<T>(url, { method: "POST", body: JSON.stringify(body), headers }),
  put: <T>(url: string, body: unknown) =>
    solicitar<T>(url, { method: "PUT", body: JSON.stringify(body) }),
  patch: <T>(url: string, body: unknown) =>
    solicitar<T>(url, { method: "PATCH", body: JSON.stringify(body) }),
  delete: <T>(url: string) => solicitar<T>(url, { method: "DELETE" }),
};
```

## 5. Paginación y filtros

### Paginación por página (11 servicios)

Las listas aceptan `page` y `page_size` como parámetros de consulta y devuelven siempre la misma envoltura:

| Parámetro | Tipo | Valor por defecto | Rango |
|---|---|---|---|
| `page` | integer | `1` | ≥ 1 |
| `page_size` | integer | `20` (algunos reportes de Business Reporting y una lista de Purchase usan `50`) | 1 a 100 |

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total_records": 0,
  "total_pages": 0
}
```

Un `page_size` fuera de rango produce `422`. En Inventory el contrato OpenAPI no declara mínimo ni máximo para `page_size`, pero el servicio lo valida en código: fuera de 1–100 responde `422` con el código `PAGE_SIZE_OUT_OF_RANGE`.

### Paginación por cursor (Product Inventory Query)

Las seis consultas de productos y existencias de Product Inventory Query usan `cursor` y `page_size` (1 a 20) y devuelven:

```json
{
  "items": [],
  "page_size": 20,
  "has_next": false,
  "next_cursor": null,
  "pagination_reset": false,
  "pagination_reset_reason": null,
  "partial": false,
  "partial_reason": null,
  "sort_applied": "name_asc",
  "resolved_at": "2026-10-19T15:00:00Z"
}
```

Para avanzar se envía `cursor=<next_cursor>` con los **mismos filtros**. Si cambian los filtros, el orden o el tamaño de página, o el cursor caduca, el servicio reinicia desde la primera página e informa `pagination_reset: true` con la causa (`FILTERS_CHANGED`, `SORT_CHANGED`, `PAGE_SIZE_CHANGED`, `CURSOR_EXPIRED`). `partial: true` con `WORK_LIMIT_REACHED` indica que la página se cortó por límite de trabajo y hay que continuar con el cursor. El valor de `sort_applied` es ilustrativo; los valores reales se documentan en la ficha del servicio.

### Filtros habituales

| Parámetro | Servicios | Significado |
|---|---|---|
| `search` | Geography, Party Identity, Product Catalog, Commercial Relationship, Operational Context, Payment Reference, Product Inventory Query | Búsqueda por texto; el campo exacto se indica en cada operación |
| `status` | Casi todos los catálogos | Normalmente `ACTIVE` o `INACTIVE`; los valores permitidos están en cada ficha |
| `branch_id` | Inventory, Sales, Purchase, Business Reporting | Restringe a una sucursal de la empresa de la ruta |
| `date_from`, `date_to`, `occurred_at_from`, `occurred_at_to`, `operation_date_from`, `operation_date_to` | Reportes, Audit, Sales, Purchase | Rangos de fecha en ISO 8601 |

## 6. Idempotencia en operaciones de negocio

Cinco operaciones exigen la cabecera `Idempotency-Key` (obligatoria; sin ella el servicio responde `422` con `errors[].code = IDEMPOTENCY_KEY_REQUIRED`):

| Servicio | Operación |
|---|---|
| Purchase | `POST /companies/{company_id}/purchases/{purchase_id}/confirmation` |
| Purchase | `POST /companies/{company_id}/purchases/{purchase_id}/receipt` |
| Purchase | `POST /companies/{company_id}/purchases/{purchase_id}/cancellation` |
| Sales | `POST /companies/{company_id}/sales/{sale_id}/confirmation` |
| Sales | `POST /companies/{company_id}/sales/{sale_id}/cancellation` |

Reglas tomadas del contrato:

- Repetir la misma clave devuelve el mismo resultado sin duplicar efectos. Una operación nueva usa otra clave.
- Reutilizar una clave con un cuerpo distinto produce `409` `IDEMPOTENCY_KEY_CONFLICT`.
- Genera la clave en el cliente antes de enviar (por ejemplo `crypto.randomUUID()`), consérvala mientras reintentas por error de red y descártala cuando la operación responda.

```ts
const clave = crypto.randomUUID();
await sio.post(
  `https://sio-sales-dev.onrender.com/api/v1/companies/${companyId}/sales/${saleId}/confirmation`,
  {},
  { "Idempotency-Key": clave },
);
```

El cuerpo exacto de cada operación está en las fichas de [Sales](../servicios/sales.md) y [Purchase](../servicios/purchase.md).

## 7. Tipos de datos y formatos

| Tipo | Formato en JSON | Ejemplo |
|---|---|---|
| Identificadores | UUID en texto | `"550e8400-e29b-41d4-a716-446655440000"` |
| Fechas | ISO 8601 `YYYY-MM-DD` | `"2026-10-19"` |
| Fechas y horas | ISO 8601 con zona, normalmente UTC | `"2026-10-19T15:00:00Z"` |
| Estados | Texto en mayúsculas | `"ACTIVE"`, `"INACTIVE"` |
| Importes y cantidades | Según el servicio: número o texto decimal | Cada ficha indica el tipo declarado en el modelo Pydantic |

Las fichas de servicio diferencian campos obligatorios y opcionales, indican los valores permitidos (enumeraciones) y las validaciones de longitud o rango declaradas en los modelos.

## 8. Clasificación de seguridad

Todas las operaciones de esta documentación llevan una etiqueta:

| Clase | Significado | Qué debe hacer el frontend |
|---|---|---|
| `READ` | Solo consulta | Nada especial |
| `WRITE` | Crea o modifica información | Validar en pantalla antes de enviar; mostrar el resultado |
| `HIGH_RISK` | Elimina, inactiva, anula, cambia estados irreversibles, afecta existencias, precios, cartera o accesos | Pedir confirmación explícita al usuario; mostrar el `trace_id` si falla |

Las API no piden confirmación: la responsabilidad de confirmar una operación sensible es de la interfaz.

## 9. Lista de verificación de la primera integración

- [ ] El login con `sio-web` devuelve un Access Token con `aud` que incluye `sio-api`.
- [ ] `GET /health/live` responde `200` en el servicio que vas a usar.
- [ ] `GET /api/v1/me/operational-context` devuelve al menos una membresía `ACTIVE`; si devuelve `memberships: []`, pide al administrador una membresía para el usuario de prueba.
- [ ] Guardaste `company_id` y `branch_id` a partir de esa respuesta.
- [ ] Tu cliente HTTP envía `Authorization`, `Accept` y, con cuerpo, `Content-Type`.
- [ ] Tu cliente HTTP trata `401`, `403`, `404`, `409`, `422` y `503` según [Errores](errores.md).
- [ ] Ninguna credencial, token ni secreto aparece en el código fuente ni en los logs.

**Siguiente paso:** [Permisos y contexto operativo](permisos.md).
