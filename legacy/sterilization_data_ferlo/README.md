# Base de datos para ferlo

Importa los CSV de esterilización (5 máquinas, F1 a F5) a SQLite, en 3 fases:
subida en bruto -> verificación -> formateo. Ver detalle de cada fase más abajo.

## Estructura de carpetas

```
data/
  F1_csv/   F2_csv/   F3_csv/   F4_csv/   F5_csv/
database/
  ferlo.db      (SQLite, se crea solo)
  schema.sql
src/
  importer.py   Fase 1: subida en bruto
  checker.py    Fase 2: verificación
  formatter.py  Fase 3: formateo
  reset_db.py   Utilidad: borra y recrea ferlo.db desde schema.sql
```

## Formato de los CSV de entrada

* Nombre de archivo: `nombreMaquina_M<AñoMes>.csv` (ej. `F1_M202607.csv`). Vienen de
  un backup, no se garantiza el formato exacto del nombre por ahora.
* Máquina (`nombreMaquina`): `F1`, `F2`, `F3`, `F4` o `F5`.
* Separado por tabulador, 2 filas de cabecera antes de los datos.

| Fecha      | Hora    | TEMP      | PRES      |
| ---------- | ------- | --------- | --------- |
| dd/MM/yyyy | H:mm:ss | Valor °C | Valor bar |

* TEMP: decimal con coma, 1 decimal (ej. `27,8`).
* PRES: decimal con coma, 3 decimales (ej. `1,284`).

## Esquema de la base de datos

* **files**: un registro por CSV importado (`filename`, `machine`, `imported_at`).
* **measurements_raw**: filas tal cual del CSV (`file_id`, `machine`, `date_raw`,
  `time_raw`, `temperature_raw`, `pressure_raw`). Sin validar ni formatear.
* **measurements**: derivada por completo de `measurements_raw` (`raw_id`, `file_id`,
  `machine`, `timestamp` unido, `temperature`/`pressure` como `REAL`). Se recrea
  entera en cada corrida del formatter, así que siempre puede regenerarse sin
  perder datos. Un valor `NULL` en `temperature`/`pressure` significa que el
  valor crudo no era interpretable (vacío o símbolo tipo `<<<<<<<<`).

`machine` está en las 3 tablas para poder filtrar por máquina sin necesidad de
JOIN. En `measurements_raw`/`measurements` se guarda el valor con el que se
importó el archivo (carpeta `F{n}_csv` o `--machine` explícito), no el que se
pueda parsear del nombre del CSV.

## Fase 1: subida de datos en bruto — `importer.py`

Lee los CSV de una carpeta y los inserta tal cual en `measurements_raw`. No
valida ni formatea nada (eso es fase 2 y 3). Los archivos ya importados
(por `filename`) se omiten.

```
python src/importer.py                  # importa las 5 maquinas (F1 a F5)
python src/importer.py --machine F3      # importa solo data/F3_csv
python src/importer.py -m F1
```

Si `ferlo.db` viene de antes de que `measurements_raw`/`measurements`
tuvieran columna `machine`, `importer.py` migra el esquema solo (añade la
columna y hace backfill desde `files.machine`) antes de importar.

Funciones:

| Función                                 | Descripción                                                                                                                                               |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `machine_folder(machine)`              | Devuelve la carpeta`data/<machine>_csv` para una máquina.                                                                                               |
| `ensure_schema(conn)`                  | Crea el esquema si la base está vacía; si ya existe pero le falta la columna`machine` en `measurements_raw`, la añade y la rellena desde `files`. |
| `already_imported(conn, filename)`     | Indica si ese archivo ya está en`files`.                                                                                                                |
| `detect_delimiter(csv_path)`           | Detecta el separador del CSV (tabulador,`;`, `,` o `\|`).                                                                                             |
| `import_file(conn, csv_path, machine)` | Importa un CSV: crea su fila en`files` e inserta sus filas en `measurements_raw`.                                                                      |
| `import_folder(conn, folder, machine)` | Importa todos los CSV de una carpeta, omitiendo los ya importados. Devuelve (archivos, omitidos, filas).                                                   |
| `parse_args()`                         | Parseo de argumentos de línea de comandos (`--machine`/`-m`).                                                                                         |
| `main()`                               | Punto de entrada: resuelve qué máquina(s) importar y vuelca el resumen final.                                                                            |

## Fase 2: verificación — `checker.py`

Consultas de solo lectura sobre `measurements_raw`: filas por archivo, huecos
de TEMP/PRESS y patrones de valores (para detectar formatos inesperados
antes del formateo).

```
python src/checker.py        # todas las maquinas
python src/checker.py F2     # solo F2
```

Funciones:

| Función                                       | Descripción                                                                                                                         |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `rows_per_file(conn, machine=None)`          | Filas de`measurements_raw` por archivo.                                                                                            |
| `temp_summary(conn, machine=None)`           | Total de filas y huecos de TEMP por máquina.                                                                                        |
| `press_summary(conn, machine=None)`          | Total de filas y huecos de PRESS por máquina.                                                                                       |
| `classify(value)`                            | Clasifica un valor crudo:`decimal_positivo`, `decimal_negativo`, `entero_positivo`, `entero_negativo`, `vacio` u `otro`. |
| `value_patterns(conn, column, machine=None)` | Cuenta filas de`temperature_raw`/`pressure_raw` por categoría de `classify` y lista los valores `otro` encontrados.         |
| `main()`                                     | Punto de entrada: corre todas las verificaciones, opcionalmente filtradas por máquina (`sys.argv[1]`).                            |

## Fase 3: formateo — `formatter.py`

Recrea `measurements` desde `measurements_raw`: une `date_raw` + `time_raw`
en un `timestamp` (`YYYY-MM-DD HH:MM:SS`) y convierte `temperature_raw`/
`pressure_raw` a `REAL`. Un valor crudo no interpretable queda como `NULL`.

```
python src/formatter.py
```

Funciones:

| Función                      | Descripción                                                                                                                                                     |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ensure_schema(conn)`       | Recrea`measurements` si le falta alguna columna esperada (`temperature`, `machine`). Es seguro: la tabla es derivada por completo de `measurements_raw`. |
| `format_measurements(conn)` | Borra y vuelve a poblar`measurements` entera a partir de `measurements_raw`. Devuelve el total de filas.                                                     |
| `main()`                    | Punto de entrada.                                                                                                                                                |

## Utilidad: `reset_db.py`

Borra `ferlo.db` y lo recrea desde cero aplicando `schema.sql`. Útil para
empezar de nuevo tras una importación duplicada o de prueba.

```
python src/reset_db.py
```

Funciones:

| Función   | Descripción                                                |
| ---------- | ----------------------------------------------------------- |
| `main()` | Borra`ferlo.db` si existe y lo recrea con `schema.sql`. |
