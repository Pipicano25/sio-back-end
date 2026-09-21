# party-identity-service

Microservicio FastAPI de SIO responsable de las identidades globales de
personas y organizaciones.

## Estado actual

Fase 1 implementada:

- paquete Python `party_identity_service`;
- configuración básica mediante variables de entorno;
- aplicación FastAPI con factory `create_app`;
- protección global con `sio-auth`;
- Swagger/OpenAPI opcional con HTTP Bearer;
- health checks públicos:
  - `GET /health/live`;
  - `GET /health/ready`.

Fase 3 implementada:

- configuración `DATABASE_URL`;
- `Database`, `Base` y sesiones SQLAlchemy;
- Alembic configurado;
- readiness con `SELECT 1` contra PostgreSQL.

Las siguientes entidades de dominio, sus migraciones, permisos de
recursos y CRUD se implementarán en fases posteriores.

Fase 4 iniciada con `PersonIdentity`:

- tabla `person_identities`;
- unicidad por país, tipo y número de identificación;
- checks para `identification_type` y `verification_status`;
- auditoría con `created_by`, `updated_by`, `created_at` y `updated_at`;
- concurrencia optimista con `version`;
- endpoint de listado paginado con búsqueda y filtros;
- endpoints de consulta, creación y actualización completa;
- permisos con slug `party-identity`.

Fase de organizaciones iniciada con `OrganizationIdentity`:

- tabla `organization_identities`;
- unicidad por país, tipo y número de identificación;
- validación de `country_id` contra `geography-service`;
- validación de identificación usando reglas activas con
  `party_kind = ORGANIZATION`;
- auditoría con `created_by`, `updated_by`, `created_at` y `updated_at`;
- concurrencia optimista con `version`;
- endpoint de listado paginado con búsqueda y filtros;
- endpoints de consulta, creación y actualización completa;
- sin endpoint de eliminación física.

Fase de parametrización de reglas iniciada:

- tabla `identification_type_rules`;
- validación opcional de número de identificación por tipo de parte,
  país y tipo de identificación.
- endpoints de consulta, creación y actualización completa de reglas.

## Variables de entorno

Ver `.env.example`.

Las reglas de formato para identificaciones no dependen de variables de
entorno. Se parametrizan en la tabla `identification_type_rules`.

`country_id` se valida consultando `geography-service`. En Docker se usa
`http://host.docker.internal:8000` para alcanzar el servicio publicado en
el host.

Si no existe ninguna regla activa para `party_kind` y `country_id`, solo se
aplican validaciones base:

- `identification_number` obligatorio;
- mínimo 1 carácter;
- máximo 40 caracteres;
- unicidad por país, tipo y número.

Si el país ya tiene reglas activas para `party_kind`, el tipo recibido debe
tener al menos una regla activa por `sigla`.

Reglas iniciales activas para Colombia:

| `party_kind` | `identification_type` | `sigla` | `number_pattern` | Edad |
|---|---|---|---|---|
| `PERSON` | `CIVIL_REGISTRY` | `RC` | `^[0-9]{10}$` | 0 a 6 |
| `PERSON` | `IDENTITY_CARD_MODERN` | `TI` | `^[0-9]{10}$` | 7 a 17 |
| `PERSON` | `CITIZEN_ID_MODERN` | `CC` | `^[0-9]{10}$` | 18+ |
| `PERSON` | `CITIZEN_ID_OLD` | `CC` | `^[0-9]{3,8}$` | 18+ |
| `PERSON` | `FOREIGN_CARD` | `CE` | `^[0-9]{3,7}$` | 7+ |
| `PERSON` | `TAX_ID` | `NIT` | `^[A-Z0-9]{4,11}-[0-9]$` | Cualquiera |
| `PERSON` | `IDENTITY_CARD_OLD` | `TI` | `^[0-9]{11}$` | 7 a 17 |

Los códigos no están cerrados por restricciones SQL; se pueden agregar
nuevos valores desde `identification-type-rules`, siempre que el país exista.

Ejemplos válidos para Colombia:

```text
RC: 1000000000
TI: 1000000000
TI: 19991234567
CC: 1000000000
CC: 12345678
CE: 1234567
NIT: 900123456-7
```

Ejemplos inválidos para Colombia:

```text
CC: 1.234.567
CE: E123456
NIT: 900123456.7
```

## Entorno de desarrollo independiente

Este microservicio tiene su propio entorno virtual en `.venv` para
desarrollarlo, ejecutarlo y probarlo sin usar entornos de otros servicios.

Crear el entorno:

```powershell
python -m venv .venv
```

