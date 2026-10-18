"""Escenario de integración sobre los datos sintéticos **existentes** de `sio-it` (sin crear datos).

Empresas elegidas por los datos que ya contienen (verificado en solo lectura el 2026-10-18):

| Empresa | Datos | Uso |
|---|---|---|
| `SALES_COMPANY` (pruebas de Sales) | 5 ventas confirmadas, 2 anuladas y 5 borradores en una sucursal; compras recibidas y anuladas; movimientos con entradas, salidas y ambos reversos | R1, R2, R4 |
| `PURCHASE_COMPANY` (pruebas de Purchase) | 6 compras recibidas, 3 pendientes, 2 anuladas tras recibirse y 1 borrador | R3 |
| `VOLUME_COMPANY` (juego sintético con volumen de DAO) | 2.142 movimientos en 3 sucursales | R4 con varias páginas; `inventario` es miembro |

Se pueden sustituir con `BRS_IT_SALES_COMPANY`, etc. Las sucursales se leen de Operational Context.
"""

from __future__ import annotations

import os

SALES_COMPANY = os.environ.get("BRS_IT_SALES_COMPANY", "63c8f964-0576-4077-928f-1b40d44cff81")
PURCHASE_COMPANY = os.environ.get("BRS_IT_PURCHASE_COMPANY", "28c13676-fccd-439d-b98e-2f868e4a9b9d")
VOLUME_COMPANY = os.environ.get("BRS_IT_VOLUME_COMPANY", "4e0f8c4a-f357-49fc-8b2b-d62c985e1ab2")
PERIOD = {"date_from": os.environ.get("BRS_IT_DATE_FROM", "2026-10-01"),
          "date_to": os.environ.get("BRS_IT_DATE_TO", "2026-10-18")}
