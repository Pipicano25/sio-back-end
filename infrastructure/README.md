# Infraestructura de SIO

Esta carpeta contiene los recursos y la configuración necesarios para levantar los servicios externos de SIO.

## Contenido

- `compose.yaml`: proyecto compose `sio`, solo infraestructura compartida
  (Keycloak, su base, RabbitMQ) y la red `sio-network`.
- `services/<microservicio>.yaml`: un proyecto compose por microservicio
  (`<microservicio>`, sin prefijo) con su base propia, su base de pruebas
  (perfil `test`) y, si ya existe, su contenedor de aplicación. Es la única
  definición Compose del microservicio. Se une a `sio-network` (externa), por eso `sio` se levanta
  primero.
- `.env.example`: plantilla de variables de entorno (una sola para todos los
  proyectos; no define `COMPOSE_PROJECT_NAME`, cada archivo declara su `name:`).
- `keycloak/`: configuración de Keycloak (Containerfile, plantilla del
  realm, realm ya renderizado, temas).
- `scripts/`: utilidades locales — `render-realm.sh`, `rebuild-all.sh`
  (regenera todos los proyectos en orden) y `reset-business-data.sh` (vacía
  los datos de negocio en desarrollo; ver "Reset de datos funcionales").

## Estructura de carpetas

```text
infrastructure/
├── compose.yaml                      (proyecto "sio")
├── services/
│   ├── geography-service.yaml        (proyecto "geography-service")
│   ├── party-identity-service.yaml   (proyecto "party-identity-service")
│   └── ...                           (uno por microservicio)
├── .env.example
├── scripts/
│   ├── rebuild-all.sh
│   ├── render-realm.sh
│   ├── reset-business-data.sh
│   └── tests/reset-business-data.test.sh
└── keycloak/
    ├── Containerfile
    ├── realm-template/
    │   └── sio-realm.template.json   (versionado en git, con placeholders)
    ├── import/
    │   └── sio-realm.json            (generado por render-realm.sh, NO versionado)
    └── themes/
```

> Nota: no hay carpeta `postgres/` con scripts de inicialización — cada
> microservicio tiene su propia base de datos PostgreSQL independiente,
> creada directamente por su propio contenedor (variables `POSTGRES_DB` /
> `POSTGRES_USER` / `POSTGRES_PASSWORD`), sin script compartido.

## Servicios incluidos

Proyecto `sio` (`compose.yaml`):

- `keycloak`: servidor de identidad.
- `keycloak-db`: base de datos PostgreSQL de Keycloak.
- `rabbitmq`: broker de mensajería para eventos de dominio entre
  microservicios (patrón outbox/inbox).

Un proyecto `<microservicio>` por microservicio (`services/<microservicio>.yaml`).
Es la **única definición Compose** del microservicio: su base de datos
PostgreSQL **independiente**, su base de pruebas (perfil `test`, solo a
pedido) y, cuando existe, su contenedor de aplicación (puertos en
`docs/port-map.md`):

| Proyecto | Contenedores |
|---|---|
| `geography-service` | `geography-db`, `geography-service`, `geography-test-db` (perfil `test`) |
| `party-identity-service` | `party-identity-db`, `party-identity-service`, `party-identity-audit-outbox-worker`, `party-identity-test-db` (perfil `test`) |
| `product-catalog-service` | `product-catalog-db`, `product-catalog-service`, `product-catalog-audit-outbox-worker`, `product-catalog-test-db` (perfil `test`) |
| `operational-context-service` | `operational-context-db`, `operational-context-service`, `operational-context-audit-outbox-worker`, `operational-context-test-db` (perfil `test`) |
| `payment-reference-service` | `payment-reference-db`, `payment-reference-service`, `payment-reference-test-db` (perfil `test`) |
| `commercial-relationship-service` | `commercial-relationship-db`, `commercial-relationship-service`, `commercial-relationship-audit-outbox-worker`, `commercial-relationship-test-db` (perfil `test`) |
| `purchase-service` | `purchase-db`, `purchase-service`, `purchase-audit-outbox-worker`, `purchase-reconciler`, `purchase-test-db` (perfil `test`) |
| `sales-service` | `sales-db`, `sales-service`, `sales-audit-outbox-worker`, `sales-reconciler`, `sales-test-db` (perfil `test`) |
| `inventory-service` | `inventory-db`, `inventory-service`, `inventory-audit-outbox-worker`, `inventory-test-db` (perfil `test`) |
| `audit-service` | `audit-db`, `audit-service`, `audit-test-db` (perfil `test`) |
| `workflow-service` | `workflow-db` |

