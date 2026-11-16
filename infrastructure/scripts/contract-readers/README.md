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
