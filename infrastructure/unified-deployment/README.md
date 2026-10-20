# Despliegue unificado de SIO

Modalidad **adicional y experimental**: los 12 microservicios FastAPI y sus 11 procesos auxiliares
(workers de auditoría, conciliadores y workers de precios) en **un solo contenedor y una sola URL**.
No reemplaza ni modifica los 12 despliegues independientes: usa el mismo código, los Dockerfiles de
cada servicio no se tocan y las bases de datos son las mismas. Keycloak sigue aparte.

| Archivo | Para qué |
| --- | --- |
| `Dockerfile` | Imagen única con las 2 librerías y los 12 servicios; arranca `supervisor.py`. |
| `supervisor.py` | PID 1: arranca la API y luego los workers, los rearranca si caen y reparte el `SIGTERM`. |
| `main.py` | Proceso de la API: construye los 12 servicios y despacha por prefijo. |
| `workers.py` | Proceso de workers: los 11 procesos auxiliares, cada uno en su hilo. |
| `registry.py` | Lista de servicios y aislamiento de su configuración (lo usan la API y los workers). |
| `requirements.txt` | Paquetes locales que instala el Dockerfile, en orden. |
| `.env.example` | Variables necesarias (sin valores reales). |
| `verify.py` | Comprobación de solo lectura de un despliegue (local o Render). |

## Arquitectura del contenedor

```
contenedor (Render: 512 MiB, 0,1 CPU)
└─ python supervisor.py                       PID 1, solo biblioteca estándar (≈ 30 MiB)
   ├─ uvicorn main:app  :$PORT                proceso de la API (≈ 175 MiB)
   │    /geography/...  /purchase/api/v1/...  … 12 aplicaciones FastAPI, un prefijo cada una
   └─ python workers.py                       proceso de workers (≈ 105 MiB), 11 hilos
        7 × audit-outbox-worker   ──HTTP──►  127.0.0.1:$PORT/audit/api/v1
        purchase-reconciler, sales-reconciler ──►  /inventory/api/v1
        purchase-price-update-worker  ──────────►  /commercial-relationship/api/v1
        commercial-relationship-price-worker      (solo su base)
```

### API: 12 servicios en un proceso ASGI

- Cada servicio se construye con **su propia fábrica** (`create_app`), sin cambios: sus routers,
  middlewares (CORS, trazas, `sio-auth`), manejadores de errores y conexiones.
- **Despacho por prefijo, no `app.mount()`**. Dentro de un `Mount`, Starlette deja la ruta completa
  en `scope["path"]` y `SIOAuthMiddleware` compara esa ruta con sus rutas públicas exactas, de modo
  que health y `/docs` pedirían token. El despachador quita el prefijo de `path` y lo pasa en
  `root_path`: cada aplicación ve las mismas rutas que en solitario y FastAPI publica `/docs` y
  `servers` con el prefijo.
- **Ciclo de vida**: un `Mount` no ejecuta el `lifespan` de la aplicación montada. Aquí se ejecuta
  el de las 12 (Geography registra su base de datos al arrancar; los demás cierran conexiones y
  clientes HTTP al terminar).
- **Llamadas entre servicios**: las `*_SERVICE_BASE_URL` apuntan por defecto a este mismo proceso
  (`http://127.0.0.1:$PORT/<servicio>[/api/v1]`). Siguen siendo HTTP, con el mismo token y las
  mismas validaciones: no hay atajos en memoria.

### Workers: 11 procesos auxiliares en un proceso aparte

- **Proceso aparte, no tareas de fondo de FastAPI**: un fallo o un bloqueo de un worker no afecta al
  bucle de eventos de la API, cada proceso tiene su GIL y el supervisor los rearranca por separado.
- **Hilos y no un proceso por worker**: cada proceso de Python con su servicio importado ocupa
  43–80 MiB (medido); los 11 como procesos sumarían ≈ 610 MiB, más que los 512 MiB de Render Free.
  En hilos, el proceso de workers ocupa ≈ 105 MiB. Los workers pasan casi todo el tiempo esperando
  a la base o a HTTP.
- **Mismo código**: el `audit-outbox-worker` usa el `Worker` y el `run_once` de `sio_audit` sin
  cambios; con `SIO_UNIFIED_AUDIT_CONCURRENCY` repite el bucle de `Worker.run()` tomando un turno
  **antes** de `run_once`, para que ningún worker espere con la transacción abierta. Los
  demás ejecutan el `run_cycle` de su módulo (`purchase_service.reconciler`,
  `purchase_service.price_update_worker`, `sales_service.reconciler`,
  `commercial_relationship_service.price_worker`) con los mismos objetos que arma su `main()` y el
  mismo bucle (ciclo, log, espera del intervalo). No se llama a `main()` porque instala manejadores
  de señal, que solo funcionan en el hilo principal. Las reglas, el orden, la idempotencia, los
  bloqueos (`FOR UPDATE SKIP LOCKED`, bloqueos consultivos) y los reintentos son los del servicio.
