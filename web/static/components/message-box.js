/*
 * Elemento reutilizable: la "caja de texto" flotante de un personaje.
 * Equivalente web de src/shared/characters/message_box.py (MessageBox), que
 * en el escritorio es una ventana propia (Qt.Dialog) centrada sobre
 * MainWindow, no un widget metido en el layout de la página.
 *
 * Antes esto era el <div id="aviso-banner"> de base.html: markup fijo dentro
 * de .content-area que empujaba el contenido de la página al aparecer y
 * desaparecer -un comportamiento sin equivalente en el escritorio, donde el
 * cuadro flota encima sin mover nada-. Ahora es un elemento que este script
 * construye una vez (ver _crear()) y reutiliza para cada aviso, igual que
 * MessageBar en el escritorio sustituye el cuadro anterior en vez de
 * apilarlos.
 *
 * Se deja como script clásico (sin import/export) a propósito, igual que el
 * resto de static/: esta página puede vivir sin salida a internet y sin
 * bundler, así que cuantos menos mecanismos nuevos, mejor.
 */

// SUCCESS/INFO se cierran solos (mismo tiempo que _AUTO_CLOSE_MS en
// message_box.py); WARNING/ERROR no están aquí a propósito -esos bloquean
// hasta que el usuario los cierra, igual que en el escritorio-.
const _AUTO_CLOSE_MS = { success: 3500, info: 3500 };

let _elementos = null;
let _autoCloseTimeout = null;
let _onClose = null;

function _crear() {
  if (_elementos) return _elementos;

  const fondo = document.createElement('div');
  fondo.className = 'message-box-fondo';
  fondo.hidden = true;

  const caja = document.createElement('div');
  caja.className = 'message-box';

  const retrato = document.createElement('div');
  retrato.className = 'message-box-retrato';

  const nombre = document.createElement('strong');
  nombre.className = 'message-box-nombre';

  const texto = document.createElement('p');
  texto.className = 'message-box-texto';

  const columna = document.createElement('div');
  columna.className = 'message-box-columna';
  columna.append(nombre, texto);

  const cerrar = document.createElement('button');
  cerrar.type = 'button';
  cerrar.className = 'message-box-cerrar';
  cerrar.setAttribute('aria-label', 'Cerrar');
  cerrar.textContent = '×';
  cerrar.addEventListener('click', cerrarMessageBox);

  caja.append(retrato, columna, cerrar);
  fondo.append(caja);
  document.body.append(fondo);

  // Esc cierra, igual que MessageBox.keyPressEvent en el escritorio.
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !fondo.hidden) cerrarMessageBox();
  });

  _elementos = { fondo, caja, retrato, nombre, texto };
  return _elementos;
}

/**
 * Muestra (o sustituye) la caja flotante.
 * @param {string} tipo - clave de SENDERS (success/info/warning/error):
 *   decide si la caja se cierra sola o espera al usuario.
 * @param {string} color - color de acento del personaje que habla.
 * @param {string} nombrePersonaje - "quién lo dice".
 * @param {string} mensaje - "qué dice".
 * @param {string} svgRetrato - marcado SVG ya teñido del personaje (lo
 *   calcula message-bar.js, que es quien conoce SENDERS y el teñido); esta
 *   caja solo lo inserta, igual que self.portrait en message_box.py muestra
 *   el mismo tinted_portrait() que ya usa MessageBar.
 * @param {{onClose?: () => void}} [opciones] - se llama al cerrarse la caja,
 *   sea cual sea el motivo (clic, Esc o auto-cierre).
 */
function mostrarMessageBox(tipo, color, nombrePersonaje, mensaje, svgRetrato, opciones = {}) {
  const { fondo, caja, retrato, nombre, texto } = _crear();

  clearTimeout(_autoCloseTimeout);
  _onClose = opciones.onClose || null;

  caja.style.borderColor = color;
  retrato.innerHTML = svgRetrato || '';
  nombre.textContent = nombrePersonaje;
  nombre.style.color = color;
  texto.textContent = mensaje;

  // WARNING/ERROR "bloquean": el fondo se oscurece y absorbe los clics de
  // fuera sin hacer nada con ellos -no hay forma de replicar en la web un
  // ApplicationModal real que impida tocar el resto de la página, pero esto
  // transmite lo mismo: hay que leer y cerrar para seguir-.
  const bloquea = !(tipo in _AUTO_CLOSE_MS);
  fondo.classList.toggle('bloquea', bloquea);
  fondo.hidden = false;

  if (!bloquea) {
    _autoCloseTimeout = setTimeout(cerrarMessageBox, _AUTO_CLOSE_MS[tipo]);
  }
}

function cerrarMessageBox() {
  if (!_elementos || _elementos.fondo.hidden) return;
  clearTimeout(_autoCloseTimeout);
  _elementos.fondo.hidden = true;
  const callback = _onClose;
  _onClose = null;
  if (callback) callback();
}
