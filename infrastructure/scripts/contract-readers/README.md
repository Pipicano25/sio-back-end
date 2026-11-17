# Roles de lectura de contrato

`provision.py` crea y comprueba los roles con los que un consumidor lee las vistas de contrato de otro servicio
(constitución 3.0.0, D27; spec `025-direct-contract-reads`, `contracts/reader-roles.md`).

Cada propietario declara en `services/<propietario>/contract/grants.yaml` qué consumidor lee qué vista. Por cada
pareja, el script crea:

| Rol | Tipo | Permisos |
|---|---|---|
| `contract_<prop>__<cons>` | `NOLOGIN` | `CONNECT` a la base, `USAGE` en `contract` y `SELECT` solo en las vistas declaradas |
| `<cons>_contract_reader` | `LOGIN`, solo lectura | Miembro de sus roles de acceso; `default_transaction_read_only=on` |

Los roles no se crean en Alembic, porque los usuarios de servicio de la VPS no tienen `CREATEROLE`.

## Uso

Desde la raíz del repositorio y **después** de `alembic upgrade head` de los propietarios:

```bash
python infrastructure/scripts/contract-readers/provision.py aplicar   --entorno local
python infrastructure/scripts/contract-readers/provision.py verificar --entorno local
```

Opciones:

- `--entorno local|aislada|servidor`. En `servidor` exige contraseñas de al menos 20 caracteres.
- `--propietario <nombre>`, repetible, para limitar a ciertos propietarios.

Entradas, solo por variables de entorno:

| Variable | Contenido |
|---|---|
| `CONTRACT_ADMIN_URL_<PROPIETARIO>` | URL de un usuario dueño de la base del propietario y con `CREATEROLE` (por ejemplo `CONTRACT_ADMIN_URL_OPERATIONAL_CONTEXT`) |
| `CONTRACT_READER_PASSWORD_<CONSUMIDOR>` | Contraseña del rol `<cons>_contract_reader` (por ejemplo `CONTRACT_READER_PASSWORD_SALES`) |

El script nunca imprime contraseñas ni URL. Ante un error de conexión muestra solo el tipo de error.

## `aplicar`

Es idempotente. Crea los roles que falten y fija la contraseña. Otorga `SELECT` en las vistas declaradas y lo revoca en
las demás vistas de `contract`. Solo revoca `CONNECT` a `PUBLIC` si el propietario declara
`revoke_public_connect: true`.

## `verificar`

Conectado como cada rol de lectura, comprueba cuatro cosas:

1. Lee cada vista declarada.
2. No lee una tabla de `public`.
3. No escribe.
4. No lee una vista declarada para otro consumidor.

Imprime `OK` o `FALLA` por comprobación y termina con código 1 si alguna falla. Con un error de configuración termina
con código 2.

## Entornos

| Entorno | Quién lo ejecuta |
|---|---|
| Local | El desarrollador, con las URL de administrador de sus contenedores |
| Pila aislada | `validation/isolated-stack/stack.sh levantar`, automáticamente |
| VPS, Neon o AWS | El responsable de la base, manualmente (`specs/025-direct-contract-reads/quickstart.md`) |

## Pruebas

Corren contra el contenedor de pruebas de Operational Context. Crean una base propia, `contract_provision_test`, y al
terminar la borran junto con sus roles:

```bash
docker start sio-operational-context-test-db
services/operational-context-service/.venv/bin/pytest infrastructure/scripts/contract-readers/tests -q
```

La URL se toma de `CONTRACT_PROVISION_TEST_ADMIN_URL` o, si falta, de `OPERATIONAL_CONTEXT_TEST_DATABASE_URL`. Solo
se aceptan bases de prueba.

## Despliegue en la VPS, Neon y AWS

Lo hace el responsable de la base, a mano. Desde este repositorio no se toca ningún servidor.

### Orden

1. **Propietario primero.** Desplegar el propietario y ejecutar `alembic upgrade head`: sus migraciones crean el
   esquema `contract` y las vistas `v1_*`. Sin ellas, un consumidor con `contract` responde `503` en esas lecturas.