- **Configuración aislada**: cada worker se construye con el entorno de **su** servicio
  (`PURCHASE__DATABASE_URL` → `DATABASE_URL`), uno tras otro y antes de arrancar ningún hilo;
  después ya no lee el entorno.

### Configuración aislada por prefijos

Los servicios y sus workers leen variables con los mismos nombres (`DATABASE_URL`,
`KEYCLOAK_TOKEN_URL`, `AUDIT_CLIENT_ID`…). Cada uno ve el entorno compartido (sin prefijo) más sus
variables con prefijo, que prevalecen; nunca las de otro servicio. Payment Reference lee el entorno
también al importarse, por eso la importación ocurre dentro del mismo entorno aislado.

## Microservicios y rutas

Prefijo público = nombre del servicio sin `-service`; detrás va la ruta original, intacta.

| Servicio | Base pública |
| --- | --- |
| geography | `/geography/...` (sin `/api/v1`, como hoy) |
| party-identity | `/party-identity/api/v1/...` |
| product-catalog | `/product-catalog/api/v1/...` |
| operational-context | `/operational-context/api/v1/...` |
| payment-reference | `/payment-reference/...` (sin `/api/v1`, como hoy) |
| commercial-relationship | `/commercial-relationship/api/v1/...` |
| purchase | `/purchase/api/v1/...` |
| sales | `/sales/api/v1/...` |
| inventory | `/inventory/api/v1/...` |
| audit | `/audit/api/v1/...` |
| product-inventory-query | `/product-inventory-query/api/v1/...` |
| business-reporting | `/business-reporting/api/v1/...` |

Cada servicio conserva `/<servicio>/health/live`, `/<servicio>/health/ready`, `/<servicio>/docs`
y `/<servicio>/openapi.json` (estos dos, con `SIO_DOCS_ENABLED=true`).

Ejemplo: lo que en solitario es
`https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases`
en el unificado es `https://<servicio-unificado>.onrender.com/purchase/api/v1/companies/{company_id}/purchases`.

## Workers incluidos

Los mismos 11 procesos que definen los Compose de `infrastructure/services/`, con los mismos nombres.

| Worker (`SIO_UNIFIED_WORKERS`) | Servicio | Comando original | Función | Base | Identidad técnica | Frecuencia |
| --- | --- | --- | --- | --- | --- | --- |
| `party-identity-audit-outbox-worker` | Party Identity | `python -m sio_audit.worker` | Entrega su `audit_outbox` a Audit | la suya | `party-identity-service` | `AUDIT_OUTBOX_POLL_INTERVAL_SECONDS` (2 s) |
| `product-catalog-audit-outbox-worker` | Product Catalog | ídem | ídem | la suya | `product-catalog-service` | 2 s |
| `operational-context-audit-outbox-worker` | Operational Context | ídem | ídem | la suya | `operational-context-service` | 2 s |
| `commercial-relationship-audit-outbox-worker` | Commercial Relationship | ídem | ídem | la suya | `commercial-relationship-service` | 2 s |
| `purchase-audit-outbox-worker` | Purchase | ídem | ídem | la suya | `purchase-service` | 2 s |
| `sales-audit-outbox-worker` | Sales | ídem | ídem | la suya | `sales-service` | 2 s |
| `inventory-audit-outbox-worker` | Inventory | ídem | ídem | la suya | `inventory-service` | 2 s |
| `purchase-reconciler` | Purchase | `python -m purchase_service.reconciler` | Cierra operaciones `RECEIVE`/`CANCEL` `PENDING` antiguas consultando Inventory por clave | Purchase | `purchase-service` | `PURCHASE_RECONCILER_INTERVAL_SECONDS` (60 s), umbral 300 s |
| `sales-reconciler` | Sales | `python -m sales_service.reconciler` | Ídem para `CONFIRM`/`CANCEL` de ventas (con compensación) | Sales | `sales-service` | `SALES_RECONCILER_INTERVAL_SECONDS` (60 s), umbral 300 s |
| `purchase-price-update-worker` | Purchase | `python -m purchase_service.price_update_worker` | Entrega las solicitudes de precio de cada recepción a CR, en orden de secuencia por presentación | Purchase | `purchase-service` | `PURCHASE_PRICE_WORKER_INTERVAL_SECONDS` (5 s), espera máx. 300 s |
| `commercial-relationship-price-worker` | Commercial Relationship | `python -m commercial_relationship_service.price_worker` | Aplica el margen de la política vigente y actualiza la lista de precios | CR | ninguna (solo su base) | `CR_PRICE_WORKER_INTERVAL_SECONDS` (5 s), lote 50 |

