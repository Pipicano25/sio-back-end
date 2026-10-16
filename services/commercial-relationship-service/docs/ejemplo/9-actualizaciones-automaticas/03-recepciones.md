# Paso 03 de 05 — Recibir dos compras

Ejercicio 9 — Actualizaciones automáticas de precio · [← Paso anterior](02-preparar-la-politica.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-consultar-actualizaciones.md)

**Objetivo:** Una recepción crea el primer precio; la segunda falla (simulado) y queda pendiente de reintento.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<ACETAMINOFEN>`, `<CAJA>` — pasos [01](01-consultar-datos.md), [02](02-preparar-la-politica.md)

---

## 1. Purchase recibe la compra 1 y el worker actualiza el precio

> **Proceso automático:** no es una llamada que haga el usuario. En un entorno real lo hacen Purchase (al registrar la recepción física) y el `commercial-relationship-price-worker`; en la validación automática lo ejecuta la prueba.

**Qué ocurre**

- Al confirmar la recepción física, Purchase registra el costo de la línea y lo entrega a Commercial Relationship con su identidad técnica (`POST /api/v1/companies/{company_id}/automatic-price-update-requests`); ningún usuario llama esa URL.
- El worker calcula 23.800 / 10 = 2.380 por caja y 2.380 × 1,30 = **3.094**. Crea el precio con `origin = AUTOMATIC` y sin fecha de fin.

**Resultado**

```json
{
  "status": "APPLIED",
  "new_price": "3094.00"
}
```

## 2. Purchase recibe la compra 2 y el worker falla (simulado)

> **Proceso automático:** no es una llamada que haga el usuario. En un entorno real lo hacen Purchase (al registrar la recepción física) y el `commercial-relationship-price-worker`; en la validación automática lo ejecuta la prueba.

**Qué ocurre**

- La recepción no depende del resultado: el inventario ya entró y Purchase no se detiene.
- El worker registra el error, cuenta el intento y programa un reintento con espera creciente. Las siguientes recepciones de esta lista y presentación esperan a que esta termine.

**Resultado**

```json
{
  "status": "FAILED",
  "new_price": null,
  "last_error_code": "RuntimeError"
}
```

---

[← Paso anterior](02-preparar-la-politica.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-consultar-actualizaciones.md)
