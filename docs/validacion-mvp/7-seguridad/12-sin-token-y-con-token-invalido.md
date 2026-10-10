# Paso 12 de 12 — Sin token y con token inválido

Ejercicio 7 — Seguridad entre empresas y permisos · [Orden del ejercicio](ORDEN.md)

---

## 1. Sin token: GET en party-identity

Paso `S-06.sin-token.party-identity.lectura` · usuario **`sin-token`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8101/api/v1/person-identities
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 2. Sin token: POST en party-identity

Paso `S-06.sin-token.party-identity.escritura` · usuario **`sin-token`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8101/api/v1/person-identities
```

```json
{}
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 3. Sin token: GET en geography

Paso `S-06.sin-token.geography.lectura` · usuario **`sin-token`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8102/global-countries
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 4. Sin token: POST en geography

Paso `S-06.sin-token.geography.escritura` · usuario **`sin-token`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8102/global-countries
```

```json
{}
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 5. Sin token: GET en product-catalog

Paso `S-06.sin-token.product-catalog.lectura` · usuario **`sin-token`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8103/api/v1/products
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 6. Sin token: POST en product-catalog

Paso `S-06.sin-token.product-catalog.escritura` · usuario **`sin-token`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8103/api/v1/categories
```

```json
{}
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 7. Sin token: GET en operational-context

Paso `S-06.sin-token.operational-context.lectura` · usuario **`sin-token`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8104/api/v1/companies
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 8. Sin token: POST en operational-context

Paso `S-06.sin-token.operational-context.escritura` · usuario **`sin-token`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8104/api/v1/companies
```

```json
{}
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 9. Sin token: GET en payment-reference

Paso `S-06.sin-token.payment-reference.lectura` · usuario **`sin-token`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8105/global-payment-methods
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 10. Sin token: POST en payment-reference

Paso `S-06.sin-token.payment-reference.escritura` · usuario **`sin-token`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8105/global-payment-methods
```

```json
{}
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 11. Sin token: GET en commercial-relationship

Paso `S-06.sin-token.commercial-relationship.lectura` · usuario **`sin-token`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/company-products
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 12. Sin token: POST en commercial-relationship

Paso `S-06.sin-token.commercial-relationship.escritura` · usuario **`sin-token`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/company-customers
```

```json
{}
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 13. Sin token: GET en purchase

Paso `S-06.sin-token.purchase.lectura` · usuario **`sin-token`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8107/api/v1/companies/<EMPRESA_A>/purchases
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 14. Sin token: POST en purchase

Paso `S-06.sin-token.purchase.escritura` · usuario **`sin-token`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8107/api/v1/companies/<EMPRESA_A>/purchases
```

```json
{}
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 15. Sin token: GET en sales

Paso `S-06.sin-token.sales.lectura` · usuario **`sin-token`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 16. Sin token: POST en sales

Paso `S-06.sin-token.sales.escritura` · usuario **`sin-token`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales
```

```json
{}
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 17. Sin token: GET en inventory

Paso `S-06.sin-token.inventory.lectura` · usuario **`sin-token`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/balances
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 18. Sin token: POST en inventory

Paso `S-06.sin-token.inventory.escritura` · usuario **`sin-token`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/inventory-adjustments
```

```json
{}
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 19. Sin token: GET en audit

Paso `S-06.sin-token.audit.lectura` · usuario **`sin-token`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8110/api/v1/companies/<EMPRESA_A>/audit-events
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 20. Sin token: POST en audit

Paso `S-06.sin-token.audit.escritura` · usuario **`sin-token`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8110/api/v1/audit-events
```

```json
{}
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 21. Token inválido: GET en party-identity

Paso `S-06.token-invalido.party-identity.lectura` · usuario **`token-invalido`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8101/api/v1/person-identities
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 22. Token inválido: POST en party-identity

Paso `S-06.token-invalido.party-identity.escritura` · usuario **`token-invalido`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8101/api/v1/person-identities
```

```json
{}
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 23. Token inválido: GET en geography

Paso `S-06.token-invalido.geography.lectura` · usuario **`token-invalido`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8102/global-countries
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 24. Token inválido: POST en geography

Paso `S-06.token-invalido.geography.escritura` · usuario **`token-invalido`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8102/global-countries
```

```json
{}
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 25. Token inválido: GET en product-catalog

Paso `S-06.token-invalido.product-catalog.lectura` · usuario **`token-invalido`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8103/api/v1/products
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 26. Token inválido: POST en product-catalog

Paso `S-06.token-invalido.product-catalog.escritura` · usuario **`token-invalido`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8103/api/v1/categories
```

```json
{}
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 27. Token inválido: GET en operational-context

Paso `S-06.token-invalido.operational-context.lectura` · usuario **`token-invalido`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8104/api/v1/companies
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 28. Token inválido: POST en operational-context

Paso `S-06.token-invalido.operational-context.escritura` · usuario **`token-invalido`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8104/api/v1/companies
```

```json
{}
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 29. Token inválido: GET en payment-reference

Paso `S-06.token-invalido.payment-reference.lectura` · usuario **`token-invalido`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8105/global-payment-methods
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 30. Token inválido: POST en payment-reference

Paso `S-06.token-invalido.payment-reference.escritura` · usuario **`token-invalido`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8105/global-payment-methods
```

```json
{}
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 31. Token inválido: GET en commercial-relationship

Paso `S-06.token-invalido.commercial-relationship.lectura` · usuario **`token-invalido`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/company-products
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 32. Token inválido: POST en commercial-relationship

Paso `S-06.token-invalido.commercial-relationship.escritura` · usuario **`token-invalido`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/company-customers
```

```json
{}
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 33. Token inválido: GET en purchase

Paso `S-06.token-invalido.purchase.lectura` · usuario **`token-invalido`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8107/api/v1/companies/<EMPRESA_A>/purchases
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 34. Token inválido: POST en purchase

Paso `S-06.token-invalido.purchase.escritura` · usuario **`token-invalido`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8107/api/v1/companies/<EMPRESA_A>/purchases
```

```json
{}
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 35. Token inválido: GET en sales

Paso `S-06.token-invalido.sales.lectura` · usuario **`token-invalido`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 36. Token inválido: POST en sales

Paso `S-06.token-invalido.sales.escritura` · usuario **`token-invalido`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales
```

```json
{}
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 37. Token inválido: GET en inventory

Paso `S-06.token-invalido.inventory.lectura` · usuario **`token-invalido`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/balances
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 38. Token inválido: POST en inventory

Paso `S-06.token-invalido.inventory.escritura` · usuario **`token-invalido`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/inventory-adjustments
```

```json
{}
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 39. Token inválido: GET en audit

Paso `S-06.token-invalido.audit.lectura` · usuario **`token-invalido`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8110/api/v1/companies/<EMPRESA_A>/audit-events
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`

## 40. Token inválido: POST en audit

Paso `S-06.token-invalido.audit.escritura` · usuario **`token-invalido`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8110/api/v1/audit-events
```

```json
{}
```

**Permiso:** ninguno; la llamada se hace sin token o con un token inválido.

**Respuesta esperada:** `401`