No hay `docker-compose.yml` dentro de `services/<microservicio>/`: antes
existía un entorno independiente por servicio cuyo proyecto tomaba el nombre de
la carpeta, y Docker Desktop mostraba dos grupos por microservicio
(`geography-service` y `sio-geography-service`). Se retiró el 2026-10-05.

Base de pruebas de un microservicio (desde la raíz del repositorio):

```bash
docker compose --file infrastructure/services/geography-service.yaml --env-file infrastructure/.env --profile test up -d geography-test-db
```

Todos comparten la red `sio-network`, así que entre contenedores se siguen
usando los nombres de servicio (`http://keycloak:8080`,
`http://party-identity-service:8000`). `depends_on` no cruza proyectos: el
orden (primero `sio`, después los microservicios) lo garantiza
`scripts/rebuild-all.sh`.

Los `<servicio>-audit-outbox-worker` (Inventory, Purchase y Sales; desde la feature 016 también Party
Identity, Product Catalog, Operational Context y Commercial Relationship) usan la imagen y la base de
su servicio y entregan la tabla `audit_outbox` a `audit-service`. Arrancan después de las migraciones
del servicio (la tabla `audit_outbox` debe existir); si Audit aún no está disponible, los eventos
quedan `PENDING` y se entregan cuando vuelve, sin bloquear la API. Cada worker usa el secreto del
cliente técnico de su servicio en `.env`; Product Catalog usa `PRODUCT_CATALOG_SERVICE_CLIENT_SECRET`
(cliente `product-catalog-service`, solo para su auditoría).

## Requisitos previos

- Docker 24+ con Docker Compose v2.
- `python3` solo si desea formatear o validar JSON con `python3 -m json.tool`.
- Copiar la plantilla de entorno antes de ejecutar:

```bash
cp .env.example .env
```

> No se incluye la base de datos de producción ni usuarios reales. Esta infraestructura es para desarrollo/local.

Después de crear `.env`, Keycloak importa el realm desde la plantilla versionada al iniciar con una
base vacía (ver sección siguiente). `./scripts/render-realm.sh` es opcional: solo comprueba que la
plantilla se resuelve con los valores de `.env`.

## Configuración de Keycloak

El realm inicial de Keycloak se define en una **plantilla**:

- `keycloak/realm-template/sio-realm.template.json`

`compose.yaml` monta esta plantilla como `/opt/keycloak/data/import/sio-realm.json` y Keycloak
(`--import-realm`) sustituye los `${VAR}` con las variables de entorno del contenedor, que vienen de
`.env` (realm, URL de `sio-web`, contraseña de los usuarios de prueba y secretos de los clientes
técnicos). Ningún secreto se versiona: la plantilla solo contiene sus referencias `${…}`.

**El repositorio es la fuente de verdad** del realm: usuarios de prueba (con `id` fijo, para que su
`sub` sea el mismo en cada reconstrucción y sigan siendo válidas las referencias que otros servicios
guardan, p. ej. las membresías de Operational Context), grupos, roles y permisos, clientes, cuentas de
servicio y sus roles, scopes y mappers. No se configura nada a mano en la consola: un cambio se hace
en la plantilla y se aplica reconstruyendo Keycloak. Ver `keycloak/import/README.md`.

El realm incluye:

- Realm `sio`
- Cliente público `sio-web`
- Recurso protegido `sio-api`
- Roles generales
- Grupos generales
- Audience mapper
- Configuración PKCE S256
- Clientes técnicos con cuenta de servicio (`party-identity-service`, `operational-context-service`,
  `commercial-relationship-service`, `inventory-service`, `purchase-service`, `sales-service`, y los clientes de pruebas
  `audit-test-emitter` e `inventory-test-operator`) y sus roles
- Usuarios de prueba (`admin.test`, `supervisor.test`, `compras.test`, `ventas.test`,
  `reportes.test`, `consulta.test`, `inventario.test`) con `id` fijo

