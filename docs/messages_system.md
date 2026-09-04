# Sistema de mensajes (shared/messages + shared/characters)

Documenta el diseño actual y las decisiones ya tomadas para no perderlas entre sesiones. Para la estructura general del proyecto ver `structure_refactor.md` en la raíz.

## Idea central: separar QUÉ se dice de QUIÉN lo dice

- **`src/shared/messages/`** — infraestructura neutra, sin Qt visual: qué se dice, qué severidad tiene, quién lo origina, y si debe anunciarse o no. No sabe nada de colores ni personajes.
- **`src/shared/characters/`** — la capa visual: qué personaje habla, de qué color se tiñe su retrato, el cuadro de diálogo (`MessageBox`) y la columna de la ventana principal (`MessageBar`) que escucha el bus y decide si mostrar algo.

Un módulo de negocio (hoy solo Steriflow, y el sandbox `prueba_ui`) solo debería importar de `shared.messages`, nunca de `shared.characters` directamente.

## Piezas

### `MessageType` (`shared/messages/types.py`)

Severidad del mensaje. Determina el personaje y el color **excepto para `DEBUG`**:

| Tipo | Personaje | Color |
|---|---|---|
| `INFO` | Yufi | `#4fc3f7` |
| `SUCCESS` | Tifa | `#66bb6a` |
| `WARNING` | Cloud | `#ffca28` |
| `ERROR` | Sephiroth | `#ef5350` |
| `DEBUG` | — (ninguno) | — |

`DEBUG` no tiene entrada en `SENDERS`/`ACCENT_COLORS` (`shared/characters/senders.py`) porque **nunca llega a esa capa**: `MessageManager.push()` fuerza `Delivery.SILENT` en cuanto `type is MessageType.DEBUG`, sin excepción — ni pasando `delivery=Delivery.CHARACTER` a mano se le puede poner un personaje a hablar. Es la severidad a usar para detalle interno/diagnóstico que solo debe quedar en `manager.history`.

### `Delivery` (`shared/messages/types.py`)

Cómo se presenta un mensaje, independiente de su severidad (salvo el caso `DEBUG` de arriba):

- `CHARACTER` (por defecto) — el personaje correspondiente al `MessageType` habla: retrato teñido en `MessageBar` + `MessageBox` emergente.
- `SILENT` — no se anuncia ningún personaje. El mensaje **sigue** quedando en `manager.history` igual que uno `CHARACTER`; la única diferencia es que `MessageBar` no lo muestra.

Cualquier `MessageType` (incluidos `INFO`/`SUCCESS`/`WARNING`/`ERROR`) puede pasarse como `SILENT` puntualmente; `DEBUG` es la única severidad que lo es *siempre*, por diseño.

### `Module` (`shared/messages/types.py`)

Qué módulo origina el mensaje. Mismos nombres que usan `Navbar`/`LogsView`. Incluye `PRUEBA_UI` (el sandbox).

### `MessageManager` (`shared/messages/manager.py`)

Instancia compartida `manager` (no se crea una por módulo). API:

```python
manager.push(module: Module, type: MessageType, text: str, delivery: Delivery = Delivery.CHARACTER) -> Message
manager.history -> list[Message]          # todo lo emitido, en orden
manager.messagePushed                     # Signal(Message), se emite en cada push
```

`push()` guarda siempre en `history` y emite la señal, sea cual sea `delivery` — el historial nunca pierde rastro de un mensaje solo porque no se haya mostrado con un personaje.

### `MessageBar` / `MessageBox` (`shared/characters/`)

`MessageBar` es la columna fija a la derecha de `MainWindow` (ver `src/app/window_app.py`), siempre visible sea cual sea el módulo activo en el `QStackedWidget` central. Escucha `manager.messagePushed` y:

- Si `delivery is Delivery.SILENT` → no hace nada visible (el mensaje ya quedó en `history`).
- Si no → tiñe el retrato del personaje correspondiente y muestra un `MessageBox` centrado sobre la ventana.

**`MessageBox`** (el cuadro de diálogo en sí, estilo FF7): ancho fijo `640px`, alto dinámico entre `210` y `480px` según el contenido (antes era `560x210` fijo y el texto que no cabía se recortaba en silencio). El texto usa un `QTextEdit` de solo lectura (no `QLabel`) con `WrapAtWordBoundaryOrAnywhere`: rompe una "palabra" muy larga sin espacios en vez de dejarla salirse del ancho de la caja. Si el contenido supera los 480px de alto, el propio `QTextEdit` muestra su scrollbar vertical en vez de recortar nada.

## Comportamiento actual conocido (no es un bug, es el diseño de hoy)

**Varios mensajes seguidos se sustituyen, no se apilan.** Si se llama a `manager.push(...)` varias veces con `delivery=CHARACTER` antes de que el usuario cierre el `MessageBox` anterior, `MessageBar._on_message_pushed` cierra el popup en curso y abre uno nuevo cada vez — se ven "salir" uno tras otro, nunca simultáneos ni acumulados. Confirmado como comportamiento esperado del diseño actual (no un fallo) en la sesión donde se construyó este sistema.

## Pendiente: rediseño "mixto por severidad" (decidido, NO implementado todavía)

Se decidió una dirección para resolver mejor el caso de varios mensajes a la vez, pero **queda por construir**:

- **`INFO`/`SUCCESS`** (rutinarios, frecuentes): dejarían de abrir un `MessageBox` automático. En su lugar, el retrato en `MessageBar` solo cambia de color (indicador), y un clic sobre él muestra un panel con los últimos mensajes de ese tipo. Nunca interrumpen solos.
- **`WARNING`/`ERROR`** (importantes, raros): mantienen el popup automático de hoy, pero si llega otro mensaje del mismo tipo mientras el anterior sigue abierto, **el mismo popup pasa a listar los últimos mensajes** (p. ej. "últimos 3 errores") en vez de cerrarse y ser reemplazado en silencio por el nuevo.
- `DEBUG` sigue sin mostrar nada nunca (ni indicador ni popup), solo historial.

Sitios a tocar cuando se aborde esto: `MessageBar` (portraits con estado de "no leído" + panel al clicar), `MessageBox` (modo "lista acumulada" para Warning/Error). No se ha empezado ningún código de esto todavía.

## Cómo probarlo manualmente

`src/modules/prueba_ui/` tiene el sandbox de prueba de este sistema:

- `messages/catalog.py` — catálogo mínimo (`_TEXTS` por `MessageType`) + `send_test_message(tipo, delivery)`. Patrón a seguir cuando un módulo real necesite su propio catálogo (ver comentario en el propio fichero sobre por qué es un dict y no funciones con nombre).
- `ui/message_test_dialog.py` — `MessageTestDialog`: un botón por severidad (incluido Debug) + checkbox "Silencioso" (fuerza `Delivery.SILENT` en cualquier tipo) + un log en vivo que escucha `manager.messagePushed` sin filtrar por módulo, mostrando `[TIME] [MODULE] [LEVEL] MENSAJE` de cada push, lo haya mostrado o no un personaje.

En la app: pestaña **Prueba UI** → grupo "Mensajes de personajes" → "Abrir diálogo de mensajes".