Consecuencia de no ejecutarlos: los eventos de auditoría quedan `PENDING` en el outbox de cada base
(no se pierden), las recepciones no actualizan precios automáticamente (las solicitudes esperan en el
outbox de Purchase) y las operaciones interrumpidas quedan `PENDING` hasta que el cliente reintente.

**No incluidos, a propósito** (no son procesos de larga duración o no pertenecen al despliegue): las
migraciones (`alembic`), los seeds (`python -m <servicio>.seed`), `party_identity_service.integrity`,
`product_catalog_service.tools.verify_image_assets`, el arranque del almacenamiento de objetos y
`workflow-service` (sin Dockerfile ni despliegue). Audit, Geography, Payment Reference, Product
Inventory Query y Business Reporting no tienen workers.

## Arrancar y detener

```bash
docker build -f infrastructure/unified-deployment/Dockerfile -t sio-unified .   # desde la raíz
docker run --rm -p 8000:8000 --env-file /ruta/fuera/del/repo/unified.env sio-unified
docker stop <contenedor>    # SIGTERM, como Render
```

1. El supervisor arranca la API y espera a que `/health/live` responda (hasta
   `SIO_UNIFIED_API_START_TIMEOUT`, 300 s).
2. Después arranca el proceso de workers: dependen de la API (Audit, Inventory y CR están en el mismo
   contenedor) y así no compiten por la CPU durante el arranque de las 12 aplicaciones.
3. **Fallos**: si la API o el proceso de workers terminan sin que se haya pedido, el supervisor los
   rearranca con espera creciente (1 s … 60 s; vuelve a 1 s tras 5 min estable). Un fallo de los
   workers nunca detiene la API. Si un worker lanza una excepción que su bucle no atrapa (p. ej. el
   worker de precios de CR ante un error de base, que en Compose terminaba el contenedor), solo ese
   hilo se reinicia con la misma espera creciente, tras descartar su pool de conexiones.
4. **Configuración inválida** de un worker: ese worker no arranca (`config_error` en
   `/health/workers`, mensaje en el log con las contraseñas ocultas) y los demás siguen.
5. **Parada** (`SIGTERM`/`SIGINT`): primero los workers (cada uno termina su ciclo en curso; lo no
   confirmado queda en su outbox), luego la API (termina las peticiones en curso) y se fuerza lo que
   quede al agotar `SIO_UNIFIED_SHUTDOWN_TIMEOUT` (25 s; Render espera 30 s).
6. **Duplicados**: un bloqueo de archivo impide un segundo supervisor o un segundo proceso de workers
   en el contenedor (salen con código 3). Cada worker existe una sola vez. Entre contenedores (dos
   despliegues contra las mismas bases), los servicios ya se protegen (`SKIP LOCKED`, bloqueos
   consultivos, idempotencia por `event_id` y `purchase_detail_id`), pero **ejecute un solo juego de
   workers**: `SIO_UNIFIED_WORKERS=none` en cualquier otro despliegue que use las mismas bases.

Logs: todo va a la salida estándar. Cada línea de un worker lleva `[worker=<nombre>]`; las del
supervisor, `[supervisor]`.

## Variables de entorno

Ver `.env.example` (solo marcadores). En resumen:

- **Proceso**: `PORT`, `SIO_UNIFIED_PUBLIC_URL`, `SIO_UNIFIED_THREAD_LIMIT`, `SIO_UNIFIED_WORKERS`
  (`all`, `none` o nombres separados por comas), `SIO_UNIFIED_SHUTDOWN_TIMEOUT`,
  `SIO_UNIFIED_API_START_TIMEOUT`, `SIO_UNIFIED_API_GRACEFUL_SECONDS`,
  `SIO_UNIFIED_WORKERS_STOP_TIMEOUT`, `SIO_UNIFIED_STATE_DIR`, `SIO_UNIFIED_AUDIT_CONCURRENCY`
  (entregas simultáneas a Audit, 1 por defecto) y `SIO_UNIFIED_WORKERS_NICE` (10 por defecto).
- **Compartidas (sin prefijo)**: `SIO_DOCS_ENABLED`, `SIO_AUTH_ISSUER`, `SIO_AUTH_AUDIENCE`,
  `SIO_AUTH_JWKS_URL` y las de Keycloak (`KEYCLOAK_BASE_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_TOKEN_URL`,
  `KEYCLOAK_TIMEOUT_SECONDS`), que usan también los workers.