No contiene datos de empresas, sucursales ni usuarios productivos.

### Sesiones y tokens de `sio-web`

| Parámetro | Valor | Efecto |
| --- | --- | --- |
| `accessTokenLifespan` | 300 s | Vida del Access Token |
| `ssoSessionIdleTimeout` | 1800 s | Sin renovar en 30 min, el Refresh Token vence y hay que volver a iniciar sesión |
| `ssoSessionMaxLifespan` | 36000 s | Ninguna sesión dura más de 10 h, aunque haya actividad |
| `revokeRefreshToken` / `refreshTokenMaxReuse` | `true` / `0` | Rotación: cada renovación entrega un Refresh Token nuevo y el anterior deja de servir. Reutilizar uno ya usado (también dos renovaciones simultáneas) **cierra la sesión**: Keycloak invalida además el Refresh Token vigente |
| Scopes de `sio-web` | sin `offline_access` | No se emiten tokens offline |
| `directAccessGrantsEnabled` | `${SIO_WEB_DIRECT_ACCESS_GRANTS_ENABLED:false}` | Grant `password` solo donde la variable vale `true` |

- El flujo del frontend es Authorization Code + PKCE S256. El grant `password` existe solo para desarrollo y
  pruebas (`services/get_token.py`, `docs/ejemplo/`, pruebas de integración): `compose.yaml` y la pila aislada
  definen `SIO_WEB_DIRECT_ACCESS_GRANTS_ENABLED=true`; un despliegue de producción no la define (o la define en
  `false`) y la plantilla lo deja desactivado.
- Los clientes técnicos usan `client_credentials` y no reciben Refresh Token: piden un token nuevo al vencer.
- `--import-realm` no reimporta un realm existente: estos valores llegan a un Keycloak ya creado solo al
  reconstruirlo o aplicándolos con la Admin API. En el realm habitual de desarrollo se aplicaron así el
  2026-10-19 (rotación y retiro de `offline_access`; el grant `password` sigue activo).
- Pruebas (solo en la pila aislada): `libs/sio-auth/tests/integration/` (permisos en login y renovación,
  rotación, reutilización, concurrencia, logout, expiración y clientes técnicos). Uso de los permisos en el
  frontend: `docs/frontend-permissions.md`.

### Validación manual con cURL

Requiere `curl` y `jq`. Cada bloque indica su entorno: **desarrollo** (`sio-*`, Keycloak `8081`) o **pila
aislada** (`sio-it-*`, Keycloak `18081`). Ambos tienen la misma política de rotación; el paso 5 cierra la sesión
usada (se vuelve a empezar por el paso 1). Si la contraseña llega vacía o errónea en dos intentos seguidos, la
protección contra fuerza bruta bloquea al usuario 60 s y Keycloak responde `Invalid user credentials` incluso con
la contraseña correcta: esperar un minuto.

```bash
# --- Desarrollo (realm habitual): contraseña de los usuarios *.test, sin mostrarla
export KEYCLOAK_TEST_USER_PASSWORD="$(grep '^KEYCLOAK_TEST_USER_PASSWORD=' infrastructure/.env | cut -d= -f2-)"
export KC_URL=http://localhost:8081 GEOGRAPHY_URL=http://127.0.0.1:8102

# --- Pila aislada (en lugar del bloque anterior; levantada con validation/isolated-stack/stack.sh)
export KEYCLOAK_TEST_USER_PASSWORD="$(grep '^KEYCLOAK_TEST_USER_PASSWORD=' validation/isolated-stack/.env | cut -d= -f2-)"
export KC_URL=http://localhost:18081 GEOGRAPHY_URL=http://127.0.0.1:18102

# --- Común
export KC_TOKEN_URL="$KC_URL/realms/sio/protocol/openid-connect/token" SIO_USER=consulta.test
jwt_payload() { local p; p=$(cut -d. -f2 <<<"$1" | tr '_-' '/+'); while (( ${#p} % 4 )); do p+="="; done; base64 -d <<<"$p" | jq "${2:-.}"; }
```

1. Login (`access_token`, `refresh_token`, `expires_in`):

