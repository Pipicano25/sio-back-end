"""Reglas de identificación iniciales de Colombia (data-model.md, estándar 4.9.1).

Copiadas de las 8 reglas activas vigentes (migraciones 0003–0010) el
2026-09-25. No incluyen `country_id`: el país se resuelve al cargar.
"""

COLOMBIAN_RULES = (
    {
        "party_kind": "PERSON",
        "identification_type": "CIVIL_REGISTRY",
        "sigla": "RC",
        "number_pattern": "^[0-9]{10}$",
        "number_pattern_description": (
            "Registro Civil de Nacimiento: NUIP numerico de 10 digitos, "
            "permitido de 0 a 6 anos."
        ),
        "example_value": "1000000000",
        "min_age_years": 0,
        "max_age_years": 6,
    },
    {
        "party_kind": "PERSON",
        "identification_type": "IDENTITY_CARD_MODERN",
        "sigla": "TI",
        "number_pattern": "^[0-9]{10}$",
        "number_pattern_description": (
            "Tarjeta de Identidad moderna: NUIP numerico de 10 digitos, "
            "permitido de 7 a 17 anos."
        ),
        "example_value": "1000000000",
        "min_age_years": 7,
        "max_age_years": 17,
    },
    {
        "party_kind": "PERSON",
        "identification_type": "IDENTITY_CARD_OLD",
        "sigla": "TI",
        "number_pattern": "^[0-9]{11}$",
        "number_pattern_description": (
            "Tarjeta de Identidad antigua o NIP: numero numerico de 11 "
            "digitos, permitido de 7 a 17 anos."
        ),
        "example_value": "19991234567",
        "min_age_years": 7,
        "max_age_years": 17,
    },
    {
        "party_kind": "PERSON",
        "identification_type": "CITIZEN_ID_MODERN",
        "sigla": "CC",
        "number_pattern": "^[0-9]{10}$",
        "number_pattern_description": (
            "Cedula de Ciudadania moderna o digital: NUIP numerico de 10 "
            "digitos, permitido desde los 18 anos."
        ),
        "example_value": "1000000000",
        "min_age_years": 18,
        "max_age_years": None,
    },
    {
        "party_kind": "PERSON",
        "identification_type": "CITIZEN_ID_OLD",
        "sigla": "CC",
        "number_pattern": "^[0-9]{3,8}$",
        "number_pattern_description": (
            "Cedula de Ciudadania antigua: numero numerico de 3 a 8 digitos, "
            "permitido desde los 18 anos."
        ),
        "example_value": "12345678",
        "min_age_years": 18,
        "max_age_years": None,
    },
    {
        "party_kind": "PERSON",
        "identification_type": "FOREIGN_CARD",
        "sigla": "CE",
        "number_pattern": "^[0-9]{3,7}$",
        "number_pattern_description": (
            "Cedula de Extranjeria: numero numerico de 3 a 7 digitos, "
            "permitido desde los 7 anos."
        ),
        "example_value": "1234567",
        "min_age_years": 7,
        "max_age_years": None,
    },
    {
        "party_kind": "PERSON",
        "identification_type": "TAX_ID",
        "sigla": "NIT",
        "number_pattern": "^[A-Z0-9]{4,11}-[0-9]$",
        "number_pattern_description": (
            "Numero de Identificacion Tributaria: base alfanumerica de 4 a 11 "
            "caracteres, guion y digito de verificacion."
        ),
        "example_value": "900123456-7",
        "min_age_years": None,
        "max_age_years": None,
    },
    {
        "party_kind": "ORGANIZATION",
        "identification_type": "TAX_ID",
        "sigla": "NIT",
        "number_pattern": "^[A-Z0-9]{4,11}-[0-9]$",
        "number_pattern_description": (
            "Numero de Identificacion Tributaria de organizacion: base "
            "alfanumerica de 4 a 11 caracteres, guion y digito de verificacion."
        ),
        "example_value": "900123456-7",
        "min_age_years": None,
        "max_age_years": None,
    },
)
