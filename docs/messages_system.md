# Sistema de mensajes (shared/messages + shared/characters)

Documenta el diseño actual y las decisiones ya tomadas para no perderlas entre sesiones. Para la estructura general del proyecto ver `structure_refactor.md` en la raíz.

## Idea central: los personajes NO son el historial

Dos cosas distintas que antes se mezclaban:

- **Historial** — los ficheros de log de cada módulo (`shared/logs/`). Es lo que se puede consultar después: la pestaña **Logs** del navbar los muestra en vivo, uno por módulo, y Steriflow tiene además su propia tabla de ejecuciones de backup en *Steriflow > Logs*.
- **Aviso** — lo que un personaje dice en voz alta *en el momento*: el resultado inmediato de una acción ("Backup Steriflow finalizado", "ERROR en backup manual: …"). No se acumula, no se relee, no se guarda.

Un backup escribe cientos de líneas de log de las que al usuario le importan una o dos, así que **hablar es opt-in**: se elige cuándo mostrar, no cuándo callar.

```python
logger.log("[Autoclave 1] PASO 4: detecta informes nuevos")            # solo historial
logger.log("Backup Steriflow finalizado", talk=MessageType.SUCCESS)    # historial + Tifa lo dice
```

Reparto de paquetes:

- **`src/shared/messages/`** — infraestructura neutra, sin Qt visual: qué se dice, qué severidad tiene y quién lo origina. No sabe nada de colores ni personajes.
- **`src/shared/characters/`** — la capa visual: qué personaje habla, de qué color se tiñe su retrato, el cuadro de diálogo (`MessageBox`) y la columna de la ventana principal (`MessageBar`) que escucha el bus.

Un módulo de negocio (hoy solo Steriflow, y el sandbox `prueba_ui`) solo debería importar de `shared.messages` / `shared.logs`, nunca de `shared.characters` directamente.

## Piezas

### `Logger` (`shared/logs/logger.py`) — la vía principal

```python
Logger(log_file_path: Path, module: Module)
logger.log(message: str, talk: MessageType | None = None) -> None
```

Escribe la línea en el fichero (y por consola, si la hay). Con `talk=MessageType.X` **además** empuja el mismo texto a `manager`, firmado por el `module` del logger. Sin `talk`, solo historial.

La línea de una que habla lleva su nivel; las demás no. Así lo accionable se encuentra de un vistazo (o con un `grep`) entre los cientos de PASO 1, PASO 2…:

```
[2026-03-14 03:00:12] [AUTOCLAVE6] PASO 5: replica lo local hacia el servidor
[2026-03-14 03:00:41] [SUCCESS] Backup Steriflow finalizado
```

El texto del popup y el del log son el mismo a propósito: lo que se le cuenta al usuario tiene que poder releerse igual luego en la pestaña Logs.

Se puede llamar desde un hilo de trabajo (un backup corre fuera del hilo de Qt): `messagePushed` la recibe `MessageBar`, que vive en el hilo de la interfaz, así que Qt entrega la llamada encolada allí.

### `MessageType` (`shared/messages/types.py`)

Severidad del aviso. Determina el personaje y el color:

| Tipo | Personaje | Color | Cómo se va | ¿Bloquea la app? |
|---|---|---|---|---|
| `INFO` | Yufi | `#4fc3f7` | solo, a los 3,5 s | no |
| `SUCCESS` | Tifa | `#66bb6a` | solo, a los 3,5 s | no |
| `WARNING` | Cloud | `#ffca28` | al pulsar OK (o Esc) | sí |
| `ERROR` | Sephiroth | `#ef5350` | al pulsar OK (o Esc) | sí |

No hay severidad "silenciosa" (antes `DEBUG`): un detalle interno no es un `Message`, es una línea de log sin `talk`.

### `Module` (`shared/messages/types.py`)

Qué módulo origina el mensaje. Mismos nombres que usan `Navbar`/`LogsView`. Incluye `PRUEBA_UI` (el sandbox).

### `MessageManager` (`shared/messages/manager.py`)

Instancia compartida `manager` (no se crea una por módulo). Es un **bus, no un almacén**:

```python
manager.push(module: Module, type: MessageType, text: str) -> None
manager.messagePushed                     # Signal(Message)
```

Un mensaje que nadie ve en el momento se pierde a propósito. No hay `history`: el rastro consultable son los ficheros de log.

`manager.push` directo (sin pasar por `Logger`) queda para el aviso que **no** tiene por qué dejar rastro: la respuesta inmediata a un clic que no es un paso de ningún proceso — p. ej. el resultado de "Comprobar conexión" en Steriflow, o "No hay autoclaves activas configuradas". Si el aviso tiene sentido releerlo mañana, va por `Logger.log(..., talk=...)`.

