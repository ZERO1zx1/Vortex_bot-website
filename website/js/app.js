/* ============================================================
   𝓐𝓮𝓽𝓱𝓮𝓻 蒼Қ — UI engine
   Features: 3D particles, tilt cards, scroll reveal, counters,
   parallax hero, command search/filter, smooth nav.
   ============================================================ */
'use strict';

/* ---------------- 3D particle background ---------------- */
(() => {
  const canvas = document.getElementById('bg-canvas');
  const ctx = canvas.getContext('2d');
  let W, H, particles, mouse = { x: -9999, y: -9999 };

  function resize() {
    W = canvas.width = window.innerWidth * Math.min(window.devicePixelRatio, 1.5);
    H = canvas.height = window.innerHeight * Math.min(window.devicePixelRatio, 1.5);
    canvas.style.width = window.innerWidth + 'px';
    canvas.style.height = window.innerHeight + 'px';
  }

  function init() {
    resize();
    const count = Math.min(90, Math.floor((W * H) / 24000));
    particles = Array.from({ length: count }, () => ({
      x: Math.random() * W,
      y: Math.random() * H,
      vx: (Math.random() - 0.5) * 0.45,
      vy: (Math.random() - 0.5) * 0.45,
      r: Math.random() * 2.2 + 0.8,
      hue: Math.random() < 0.7 ? 218 : (Math.random() < 0.5 ? 168 : 30),
    }));
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    for (const p of particles) {
      p.x += p.vx; p.y += p.vy;
      if (p.x < -10) p.x = W + 10; if (p.x > W + 10) p.x = -10;
      if (p.y < -10) p.y = H + 10; if (p.y > H + 10) p.y = -10;
    }
    // lines between close particles
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const a = particles[i], b = particles[j];
        const dx = a.x - b.x, dy = a.y - b.y;
        const dist = Math.hypot(dx, dy);
        if (dist < 130) {
          ctx.strokeStyle = `rgba(137,180,250,${(1 - dist / 130) * 0.18})`;
          ctx.lineWidth = 0.7;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }
    }
    // dots
    for (const p of particles) {
      ctx.fillStyle = `hsla(${p.hue}, 80%, 78%, 0.85)`;
      ctx.shadowColor = `hsla(${p.hue}, 80%, 78%, 0.8)`;
      ctx.shadowBlur = 10;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.shadowBlur = 0;
    requestAnimationFrame(draw);
  }

  window.addEventListener('resize', () => { init(); });
  window.addEventListener('mousemove', (e) => {
    mouse.x = e.clientX; mouse.y = e.clientY;
  });
  init();
  draw();
})();

/* ---------------- 3D tilt on hover ---------------- */
(() => {
  document.querySelectorAll('[data-tilt]').forEach(el => {
    const max = 9;
    el.addEventListener('mousemove', (e) => {
      const r = el.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width;
      const py = (e.clientY - r.top) / r.height;
      const rx = (py - 0.5) * -max * 2;
      const ry = (px - 0.5) * max * 2;
      el.style.transform = `perspective(900px) rotateX(${rx}deg) rotateY(${ry}deg) translateZ(6px)`;
    });
    el.addEventListener('mouseleave', () => {
      el.style.transform = '';
    });
  });
})();

/* ---------------- Scroll reveal ---------------- */
const revealIO = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      e.target.classList.add('revealed');
      revealIO.unobserve(e.target);
    }
  });
}, { threshold: 0.15 });
function observeReveal() {
  document.querySelectorAll('[data-reveal]:not(.revealed)').forEach(el => revealIO.observe(el));
}
document.querySelectorAll('[data-reveal]').forEach(el => revealIO.observe(el));

/* ---------------- Count-up stat numbers ---------------- */
(() => {
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (!e.isIntersecting) return;
      const el = e.target;
      io.unobserve(el);
      const target = parseInt(el.dataset.count, 10);
      const suffix = el.dataset.suffix || '';
      const dur = 1600;
      const start = performance.now();
      function step(now) {
        const t = Math.min((now - start) / dur, 1);
        const eased = 1 - Math.pow(1 - t, 3);
        el.textContent = Math.round(target * eased) + suffix;
        if (t < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    });
  }, { threshold: 0.4 });
  document.querySelectorAll('.stat-num[data-count]').forEach(el => io.observe(el));
})();

/* ---------------- Hero parallax ---------------- */
(() => {
  const targets = document.querySelectorAll('[data-parallax]');
  if (!targets.length) return;
  let ticking = false;
  window.addEventListener('scroll', () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      const y = window.scrollY;
      targets.forEach(el => {
        const speed = parseFloat(el.dataset.parallax);
        el.style.transform = `translateY(${y * speed * -0.12}px)`;
      });
      ticking = false;
    });
  }, { passive: true });
})();