```bash
RESP=$(curl -s -X POST "$KC_TOKEN_URL" -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username="$SIO_USER" --data-urlencode password="$KEYCLOAK_TEST_USER_PASSWORD")
echo "$RESP" | jq '{token_type, expires_in, refresh_expires_in, access_token: (.access_token[0:20]+"…"), refresh_token: (.refresh_token[0:20]+"…")}'
export ACCESS_TOKEN=$(jq -r .access_token <<<"$RESP") REFRESH_TOKEN=$(jq -r .refresh_token <<<"$RESP")
# {"token_type": "Bearer", "expires_in": 300, "refresh_expires_in": 1800, "access_token": "eyJhbGciOiJSUzI1NiIs…", ...}
```

2. Refresh Token (renovar sin credenciales):

```bash
export OLD_REFRESH_TOKEN=$REFRESH_TOKEN
RESP=$(curl -s -X POST "$KC_TOKEN_URL" -d grant_type=refresh_token -d client_id=sio-web \
  --data-urlencode refresh_token="$REFRESH_TOKEN")
echo "$RESP" | jq '{expires_in, refresh_expires_in, refresh_token_nuevo: (.refresh_token != env.OLD_REFRESH_TOKEN)}'
export ACCESS_TOKEN=$(jq -r .access_token <<<"$RESP") REFRESH_TOKEN=$(jq -r .refresh_token <<<"$RESP")
# {"expires_in": 300, "refresh_expires_in": 1800, "refresh_token_nuevo": true}
```

3. Permisos del Access Token (repetir tras el login y tras cada renovación):

```bash
jwt_payload "$ACCESS_TOKEN" '{preferred_username, aud, exp, permisos: .resource_access["sio-api"].roles}'
# {"preferred_username": "consulta.test", "aud": ["sio-api", "account"], "exp": 1792380564,
#  "permisos": ["consulta", "perm:geography:global_countries:read", "perm:operational-context:branches:read", ...]}
```

Los permisos son los valores `perm:{servicio}:{recurso}:{accion}` de `resource_access.sio-api.roles` (`all` es
comodín); el valor sin `perm:` (`consulta`) es el perfil del grupo y no concede nada. Detalle en
`docs/frontend-permissions.md`.

4. API protegida (Geography, permiso `perm:geography:global_countries:read`):

```bash
curl -s "$GEOGRAPHY_URL/global-countries?page_size=2" -H "Authorization: Bearer $ACCESS_TOKEN" | jq '{page, total_records, items: [.items[].name]}'
# 200 con la página de países (en la pila aislada, sin seed, "total_records": 0)
curl -s "$GEOGRAPHY_URL/global-countries" | jq .
# {"detail": "Se requiere un token de acceso Bearer"}   (401 sin token)
```

5. Rotación (después del paso 2; cierra esa sesión):

```bash
curl -s -X POST "$KC_TOKEN_URL" -d grant_type=refresh_token -d client_id=sio-web \
  --data-urlencode refresh_token="$OLD_REFRESH_TOKEN" | jq .
# {"error": "invalid_grant", "error_description": "Maximum allowed refresh token reuse exceeded"}
curl -s -X POST "$KC_TOKEN_URL" -d grant_type=refresh_token -d client_id=sio-web \
  --data-urlencode refresh_token="$REFRESH_TOKEN" | jq .error
# "invalid_grant"   (la reutilización invalidó también el token vigente: volver al paso 1)
```

Cerrar la sesión (con un Refresh Token vigente, p. ej. tras repetir los pasos 1 y 2; el Access Token emitido vale
hasta su `exp`):

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST "$KC_URL/realms/sio/protocol/openid-connect/logout" \
  -d client_id=sio-web --data-urlencode refresh_token="$REFRESH_TOKEN"   # 204
