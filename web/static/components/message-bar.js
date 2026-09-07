/*
  Equivalente web de src/shared/characters/message_bar.py: 
    4 personajes
    siempre visibles (en silencio, blanco)
    el que "habla" se tiñe con su color de acento mientras dura el aviso 
    no solo aparece al mandar un

 
  Mismo truco que src/shared/characters/portrait.py para teñir: 
    los SVG son a dos colores (background: blanco + shader: negro)
    se sustituye el relleno blanco

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

async function _svgTeñido(tipo, hablando) {
  const crudo = await _svgCrudo(tipo);
  const color = hablando ? SENDERS[tipo].color : '#ffffff';
  return crudo.replace(/fill:#ffffff/gi, `fill:${color}`);
}

async function _pintarPortrait(tipo, hablando) {
  const el = document.querySelector(`.portrait[data-tipo="${tipo}"]`);
  if (!el) return;
  el.innerHTML = await _svgTeñido(tipo, hablando);
}

let _tipoHablando = null;

async function mostrarAviso(tipo, texto) {
  if (!SENDERS[tipo]) tipo = 'info';
  const anterior = _tipoHablando;
  _tipoHablando = tipo;

  if (anterior && anterior !== tipo) await _pintarPortrait(anterior, false);
  await _pintarPortrait(tipo, true);

  // La caja en sí (dónde y cómo se muestra "qué dice") es responsabilidad
  // de message-box.js; aquí solo se decide "quién habla" -incluido el
  // retrato ya teñido que va dentro de la caja- y se apaga cuando esa caja
  // se cierre, sea cual sea el motivo.
  const svgRetrato = await _svgTeñido(tipo, true);
  mostrarMessageBox(tipo, SENDERS[tipo].color, SENDERS[tipo].name, texto, svgRetrato, {
    onClose: () => {
      if (_tipoHablando === tipo) {
        _pintarPortrait(tipo, false);
        _tipoHablando = null;
      }
    },
  });
}

document.addEventListener('DOMContentLoaded', () => {
  for (const tipo of ORDEN_PORTRAITS) _pintarPortrait(tipo, false);
});