- **Por servicio (con prefijo)**: `DATABASE_URL` de los 10 servicios con base (la API y los workers
  de ese servicio usan la misma), las cuentas técnicas (`*_CLIENT_ID`, `*_CLIENT_SECRET` y, para el
  worker de auditoría, `AUDIT_CLIENT_ID`/`AUDIT_CLIENT_SECRET`, que en Compose son la cuenta del
  propio servicio), secretos de firma y los ajustes de intervalos, lotes y reintentos
  (`AUDIT_OUTBOX_*`, `*_RECONCILER_*`, `PURCHASE_PRICE_WORKER_*`, `CR_PRICE_WORKER_*`).
- Las `*_SERVICE_BASE_URL` no se definen: apuntan solas a este contenedor (`AUDIT_SERVICE_BASE_URL`
  de los workers de auditoría incluida).
- Cada worker de auditoría escribe su latido en un archivo propio
  (`$SIO_UNIFIED_STATE_DIR/heartbeat/<worker>`): el valor por defecto de `sio-audit` lo compartirían
  los siete.

## Health checks

| Ruta | Uso |
| --- | --- |
| `GET /health/live` | Proceso de la API vivo. **Health check de Render.** |
| `GET /health/ready` | `200` si los 12 `health/ready` responden `200`; si no, `503` con el detalle. |
| `GET /health/workers` | Estado que publica el proceso de workers cada 5 s: por worker `state` (`running`, `restarting`, `stopped`, `config_error`), `healthy`, último ciclo, reinicios y tipo del último fallo (nunca mensajes ni secretos). `503` si falta, tiene más de 60 s o algún worker no está sano; `200` con `disabled` si `SIO_UNIFIED_WORKERS=none`. |
| `GET /<servicio>/health/live`, `/ready` | Los de cada servicio, sin cambios. |
| `GET /` | Índice de servicios y prefijos. |

`/health/workers` **no** debe ser el health check de Render: un worker con problemas haría que
Render reiniciara también las API.

Cómo leerlos (verificado en la pila aislada, 0,1 CPU):

| Situación | `/health/live` | `/health/ready` | `/health/workers` |
| --- | --- | --- | --- |
| Arrancando (las 12 API se importan, ≈ 75–81 s con 0,1 CPU) | sin respuesta | sin respuesta | sin respuesta |
| API lista, workers aún construyéndose (hasta ≈ 112–115 s) | `200` | `200` | `503 unavailable` |
| `SIO_UNIFIED_WORKERS=none` | `200` | `200` | `200 disabled` |
| Todo en marcha | `200` | `200` | `200 ok` |
| Un worker con configuración inválida | `200` | `200` | `503 degraded`, ese worker `config_error` |
| Un worker en bucle de fallos | `200` | `200` | `503 degraded`, `restarting` |
| Proceso de workers caído o colgado | `200` | `200` | `503 stale` (> 60 s) hasta que el supervisor lo rearranca |
| Una base o dependencia caída | `200` | `503` con el servicio afectado | según el worker |

**Límite**: `healthy` indica que el bucle del worker gira, no que entregue. Con una credencial
incorrecta (p. ej. `AUDIT_CLIENT_SECRET`), Keycloak responde `401`, el evento queda `PENDING` con
`last_error_code=TokenUnavailableError` y se reintenta con espera creciente, pero el worker sigue
`healthy`. Se detecta en los logs (`Audit no disponible … causa=TokenUnavailableError`, `Audit
rechazó la identidad`) y con `neon-readonly-check.sql`.

## Probar localmente

Solo con bases y servicios de prueba aislados; nunca con Neon ni con credenciales reales.

1. Bases: una base PostgreSQL desechable por servicio con el esquema del servicio (por ejemplo, la
   pila aislada `sio-it` o una base en `tmpfs` con el esquema copiado de una base local de prueba).
2. Un emisor de tokens de prueba o el Keycloak de la pila aislada, con las cuentas técnicas de la
   plantilla del realm.
3. Un `.env` fuera del repositorio con las variables de `.env.example` apuntando a ese entorno.
4. `docker run` como arriba (para simular Render Free: `--cpus 0.1 --memory 512m`) y:
   - `python infrastructure/unified-deployment/verify.py http://localhost:8000 --expected-operations 411`
   - `curl http://localhost:8000/health/workers`
5. Para ver procesar a los workers, escriba en las bases de prueba lo que escriben los servicios
   (eventos con `sio_audit.outbox.record_audit_event`, solicitudes del outbox de precios, operaciones
   `PENDING` antiguas) o use las API de escritura del propio entorno de prueba.

## Verificación realizada (local, 2026-10-19)