unset KEYCLOAK_TEST_USER_PASSWORD ACCESS_TOKEN REFRESH_TOKEN OLD_REFRESH_TOKEN RESP
```

## Comandos principales

### Levantar todo el entorno

Lo más simple es el script, que levanta `sio` y luego cada microservicio,
aplica migraciones y (en modo completo) carga los datos iniciales:

```bash
bash scripts/rebuild-all.sh --rebuild   # conserva la información
bash scripts/rebuild-all.sh --status    # estado por proyecto
```

### Levantar la infraestructura

```bash
cp .env.example .env   # si aún no existe
docker compose --file compose.yaml --env-file .env up --build -d
```

Luego, cada microservicio en su propio proyecto (requiere `sio` arriba, por
la red `sio-network` y Keycloak):

```bash
docker compose --file services/geography-service.yaml --env-file .env up --build -d
```

Los comandos de las secciones siguientes aplican igual a cualquier
`services/<microservicio>.yaml`.

Para levantar solo Keycloak (y su base de datos, por dependencia):

```bash
docker compose --file compose.yaml --env-file .env up --build -d keycloak
```

### Listar servicios en ejecución

```bash
docker compose --file compose.yaml --env-file .env ps
```

## Detener servicios

### Parar servicios (mantener contenedores)

```bash
docker compose --file compose.yaml --env-file .env stop
```

### Iniciar servicios detenidos

```bash
docker compose --file compose.yaml --env-file .env start
```

### Detener y eliminar contenedores sin eliminar datos

```bash
docker compose --file compose.yaml --env-file .env down
```

### Forzar recreación del contenedor de Keycloak DB

```bash
docker compose --file compose.yaml --env-file .env up -d --force-recreate keycloak-db
```

### Reconstruir Keycloak desde la plantilla

`--import-realm` no sobrescribe un realm que ya existe: para aplicar un cambio de la plantilla se
reconstruye Keycloak desde cero (se pierden solo sesiones y datos que no estén en la plantilla):

```bash
docker compose --file compose.yaml --env-file .env stop keycloak keycloak-db
docker compose --file compose.yaml --env-file .env rm -f keycloak keycloak-db
docker volume rm sio-keycloak-db-data
docker compose --file compose.yaml --env-file .env up -d keycloak-db keycloak
```

Después, reiniciar `sio-operational-context-service` (guarda en memoria el UUID interno del cliente
`sio-api`, que cambia al reconstruir Keycloak), verificar que los usuarios de prueba y las cuentas de
servicio obtienen token y ejecutar las pruebas `-m integration` de los microservicios.

## Validación de configuración

Verificar que el archivo `docker compose` sea válido:

```bash
docker compose --file compose.yaml --env-file .env config
```

### Verificar OpenID Connect

```bash
curl http://localhost:8081/realms/sio/.well-known/openid-configuration
```

Formatear la respuesta JSON (requiere Python):

```bash
curl -s http://localhost:8081/realms/sio/.well-known/openid-configuration | python3 -m json.tool
```

### Verificar el health check de Keycloak

```bash
curl http://localhost:9000/health/ready
```

## Gestión de volúmenes

Cada base de datos tiene su propio volumen nombrado
`sio-<microservicio>-db-data` (ver `services/<microservicio>.yaml`), más
`sio-keycloak-db-data` y `sio-rabbitmq-data`.

Para eliminar únicamente el volumen de Keycloak:

```bash
docker volume rm sio-keycloak-db-data
```

Para eliminar el volumen de un microservicio en particular (ejemplo con
`operational-context`):

```bash
docker volume rm sio-operational-context-db-data
```

Después, levanta de nuevo los servicios:

```bash
docker compose --file services/operational-context-service.yaml --env-file .env up --build -d
```

## Almacenamiento de objetos (MinIO)

Proyecto `object-storage` (`services/object-storage.yaml`): almacenamiento propio de SIO, compatible
con S3, para el contenido de los activos de Product Catalog (imágenes de producto).

- Bucket privado `sio-product-assets` (sin acceso anónimo); objetos por hash: `assets/<sha256>.<ext>`.
- Volumen persistente `sio-object-storage-data`: **ni `rebuild-all.sh --full` ni
  `reset-business-data.sh` lo borran**. Vaciarlo sería una operación explícita aparte.
- Imagen fijada por digest (MinIO dejó de publicar imágenes gratuitas; se usa la compilación desde el
  código fuente de Chainguard).
- Puertos solo locales: API `127.0.0.1:9002`, consola `127.0.0.1:9003`. Entre contenedores:
  `http://object-storage:9000` (red `sio-network`).