/* ---------------- Navbar scroll style + burger ---------------- */
(() => {
  const nav = document.querySelector('.navbar');
  const burger = document.getElementById('nav-burger');
  const links = document.querySelector('.nav-links');
  window.addEventListener('scroll', () => {
    nav.style.background = window.scrollY > 40
      ? 'rgba(11,11,20,0.92)'
      : 'rgba(11,11,20,0.65)';
  }, { passive: true });
  burger?.addEventListener('click', () => {
    links.classList.toggle('open');
  });
  links?.querySelectorAll('a').forEach(a => a.addEventListener('click', () => links.classList.remove('open')));
})();

/* ---------------- Commands: render + search + filter ---------------- */
(() => {
  const grid = document.getElementById('cmd-grid');
  const search = document.getElementById('cmd-search');
  const filters = document.getElementById('cmd-filters');
  let currentCat = 'all';

  function meta(cat) {
    return window.CAT_META?.[cat] || { label: cat, color: '#89B4FA', icon: '🔧' };
  }

  function render() {
    const q = (search?.value || '').trim().toLowerCase();
    const items = window.COMMAND_LIST.filter(c => {
      const catOk = currentCat === 'all' || c.cat === currentCat;
      const qOk = !q || c.name.includes(q) || c.desc.toLowerCase().includes(q);
      return catOk && qOk;
    });
    if (!grid) return;
    if (q) {
      /* Global search: flat card grid of all matching commands */
      grid.innerHTML = items.length
        ? `<div class="cmd-panels search-mode">` + items.map((c, i) => cmdCard(c, i)).join('') + `</div>`
        : '<div class="cmd-empty">🔍 Олдсонгүй — өөр үгээр хайгаарай.</div>';
      return;
    }
    /* Category view: one themed panel per visible category, panels are direct grid children */
    const cats = currentCat === 'all' ? window.COMMAND_CATS.filter(c => c !== 'all') : [currentCat];
    const parts = [];
    for (const cat of cats) {
      const m = meta(cat);
      const list = items.filter(c => c.cat === cat);
      if (!list.length) continue;
      parts.push(`
      <div class="cmd-panel" style="--cat-color:${m.color}" data-reveal>
        <div class="panel-head">
          <div class="panel-badge">${m.icon} ${m.label}</div>
          <div class="panel-count">${list.length} команд · ${list.filter(c => c.type === 'slash').length} slash / ${list.filter(c => c.type === 'text').length} text</div>
        </div>
        <div class="panel-grid">
          ${list.map((c, i) => cmdCard(c, i)).join('')}
        </div>
      </div>`);
    }
    grid.innerHTML = parts.join('') || '<div class="cmd-empty">📭 Энэ ангилалд команд алга.</div>';
    /* Trigger reveal for the freshly rendered panels */
    observeReveal();
  }

  function cmdCard(c, i) {
    const m = meta(c.cat);
    return `<div class="cmd-card" style="--cat-color:${m.color};animation-delay:${Math.min(i * 0.03, 0.5)}s">
      <span class="cmd-icon">${c.icon}</span>
      <div class="cmd-body">
        <span class="cmd-name">${c.type === 'slash' ? '/' : 'A!'}${c.name}</span>
        <span class="cmd-desc">${c.desc}</span>
      </div>
      <span class="cmd-cat">${m.icon} ${m.label}</span>
      <span class="cmd-type ${c.type}">${c.type === 'slash' ? 'SLASH' : 'TEXT'}</span>
    </div>`;
  }

  search?.addEventListener('input', render);
  filters?.addEventListener('click', (e) => {
    const btn = e.target.closest('.filter');
    if (!btn) return;
    filters.querySelectorAll('.filter').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentCat = btn.dataset.cat;
    render();
  });
  render();
})();

/* ---------------- Premium cards: cursor-following glow ---------------- */
(() => {
  document.querySelectorAll('.price-card').forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const r = card.getBoundingClientRect();
      card.style.setProperty('--mx', `${((e.clientX - r.left) / r.width) * 100}%`);
      card.style.setProperty('--my', `${((e.clientY - r.top) / r.height) * 100}%`);
    });
  });
})();

/* ---------------- Invite button: real Discord invite link ---------------- */
(() => {
  // Set your actual invite URL in js/config.js or here.
  const INVITE_URL = window.AETHER_CONFIG?.INVITE_URL || 'https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot%20applications.commands';
  document.querySelectorAll('a[href="#invite"]').forEach(a => {
    a.href = INVITE_URL;
    a.setAttribute('target', '_blank');
    a.setAttribute('rel', 'noopener');
  });
})();

