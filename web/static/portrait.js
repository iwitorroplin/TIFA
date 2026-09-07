/*
 * Equivalente web de src/shared/characters/message_bar.py: los 4 personajes
 * están siempre visibles (en silencio, blanco), y el que "habla" se tiñe con
 * su color de acento mientras dura el aviso -no solo aparece al mandar un
 * mensaje, como en el escritorio-.
 *
 * Mismo truco que src/shared/characters/portrait.py para teñir: los SVG son
 * a dos colores (fondo blanco + tinta negra); se sustituye el relleno blanco
 * por el color de acento en el propio navegador. "Silencio" en el escritorio
 * es literalmente blanco (_SILENT_COLOR = "#ffffff"), así que "en silencio"
 * aquí es no tocar el SVG crudo -sin reemplazo alguno-.
 *
 * La tabla SENDERS es un espejo a mano de
 * src/shared/characters/senders.py -no se puede importar ese fichero aquí:
 * arrastra PySide6 (QColor), igual que arrastraba shared/logs/logger.py.
 *
 * A diferencia del escritorio, aquí no hay un bus de mensajes en vivo entre
 * módulos (eso pedía WebSockets, fuera de alcance): `mostrarAviso()` solo
 * reacciona a lo que esta misma página acaba de hacer.
 */

const SENDERS = {
  success: { name: 'Tifa',      svg: '/assets/images/characters/tifa.svg',      color: '#66bb6a' },
  info:    { name: 'Yufi',      svg: '/assets/images/characters/yufi.svg',      color: '#4fc3f7' },
  warning: { name: 'Cloud',     svg: '/assets/images/characters/cloud.svg',     color: '#ffca28' },
  error:   { name: 'Sephiroth', svg: '/assets/images/characters/sephiroth.svg', color: '#ef5350' },
};
// Mismo orden que _PORTRAIT_ORDER en message_bar.py.
const ORDEN_PORTRAITS = ['success', 'info', 'warning', 'error'];

const _svgCache = {};

async function _svgCrudo(tipo) {
  const sender = SENDERS[tipo];
  if (!_svgCache[sender.svg]) {
    const res = await fetch(sender.svg);
    _svgCache[sender.svg] = await res.text();
  }
  return _svgCache[sender.svg];
}

async function _pintarPortrait(tipo, hablando) {
  const el = document.querySelector(`.portrait[data-tipo="${tipo}"]`);
  if (!el) return;
  const crudo = await _svgCrudo(tipo);
  const color = hablando ? SENDERS[tipo].color : '#ffffff';
  el.innerHTML = crudo.replace(/fill:#ffffff/gi, `fill:${color}`);
}

let _tipoHablando = null;
let _avisoTimeout = null;

async function mostrarAviso(tipo, texto) {
  if (!SENDERS[tipo]) tipo = 'info';
  const anterior = _tipoHablando;
  _tipoHablando = tipo;

  if (anterior && anterior !== tipo) await _pintarPortrait(anterior, false);
  await _pintarPortrait(tipo, true);

  const banner = document.getElementById('aviso-banner');
  if (banner) {
    banner.style.borderColor = SENDERS[tipo].color;
    banner.querySelector('.aviso-nombre').textContent = SENDERS[tipo].name;
    banner.querySelector('.aviso-texto').textContent = texto;
    banner.hidden = false;
  }

  clearTimeout(_avisoTimeout);
  // Igual que MessageBar en el escritorio: éxito/info se cierran solos,
  // aviso/error esperan a que alguien los cierre a mano.
  if (tipo === 'success' || tipo === 'info') {
    _avisoTimeout = setTimeout(_cerrarAviso, 4000);
  }
}

function _cerrarAviso() {
  clearTimeout(_avisoTimeout);
  const banner = document.getElementById('aviso-banner');
  if (banner) banner.hidden = true;
  if (_tipoHablando) {
    _pintarPortrait(_tipoHablando, false);
    _tipoHablando = null;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  for (const tipo of ORDEN_PORTRAITS) _pintarPortrait(tipo, false);

  const cerrar = document.getElementById('aviso-cerrar');
  if (cerrar) cerrar.addEventListener('click', _cerrarAviso);
});