Activar el entorno:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instalar el servicio con sus dependencias:

```powershell
python -m pip install -e .
```

Crear el archivo local de variables:

```powershell
Copy-Item .env.example .env
```

Ejecutar localmente:

```powershell
python -m uvicorn party_identity_service.main:app --reload --host 127.0.0.1 --port 8002 --env-file .env
```

Endpoints iniciales:

- `GET http://127.0.0.1:8002/health/live`
- `GET http://127.0.0.1:8002/health/ready`
- `GET http://127.0.0.1:8002/docs`

Endpoints de personas:

- `GET http://127.0.0.1:8002/person-identities`
- `GET http://127.0.0.1:8002/person-identities/{person_identity_id}`
- `POST http://127.0.0.1:8002/person-identities`
- `PUT http://127.0.0.1:8002/person-identities/{person_identity_id}`

Endpoints de organizaciones:

- `GET http://127.0.0.1:8002/organization-identities`
- `GET http://127.0.0.1:8002/organization-identities/{organization_identity_id}`
- `POST http://127.0.0.1:8002/organization-identities`
- `PUT http://127.0.0.1:8002/organization-identities/{organization_identity_id}`

Endpoints de reglas de identificación:

- `GET http://127.0.0.1:8002/identification-type-rules`
- `GET http://127.0.0.1:8002/identification-type-rules/{rule_id}`
- `POST http://127.0.0.1:8002/identification-type-rules`
- `PUT http://127.0.0.1:8002/identification-type-rules/{rule_id}`

Ejemplo para crear una regla de cédula colombiana:

```json
{
  "party_kind": "PERSON",
  "country_id": "00000000-0000-0000-0000-000000000000",
  "identification_type": "CITIZEN_ID_MODERN",
  "sigla": "CC",
  "number_pattern": "^[0-9]{10}$",
  "number_pattern_description": "Cedula de Ciudadania moderna o digital: NUIP numerico de 10 digitos, permitido desde los 18 anos.",
  "example_value": "1000000000",
  "min_age_years": 18,
  "max_age_years": null,
  "is_active": true,
  "valid_from": null,
  "valid_to": null
}
```

Ejemplo para crear una organización:

```json
{
  "country_id": "00000000-0000-0000-0000-000000000000",
  "identification_type": "NIT",
  "identification_number": "900123456-7",
  "legal_name": "SIO Demo S.A.S.",
  "trade_name": "SIO Demo",
  "organization_type": "SAS",
  "registration_status": "ACTIVE",
  "website": "https://example.com"
}
```

Ejemplo para actualizar una organización:

```json
{
  "country_id": "00000000-0000-0000-0000-000000000000",
  "identification_type": "NIT",
  "identification_number": "900123456-7",
  "legal_name": "SIO Demo S.A.S.",
  "trade_name": "SIO Demo Colombia",
  "organization_type": "SAS",
  "registration_status": "ACTIVE",
  "website": "https://example.com",
  "version": 1
}
```

## Docker y PostgreSQL

El servicio cuenta con un entorno Docker independiente:

- `party-identity-db`: PostgreSQL persistente de desarrollo;
- `party-identity-test-db`: PostgreSQL temporal para pruebas, bajo
  profile `test`;
- `party-identity-service`: API FastAPI del microservicio.

Levantar entorno de desarrollo:

```powershell
docker compose up --build
```

Levantar únicamente PostgreSQL:

```powershell
docker compose up -d party-identity-db
```

Levantar PostgreSQL de test:

```powershell
docker compose --profile test up -d party-identity-test-db
```

Ejecutar pruebas:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Las pruebas de contrato usan `PARTY_IDENTITY_TEST_DATABASE_URL` y exigen
que apunte a una base cuyo nombre contenga `test`, siguiendo el mismo
patrón de seguridad usado en `geography-service`.

Conexión local para DBeaver, DataGrip o pgAdmin:

- host: `127.0.0.1`;
- port: `55435`;
- database: `sio_party_identity`;
- user: `sio_party_identity`;
- password: `sio_party_identity_dev_change_me`.

La variable `DATABASE_URL` se inyecta dentro del contenedor de la API.
En ejecución local, `.env` contiene una `DATABASE_URL` apuntando a
`127.0.0.1:55435`.

## Alembic

Alembic queda configurado para leer `DATABASE_URL` desde `.env`.

Consultar revisión actual:

```powershell
alembic current
```

Crear migraciones futuras:

```powershell
alembic revision --autogenerate -m "descripcion"
```

Aplicar migraciones:

```powershell
alembic upgrade head
```
