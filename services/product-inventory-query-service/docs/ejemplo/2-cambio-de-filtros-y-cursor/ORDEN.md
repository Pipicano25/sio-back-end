# Ejercicio 2: Cambio de filtros y cursor

Un cursor está ligado a la empresa, al endpoint, a los filtros, al orden y al tamaño de página. Si el frontend cambia algo y conserva el cursor, la consulta se reinicia sin error; un cursor alterado es `422`.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente y solo consulta: no cambia ningún dato.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-primera-pagina.md](01-primera-pagina.md) | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Colgate&page_size=2` | `ventas.test` | `200` |
| 2 | [02-cambio-de-busqueda.md](02-cambio-de-busqueda.md) | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Abrilar&page_size=2&cursor=<CURSOR>` | `ventas.test` | `200` |
| 3 | [03-cambio-de-tamano.md](03-cambio-de-tamano.md) | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Colgate&page_size=3&cursor=<CURSOR>` | `ventas.test` | `200` |
| 4 | [04-cambio-de-orden.md](04-cambio-de-orden.md) | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Colgate&page_size=2&sort=internal_code:desc&cursor=<CURSOR>` | `ventas.test` | `200` |
| 5 | [05-cursor-alterado.md](05-cursor-alterado.md) | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Colgate&page_size=2&cursor=v1.eyJ9.firma-alterada` | `ventas.test` | `422` |

## Por qué este orden

- Los pasos que usan `<CURSOR>` necesitan el cursor de la respuesta anterior. Un cursor vence a los 15 minutos y solo vale con los mismos filtros, orden y `page_size`.

## Variables

| Variable | Se guarda en | Se usa en |
| --- | --- | --- |
| `<CURSOR>` | paso 1 (`next_cursor`) | pasos 2, 3, 4 |
