/* ═══════════════════════════════════════════════════════════════════
   SAPIEN — Reader JS
   ═══════════════════════════════════════════════════════════════════ */

// ── Estado ──────────────────────────────────────────────────────────
const state = {
  fontSize:     parseInt(localStorage.getItem('s_fontSize'))  || 18,
  font:         localStorage.getItem('s_font')   || 'sans',
  theme:        localStorage.getItem('s_theme')  || 'dark',
  audio: {
    totalParts:  0,
    currentPart: 0,
    isPlaying:   false,
    element:     null,
  }
};

// ── Elementos ────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const toolbar      = $('reader-toolbar');
const drawer       = $('chapter-drawer');
const overlay      = $('drawer-overlay');
const settingsPanel= $('settings-panel');
const content      = $('reader-content');
const audioPlayer  = $('audio-player');

// ── Inicialização ────────────────────────────────────────────────────
(function init() {
  applyTheme(state.theme);
  applyFont(state.font);
  applyFontSize(state.fontSize);
  scrollToActiveChapter();
  bindAll();
})();

// ── Toolbar Auto-hide ────────────────────────────────────────────────
let toolbarTimer;
let toolbarVisible = true;

function showToolbar() {
  toolbar.classList.remove('hidden-bar');
  toolbarVisible = true;
  clearTimeout(toolbarTimer);
  toolbarTimer = setTimeout(hideToolbar, 3000);
}
function hideToolbar() {
  if (drawer.classList.contains('open') || settingsPanel && !settingsPanel.classList.contains('hidden')) return;
  toolbar.classList.add('hidden-bar');
  toolbarVisible = false;
}

document.addEventListener('mousemove', e => {
  if (e.clientY < 120) showToolbar();
  else if (toolbarVisible) {
    clearTimeout(toolbarTimer);
    toolbarTimer = setTimeout(hideToolbar, 2000);
  }
});
document.addEventListener('touchstart', showToolbar, { passive: true });

// ── Drawer ────────────────────────────────────────────────────────────
function openDrawer() {
  drawer.classList.add('open');
  overlay.classList.add('active');
  showToolbar();
}
function closeDrawer() {
  drawer.classList.remove('open');
  overlay.classList.remove('active');
}

// ── Settings Panel ────────────────────────────────────────────────────
function toggleSettings() {
  settingsPanel.classList.toggle('hidden');
}

function applyTheme(theme) {
  document.body.classList.remove('sepia', 'light');
  if (theme !== 'dark') document.body.classList.add(theme);
  localStorage.setItem('s_theme', theme);
  document.querySelectorAll('.theme-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.theme === theme);
  });
}
function applyFont(font) {
  if (!content) return;
  content.classList.toggle('font-serif', font === 'serif');
  localStorage.setItem('s_font', font);
  document.querySelectorAll('.font-toggle').forEach(b => {
    b.classList.toggle('active', b.dataset.font === font);
  });
}
function applyFontSize(size) {
  size = Math.max(13, Math.min(28, size));
  state.fontSize = size;
  document.documentElement.style.setProperty('--reader-font-size', size + 'px');
  const label = $('font-size-label');
  if (label) label.textContent = size + 'px';
  localStorage.setItem('s_fontSize', size);
}

function scrollToActiveChapter() {
  const active = document.querySelector('.chapter-item.active');
  if (active) active.scrollIntoView({ block: 'center', behavior: 'smooth' });
}

// ── Busca de capítulos ────────────────────────────────────────────────
const searchInput = $('chapter-search');
searchInput?.addEventListener('input', function() {
  const query = this.value.toLowerCase();
  document.querySelectorAll('.chapter-item').forEach(item => {
    const title = item.dataset.title || '';
    item.style.display = title.includes(query) ? '' : 'none';
  });
});

// ── Audio ─────────────────────────────────────────────────────────────
async function initAudio() {
  audioPlayer.classList.remove('hidden');
  const res = await fetch(`/api/audio/info/${encodeURIComponent(NOVEL)}/${CAP}`);
  const data = await res.json();
  state.audio.totalParts = data.total_parts;
  state.audio.currentPart = 0;
  await loadAndPlayChunk(0);
}

async function loadAndPlayChunk(part) {
  const audio = state.audio;
  if (part < 0 || part >= audio.totalParts) return;

  // Para áudio anterior
  if (audio.element) {
    audio.element.pause();
    audio.element.src = '';
  }

  audio.currentPart = part;
  updateChunkLabel();
  updateProgressFill();

  const url = `/api/audio/${encodeURIComponent(NOVEL)}/${CAP}/${part}`;
  const el = new Audio(url);
  audio.element = el;
  audio.isPlaying = true;
  updatePlayPauseIcon();

  el.addEventListener('timeupdate', () => {
    const pct = el.duration ? (el.currentTime / el.duration) * 100 : 0;
    const fill = $('audio-progress-fill');
    if (fill) fill.style.width = pct + '%';
  });
  el.addEventListener('ended', () => {
    if (audio.currentPart + 1 < audio.totalParts) {
      loadAndPlayChunk(audio.currentPart + 1);
    } else {
      audio.isPlaying = false;
      updatePlayPauseIcon();
    }
  });
  el.addEventListener('error', () => {
    console.error('Erro no chunk de áudio', part);
  });

  try { await el.play(); } catch (e) { console.warn('Autoplay bloqueado:', e); }
}