- Credenciales solo en `infrastructure/.env` (ver `.env.example`): `MINIO_ROOT_*` (solo para el
  bootstrap), `PRODUCT_CATALOG_ASSET_STORAGE_*` (solo lectura) y `MIGRATION_ASSET_STORAGE_*`
  (lectura y escritura, sin borrado). Sin ellas, `rebuild-all.sh` omite el proyecto con un aviso.
- Bootstrap idempotente (`object-storage/bootstrap.sh`; `rebuild-all.sh` lo ejecuta tras levantar):

```bash
docker compose --project-name object-storage --file infrastructure/services/object-storage.yaml \
  --env-file infrastructure/.env up -d --wait
docker compose --project-name object-storage --file infrastructure/services/object-storage.yaml \
  --env-file infrastructure/.env run --rm object-storage-bootstrap
```

El frontend nunca habla con MinIO: obtiene el contenido por
`GET /api/v1/products/{product_id}/assets/{asset_id}/content` (Product Catalog).
Pruebas: `bash infrastructure/scripts/tests/object-storage.test.sh [--live]` (`--live` usa un MinIO
efímero aislado).

## Reset de datos funcionales

> **Solo para entornos de desarrollo o pruebas. Nunca en producción.** Borra
> de forma irreversible las empresas, sucursales, usuarios operativos,
> identidades, productos, clientes, proveedores, listas de precios, compras,
> ventas, inventario (kardex, saldos y capas FIFO) y eventos de auditoría.

`scripts/reset-business-data.sh` deja el entorno sin datos de negocio, listo
para una importación, sin tocar bases, esquemas ni volúmenes:

```bash
# Muestra qué borraría (servicio, tabla, filas) sin modificar nada
bash infrastructure/scripts/reset-business-data.sh --dry-run

# Ejecuta el borrado (exige el texto exacto)
bash infrastructure/scripts/reset-business-data.sh --confirm RESET-SIO-BUSINESS-DATA
```

- **Limpia**, en este orden: Sales → Purchase → Inventory → Commercial
  Relationship → Operational Context → Product Catalog → Party Identity →
  Audit (los dependientes antes que aquello a lo que referencian).
- **Conserva**: Geography y Payment Reference (no se tocan), Keycloak con sus
  usuarios y clientes, `alembic_version`, y los maestros de los seeds: unidades
  de medida, tipos de empaque y tipos de grupo (Product Catalog); sectores
  CIIU, reglas de identificación y la trazabilidad de la migración `0020`
  (Party Identity).
- **Cómo**: detiene APIs, workers y conciliadores (`docker compose stop`), hace
  un `TRUNCATE` por base en una transacción sobre una lista explícita de
  tablas, sin `CASCADE`, los vuelve a iniciar, ejecuta los seeds idempotentes y
  valida: migraciones en head, `/health/live` y `/health/ready`, Geography y
  Payment Reference intactos, maestros conservados y 0 filas en lo limpiado.
- **Protecciones**: sin `--confirm` no borra; se niega si `KEYCLOAK_PUBLIC_URL`
  no apunta a la máquina local o si `SIO_ENVIRONMENT` (opcional) no es
  `development`, `test` o `local`; se detiene si una base tiene una tabla que
  el script no clasifica o si un servicio no está en head. Nunca ejecuta
  `docker compose down -v`, `docker volume rm` ni `DROP DATABASE`.
- La salida por consola es el único registro; no escribe archivos ni muestra
  valores de `.env`.

Pruebas del script (sin borrar nada): `bash infrastructure/scripts/tests/reset-business-data.test.sh`
(con `--live` también ejecuta el `--dry-run` contra el entorno levantado).

## URLs de administración

- Keycloak Admin: `http://localhost:8081/admin/master/console/`
- Keycloak Account: `http://localhost:8081/realms/sio/account/`

### Usuarios de ejemplo

| Usuario           |
| ----------------- |
| `admin.test`      |
| `supervisor.test` |
| `compras.test`    |
| `ventas.test`     |
| `inventario.test` |
| `reportes.test`   |
| `consulta.test`   |

## Notas adicionales

- El servicio `keycloak` se construye desde `keycloak/Containerfile`.
- El servicio `keycloak` importa automáticamente el realm definido en `keycloak/import/`.
- Las contraseñas de ejemplo deben cambiarse antes de usar la infraestructura en un entorno compartido.
