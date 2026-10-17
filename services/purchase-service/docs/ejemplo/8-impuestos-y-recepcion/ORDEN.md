# Ejercicio 8: Impuesto de compra por tasa

Spec 021: el impuesto de cada línea ya no se escribe; Purchase lo calcula con la tasa de compra del producto en Commercial Relationship (`(subtotal − descuento) × tasa`). Un supervisor puede ajustar la tasa de una línea para que coincida con la factura del proveedor (permiso propio); el comprador no. Las tasas son **ficticias**: 19 % (arroz) y 0 % (aceite) no representan tarifas reales.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base nueva con el reloj fijo en el 5 de noviembre de 2026.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-borrador-con-impuesto-calculado.md](01-borrador-con-impuesto-calculado.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `compras.test` | `201` |
| 2 | [02-ajustar-la-tasa-de-una-linea.md](02-ajustar-la-tasa-de-una-linea.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/details` | `supervisor.test` | `201` |
| 3 | [03-comprador-sin-permiso-de-ajuste.md](03-comprador-sin-permiso-de-ajuste.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/details` | `compras.test` | `403` |
| 4 | [04-tasa-fuera-de-rango.md](04-tasa-fuera-de-rango.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/details` | `supervisor.test` | `422` |
| 5 | [05-presentacion-repetida.md](05-presentacion-repetida.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/details` | `compras.test` | `409` |
| 6 | [06-confirmar-sin-politica-de-ganancia.md](06-confirmar-sin-politica-de-ganancia.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/confirmation` | `compras.test` | `409` |

## Por qué este orden

- La numeración necesita una secuencia activa antes de confirmar; la confirmación necesita un borrador; la anulación y los hitos de recepción necesitan una compra confirmada.

## Variables

| Variable | Se guarda en | Se usa en |
| --- | --- | --- |
| `<COMPRA>` | paso 1 (`id`) | pasos 2, 3, 4, 5, 6 |