Imagen construida con este Dockerfile (Python 3.13, FastAPI 0.149, Starlette 1.9; `pip check` sin
conflictos). Todo en local, sin Keycloak real, sin Neon y sin escrituras en bases reales:

- **Bases**: una PostgreSQL desechable (`tmpfs`) con el esquema copiado en solo lectura
  (`pg_dump --schema-only`) de las bases locales de desarrollo, sin ejecutar migraciones, más datos
  ficticios.
- **Tokens**: un emisor de prueba con las cuentas técnicas y los roles de la plantilla del realm.
- **Fase 1** (solo API): bases de prueba o de desarrollo local en solo lectura.

### API (fase 1, repetida con los workers activos)

| Prueba | Resultado |
| --- | --- |
| `health/live`, `health/ready`, `docs`, `openapi.json` de los 12 | 200 |
| Contrato OpenAPI frente al publicado hoy en Render | 11 idénticos; Product Catalog idéntico salvo la ruta pública de imágenes, que solo aparece con su secreto (en Render no lo está) |
| `verify.py`: 411 operaciones, preflight CORS y `401` sin token en cada operación protegida | 0 fallos |
| Paridad unificado vs. cada servicio en solitario (sin token, token inválido, sin roles, todos los permisos) | 1419 comparaciones en la fase 1 y 1415 con los workers activos (sin la ruta de imágenes), **0 diferencias** |
| Multi-tenant y permisos | `404` para otra empresa o usuario sin membresía; `403` sin el permiso |

### Workers y supervisor (fase 2)

| Prueba | Resultado |
| --- | --- |
| Arranque | API lista en 5–8 s y los 11 workers en marcha 2 s después; con 0,1 CPU, 73 s y 115 s |
| Aislamiento de variables | Cada worker usa la base, la cuenta técnica, la URL (127.0.0.1), los intervalos y el latido de su servicio |
| Auditoría (7 emisores) | 140 eventos escritos con `record_audit_event` → `SENT`; en Audit, `source_service` correcto por emisor y sin duplicados. Bajo saturación, 2100 eventos guardados exactamente una vez |
| Precios: Purchase → CR → lista | Secuencia 1 entregada antes que la 2 aunque la 2 era más antigua. Costos 2.380, 2.618, 2.856, 2.975 y 3.094 con margen 30 % → precios 3.094; 3.403,40; 3.712,80; 3.867,50; 4.022,20, y el anterior cerrado `AUTOMATIC_SUPERSEDED`. `updated_by = system:commercial-relationship-price-worker` |
| Precios: vigencia | Presentación que entra a la política mañana → `SKIPPED_NO_POLICY`; lista sin política → sin aplicación |
| Precios: idempotencia | Reenviar una solicitud entregada → `202` con el mismo `request_id`, sin aplicaciones ni precios nuevos; mismo detalle con otro contenido → `409 REQUEST_CONFLICT`. Un trigger de Purchase impide volver a `PENDING` lo entregado |
| Reintentos (emisor de tokens caído) | Eventos y solicitudes quedan `PENDING` con espera creciente, nada se marca sin confirmación; al volver, todo se entrega solo |
| Conciliadores | Operación `PENDING` antigua → Inventory por clave (`404`) → `FAILED OPERATION_NOT_APPLIED` con `system:purchase-reconciler` / `system:sales-reconciler` y su evento de auditoría entregado; la reciente (bajo el umbral) no se toca; claves de idempotencia intactas |
| Fallo dentro de un worker | Worker de precios de CR con su tabla oculta: reinicios con espera 1, 2, 4, 8, 16 s, la API sin efecto; al restablecer la tabla, se recupera y aplica la secuencia siguiente |
| Proceso de workers con `SIGKILL` | Rearrancado en 1 s; la API respondió 148 de 148 comprobaciones |
| API con `SIGKILL` | Rearrancada; responde en 5,2 s; los workers siguen (mismo PID) |
| Base congelada 30 s (`docker pause`) | `/health/live` sigue en 200; los workers esperan; 6 s después de descongelar, todo lo pendiente se procesa |
| Duplicados | Segundo `supervisor.py` o `workers.py` en el contenedor → código 3, no arranca |
| Apagado (`docker stop`) | 0,9 s en reposo y 5,4 s con los workers ocupados, código 0, workers antes que la API |
| `SIO_UNIFIED_WORKERS=none` | Solo la API; `/health/workers` → `200 disabled` |

### Integración en la pila aislada `sio-it` (fase 3, 2026-10-19)

