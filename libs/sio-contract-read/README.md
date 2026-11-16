# sio-contract-read

Librería compartida para que un microservicio de SIO **lea directamente**, en solo lectura, las vistas de contrato
que publica otro servicio en su base (constitución 3.0.0, D27; spec `025-direct-contract-reads`).

El objetivo es eliminar solicitudes HTTP internas de solo lectura. Las escrituras, los errores visibles y los
permisos no cambian: el consumidor sigue exponiendo el mismo puerto y elige el adaptador por configuración.

## Qué incluye

| Módulo | Uso |
|---|---|
| `settings` | `ContractReadSettings.from_env(prefijo, timeout_seconds=…)` valida las variables de un propietario. |
| `engine` | `create_contract_engine(settings, application_name=…)` crea un motor pequeño, de solo lectura y con `statement_timeout`; `read`, `read_one` y `chunked`. |
| `errors` | `contract_errors(on_unavailable)` convierte cualquier error de base en la misma excepción de indisponibilidad que hoy produce el adaptador HTTP. |
| `provisioning` | Lógica de roles usada por `infrastructure/scripts/contract-readers/provision.py`. |
| `testing` | `create_owner_schema(...)` crea `<cons>_test__<prop>` con las migraciones reales del propietario. |

## Variables

Por propietario (`<PREFIJO>` es, por ejemplo, `PRODUCT_CATALOG` u `OPERATIONAL_CONTEXT`):

| Variable | Valor |
|---|---|
| `<PREFIJO>_READ_SOURCE` | `http` (por defecto) o `contract` |
| `<PREFIJO>_CONTRACT_DATABASE_URL` | Obligatoria con `contract`; `postgresql+psycopg://<cons>_contract_reader:…@host:puerto/base` |

Comunes a los propietarios de un consumidor:

| Variable | Rango | Por defecto |
|---|---|---|
| `CONTRACT_READ_POOL_SIZE` | 1–10 | 1 |
| `CONTRACT_READ_MAX_OVERFLOW` | 0–10 | 2 |
| `CONTRACT_READ_CONNECT_TIMEOUT_SECONDS` | 1–10 | 2 |

El tiempo máximo de cada consulta (`statement_timeout` y espera del pool) es el mismo de la integración HTTP que se
reemplaza; el consumidor lo pasa como `timeout_seconds`.

## Uso en un adaptador

```python
from sio_contract_read import contract_errors, read_one

SQL = "SELECT id, status FROM contract.v1_companies WHERE id = :id"

class ContractCompanyDirectory:
    def __init__(self, engine):
        self._engine = engine

    def get_company(self, company_id):
        with contract_errors(lambda cause: OwnerUnavailableError(), dependency="operational-context"):
            row = read_one(self._engine, SQL, {"id": company_id})
        return None if row is None else CompanyInfo(**row)
```

Reglas (D27):

- solo se consultan vistas `contract.v<N>_*`, nunca tablas;
- toda consulta filtra por empresa cuando el recurso pertenece a una;
- no hay caché: cada lectura es en vivo;
- el adaptador HTTP se conserva y se elige con `<PREFIJO>_READ_SOURCE`.

## Pruebas

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/pytest
```

## Estado

- Versión 0.1.0. Se instala en cada consumidor como dependencia local, igual que `sio-auth` (D18 interino).
- Propietarios y consumidores en `specs/025-direct-contract-reads/data-model.md`.