2. **Roles.** Con un usuario administrador de cada base (con `CREATEROLE`), exportar `CONTRACT_ADMIN_URL_<PROPIETARIO>`
   y `CONTRACT_READER_PASSWORD_<CONSUMIDOR>` (al menos 20 caracteres) y ejecutar:

   ```bash
   python infrastructure/scripts/contract-readers/provision.py aplicar   --entorno servidor
   python infrastructure/scripts/contract-readers/provision.py verificar --entorno servidor
   ```

   `verificar` debe imprimir solo `OK`. Con `--propietario <nombre>` se puede hacer un propietario cada vez.
3. **Consumidor después.** En cada consumidor, definir `<PROPIETARIO>_CONTRACT_DATABASE_URL` (rol
   `<cons>_contract_reader`) y `<PROPIETARIO>_READ_SOURCE=contract`, y reiniciarlo. Conviene pasar un propietario cada
   vez y comprobar el servicio antes del siguiente.

### Vuelta atrás

Poner `<PROPIETARIO>_READ_SOURCE=http` en el consumidor y reiniciarlo. No hace falta cambiar código, ni la base, ni
borrar los roles: el adaptador HTTP sigue en el código y vuelve a usarse tal cual.

Para retirar del todo una pareja, quitar el consumidor del `grants.yaml` del propietario y volver a ejecutar
`aplicar`: revoca el `SELECT` sobre esas vistas.

### Conexiones

Cada pareja abre como máximo `CONTRACT_READ_POOL_SIZE + CONTRACT_READ_MAX_OVERFLOW` conexiones por proceso (3 por
defecto), y cada motor propio `DB_POOL_SIZE + DB_MAX_OVERFLOW` (5 por defecto). En el peor caso, 29 parejas × 3 = 87
lecturas más 10 servicios × 5 = 50 propias, más los workers (`specs/025-direct-contract-reads/contracts/configuration.md`).
Los pools abren conexiones solo bajo demanda, así que el uso real es mucho menor. Para medirlo, en cada servidor:

```sql
SELECT datname, usename, application_name, state, count(*)
FROM pg_stat_activity
WHERE backend_type = 'client backend'
GROUP BY 1, 2, 3, 4
ORDER BY 5 DESC;
```

Las lecturas de contrato se identifican por `usename` (`<cons>_contract_reader`) y por `application_name`, que es el
nombre del consumidor. Si la suma se acerca al 80 % de `max_connections`, subir `max_connections`, bajar los pools o
poner un agrupador de conexiones (abajo).

### Por plataforma

| Plataforma | Notas |
|---|---|
| VPS | Todas las bases comparten el servidor `sio-postgres-18` y sus roles: un solo `<cons>_contract_reader` por consumidor sirve para todas sus bases, con una sola contraseña. La URL apunta a `sio-postgres-18:5432/<base>`. Con `max_connections=100`, revisar la suma antes de activar todas las parejas (se recomienda 200 o PgBouncer). |
| Neon | Cada proyecto tiene su servidor y sus roles: si los propietarios están en proyectos distintos, el rol se crea en cada uno, y conviene la misma contraseña. Usar el host **directo**, sin `-pooler`: el agrupador en modo transacción no acepta el parámetro de arranque `options`, con el que el consumidor fija `statement_timeout`, solo lectura y `application_name`. Si la base se suspende, la primera conexión puede tardar más de 2 s: subir `CONTRACT_READ_CONNECT_TIMEOUT_SECONDS` (máximo 10). |
| AWS (RDS o Aurora) | El usuario maestro tiene `CREATEROLE` (`rds_superuser`). Las bases en el mismo clúster comparten roles, como en la VPS. Con RDS Proxy, comprobar antes que el proxy respeta el parámetro de arranque `options` (conectado por el proxy, `SHOW statement_timeout` debe dar el tiempo del consumidor) o conectar los lectores directamente a la instancia. Los grupos de seguridad deben permitir el tráfico del consumidor al puerto de la base del propietario. |