El contenedor unificado (`sio-it-unified`, etiqueta `sio.integration.isolated=true`, red
`sio-it-network`, 512 MiB) sobre las bases efímeras (tmpfs) y el Keycloak de la pila, con los 11
workers individuales de la pila **detenidos**: todo el trabajo auxiliar lo hizo el contenedor
unificado. Antes de cualquier prueba se comprobó, desde dentro del contenedor, que las 21
`DATABASE_URL` (10 API y 11 workers) resuelven a contenedores `sio-it-*-db` con la etiqueta de
aislamiento, Keycloak a `sio-it-keycloak` y las URL entre servicios a `127.0.0.1`; y la barrera
`validation/isolation_guard.py` aceptó cada URL de las suites.

| Prueba | Resultado |
| --- | --- |
| Purchase `test_real_flow` + `test_policy_changes_before_receipt` | 13/13: borrador → confirmación → recepción → entrada en Inventory (24 u, costo 10.000 sin IVA) → anulación con reverso; políticas que faltan, que se quitan o cambian después de confirmar |
| Sales `test_real_flow` + `test_automatic_pricing_flow` | 14/14: precio automático tras la recepción usado en la venta, salidas y reversos |
| Commercial Relationship `test_real_dependencies` + `test_audit_delivery` | 13/13 (2 omitidas por la propia suite: token técnico no emitido en el realm de la pila) |
| Inventory (dependencias reales y auditoría) | 14/17; las 3 que fallan detienen contenedores por nombre fijo del entorno persistente (`sio-operational-context-service`…), no los del contenedor unificado: no aplican aquí |
| Conciliación de compra existente en Inventory | Recepción con la base de Inventory congelada → Purchase `503` a los 10,1 s y operación `PENDING`; al reanudar, Inventory aplica la entrada. El conciliador unificado la encuentra por clave → `SUCCEEDED`, recepción `RECEIVED`, **una sola** entrada (+10), capa FIFO con costo 2.000 sin IVA. Después el worker de entrega y el de CR aplican la política: costo 2.380 → precio 3.094,00 en la lista |
| Conciliación de venta existente en Inventory | Igual con una venta: operación `SUCCEEDED`, venta `CONFIRMED` con número `FV-202610-000001`, una sola salida (2 de 2 ejecuciones) |
| Compensación de venta | Salida aplicada en Inventory y secuencias desactivadas antes de conciliar → el conciliador no puede numerar, revierte la salida (`compensation_operation_id`), cierra `FAILED SEQUENCE_NOT_CONFIGURED`, venta en borrador y saldo restituido |
| Health checks con 0,1 CPU | `none`: live a los 75 s, 2 procesos, 178 MiB, `/health/workers` `200 disabled`. `all` con un secreto vacío: live a los 81 s, estado de workers a los 112 s, `503 degraded` con ese worker `config_error` y los otros 10 `running` |
| `neon-readonly-check.sql` | Todas las consultas válidas sobre el esquema migrado; dentro de la transacción `READ ONLY` un `UPDATE` es rechazado (`cannot execute UPDATE in a read-only transaction`) |
| Conexiones | `none`: 1 por base. `all`: 1–2 por base de emisor, 14 en total en reposo |

## Memoria y CPU medidas

Límites de Render Free simulados con `--cpus 0.1 --memory 512m`. CPU en núcleos, medida en el
cgroup; el 100 % de la cuota son 0,1 núcleos. Carga de la API: 2 clientes de lectura durante 60 s.

| Escenario | Memoria | CPU | API |
| --- | --- | --- | --- |
| Solo API (`SIO_UNIFIED_WORKERS=none`), reposo | ≈ 160 MiB | 0,002 (2 %) | 3,8 pet./s, p50 0,4 s, p95 1,3 s |
| API + 11 workers, reposo | 236–268 MiB | 0,009–0,011 (9–11 %) | 3,9 pet./s, p50 0,3 s, p95 1,5 s |
| Acumulado (2100 eventos + 50 precios), valores de Compose (lote 100, 5 s, 7 entregas a la vez) | pico 328 MiB | 0,1 (100 %) | **0,1 pet./s, p50 27 s, `503`**; 5 min sin confirmar ningún evento |
| Mismo acumulado con la mitigación (1 entrega a la vez, lote 20, 30 s, `nice` 10) | 252–278 MiB | 0,1 (100 %) mientras dura | 2,0 pet./s, p50 0,7 s, p95 3,5 s, 0 errores; precios en < 2 min y auditoría vaciada en ≈ 3,3 min |
| Arranque con 0,1 CPU | 236 MiB | — | API viva a los 73 s; workers sanos a los 115 s |

Procesos: 3. El supervisor ocupa ≈ 20 MiB, la API 170–190 MiB y los workers 105–120 MiB (11 hilos).
Como 11 procesos separados, los workers sumarían ≈ 610 MiB.

