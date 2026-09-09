# Ferlo: lo que todavía no se ha portado a TIFA

Copia parcial y congelada de `sterilization_analysis` (repo hermano, fuera de
TIFA), de la Fase 0 del port de Ferlo. La Fase 2 ya movió `analysis/` -sin
tocar una línea, salvo los recortes deliberados de D6 y F0/VP- a
`src/modules/ferlo/logic/analysis/`, con sus propios tests en
`tests/ferlo/analysis/`. Ese código y esos 4 ficheros de test **ya no viven
aquí**: lo que queda es lo que la Fase 1 (entrada de datos, todavía sin
empezar) sigue necesitando como referencia -`io/`, `test_normalize.py` y
`test_datos_reales.py`, más el `core/`/`services/` de los que ambos
dependen-.

Solo se vendoriza lo que hace falta para correr esos tests: `core`, `analysis`,
`io` y `services/analysis_service.py` -sin Qt, sin CLI, sin `storage/`, sin
`ui/`, sin `pizza/` ni `steriflow/`, que no son "núcleo" y no se portan-.
`sterilization_analysis` se borrará cuando termine la refactorización; este
directorio es la copia que se queda dentro de TIFA para que nada dependa de
una ruta fuera del repo.

## Qué hay aquí

```
src/steril/
  core/       config, enums, modelos, esquema de settings
  analysis/   segmentacion, fases, metricas, cobertura, validacion
              (se queda: test_datos_reales.py y services/analysis_service.py
              todavia lo importan; la copia que manda ya es logic/analysis/)
  io/         lector .xlsx de Ferlo, normalizacion
  services/   analysis_service.py: orquesta importar -> normalizar -> analizar
tests/
  conftest.py            recortado: sin la fixture `conn` (storage/ no viene)
  test_normalize.py      fechas, huecos, calibracion, columna Tiempo legada
  test_datos_reales.py   referencia contra los 33 ciclos reales de data/
                          (xfail: ver docstring del modulo)
data/
  Ferlo1.xlsx ... Ferlo5.xlsx   el dia 31/07/2026 de los 5 autoclaves
```

## Qué se dejó fuera y por qué

* **`storage/`, `pizza/`, `steriflow/`.** TIFA ya tiene su propio esquema por
  módulo (ver `src/modules/steriflow/logic/schema.py`); portar el esquema
  propio de `sterilization_analysis` no tiene sentido dos veces.
* **`ui/`, `cli/`, `report/`.** Chasis de PySide6 y CLI: se rehacen con los
  componentes de TIFA en fases posteriores, no se portan tal cual.
* **`analysis/reconstruction.py`.** Ningún test de los portados lo importa.
* **F₀ y VP.** El cálculo de letalidad sigue en el código porque no se ha
  tocado ni una línea, pero no entra en el esquema ni en la interfaz de Ferlo
  hasta que se pida (ver el documento de la Fase 0 del port).

## Cómo correr los tests

```
pytest legacy/sterilization_analysis/tests
```

`tests/conftest.py` inserta `src/` en `sys.path`, así que no hace falta
instalar el paquete. `test_datos_reales.py` necesita `openpyxl` (lector de
`.xlsx`) y genera `config/settings.json` la primera vez que corre -se
regenera solo a partir de `DEFAULT_SETTINGS`, igual que en el origen-.

## Qué pasó en la Fase 2 (ya hecho)

`src/steril/analysis/` se movió a `src/modules/ferlo/logic/analysis/`, con
`core/config.py` reducido a `logic/config.py` (solo las secciones que el
cálculo usa) y `core/enums.py`+`core/models.py` fundidos en
`logic/analysis/models.py`. Dos cambios deliberados, no bugs del port:

* **D6** - `validate.py` pasa de 4 criterios a 2, sin techo: media oficial
  *y* media estable >= consigna - tolerancia, y duración >= tiempo de
  consigna - tolerancia. `over_temperature`/`over_time` ya no se emiten.
* **F0/VP** - fuera del cálculo, del esquema y de la interfaz. Ese código
  sigue aquí, en `src/steril/analysis/metrics.py`, sin usarse.

`test_segmentation.py`, `test_phases.py`, `test_cobertura.py` y
`test_validation.py` se portaron a `tests/ferlo/analysis/` (el último,
adaptado a D6) y se borraron de aquí -tenerlos en los dos sitios producía un
choque de nombres de módulo en pytest, y la copia de TIFA es la que manda-.

## Qué queda pendiente (Fase 1)

`io/` (lector .xlsx, normalización), `test_normalize.py` y
`test_datos_reales.py` -y el `core/`/`services/` de los que dependen- siguen
aquí sin portar. Cuando la Fase 1 traiga la entrada de datos real (CSV, no
.xlsx; ver el documento de la Fase 1 del port), este directorio entero deja
de hacer falta y se borra.
