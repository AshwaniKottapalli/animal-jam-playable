import { Game } from './game.js';

const app    = document.getElementById('app');
const canvas = document.getElementById('gameCanvas');

function resize() {
  const ww = window.innerWidth;
  const wh = window.innerHeight;
  const aspect = 9 / 16;

  const h = wh;
  const w = wh * aspect;

  app.style.width   = `${w}px`;
  app.style.height  = `${h}px`;
  app.style.left    = `${(ww - w) / 2}px`;
  app.style.top     = '0px';

  canvas.width        = 720;
  canvas.height       = 1280;
  canvas.style.width  = `${w}px`;
  canvas.style.height = `${h}px`;
}

resize();
window.addEventListener('resize', resize);
new ResizeObserver(resize).observe(document.body);

function startGame() {
  const game = new Game(app);
  game.start();
}

// ── MRAID v2.0 ───────────────────────────────────────────────────────────────
// Use mraid.open() for CTA if available, else fall back to window.open().
// Expose globally so game.js can call it.
window.mraidOpen = function(url) {
  if (typeof mraid !== 'undefined') {
    mraid.open(url);
  } else {
    window.open(url, '_blank');
  }
};

if (typeof mraid !== 'undefined') {
  // MRAID environment — wait for ready before sizing/starting
  if (mraid.getState() === 'loading') {
    mraid.addEventListener('ready', () => { resize(); startGame(); });
  } else {
    resize();
    startGame();
  }
} else {
  // Browser / non-MRAID environment
  startGame();
}