**Mitigación incluida** (sin perder datos: todo queda en el outbox hasta que Audit lo confirma):
- `SIO_UNIFIED_AUDIT_CONCURRENCY=1`: los 7 workers de auditoría ejecutan de a un ciclo. El turno se
  toma antes de abrir la transacción, así que mientras esperan no bloquean filas ni conexiones.
- `SIO_UNIFIED_WORKERS_NICE=10`: con poca CPU, la API va primero.
- En `.env.example`, lotes de 20 y 30 s de espera para los workers de auditoría.

Sin estos ajustes, cada lote de 100 tarda más de 5 s en Audit, el worker no recibe la confirmación,
reintenta, y el contenedor queda saturado sin avanzar.

## Limitaciones y riesgos

- **Trabajo pendiente acumulado en Neon.** Si hoy nadie ejecuta los workers contra Neon, los outbox de
  auditoría y de precios y las operaciones `PENDING` se acumulan. Al primer arranque con workers, se
  procesa todo:
  - se entregan los eventos de auditoría;
  - se **actualizan precios reales** con la política vigente en la fecha de cada recepción;
  - se cierran las operaciones antiguas.

  Es el comportamiento correcto, pero conviene revisarlo antes en solo lectura (ver "Publicarlo") y
  habilitar los workers por etapas.
- **CPU (0,1).** En reposo los workers usan ≈ 7 % de la cuota. Mientras procesan un acumulado, la CPU
  llega al 100 % y la API se vuelve más lenta (p50 de 0,3 s a 0,7 s con la mitigación); sin ella,
  deja de responder. Las cadenas de llamadas internas pueden agotar sus `*_TIMEOUT_SECONDS`.
- **Suspensión de Render Free.** Tras 15 min sin tráfico HTTP, Render detiene el contenedor y con él
  los workers. Lo pendiente espera, sin perderse, hasta la siguiente petición. Al despertar hay
  ≈ 75 s de arranque y después el acumulado compite con la API.
- **Neon.** Mientras el contenedor está despierto, los 7 workers de auditoría consultan su base cada
  2 s y los demás cada 5–60 s. Esas bases no llegan a suspenderse y consumen horas de cómputo del
  plan. Con `<SERVICIO>__AUDIT_OUTBOX_POLL_INTERVAL_SECONDS` más alto se reduce, a cambio de más
  demora. Hay hasta 11 conexiones más (cada worker con su pool, igual que en Compose).
- **Un solo juego de workers.** Los bloqueos de archivo (`supervisor.lock`, `workers.lock`) solo
  evitan un segundo proceso **dentro del mismo contenedor**; no son una exclusión distribuida. Otro
  despliegue (Compose, otro Web Service o la instancia nueva durante un redeploy de Render, que
  convive unos segundos con la anterior) puede ejecutar los mismos workers contra las mismas bases.
  La integridad no depende de esos bloqueos: los workers de auditoría y los conciliadores toman
  filas con `FOR UPDATE SKIP LOCKED`, Audit es idempotente por `event_id`, CR por solicitud y los
  conciliadores consultan Inventory por clave sin reaplicar. Aun así, para operar con un solo juego
  use `SIO_UNIFIED_WORKERS=none` en los demás despliegues.
- **Hilos dentro del proceso de workers.** Revisado: cada worker se construye con su entorno antes
  de arrancar ningún hilo y después no lee `os.environ` (solo `load_settings()` lo lee); cada uno
  tiene su engine y pool de SQLAlchemy, sus sesiones por ciclo, su cliente HTTP y su cliente de
  token (con su propio bloqueo); el `trace_id` es un `ContextVar` por hilo. No hay estado de módulo
  compartido entre servicios. Con `SIO_UNIFIED_AUDIT_CONCURRENCY` el turno se toma antes de abrir la
  transacción, así que ningún worker espera con filas bloqueadas.
- **Pooler de Neon.** Los servicios solo usan `pg_advisory_xact_lock` (de transacción) y `SET
  LOCAL`, compatibles con el pooler en modo transacción; se recomienda mantener las mismas
  `DATABASE_URL` que usan hoy los 12 servicios (no verificado con el pooler).
- **Fallos compartidos.** Un fallo grave del proceso de la API afecta a los 12 servicios a la vez.
  Uno del proceso de workers detiene los 11 hasta que el supervisor lo rearranca (1 s). Todos los
  hilos de la API comparten `SIO_UNIFIED_THREAD_LIMIT`.
- **Base que no responde.** Los workers no tienen tiempo máximo por consulta (igual que en
  Compose): con la base congelada esperan sin marcarse caídos hasta que vence su latido (1–4 min).
