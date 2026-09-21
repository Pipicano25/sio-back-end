"""Constantes utilizadas por la carga geográfica inicial."""

from typing import Final


SOUTH_AMERICA_COUNTRIES: Final[dict[str, dict[str, str]]] = {
    "AR": {
        "name": "Argentina",
        "division_type": "PROVINCE",
    },
    "BO": {
        "name": "Bolivia",
        "division_type": "DEPARTMENT",
    },
    "BR": {
        "name": "Brasil",
        "division_type": "STATE",
    },
    "CL": {
        "name": "Chile",
        "division_type": "REGION",
    },
    "CO": {
        "name": "Colombia",
        "division_type": "DEPARTMENT",
    },
    "EC": {
        "name": "Ecuador",
        "division_type": "PROVINCE",
    },
    "GY": {
        "name": "Guyana",
        "division_type": "REGION",
    },
    "PY": {
        "name": "Paraguay",
        "division_type": "DEPARTMENT",
    },
    "PE": {
        "name": "Perú",
        "division_type": "REGION",
    },
    "SR": {
        "name": "Surinam",
        "division_type": "DISTRICT",
    },
    "UY": {
        "name": "Uruguay",
        "division_type": "DEPARTMENT",
    },
    "VE": {
        "name": "Venezuela",
        "division_type": "STATE",
    },
}


SEED_ACTOR: Final[str] = "system:geography-seed"