### `MessageBar` / `MessageBox` (`shared/characters/`)

`MessageBar` es la columna fija a la derecha de `MainWindow` (ver `src/app/window_app.py`), siempre visible sea cual sea el módulo activo en el `QStackedWidget` central. Escucha `manager.messagePushed`, tiñe el retrato del personaje que habla y muestra un `MessageBox` centrado sobre la ventana.

**`MessageBox`**: ancho fijo `640px`, alto dinámico entre `210` y `480px` según el contenido. El texto usa un `QTextEdit` de solo lectura (no `QLabel`) con `WrapAtWordBoundaryOrAnywhere`: rompe una "palabra" muy larga sin espacios en vez de dejarla salirse del ancho de la caja. Si el contenido supera los 480px de alto, el propio `QTextEdit` muestra su scrollbar vertical en vez de recortar nada.

**Una sola regla, dos comportamientos: o el mensaje se va solo, o bloquea la ventana hasta que lo cierres tú.** Nunca las dos cosas y nunca ninguna — un aviso que se queda flotando mientras cambias de pestaña no es ni lo uno ni lo otro: ni te ha dejado seguir, ni te has enterado.

- `INFO`/`SUCCESS` (`_AUTO_CLOSE_MS`): temporizador hijo del propio cuadro, arrancado en `showEvent`. Confirmar un backup no debería costar un clic, y menos aún congelar la app 3,5 s.
- `WARNING`/`ERROR`: modales de aplicación. No se puede cambiar de pestaña ni tocar nada hasta pulsar OK (o Esc, que es la única otra salida: la ventana no tiene barra de título).

Para poder ser modal, el cuadro es una **ventana propia** (`Qt.Dialog | Qt.FramelessWindowHint`), no un widget hijo de `MainWindow` como antes: `setWindowModality` no hace nada sobre un widget que no es ventana. Se muestra con `show()` y no con `exec()` — bloquea la entrada del usuario sin abrir un bucle de eventos anidado, que es lo que permite que `MessageBar` siga sustituyendo el cuadro en curso cuando llega otro mensaje y que un backup en segundo plano pueda seguir avisando. Al ser ventana, `MessageBar` lo centra en coordenadas de pantalla (`window.frameGeometry().center()`), no de widget.

## Comportamiento actual conocido (es el diseño, no un bug)

**Varios mensajes seguidos se sustituyen, no se apilan.** Si llegan dos pushes antes de que el usuario cierre el `MessageBox` anterior, `MessageBar._on_message_pushed` cierra el que hay y abre el nuevo. Aquí solo se ve lo inmediato; lo acumulado se consulta en la pestaña Logs. Por eso el rediseño que se llegó a plantear —retratos con marca de "no leído", panel de últimos mensajes al clicar, popup en modo lista— **queda descartado**: era construir un segundo historial peor que el que ya dan los logs.

## Quién habla hoy

| Sitio | Qué dice | Severidad |
|---|---|---|
| `BackupService._announce_end` | "…finalizado", o "…finalizado, con N incidencia(s)" | `SUCCESS` / `WARNING` |
| `Scheduler.run` | el backup programado reventó | `ERROR` |
| `BackupRunner` | acción ignorada por haber otra en curso; excepción a media ejecución | `WARNING` / `ERROR` |
| `SteriflowHomePage._on_auto_mode_toggled` | backups automáticos activados/desactivados a mano | `INFO` |
| `SteriflowConfigPage._persist` | configuración guardada | `SUCCESS` |
| `SteriflowDataPage._export_selected_to_pdf` | PDF de ciclos guardado, o no se pudo guardar | `SUCCESS` / `ERROR` |
| `AppFolderButton` | la carpeta no abre (típicamente, red caída) | `WARNING` |
| `SteriflowHomePage` | resultado de "Comprobar conexión"; "no hay autoclaves activas" | vía `manager.push`: no va al log |

Todos menos el último van por `Logger.log(..., talk=...)`, así que dejan la misma frase en el fichero de log.

Dos detalles que sostienen la tabla:

- **El mensaje final de un backup cuenta incidencias antes de elegir severidad** (`_announce_end`). Un fallo con una autoclave no corta el pipeline —una máquina apagada no debe impedir copiar el resto—, así que un `SUCCESS` fijo estaría tapando media copia sin hacer. Cuenta excepciones y robocopy con código ≥ 8; una autoclave inactiva, apagada o sin carpeta de origen es un salto previsto, no una incidencia (si contara, casi todas las noches acabarían en `WARNING` y el aviso dejaría de significar nada).
- **`BackupRunner` emite `started`/`finished` sin texto**: las señales solo habilitan y deshabilitan botones, el aviso lo da la capa que escribe el log.

### Lo que NO habla, y debe seguir así