function togglePlayPause() {
  const audio = state.audio;
  if (!audio.element) { initAudio(); return; }

  if (audio.isPlaying) {
    audio.element.pause();
    audio.isPlaying = false;
  } else {
    audio.element.play();
    audio.isPlaying = true;
  }
  updatePlayPauseIcon();
}

function skipChunk(delta) {
  loadAndPlayChunk(state.audio.currentPart + delta);
}

function stopAudio() {
  if (state.audio.element) {
    state.audio.element.pause();
    state.audio.element.src = '';
    state.audio.element = null;
  }
  state.audio.isPlaying = false;
  state.audio.currentPart = 0;
  audioPlayer.classList.add('hidden');
}

function updatePlayPauseIcon() {
  const iconPlay  = $('icon-play');
  const iconPause = $('icon-pause');
  if (!iconPlay || !iconPause) return;
  iconPlay.classList.toggle('hidden',  state.audio.isPlaying);
  iconPause.classList.toggle('hidden', !state.audio.isPlaying);
}

function updateChunkLabel() {
  const el = $('chunk-label');
  if (el) el.textContent = `Trecho ${state.audio.currentPart + 1} / ${state.audio.totalParts}`;
}

function updateProgressFill() {
  const fill = $('audio-progress-fill');
  if (fill) fill.style.width = '0%';
}

// ── Touch navigation (mobile) ─────────────────────────────────────────
let touchStartX = 0;
document.addEventListener('touchstart', e => { touchStartX = e.touches[0].clientX; }, { passive: true });
document.addEventListener('touchend', e => {
  if (drawer.classList.contains('open')) return;
  const dx   = e.changedTouches[0].clientX - touchStartX;
  const W    = window.innerWidth;
  const zone = touchStartX / W;

  // Swipe longo horizontal → navega capítulo
  if (Math.abs(dx) > W * 0.35) {
    const prevLink = document.querySelector('.float-prev, .nav-prev');
    const nextLink = document.querySelector('.float-next, .nav-next');
    if (dx > 0 && prevLink) prevLink.click();
    if (dx < 0 && nextLink) nextLink.click();
    return;
  }

  // Toque simples por zona
  if (Math.abs(dx) < 10) {
    if (zone < 0.25) {
      const prevLink = document.querySelector('.nav-prev');
      if (prevLink) prevLink.click();
    } else if (zone > 0.75) {
      const nextLink = document.querySelector('.nav-next');
      if (nextLink) nextLink.click();
    } else {
      showToolbar();
    }
  }
}, { passive: true });

// ── Bind Events ───────────────────────────────────────────────────────
function bindAll() {
  $('btn-menu')?.addEventListener('click', openDrawer);
  $('drawer-close')?.addEventListener('click', closeDrawer);
  overlay?.addEventListener('click', closeDrawer);

  $('btn-settings')?.addEventListener('click', e => {
    e.stopPropagation();
    toggleSettings();
  });
  document.addEventListener('click', e => {
    if (!settingsPanel?.contains(e.target) && e.target !== $('btn-settings')) {
      settingsPanel?.classList.add('hidden');
    }
  });

  $('btn-audio')?.addEventListener('click', () => {
    if (audioPlayer.classList.contains('hidden')) initAudio();
    else togglePlayPause();
  });
  $('btn-play-pause')?.addEventListener('click', togglePlayPause);
  $('btn-prev-chunk')?.addEventListener('click', () => skipChunk(-1));
  $('btn-next-chunk')?.addEventListener('click', () => skipChunk(1));
  $('btn-close-audio')?.addEventListener('click', stopAudio);

  // Font toggles
  document.querySelectorAll('.font-toggle').forEach(btn =>
    btn.addEventListener('click', () => { state.font = btn.dataset.font; applyFont(btn.dataset.font); })
  );
  // Size buttons
  document.querySelectorAll('.size-btn').forEach(btn =>
    btn.addEventListener('click', () => applyFontSize(state.fontSize + parseInt(btn.dataset.delta)))
  );
  // Theme buttons
  document.querySelectorAll('.theme-btn').forEach(btn =>
    btn.addEventListener('click', () => { state.theme = btn.dataset.theme; applyTheme(btn.dataset.theme); })
  );

  // Keyboard
  document.addEventListener('keydown', e => {
    if (e.key === 'ArrowRight' || e.key === 'l') document.querySelector('.nav-next')?.click();
    if (e.key === 'ArrowLeft'  || e.key === 'h') document.querySelector('.nav-prev')?.click();
    if (e.key === 'Escape') { closeDrawer(); settingsPanel?.classList.add('hidden'); }
    if (e.key === ' ') { e.preventDefault(); togglePlayPause(); }
  });

  // Inicia o auto-hide
  toolbarTimer = setTimeout(hideToolbar, 3000);
}