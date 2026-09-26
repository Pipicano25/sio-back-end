"""Datos base de la carga inicial (R-19).

Se usa `LT` (sección 4.2 de `docs/SIO Database.md`) y no `L`, para no tener dos
códigos del mismo concepto. Los tipos de empaque usan código en inglés y nombre
en español (sección 4.3.4).
"""

UNITS = (
    {"code": "UND", "name": "Unidad", "symbol": "und", "measurement_type": "UNIT", "allows_decimals": False},
    {"code": "KG", "name": "Kilogramo", "symbol": "kg", "measurement_type": "MASS", "allows_decimals": True},
    {"code": "G", "name": "Gramo", "symbol": "g", "measurement_type": "MASS", "allows_decimals": True},
    {"code": "LT", "name": "Litro", "symbol": "L", "measurement_type": "VOLUME", "allows_decimals": True},
    {"code": "ML", "name": "Mililitro", "symbol": "mL", "measurement_type": "VOLUME", "allows_decimals": True},
    {"code": "M", "name": "Metro", "symbol": "m", "measurement_type": "LENGTH", "allows_decimals": True},
    {"code": "CM", "name": "Centímetro", "symbol": "cm", "measurement_type": "LENGTH", "allows_decimals": True},
    {"code": "M2", "name": "Metro cuadrado", "symbol": "m²", "measurement_type": "AREA", "allows_decimals": True},
)

PACKAGING_TYPES = (
    {"code": "BOX", "name": "Caja"},
    {"code": "BOTTLE", "name": "Frasco"},
    {"code": "TUBE", "name": "Tubo"},
    {"code": "BAG", "name": "Bolsa"},
    {"code": "PACK", "name": "Paquete"},
    {"code": "CAN", "name": "Lata"},
    {"code": "JAR", "name": "Tarro"},
    {"code": "ENVELOPE", "name": "Sobre"},
    {"code": "ROLL", "name": "Rollo"},
    {"code": "BLISTER", "name": "Blíster"},
)

GROUP_TYPES = tuple(
    {"code": f"GROUP_{number}", "name": f"Grupo {number}", "allows_multiple": False, "display_order": number}
    for number in range(1, 16)
)