- **Diferencias con Compose.** Los workers comparten un proceso y no se llama a su `main()`. En lugar
  de reiniciar el contenedor, se reinicia el hilo. Purchase y Sales agregan `[worker=…]` a sus logs.
  La comprobación `--check` de cada worker se sustituye por `/health/workers`.
- **Secretos concentrados.** El Web Service unificado tiene los secretos de los 12 servicios.
- **Keycloak.** Las cuentas técnicas son las mismas que usan hoy los servicios; no requiere cambios
  en el realm.

## Publicarlo como un Web Service nuevo en Render (sin tocar los 12 actuales)

1. **Revisar en solo lectura** lo pendiente en Neon con `neon-readonly-check.sql` (un bloque por
   base, cada uno en `BEGIN TRANSACTION READ ONLY … ROLLBACK`, sin leer `payload`):

   | Base | Qué mirar | Qué pasará al activar |
   | --- | --- | --- |
   | PI, PC, OC, CR, Purchase, Sales, Inventory (`audit_outbox`) | `PENDING` y `vencidos_ahora`; `last_status_code`/`last_error_code` | Se entregan a Audit en lotes de 20. `401`/`403`/`409`/`422` repetidos = problema de identidad o de contenido, no atraso |
   | Purchase (`purchase_price_update_outbox`) | `PENDING`, empresas y presentaciones, pendientes de más de 1 día | Cada una puede crear un **precio nuevo real** cuando CR la aplique |
   | CR (`automatic_price_applications`) | `PENDING`/`FAILED` vencidas y su `last_error_code` | `APPLIED` crea el precio y cierra el anterior |
   | Purchase y Sales (`*_operations`) | `PENDING` con `updated_at` de más de 300 s | El conciliador consulta Inventory por clave: completa, marca `FAILED` o (Sales) compensa |
   | Cualquiera (`pg_stat_activity`) | Conexiones actuales y `max_connections` | El servicio nuevo suma ≈ 14 en reposo con workers y las de los pools de la API bajo carga |

   Riesgos: si hay solicitudes de precio antiguas, decidir con negocio antes de activar el worker de
   precios; si las mismas bases ya tienen workers en otro despliegue, ese juego y el nuevo
   competirán (sin duplicar datos). Use un rol de solo lectura si existe y no guarde la URL en
   archivos versionados.
2. Crear un **Web Service nuevo** (no editar los existentes) desde este repositorio:
   - Runtime: Docker. **Dockerfile Path**: `infrastructure/unified-deployment/Dockerfile`.
     **Docker Build Context**: `.` (raíz del repositorio).
   - **Health Check Path**: `/health/live` (no `/health/workers`).
3. Cargar las variables de `.env.example` con los valores actuales de cada servicio, copiados desde
   cada Web Service de Render a su prefijo. No modificar las variables de los 12.
4. Fijar `SIO_UNIFIED_PUBLIC_URL` con la URL que asigne Render.
5. **Primera publicación con `SIO_UNIFIED_WORKERS=none`** (con 0,1 CPU la API tarda ≈ 75–81 s en
   abrir el puerto; `SIO_UNIFIED_API_START_TIMEOUT=300` deja margen) y comprobar `/health/live` y
   `/health/ready` en `200` y `/health/workers` en `200 disabled`, y
   `python infrastructure/unified-deployment/verify.py https://<nuevo>.onrender.com --expected-operations 411`
   (con `SIO_DOCS_ENABLED=true`; luego puede volver a `false`).
6. Habilitar los workers por etapas (cada cambio de variable redespliega; ≈ 2 min hasta
   `/health/workers` en `200 ok`) y vigilar `/health/workers`, los logs y la CPU antes de pasar a la
   siguiente:
   - **Etapa A, auditoría**: `party-identity-audit-outbox-worker,product-catalog-audit-outbox-worker,operational-context-audit-outbox-worker,commercial-relationship-audit-outbox-worker,purchase-audit-outbox-worker,sales-audit-outbox-worker,inventory-audit-outbox-worker`.
     Esperar a que el SQL de revisión muestre los `audit_outbox` sin `PENDING` vencidos.
   - **Etapa B, conciliadores**: añadir `purchase-reconciler,sales-reconciler`.
   - **Etapa C, precios** (solo tras decidir sobre las solicitudes pendientes): añadir
     `commercial-relationship-price-worker` y después `purchase-price-update-worker`, o `all`.
   - Para retroceder: volver a la lista anterior o a `none`; lo no procesado queda en los outbox.
7. Los clientes (frontends) usan la URL única con los prefijos de la tabla de rutas. Los 12 Web
   Services siguen activos con sus URL actuales.
