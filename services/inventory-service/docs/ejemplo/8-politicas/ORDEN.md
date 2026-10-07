# Ejercicio 8: Políticas de inventario

El administrador consulta la política por defecto, registra la de la empresa (solo FIFO), la cambia con control de versión y configura los niveles de reposición de un producto en la sucursal (una política activa por producto y sucursal).

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base nueva.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-politica-por-defecto.md](01-politica-por-defecto.md) | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policy` | `admin.test` | `200` |
| 2 | [02-registrar-politica.md](02-registrar-politica.md) | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policy` | `admin.test` | `201` |
| 3 | [03-cambiar-a-jit.md](03-cambiar-a-jit.md) | `PUT /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policy` | `admin.test` | `200` |
| 4 | [04-otro-metodo-de-valoracion.md](04-otro-metodo-de-valoracion.md) | `PUT /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policy` | `admin.test` | `422` |
| 5 | [05-politica-de-producto.md](05-politica-de-producto.md) | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policies` | `admin.test` | `201` |
| 6 | [06-politica-duplicada.md](06-politica-duplicada.md) | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policies` | `admin.test` | `409` |
| 7 | [07-inactivar.md](07-inactivar.md) | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policies/<POLITICA>/deactivate` | `admin.test` | `200` |
| 8 | [08-consultar-politicas.md](08-consultar-politicas.md) | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policies?branch_id=d44b0000-0000-4000-8000-000000000001` | `inventario.test` | `200` |

## Por qué este orden

- Los saldos nacen de las entradas: las entradas van primero; las salidas, reversos y consultas dependen del saldo que dejan los pasos anteriores.

## Variables

| Variable | Se guarda en | Se usa en |
| --- | --- | --- |
| `<POLITICA>` | paso 5 (`id`) | pasos 7 |
