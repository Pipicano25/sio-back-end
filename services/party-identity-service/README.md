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
- validación opcional de número de identificación por país y tipo.

## Variables de entorno

Ver `.env.example`.

Para activar reglas específicas de Colombia en `PersonIdentity`, se debe
configurar el UUID externo de Colombia proveniente de Geography Service:

```powershell
PARTY_IDENTITY_COLOMBIA_COUNTRY_ID=<uuid-de-colombia>
```

Si esta variable está vacía, solo se aplican validaciones base:

- `identification_number` obligatorio;
- mínimo 1 carácter;
- máximo 40 caracteres;
- unicidad por país, tipo y número.

Reglas iniciales de Colombia:

| Tipo | Regla |
|---|---|
| `NATIONAL_ID` | Solo dígitos, entre 6 y 10 caracteres. |
| `FOREIGN_ID` | Letras mayúsculas y dígitos, entre 3 y 20 caracteres. |
| `PASSPORT` | Letras mayúsculas y dígitos, entre 6 y 20 caracteres. |
| `TAX_ID` | Dígitos entre 5 y 15 caracteres, con dígito de verificación opcional separado por guion. |

Ejemplos válidos para Colombia:

```text
NATIONAL_ID: 1234567890
FOREIGN_ID: E123456
PASSPORT: AB123456
TAX_ID: 900123456-7
```

Ejemplos inválidos para Colombia:

```text
NATIONAL_ID: 1.234.567
PASSPORT: AB 123456
TAX_ID: 900123456.7
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
python -m alembic current
```

Crear migraciones futuras:

```powershell
python -m alembic revision --autogenerate -m "descripcion"
```

Aplicar migraciones:

```powershell
python -m alembic upgrade head
```
