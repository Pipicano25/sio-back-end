# Snapshot CIIU Rev. 5 A.C. (DANE)

Datos del catálogo `global_business_sectors` con `classification_system = CIIU_REV5_AC`, cargados
con `python -m party_identity_service.seed load-business-sectors` (FR-055 a FR-058, DS-10).

## Fuente oficial

- **Organismo**: Departamento Administrativo Nacional de Estadística (DANE), Colombia.
- **Documento**: "Clasificación Industrial Internacional Uniforme de todas las actividades
  económicas Revisión 5 Adaptada para Colombia (CIIU Rev. 5 A.C.) — Estructura detallada".
- **Edición**: CIIU Rev. 5 A.C., establecida por la Resolución 992 de 2026 del DANE (6 de agosto de
  2026), que deroga la Resolución 2306 de 2022 (CIIU Rev. 4 A.C.).
- **Página**: https://www.dane.gov.co/index.php/sistema-estadistico-nacional-sen/normas-y-estandares/nomenclaturas-y-clasificaciones/clasificaciones/clasificacion-industrial-internacional-uniforme-de-todas-las-actividades-economicas-ciiu
- **Archivo**: https://www.dane.gov.co/files/sen/nomenclatura/ciiu/CIIU_5_AC_Estructura_detallada.xlsx
  (`Last-Modified` del servidor: 2026-08-11 15:28:21 GMT; 96206 bytes).
- **Fecha de obtención**: 2026-10-02.

El archivo se guarda sin modificar en `source/CIIU_5_AC_Estructura_detallada.xlsx`.

## Huellas

- **SHA-256 del original (`source/CIIU_5_AC_Estructura_detallada.xlsx`)**: `ef5e93f0246d7c3efb74caf5dfa6888fe4c1e7fe196b6a7dd5e144908bd18b16`
- **SHA-256 del CSV (`ciiu_rev5_ac.csv`)**: `7334b5d149e9d24cf8ce49ea4c27b147dd1e706fb1ae42966fda1540888f2452`

El `seed` recalcula el SHA-256 del CSV y lo compara con la línea anterior antes de escribir; si no
coincide, falla sin cargar nada. El CSV se guarda con saltos de línea LF (`../.gitattributes`).

## Conteos por nivel

| Nivel | Registros |
| --- | --- |
| SECTION | 22 |
| DIVISION | 87 |
| GROUP | 266 |
| CLASS | 544 |
| Total | 919 |

## Derivación

`ciiu_rev5_ac.csv` (columnas `level`, `code`, `name`, `parent_code`) se genera con el conversor
reproducible, desde `services/party-identity-service/`:

```text
pip install -e ".[tools]"            # openpyxl, solo para el conversor
python scripts/ciiu/convert_dane_ciiu.py
```

Reglas: sección (letra) sin padre; división (2 dígitos) → su sección; grupo (3 dígitos) → división
de sus 2 primeros dígitos; clase (4 dígitos) → grupo de sus 3 primeros dígitos. Los títulos se
copian tal como los publica el DANE (solo se recortan espacios exteriores); ninguno se transcribe a
mano. El título más largo tiene 222 caracteres (división `15`).

Para actualizar a una publicación nueva del DANE: reemplazar el archivo de `source/`, ejecutar el
conversor y copiar aquí los SHA-256, los conteos y la fecha de obtención.