Los pasos del pipeline (PASO 0-6), la ronda de disponibilidad cada 30 minutos, "Siguiente ejecución: …", los errores de extracción PDF a PDF (quedan marcados en la base de datos y se reintentan) y el arranque del controller al abrir la app. Son historial puro: cientos de líneas por ejecución, ninguna accionable en el momento.

### `QMessageBox` o personaje

Los dos conviven a propósito, con este criterio:

- **Dentro de un diálogo modal** (`_AutoclaveDialog`, `_ScheduleDialog`, que usan `.exec()`) → `QMessageBox`. El `MessageBox` de personaje es hijo de `MainWindow`, y el modal de aplicación del diálogo lo dejaría bloqueado.
- **Validaciones de formulario en la propia página** ("la carpeta de logs es obligatoria") → `QMessageBox`: corrigen un campo concreto que tienes delante, no son el resultado de un proceso.
- **Resultado de una acción** (guardado, backup, PDF, apertura de carpeta) → personaje.

## Qué mantiene vivos a los logs

Ahora que el historial son los ficheros, hay dos piezas en `src/app/housekeeping.py` que corren al arrancar (desde `src/__main__.py`, después de crear `QApplication` y antes de la ventana):

- **`purge_module_logs()`** — borra los `*.log` con más de `logs.retentionMonths` meses (appConfig, editable en la pestaña **Configuración** del navbar; `0` = no borrar nunca). Recorre el registro de módulos, así que un módulo nuevo entra en la limpieza en cuanto declare su `log_path`, sin tocar nada. Cada ejecución de backup deja su propio fichero y hay varias al día: sin esto son miles de ficheros en un par de años, que además se releen del disco cada vez que se abre la pestaña Logs. **No habla aunque borre cien ficheros**: un popup nada más abrir la app es justo lo que este sistema intenta no ser.
- **`install_crash_handler()`** — `sys.excepthook` y `threading.excepthook` escriben el volcado completo en `data/logs/tifa.log` y dicen un `ERROR` corto. Sin esto, un fallo no capturado va a stderr, que en una app de ventanas no lee nadie: desaparecía sin dejar rastro. Cubre también los hilos de trabajo, que es donde corre el backup.

`Logger` no imprime por consola a ciegas (`_to_console`): empaquetada con pythonw o como `.exe` no hay `sys.stdout`, y un `print()` suelto reventaría en cada línea — el módulo que escribe el historial sería el primero en caerse.

## Conversaciones (añadido, no sistema)

`shared/characters/conversation.py` es un guiño aparte: doble clic en un retrato de `MessageBar` y ese personaje arranca una charla, donde cada OK pasa el turno al siguiente. **No pasa por `manager`, no deja rastro en el log y no tiene severidad** — Tifa ahí no anuncia un éxito, solo habla. Lo que reusa es la estructura: el mismo `MessageBox`, los mismos retratos y colores de `senders.py`, y el mismo índice por `MessageType`, con alias (`TIFA`, `CLOUD`, `YUFI`, `SEPHIROTH`) para que un guion no se lea como "SUCCESS dice…".

```python
CONVERSATIONS[TIFA] = script(
    (TIFA, "Ya está todo copiado. ¿Ves? No era tan difícil."),
    (CLOUD, "Lo difícil no es copiar. Es acordarse de mirar si salió bien."),
)
```

Reglas: los cuadros se crean con `auto_close=False`, así que esperan al usuario (la regla de siempre se mantiene: no se cierran solos, luego bloquean). **Un aviso real siempre gana** — si un backup termina o falla a mitad de la charla, la charla se corta. `Esc` abandona la conversación entera; `OK` solo pasa de línea.

Se engancha con una línea en `window_app.py` (`conversation.attach(self._message_bar)`) y se quita borrándola. Lo único que `MessageBar` expone para esto es `portraitDoubleClicked`: sabe qué retrato se pulsó, no qué hacer con ello.

## Cómo probarlo manualmente

`src/modules/prueba_ui/` tiene el sandbox:

- `messages/catalog.py` — catálogo mínimo (`_TEXTS` por `MessageType`) + `send_test_message(tipo)`. Va por `manager.push` porque el sandbox no tiene proceso ni log propio que contar; un módulo real anuncia desde su log.
- `ui/message_test_dialog.py` — `MessageTestDialog`: un botón por severidad + un panel que escucha `manager.messagePushed` sin filtrar por módulo y anota `[TIME] [MODULE] [LEVEL] MENSAJE`. Ese panel no es el historial de la app: sirve para comprobar que un mensaje salió aunque su cuadro ya se haya cerrado solo.

En la app: pestaña **Prueba UI** → grupo "Mensajes de personajes" → "Abrir diálogo de mensajes".