/* ---------------- Bot heartbeat: жинхэнэ Online / Offline ---------------- */
(() => {
  const cfg = window.AETHER_CONFIG || {};
  const HEARTBEAT_URL = cfg.HEARTBEAT_URL || '';
  const APIKEY = cfg.HEARTBEAT_APIKEY || '';
  const TIMEOUT_MS = cfg.HEARTBEAT_TIMEOUT_MS || 6000;
  const POLL_MS = cfg.HEARTBEAT_POLL_MS || 60000;

  const dot = document.getElementById('status-dot');
  const text = document.getElementById('online-text');
  // "Сүүлд:" мэдээлэл — status-meta эсвэл uptime bars дэргэд байвал шинэчилнэ
  const lastSeenEl = document.getElementById('last-seen') || document.querySelector('.uptime-bars .uptime-meta, .status-meta');
  if (!dot || !text) return;

  const fmtTime = (iso) => {
    if (!iso) return '';
    const d = new Date(iso);
    return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  };
  const fmtSince = (iso) => {
    if (!iso) return '';
    const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
    if (mins < 1) return 'саяхан';
    if (mins < 60) return `${mins} мин өмнө`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs} цаг ${mins % 60} мин өмнө`;
    const days = Math.floor(hrs / 24);
    return `${days} хоног ${hrs % 24} цаг өмнө`;
  };

  const setOnline = (row) => {
    dot.className = 'status-dot online';
    text.textContent = 'Online';
    if (lastSeenEl && row?.uptime_since) {
      lastSeenEl.textContent = `Бот ${fmtSince(row.uptime_since)} асаагдсан · сүүлд: ${fmtTime(row.uptime_since)}`;
    }
  };
  const setOffline = (row) => {
    dot.className = 'status-dot offline';
    text.textContent = 'Offline';
    if (lastSeenEl) {
      lastSeenEl.textContent = row?.last_ping
        ? `Сүүлд онлайн байсан: ${fmtSince(row.last_ping)} (${fmtTime(row.last_ping)})`
        : 'Бот одоогоор унтарсан байна';
    }
  };

  if (!HEARTBEAT_URL) {
    // URL тохируулаагүй бол Manual mode — үргэлж Online харуулна.
    setOnline();
    return;
  }

  const check = async () => {
    try {
      const ctrl = new AbortController();
      const t = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
      const res = await fetch(HEARTBEAT_URL, {
        signal: ctrl.signal,
        cache: 'no-store',
        headers: APIKEY ? { apikey: APIKEY, Authorization: `Bearer ${APIKEY}` } : undefined,
      });
      clearTimeout(t);
      if (!res.ok) { setOffline(null); return; }
      const rows = await res.json();
      const row = Array.isArray(rows) ? rows[0] : null;
      if (!row?.last_ping) { setOffline(row); return; }
      const age = Date.now() - new Date(row.last_ping).getTime();
      if (age <= TIMEOUT_MS) setOnline(row); else setOffline(row);
    } catch {
      setOffline(null);
    }
  };
  check();
  setInterval(check, POLL_MS);
})();

/* ---------------- Mobile: tilt reset on touch ---------------- */
document.querySelectorAll('[data-tilt]').forEach(el => {
  el.addEventListener('touchstart', () => { el.style.transform = ''; }, { passive: true });
});

/* ---------------- Scroll to top ---------------- */
(() => {
  const btn = document.getElementById('scroll-top');
  if (!btn) return;
  window.addEventListener('scroll', () => {
    btn.classList.toggle('visible', window.scrollY > 500);
  }, { passive: true });
  btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
})();

/* ---------------- Language switcher: MN / EN ---------------- */
const AETHER_I18N = {
  mn: {
    'nav.features': 'Онцлогууд',
    'nav.commands': 'Командууд',
    'nav.stats': 'Статистик',
    'hero.badge': '🇲🇳 Монгол Discord бот',
    'hero.subtitle': 'Эдийн засаг, түвшин, гэрлэл, дэлгүүр, тоглоом, модерац — бүгдийг нэг ботонд. Таны серверийг амьд болго.',
    'hero.viewCommands': 'Командууд үзэх',
    'hero.tags1': 'Slash + Text команд',
    'features.tag': 'ОНЦЛОГ ФУНКЦҮҮД',
    'features.title1': 'Бүгд нэг дор.',
    'commands.tag': 'КОМАНДУУД',
    'commands.title2': 'команд',
    'stats.tag': 'СТАТИСТИК',
    'stats.title1': 'Тоогоор',
    'stats.title2': 'хэлбэл',
    'stats.cmd': 'Команд (44 slash / 74 text)',
    'stats.tables': 'Database таблиц',
    'status.sub': '24/7 ажилладаг, Supabase дээр суурилсан бат бөх backend',
    'premium.title1': 'Дээд түвшний',
    'premium.title2': 'эрх',
    'premium.soon': 'Удахгүй',
    'premium.note': '🚧 Premium систем одоогоор боловсруулагдаж байна. Бэлэн болоход танд Discord дамжуулан мэдэгдэнэ. Одоогоор бүх үндсэн командууд <strong>ҮНЭГҮЙ</strong>.',
    'faq.title1': 'Түгээмэл',
    'faq.title2': 'асуултууд',
    'invite.title1': 'Серверээ',
    'invite.title2': 'амьдруулъя',
    'invite.sub': 'Нэг даралтаар нэмээд, өнөөдрөөс эхлүүл.',
    'invite.btn': 'Server-т элсэх',
    'footer.brand': 'Монгол Discord бот',
    'footer.faq': 'Асуулт хариулт',
    'footer.copy': '© 2026 𝓐𝓮𝓽𝓱𝓮𝓻 蒼Қ. Бүх эрх хуулиар хамгаалагдсан.',
    'heartbeat.checking': 'Ботын жинхэнэ төлөвийг шалгаж байна…',
    'heartbeat.now': 'Сүүлд онлайн байсан: саяхан',
    'heartbeat.ago': 'Сүүлд онлайн байсан: {since} ({time})',
    'heartbeat.off': 'Бот одоогоор унтарсан байна',
    'heartbeat.up': 'Бот {since} асаагдсан · сүүлд: {time}',
  },
  en: {
    'nav.features': 'Features',
    'nav.commands': 'Commands',
    'nav.stats': 'Stats',
    'hero.badge': '🇲🇳 Mongolian Discord Bot',
    'hero.subtitle': 'Economy, leveling, marriage, shop, games, moderation — everything in one bot. Bring your server to life.',
    'hero.viewCommands': 'View commands',
    'hero.tags1': 'Slash + Text commands',
    'features.tag': 'FEATURES',
    'features.title1': 'All in one.',
    'commands.tag': 'COMMANDS',
    'commands.title2': 'commands',
    'stats.tag': 'STATISTICS',
    'stats.title1': 'By the',
    'stats.title2': 'numbers',
    'stats.cmd': 'Commands (44 slash / 74 text)',
    'stats.tables': 'Database tables',
    'status.sub': 'Runs 24/7 with a Supabase-backed heartbeat',
    'premium.title1': 'Top-tier',
    'premium.title2': 'perks',
    'premium.soon': 'Coming Soon',
    'premium.note': '🚧 The Premium system is under development. We will notify you via Discord when it is ready. For now, all core commands are <strong>FREE</strong>.',
    'faq.title1': 'Frequently',
    'faq.title2': 'asked questions',
    'invite.title1': 'Let\u2019s bring your',
    'invite.title2': 'server to life',
    'invite.sub': 'One click, done — start today.',
    'invite.btn': 'Join server',
    'footer.brand': 'Mongolian Discord bot',
    'footer.faq': 'FAQ',
    'footer.copy': '© 2026 𝓐𝓮𝓽𝓱𝓮𝓻 蒼Қ. All rights reserved.',
    'heartbeat.checking': 'Checking real bot status…',
    'heartbeat.now': 'Last online: just now',
    'heartbeat.ago': 'Last online: {since} ({time})',
    'heartbeat.off': 'Bot is currently offline',
    'heartbeat.up': 'Bot started {since} · last ping: {time}',
  },
};

(() => {
  const applyLang = (lang) => {
    const dict = AETHER_I18N[lang] || AETHER_I18N.mn;
    document.documentElement.lang = lang;
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const v = dict[el.getAttribute('data-i18n')];
      if (v !== undefined) el.innerHTML = v;
    });
    document.querySelectorAll('.lang-btn').forEach(b => {
      b.classList.toggle('active', b.getAttribute('data-lang') === lang);
    });
    try { localStorage.setItem('aether-lang', lang); } catch {}
    // Heartbeat статусын текстүүдийг одоогийн төлөвөөр дахин зурна
    if (window.__aetherLang === 'en' || window.__aetherLang === 'mn') {
      // status нь аль хэдийн тогтсон байвал last-seen-ийг зөвхөн шалгах текстээр
      const ls = document.getElementById('last-seen');
      if (ls && ls.textContent.includes('…') === false && ls.dataset.ok !== '1') {
        ls.textContent = dict['heartbeat.checking'];
      }
    }
    window.__aetherLang = lang;
  };
  let lang = 'mn';
  try { lang = localStorage.getItem('aether-lang') || 'mn'; } catch {}
  const switcher = document.getElementById('lang-switcher');
  if (switcher) {
    switcher.querySelectorAll('.lang-btn').forEach(b => {
      b.addEventListener('click', () => applyLang(b.getAttribute('data-lang')));
    });
  }
  applyLang(lang);
})();
