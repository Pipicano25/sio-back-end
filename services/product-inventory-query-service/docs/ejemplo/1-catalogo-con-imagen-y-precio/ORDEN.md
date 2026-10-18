# Ejercicio 1: Catálogo con imagen y precio

Buscar «Colgate» solo con imagen (ruta R-B: Commercial Relationship busca y Product Catalog evalúa la imagen sobre esos candidatos), en páginas de 2 con cursor, con una presentación sin precio.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente y solo consulta: no cambia ningún dato.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-primera-pagina.md](01-primera-pagina.md) | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Colgate&has_image=true&page_size=2` | `ventas.test` | `200` |
| 2 | [02-segunda-pagina.md](02-segunda-pagina.md) | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Colgate&has_image=true&page_size=2&cursor=<CURSOR>` | `ventas.test` | `200` |

## Por qué este orden

- Los pasos que usan `<CURSOR>` necesitan el cursor de la respuesta anterior. Un cursor vence a los 15 minutos y solo vale con los mismos filtros, orden y `page_size`.

## Variables

| Variable | Se guarda en | Se usa en |
| --- | --- | --- |
| `<CURSOR>` | paso 1 (`next_cursor`) | pasos 2 |
