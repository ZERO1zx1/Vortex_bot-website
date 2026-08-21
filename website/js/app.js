/* ============================================================
   𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹 — UI engine
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

  function particleHues() {
    const cs = getComputedStyle(document.documentElement);
    const n = (s) => parseFloat(cs.getPropertyValue(s)) || 218;
    return [n('--particle-hue-a'), n('--particle-hue-b'), n('--particle-hue-c')];
  }
  function isLight() { return document.documentElement.getAttribute('data-theme') === 'light'; }

  function init() {
    resize();
    const [ha, hb, hc] = particleHues();
    const count = Math.min(90, Math.floor((W * H) / 24000));
    particles = Array.from({ length: count }, () => ({
      x: Math.random() * W,
      y: Math.random() * H,
      vx: (Math.random() - 0.5) * 0.45,
      vy: (Math.random() - 0.5) * 0.45,
      r: Math.random() * 2.2 + 0.8,
      hue: Math.random() < 0.7 ? ha : (Math.random() < 0.5 ? hb : hc),
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
    const linkAlpha = isLight() ? 0.14 : 0.18;
    const lineColor = isLight() ? `rgba(59,94,168,` : `rgba(137,180,250,`;
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const a = particles[i], b = particles[j];
        const dx = a.x - b.x, dy = a.y - b.y;
        const dist = Math.hypot(dx, dy);
        if (dist < 130) {
          ctx.strokeStyle = `${lineColor}${(1 - dist / 130) * linkAlpha})`;
          ctx.lineWidth = 0.7;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }
    }
    // dots — light mode uses slightly deeper saturation for visibility
    const dotLight = isLight() ? 72 : 78;
    for (const p of particles) {
      ctx.fillStyle = `hsla(${p.hue}, 80%, ${dotLight}%, 0.85)`;
      ctx.shadowColor = `hsla(${p.hue}, 80%, ${dotLight}%, 0.8)`;
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

/* ---------------- Dark / Light theme toggle ---------------- */
(() => {
  const root = document.documentElement;
  const meta = document.querySelector('meta[name="theme-color"]');
  const applyTheme = (theme) => {
    root.setAttribute('data-theme', theme === 'light' ? 'light' : 'dark');
    if (meta) meta.setAttribute('content', theme === 'light' ? '#F7F9FC' : '#0B0B14');
    try { localStorage.setItem('aether-theme', theme); } catch {}
    window.__aetherTheme = theme;
  };
  let theme = 'dark';
  try {
    const saved = localStorage.getItem('aether-theme');
    const prefersLight = window.matchMedia?.('(prefers-color-scheme: light)')?.matches;
    theme = (saved === 'light' || saved === 'dark') ? saved : (prefersLight ? 'light' : 'dark');
  } catch {}
  applyTheme(theme);
  const toggle = document.getElementById('theme-toggle');
  if (toggle) {
    toggle.setAttribute('aria-label', 'Toggle dark/light theme');
    toggle.addEventListener('click', () => applyTheme(window.__aetherTheme === 'light' ? 'dark' : 'light'));
  }
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
    const light = document.documentElement.getAttribute('data-theme') === 'light';
    nav.style.background = window.scrollY > 40
      ? (light ? 'rgba(247,249,252,0.94)' : 'rgba(11,11,20,0.92)')
      : (light ? 'rgba(247,249,252,0.78)' : 'rgba(11,11,20,0.65)');
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

  /* URL-ээс хайлтын query авах: #commands?q=work эсвэл #commands?cmd=marry эсвэл &cat=Economy (W1 fix) */
  const safeDecode = (s) => { try { return decodeURIComponent(s); } catch { return s; } };  // W4 fix
  const parseHash = () => (window.location.hash || '').match(/[?&]q=([^&#]+)/i);
  const parseHashCat = () => (window.location.hash || '').match(/[?&]cat=([^&#]+)/i);
  let m = parseHash();
  let firstLoad = true;
  /* Async ачаалалтай үед hash ачаалагдаагүй байж болох тул hashchange-г хүлээнэ */
  /* URL-ийн category-г тохиргоо болгон идэвхжүүлэх (WI1) */
  const applyHashCat = () => {
    const cm = parseHashCat();
    if (cm && filters) {
      const catBtn = filters.querySelector(`.filter[data-cat="${cm[1]}"]`);
      if (catBtn && currentCat !== cm[1]) {
        filters.querySelectorAll('.filter').forEach(b => b.classList.remove('active'));
        catBtn.classList.add('active');
        currentCat = cm[1];
        render();
        syncUrl();
      }
    }
  };
  const applyHashSearch = () => {
    m = parseHash();
    if (m && search) {
      const q = safeDecode(m[1]);
      if (search.value !== q) {
        search.value = q;
        render();
        syncUrl();
        /* Зөвхөн анхны ачаалал дээр scroll хийнэ (W2 fix) */
        if (firstLoad) { firstLoad = false; search.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
      }
    }
    applyHashCat();
  };
  if (m && search) {
    search.value = safeDecode(m[1]);
    /* Category-г URL-ээс авах бол товчийг идэвхжүүлнэ (WI1) */
    const cm = parseHashCat();
    if (cm) {
      const catBtn = filters?.querySelector(`.filter[data-cat="${cm[1]}"]`);
      if (catBtn) {
        filters.querySelectorAll('.filter').forEach(b => b.classList.remove('active'));
        catBtn.classList.add('active');
        currentCat = cm[1];
      }
    }
    render();
    syncUrl();
    setTimeout(() => { firstLoad = false; search.scrollIntoView({ behavior: 'smooth', block: 'center' }); }, 300);
  } else { firstLoad = false; }
  window.addEventListener('hashchange', applyHashSearch);
  /* Хожим hash тогтох боломжтой (async navigation) — 3 удаа шалгана */
  [400, 1200, 3000].forEach(t => setTimeout(applyHashSearch, t));
  /* Хайлтыг URL-д тусгах (линк хуваалцах боломжтой) — category-г бас тусгана (WI1) */
  const syncUrl = () => {
    if (!search) return;
    const q = search.value.trim();
    const url = new URL(window.location.href);
    let h = '#commands';
    const parts = [];
    if (q) parts.push('q=' + encodeURIComponent(q));
    if (currentCat !== 'all') parts.push('cat=' + encodeURIComponent(currentCat));
    if (parts.length) h += '?' + parts.join('&');
    url.hash = h;
    history.replaceState(null, '', url.toString());
  };

  function meta(cat) {
    return window.CAT_META?.[cat] || { label: cat, color: '#89B4FA', icon: '🔧' };
  }
  function catLabel(m) {
    return (window.__aetherLang === 'en' && m.labelEN) || m.label;
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
          <div class="panel-badge">${m.icon} ${catLabel(m)}</div>
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
      <span class="cmd-cat">${m.icon} ${catLabel(m)}</span>
      <span class="cmd-type ${c.type}">${c.type === 'slash' ? 'SLASH' : 'TEXT'}</span>
    </div>`;
  }

  /* URL-ээс ирсэн query-г input-д оноох (render()-ийн өмнө) */
  /* Sticky toolbar: хэрэглэгч доош scroll хийхэд хайлтын талбар дээд талд наалдана (WI4) */
  const toolbar = document.querySelector('.cmd-toolbar');
  const stickyObserver = () => {
    if (!toolbar) return;
    const sec = document.getElementById('commands');
    const rect = sec.getBoundingClientRect();
    const inputRect = search.getBoundingClientRect();
    toolbar.classList.toggle('sticky', rect.top < 0 && inputRect.bottom > 0);
  };
  window.addEventListener('scroll', stickyObserver, { passive: true });
  /* Debounce: render()-ийг 80мс-ийн дараа хийнэ — 118 карт бүр дарах бүр зурагдахгүй (WI3) */
  let _debounceTimer = null;
  search?.addEventListener('input', () => {
    if (_debounceTimer) clearTimeout(_debounceTimer);
    _debounceTimer = setTimeout(() => { render(); syncUrl(); }, 80);
  });
  filters?.addEventListener('click', (e) => {
    const btn = e.target.closest('.filter');
    if (!btn) return;
    filters.querySelectorAll('.filter').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentCat = btn.dataset.cat;
    render();
    syncUrl();  /* Category өөрчлөлт URL-д тусна (WI1) */
  });
  render();
  /* Хэл солиход анги/картын шошгыг дахин зурахын тулд глобал болгоно */
  window.__aetherRender = render;
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
  const setInvite = (a) => {
    if (!a) return;
    a.href = INVITE_URL;
    a.removeAttribute('onclick');
    a.onclick = null;
    a.setAttribute('target', '_blank');
    a.setAttribute('rel', 'noopener');
  };
  // Бүх "элсэх" холбоос (nav, hero, premium, invite CTA, footer биш) — аюулгүй, баталгаажсан
  document.querySelectorAll('a.nav-invite, .hero-actions a.btn-primary, a.btn-ghost[href^="https://discord.com/oauth2"], #invite-btn').forEach(setInvite);
  // Нэмэлт баталгаа: invite-btn id-тэй элемент заавал ажиллана (ямар ч хэв маягтай)
  setInvite(document.getElementById('invite-btn'));
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
    'cmd.placeholder': '🔎 Команд хайх... (жишээ нь: A!daily, /ban, marry)',
    'cat.all': '🌐 Бүгд',
    'cat.economy': '💰 Economy',
    'cat.leveling': '📊 Leveling',
    'cat.social': '💍 Гэр бүл',
    'cat.games': '🎲 Тоглоом',
    'cat.moderation': '🛡️ Модерац',
    'cat.admin': '⚙️ Админ',
    'cat.utility': '🔧 Бусад',
    'stats.cog': 'Cog',
    'stats.uptime': 'Uptime',
    'community.tag': 'DISCORD SERVER',
    'community.title': 'Албан ёсны <span class="accent">AETHER</span> сервер',
    'community.subtitle': '🌌 AETHER SERVER — YOUR GAMING COMMUNITY<br/>Төрөл бүрийн тоглоом · Active Community · Endless Events',
    'community.rules': 'ОФИЦИАЛЬ СЕРВЕРИЙН ДҮРМҮҮД',
    'community.punish': 'ШИЙТГЭЛИЙН СИСТЕМ',
    'community.punish_imp': 'АНХААРАЛ:',
    'community.staff_title': 'AETHER — STAFF-ИЙН <span class="accent">ТАНИЛЦУУЛГА</span>',
    'rule.r1t': 'ХҮНДЭТГЭЛ',
    'rule.r2t': 'НУУЦЛАЛ',
    'rule.r3t': 'АЮУЛГҮЙ БАЙДАЛ',
    'rule.r4t': 'КОНТЕНТ',
    'rule.r5t': 'ЧАТ',
    'rule.r6t': 'ROLEPLAY',
    'rule.r7t': 'СУВГУУД',
    'rule.r8t': 'STAFF',
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
    'faq.q1': 'Ботыг хэрхэн сервертээ нэмэх вэ?',
    'faq.a1': '𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹 нь <strong>private bot</strong> — зөвхөн нэг Discord серверт ажилладаг, өөр серверт нэмэх боломжгүй. Бусад серверүүдтэй <span data-i18n="faq.a1join">Discord сервертээ элсэж</span> бүх командиудыг үнэгүй ашиглаарай.',
    'faq.a1join': 'Discord сервертээ элсэж',
    'faq.q2': 'Командууд хэрхэн ашиглах вэ?',
    'faq.a2': 'Admin ба Модерац командыг <code class="mono">/</code> slash байдлаар (жишээ нь /ban), бусад бүх командыг <code class="mono">A!</code> префиксээр (жишээ нь A!daily, A!work) ашиглана.',
    'faq.q3': 'Мөнгөний систем хэрхэн ажилладаг вэ?',
    'faq.a3': '<code class="mono">A!daily</code> дарж өдөр бүрийн урамшуулал авах, <code class="mono">A!work</code> ажиллах, <code class="mono">A!market</code> дэлгүүрээс юм худалдаж авах, <code class="mono">A!gamble</code> казино тоглохоор мөнгө олж болно.',
    'faq.q4': 'Бот 24/7 ажилладаг уу?',
    'faq.a4': 'Тийм ээ — Supabase backend дээр heartbeat системээр ажилладаг. Энэ вэбсайтын “Ботын төлөв” хэсгээс жинхэнэ цаг хугацааны Online/Offline төлөвийг харж болно.',
    'faq.q5': 'Өгөгдөл хадгалагддаг уу?',
    'faq.a5': 'Тийм — Supabase (PostgreSQL) дээр 57 таблицээр хэрэглэгч, эдийн засаг, гэрлэл, түвшин гэх мэт бүх өгөгдөл бат бөх хадгалагдана. Бот унтарч асахад ч мөнгө, түвшин устахгүй.',
    'faq.q6': 'Premium хэдийд нээгдэх вэ?',
    'faq.a6': 'Premium систем одоогоор боловсруулагдаж байна. Бэлэн болоход Discord дамжуулан мэдэгдэх болно. Одоогоор бүх үндсэн командууд <strong>ҮНЭГҮЙ</strong>.',
    'faq.q7': 'Алдаа гарвал хаана хэлэх вэ?',
    'faq.a7': 'Discord дамжуулан шууд хэлэх эсвэл <a href="https://github.com/ZERO1zx1/gurtendev/issues" target="_blank" rel="noopener">GitHub Issues</a> хуудсанд бичээрэй.',
    'modal.howto': '👆 Командын карт дээр дарвал дэлгэрэнгүй харна',
    'modal.args': 'Аргумент',
    'modal.example': 'Жишээ',
    'modal.close': 'Хаах',
    'modal.required': 'заавал',
    'modal.optional': 'сонголттой',
    'cmd.addmoney.desc': 'Хэрэглэгчид мөнгө нэмэх (админ)',
    'cmd.addxp.desc': 'Хэрэглэгчид XP нэмэх (админ)',
    'cmd.adopt.desc': 'Хүүхэд үрчлэх',
    'cmd.autoaccept.desc': 'Автомат зөвшөөрөл',
    'cmd.balance.desc': 'Таны мөнгөн дүн',
    'cmd.ban.desc': 'Серверээс банлах',
    'cmd.boost.desc': 'Boost мэдээлэл',
    'cmd.buy.desc': 'Хувьцаа худалдаж авах',
    'cmd.cafe.desc': 'Кафегийн цэс ба мэдээлэл',
    'cmd.cancel.desc': 'Урсгал цуцлах',
    'cmd.avatar.desc': 'Хүний аватар харах',
    'cmd.codes.desc': 'Промо кодууд',
    'cmd.end.desc': 'Сугалааг эрт дуусгах',
    'cmd.relationship.desc': 'Гэр бүлийн холбоо',
    'cmd.children.desc': 'Таны хүүхдүүд',
    'cmd.clear.desc': 'Мессеж цэвэрлэх (purge)',
    'cmd.coinflip.desc': 'Зоос шидэх',
    'cmd.confess.desc': 'Аноним илчлэл',
    'cmd.count_stats_server.desc': 'Тооллын статистик',
    'cmd.counting.desc': 'Тоо тоолох дуулаан',
    'cmd.daily.desc': 'Өдөр бүрийн мөнгөний урамшуулал',
    'cmd.dice.desc': 'Шоо шидэх',
    'cmd.dine.desc': 'Кафед хоол идэх',
    'cmd.disown.desc': 'Хүүхдээсээ татгалзах',
    'cmd.divorce.desc': 'Салалт',
    'cmd.entries.desc': 'Сугалааны оролцогчид',
    'cmd.familytree.desc': 'Гэр бүлийн мод',
    'cmd.fulltree.desc': 'Бүрэн гэр бүлийн мод',
    'cmd.gamble.desc': 'Шуудайнд мөнгө тавих',
    'cmd.gift.desc': 'Ханиандаа бэлэг өгөх',
    'cmd.giveaway.desc': 'Сугалаа явуулах',
    'cmd.grank.desc': 'Server-ийн XP жагсаалт',
    'cmd.graph.desc': 'Хувьцааны график',
    'cmd.help.desc': 'Бүх командыг ангиллаар нь',
    'cmd.invite.desc': 'Урилгын холбоос',
    'cmd.inviter.desc': 'Хэн таныг урьсныг харах',
    'cmd.invites.desc': 'Таны урилгууд ба XP урамшуулал',
    'cmd.kick.desc': 'Хөөх',
    'cmd.leaderboard.desc': 'Түвшингийн тэргүүнүүд',
    'cmd.leveling_setup.desc': 'Leveling-ийн тохиргоо (админ)',
    'cmd.list.desc': 'Жагсаалт харах',
    'cmd.lock.desc': 'Суваг түгжих',
    'cmd.love.desc': 'Хайрын хэмжээ харах',
    'cmd.mafia.desc': 'Mafia тоглоом',
    'cmd.mafiacreate.desc': 'Mafia тоглоом үүсгэх (админ)',
    'cmd.mafiaend.desc': 'Mafia-г дуусгах (админ)',
    'cmd.mafiastart.desc': 'Mafia-г эхлүүлэх (админ)',
    'cmd.makeparent.desc': 'Гэр бүлийн эцэг/эх болгох',
    'cmd.market.desc': 'Кафегийн дэлгүүр, хоол/уух зүйлс',
    'cmd.marketplace.desc': 'Зарын зах зээл',
    'cmd.marriage_setup.desc': 'Гэрлэлийн тохиргоо (админ)',
    'cmd.marriagepro.desc': 'Гэрлэлийн профиль',
    'cmd.marry.desc': 'Гэрлэх',
    'cmd.mines.desc': 'Уурхайн тоглоом',
    'cmd.mp.desc': 'Marketplace-ийн товчлол',
    'cmd.partners.desc': 'Партнер серверүүд',
    'cmd.pay.desc': 'Нөгөө хүн рүү мөнгө шилжүүл',
    'cmd.placeholders.desc': 'Placeholder мэдээлэл',
    'cmd.propose.desc': 'Хайртай хүнээсээ гэрлэлтийн санал тавь',
    'cmd.pvp.desc': 'Тоглогч хоорондын тулаан',
    'cmd.rank.desc': 'Таны түвшин ба XP',
    'cmd.removemoney.desc': 'Хэрэглэгчээс мөнгө хасах (админ)',
    'cmd.removexp.desc': 'XP хасах (админ)',
    'cmd.reroll.desc': 'Сугалааг дахин татах',
    'cmd.rob.desc': 'Нэгнээсээ хулгайлах (эрсдэлтэй!)',
    'cmd.roulette.desc': 'Рулетка',
    'cmd.rps.desc': 'Чулуу-цаас-хайч',
    'cmd.sell.desc': 'Хувьцаа зарах',
    'cmd.serveractivity.desc': 'Server-ийн идэвхтэй байдал',
    'cmd.slots.desc': 'Слот машин',
    'cmd.spouse.desc': 'Таны ханийн мэдээлэл',
    'cmd.stock.desc': 'Хувьцааны мэдээлэл',
    'cmd.stock_leaderboard.desc': 'Хувьцааны лидерборд',
    'cmd.stock_ticker.desc': 'Хувьцааны жагсаалт',
    'cmd.template_create.desc': 'Загвар үүсгэх',
    'cmd.template_delete.desc': 'Загвар устгах',
    'cmd.template_edit.desc': 'Загвар засах',
    'cmd.template_list.desc': 'Загварууд харах',
    'cmd.template_preview.desc': 'Загвар урьдчилж харах',
    'cmd.timeout.desc': 'Түр хугацаагаар хаах',
    'cmd.trade.desc': 'Бараа солилцоо',
    'cmd.tree.desc': 'Гэр бүлийн модны товчлол',
    'cmd.unban.desc': 'Баныг авах',
    'cmd.unlock.desc': 'Суваг тайлах',
    'cmd.warn.desc': 'Сануулга өгөх',
    'cmd.warnings.desc': 'Таны сануулгууд',
    'cmd.work.desc': 'Ажиллаж мөнгө ол',
    'cmd.workphrase.desc': 'Ажлын үгсийн жагсаалт тохируулах',
    'about.p1': '𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹 — Монгол хэл дээрх бүрэн эрхт Discord бот бөгөөд AETHER gaming community-ийн албан ёсны иж бүрэн хөдөлгүүр юм.',
    'about.p2': 'Эдийн засаг, түвшин, гэрлэл, дэлгүүр, казино, mafia, модерац — 29 cog, 118 команд бүгд нэг системд. Supabase (PostgreSQL) backend-ээр 24/7 бат бөх ажиллана.',
    'about.q': 'Бид бол',
    'about.tag': 'Бидний тухай',
    'community.active': 'Active Community',
    'community.active_d': 'Идэвхтэй гишүүд, 24/7 чат, найзуудтай бол.',
    'community.event': 'Event & Giveaway',
    'community.event_d': 'Тогтмол сугалаа, тоглоомын тэмцээн, бэлэг өгөлт.',
    'community.gaming': 'Gaming',
    'community.gaming_d': 'Roblox + бусад тоглоомын лобби, дуо хайх, тэмцээн зохиох.',
    'community.intro': 'AETHER — Монголын идэвхтэй gaming community. Roblox болон бусад тоглоомын хүмүүс нэг дороо тоглож, найзалж, уралдадаг.',
    'community.punish_note': 'Дүрэм зөрчсөн тохиолдолд дараах шийтгэлийн шатлал автоматаар үйлчилнэ. Давтан зөрчил шийтгэлийг хүндрүүлнэ.',
    'community.staff_intro': 'AETHER серверийг идэвхтэй удирдаж буй баг. Асуудал гарвал эдгээр хүмүүст хандана уу.',
    'community.topup': 'Top-Up & Currency',
    'community.topup_d': 'Game currency, top-up тусламж, хямдхан үнээр авна.',
    'faq.tag': 'АСУУЛТ ХАРИУЛТ',
    'feat.cas': 'Казино & Тоглоом',
    'feat.cas_d': 'Coinflip, slots, roulette, mines, pvp, counting, cards.',
    'feat.econ': 'Эдийн засаг',
    'feat.econ_d': 'daily, work, gamble, мөнгөний систем. Хөдөлмөрлөөд баяжина.',
    'feat.fun': 'Fun & Бусад',
    'feat.fun_d': 'Cafe, quests, confessions, giveaway, temp voice, avatar logger.',
    'feat.lvl': 'Түвшин / Leveling',
    'feat.lvl_d': 'XP систем, leaderboard, voice XP. Идэвхтэй байх тусам түвшин авна.',
    'feat.maf': 'Mafia',
    'feat.maf_d': 'Дорнодын мафия тоглоом — нойрсох, шалгах, ялалт байгуул.',
    'feat.mar': 'Гэрлэл / Гэр бүл',
    'feat.mar_d': 'Учрахаас эхлээд гэр бүлийн мод хүртэл. Хайртай хүнтэйгээ гэрлэ.',
    'feat.mod': 'Модерац',
    'feat.mod_d': 'Ban, kick, warn, timeout, purge, mod-log. Цэвэрхэн сервер.',
    'feat.shop': 'Дэлгүүр & Хувьцаа',
    'feat.shop_d': 'Market, marketplace, амьд stock систем. Худалдаж, худалд.',
    'rule.r1': 'Бүх гишүүдийг хүндэлж харьцана. Доромжлох, дорд үзэх, үндсэрхэх үйлдэл хүлээн зөвшөөрөгдөхгүй.',
    'rule.r2': 'Бусдын хувийн мэдээлэл (ID, утас, хаяг) нийтлэх, түгээх хориглоно.',
    'rule.r3': 'Аюултай холбоос, залилан, вирус хуваалцах, бусдыг мэхлэх оролдлого хориглоно.',
    'rule.r4': 'NSFW контент, зүй бус контент серверт байршуулахыг хориглоно.',
    'rule.r5': 'Спам, flood, бусдын чат тасалдуулах, тоглоом дунд хориглоно.',
    'rule.r6': 'RP сувгаас гадна roleplay хийх, бусдын RP-д санамсаргүй нэвтрэх хориглоно.',
    'rule.r7': 'Сувгуудыг зориулалтын дагуу ашиглана. Зөв сувгаар ярина.',
    'rule.r8': 'Staff-ийн шийдвэрийг хүндэтгэнэ. Шударга бус шийдвэр Discord-оор гомдол мэдүүлнэ.',
    'staff.aferrz': 'Helper',
    'staff.aiken': 'Helper',
    'staff.aiku': 'Helper',
    'staff.bakuna': 'Moderator',
    'staff.irla': 'Moderator',
    'staff.vortex': 'Founder / Developer',
    'status.refresh': '24/7 онлайн — жинхэнэ цагийн heartbeat',
    'status.tag': 'БОТЫН ТӨЛӨВ',
    'status.title1': 'Ботын',
    'status.title2': 'төлөв',
    'invite.title1': 'Серверээ',
    'invite.title2': 'амьдруулъя',
    'invite.sub': 'Нэг даралтаар нэмээд, өнөөдрөөс эхлүүл.',
    'invite.btn': 'Server-т элсэх',
    'footer.brand': 'Монгол Discord бот',
    'footer.faq': 'Асуулт хариулт',
    'footer.copy': '© 2026 𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹. Бүх эрх хуулиар хамгаалагдсан.',
    'heartbeat.checking': 'Ботын жинхэнэ төлөвийг шалгаж байна…',
    'ui.scrolltop': 'Дээшээ',
    'heartbeat.now': 'Сүүлд онлайн байсан: саяхан',
    'heartbeat.ago': 'Сүүлд онлайн байсан: {since} ({time})',
    'heartbeat.off': 'Бот одоогоор унтарсан байна',
    'heartbeat.up': 'Бот {since} асаагдсан · сүүлд: {time}',

    'nav.changelog': 'Changelog',
    'cl.tag': 'ШИНЭЧЛЭЛ',
    'cl.title1': 'Хувилбарын',
    'cl.title2': 'тэмдэглэл',
    'cl.new': 'ШИНЭ',
    'cl.fix': 'ЗАСВАР',
    'cl.v24_t': 'v2.4 — Reaction roles &amp; Auto-moderation',
    'cl.v24_d': 'Emoji дарж үүрэг авах систем (`/rr setup`), анти-спам, антиссылка, анти-райд хамгаалалт (`/automod`), хэл солиход бүрэн хариу өгөх rotating presence.',
    'cl.v23_t': 'Бүтэн dark/light горим',
    'cl.v23_d': 'Вэбсайт бүрэн dark/light горимтой болж, шинэ лого болон favicon, OG banner нэмэгдлээ. i18n 217 түлхүүр (MN = EN).',
    'cl.v22_t': 'Mobile бүрэн засвар',
    'cl.v22_d': 'Командын картнууд, badge-ууд, хайлтын input 390px утасны дэлгэцэд бүрэн цэгцтэй болсон. 118 команд бүгдийн MN/EN тайлбартай.',
    'cl.v21_t': 'Вэбсайт үндэс',
    'cl.v21_d': '3D хөдөлгөөнт hero, командын каталог (хайлт, filter, modal), live Online/Offline статус, staff ба дүрмийн хэсэг нээгдлээ.',
  },
  en: {
    'nav.features': 'Features',
    'nav.commands': 'Commands',
    'nav.stats': 'Stats',
    'hero.badge': '🇲🇳 Mongolian Discord Bot',
    'hero.subtitle': 'Economy, leveling, marriage, shop, games, moderation — everything in one bot. Bring your server to life.',
    'hero.viewCommands': 'View commands',
    'hero.tags1': 'Slash + Text commands',
    'cmd.placeholder': '🔎 Search commands... (e.g. A!daily, /ban, marry)',
    'cat.all': '🌐 All',
    'cat.economy': '💰 Economy',
    'cat.leveling': '📊 Leveling',
    'cat.social': '💍 Family',
    'cat.games': '🎲 Games',
    'cat.moderation': '🛡️ Moderation',
    'cat.admin': '⚙️ Admin',
    'cat.utility': '🔧 Utility',
    'stats.cog': 'Cogs',
    'stats.uptime': 'Uptime',
    'community.tag': 'DISCORD SERVER',
    'community.title': 'Official <span class="accent">AETHER</span> server',
    'community.subtitle': '🌌 AETHER SERVER — YOUR GAMING COMMUNITY<br/>All kinds of games · Active Community · Endless Events',
    'community.rules': 'OFFICIAL SERVER RULES',
    'community.punish': 'PUNISHMENT SYSTEM',
    'community.punish_imp': 'IMPORTANT:',
    'community.staff_title': 'AETHER — STAFF <span class="accent">INTRO</span>',
    'rule.r1t': 'RESPECT',
    'rule.r2t': 'PRIVACY',
    'rule.r3t': 'SAFETY',
    'rule.r4t': 'CONTENT',
    'rule.r5t': 'CHAT',
    'rule.r6t': 'ROLEPLAY',
    'rule.r7t': 'CHANNELS',
    'rule.r8t': 'STAFF',
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
    'faq.q1': 'How do I add the bot to my server?',
    'faq.a1': '𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹 is a <strong>private bot</strong> — it runs on exactly one Discord server and cannot be invited to other servers. To use all commands, simply <span data-i18n="faq.a1join">join our Discord server</span> and start typing.',
    'faq.a1join': 'join our Discord server',
    'faq.q2': 'How do I use the commands?',
    'faq.a2': 'Admin and Moderation commands are slash-only (e.g. /ban). All other commands use the <code class="mono">A!</code> prefix (e.g. A!daily, A!work).',
    'faq.q3': 'How does the economy work?',
    'faq.a3': 'Use <code class="mono">A!daily</code> for the daily reward, <code class="mono">A!work</code> to work, <code class="mono">A!market</code> to buy from the shop, and <code class="mono">A!gamble</code> for casino games.',
    'faq.q4': 'Does the bot run 24/7?',
    'faq.a4': 'Yes — it runs on a Supabase-backed heartbeat. You can see its real-time Online/Offline status right here in the “Bot Status” section.',
    'faq.q5': 'Is my data saved?',
    'faq.a5': 'Yes — everything (users, economy, marriage, levels) is safely stored in 57 Supabase (PostgreSQL) tables. Your coins and level never disappear, even if the bot restarts.',
    'faq.q6': 'When will Premium launch?',
    'faq.a6': 'The Premium system is under development and will be announced via Discord. Until then, all core commands are <strong>FREE</strong>.',
    'faq.q7': 'Where can I report a bug?',
    'faq.a7': 'Tell us directly via Discord or open an issue on <a href="https://github.com/ZERO1zx1/gurtendev/issues" target="_blank" rel="noopener">GitHub Issues</a>.',
    'modal.howto': '👆 Click a command card to see its details',
    'modal.args': 'Arguments',
    'modal.example': 'Example',
    'modal.close': 'Close',
    'modal.required': 'required',
    'modal.optional': 'optional',
    'cmd.daily.desc': 'Claim your daily coin reward',
    'cmd.work.desc': 'Work to earn coins',
    'cmd.balance.desc': 'View your coin balance',
    'cmd.pay.desc': 'Send coins to another user',
    'cmd.rob.desc': 'Attempt to rob another user (risky!)',
    'cmd.workphrase.desc': 'Customize your work phrases',
    'cmd.addmoney.desc': 'Add coins to a user (admin)',
    'cmd.removemoney.desc': 'Remove coins from a user (admin)',
    'cmd.market.desc': 'Browse the cafe shop items',
    'cmd.dine.desc': 'Eat a meal at the cafe (spend coins)',
    'cmd.cafe.desc': 'View cafe menu and info',
    'cmd.rank.desc': 'View your rank and XP',
    'cmd.grank.desc': 'View the global XP leaderboard',
    'cmd.leaderboard.desc': 'Show the top users by rank',
    'cmd.serveractivity.desc': 'View server activity stats',
    'cmd.addxp.desc': 'Add XP to a user (admin)',
    'cmd.removexp.desc': 'Remove XP from a user (admin)',
    'cmd.leveling_setup.desc': 'Configure leveling settings (admin)',
    'cmd.invites.desc': 'View your invites and invite XP',
    'cmd.inviter.desc': 'See who invited you',
    'cmd.propose.desc': 'Propose marriage to someone',
    'cmd.marry.desc': 'Marry your partner',
    'cmd.divorce.desc': 'End your marriage',
    'cmd.spouse.desc': 'View your spouse info',
    'cmd.love.desc': 'Check your love level',
    'cmd.gift.desc': 'Send a gift to your spouse',
    'cmd.adopt.desc': 'Adopt a child',
    'cmd.disown.desc': 'Disown a child',
    'cmd.children.desc': 'List your children',
    'cmd.makeparent.desc': 'Assign parents to a child (admin)',
    'cmd.familytree.desc': 'View your family tree',
    'cmd.tree.desc': 'Family tree summary',
    'cmd.fulltree.desc': 'Full family tree view',
    'cmd.marriage_setup.desc': 'Marriage system settings (admin)',
    'cmd.marriagepro.desc': 'Your marriage profile',
    'cmd.confess.desc': 'Anonymous confession in the channel',
    'cmd.gamble.desc': 'Gambling with buttons (high/low)',
    'cmd.coinflip.desc': 'Flip a coin (heads/tails)',
    'cmd.slots.desc': 'Play the slot machine',
    'cmd.roulette.desc': 'Play roulette',
    'cmd.dice.desc': 'Roll dice against the bot',
    'cmd.rps.desc': 'Rock-paper-scissors vs the bot',
    'cmd.mines.desc': 'Minesweeper-style mine game',
    'cmd.counting.desc': 'Counting challenge (1,2,3...) with members',
    'cmd.count_stats_server.desc': 'Server counting stats',
    'cmd.pvp.desc': 'Duel another player',
    'cmd.trade.desc': 'Trade items with another user',
    'cmd.marketplace.desc': 'Open the item marketplace',
    'cmd.mp.desc': 'Marketplace shortcut',
    'cmd.stock.desc': 'View stock market info',
    'cmd.graph.desc': 'View stock price chart',
    'cmd.buy.desc': 'Buy stocks',
    'cmd.sell.desc': 'Sell your stocks',
    'cmd.stock_ticker.desc': 'List available tickers',
    'cmd.stock_leaderboard.desc': 'Stock profit leaderboard',
    'cmd.mafia.desc': 'Join a Mafia game round',
    'cmd.mafiacreate.desc': 'Create a Mafia game (admin)',
    'cmd.mafiastart.desc': 'Start the Mafia game (admin)',
    'cmd.mafiaend.desc': 'End the Mafia game (admin)',
    'cmd.giveaway.desc': 'Start a giveaway',
    'cmd.reroll.desc': 'Reroll the giveaway',
    'cmd.end.desc': 'End a giveaway early',
    'cmd.ban.desc': 'Ban a user from the server',
    'cmd.unban.desc': 'Unban a user',
    'cmd.kick.desc': 'Kick a user from the server',
    'cmd.timeout.desc': 'Timeout a user temporarily',
    'cmd.warn.desc': 'Issue a warning (admin)',
    'cmd.warnings.desc': 'View a user',
    'cmd.clear.desc': 'Bulk-delete messages',
    'cmd.lock.desc': 'Lock a channel (admin)',
    'cmd.unlock.desc': 'Unlock a channel (admin)',
    'cmd.template_create.desc': 'Create an embed template (admin)',
    'cmd.template_edit.desc': 'Edit a template (admin)',
    'cmd.template_delete.desc': 'Delete a template (admin)',
    'cmd.template_list.desc': 'List saved templates',
    'cmd.template_preview.desc': 'Preview a template (admin)',
    'cmd.help.desc': 'List all commands by category',
    'cmd.invite.desc': 'Get the bot invite link',
    'cmd.avatar.desc': 'View a user',
    'cmd.boost.desc': 'Server boost info',
    'cmd.partners.desc': 'Partner server list',
    'cmd.entries.desc': 'Giveaway entries list',
    'cmd.list.desc': 'View various lists',
    'cmd.relationship.desc': 'Relationship between two users',
    'cmd.placeholders.desc': 'Placeholder info',
    'cmd.codes.desc': 'Redeem a promo code',
    'cmd.autoaccept.desc': 'Toggle auto-accept flows',
    'cmd.cancel.desc': 'Cancel any active flow',
    'about.p1': '𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹 is a full-featured Mongolian Discord bot and the official engine of the AETHER gaming community.',
    'about.p2': 'Economy, leveling, marriage, shop, casino, mafia, moderation — 29 cogs and 118 commands in one system. Supabase (PostgreSQL) backend keeps it running 24/7.',
    'about.q': 'Who we are',
    'about.tag': 'ABOUT US',
    'community.active': 'Active Community',
    'community.active_d': 'Active members, 24/7 chat, make friends with us.',
    'community.event': 'Event & Giveaway',
    'community.event_d': 'Regular giveaways, gaming tournaments and prizes.',
    'community.gaming': 'Gaming',
    'community.gaming_d': 'Roblox + other game lobbies, duo finder, tournaments.',
    'community.intro': 'AETHER is an active Mongolian gaming community. Roblox players and friends gather here to play, chat and compete.',
    'community.punish_note': 'Breaking a rule triggers the punishment ladder below. Repeat offenses make it harsher.',
    'community.staff_intro': 'The team actively managing the AETHER server. Reach out to them if you need help.',
    'community.topup': 'Top-Up & Currency',
    'community.topup_d': 'Game currency and top-up help at friendly prices.',
    'faq.tag': 'FAQ',
    'feat.cas': 'Casino & Games',
    'feat.cas_d': 'Coinflip, slots, roulette, mines, pvp, counting, cards.',
    'feat.econ': 'Economy',
    'feat.econ_d': 'daily, work, gamble — a full money system. Work hard, get rich.',
    'feat.fun': 'Fun & More',
    'feat.fun_d': 'Cafe, quests, confessions, giveaways, temp voice, avatar logger.',
    'feat.lvl': 'Leveling',
    'feat.lvl_d': 'XP system, leaderboard, voice XP. More activity = more levels.',
    'feat.maf': 'Mafia',
    'feat.maf_d': 'Eastern mafia game — sleep, check, win.',
    'feat.mar': 'Marriage & Family',
    'feat.mar_d': 'From proposing to a full family tree. Marry the one you love.',
    'feat.mod': 'Moderation',
    'feat.mod_d': 'Ban, kick, warn, timeout, purge, mod-log. A clean server.',
    'feat.shop': 'Shop & Stocks',
    'feat.shop_d': 'Market, marketplace and a live stock system. Buy and sell.',
    'rule.r1': 'Respect everyone. Insults, discrimination and harassment are not tolerated.',
    'rule.r2': 'Do not post or share other people\'s private information (ID, phone, address).',
    'rule.r3': 'Dangerous links, scams, viruses and any attempt to deceive others are banned.',
    'rule.r4': 'NSFW and inappropriate content is not allowed on the server.',
    'rule.r5': 'No spam, flooding or disrupting other members\' chat.',
    'rule.r6': 'Roleplay belongs in RP channels only — do not jump into others\' roleplay.',
    'rule.r7': 'Use each channel for its purpose and post in the right channel.',
    'rule.r8': 'Respect staff decisions. Report unfair rulings via Discord.',
    'staff.aferrz': 'Helper',
    'staff.aiken': 'Helper',
    'staff.aiku': 'Helper',
    'staff.bakuna': 'Moderator',
    'staff.irla': 'Moderator',
    'staff.vortex': 'Founder / Developer',
    'status.refresh': '24/7 online — real-time heartbeat',
    'status.tag': 'BOT STATUS',
    'status.title1': 'Bot',
    'status.title2': 'status',
    'invite.title1': 'Let\u2019s bring your',
    'invite.title2': 'server to life',
    'invite.sub': 'One click, done — start today.',
    'invite.btn': 'Join server',
    'footer.brand': 'Mongolian Discord bot',
    'footer.faq': 'FAQ',
    'footer.copy': '© 2026 𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹. All rights reserved.',
    'heartbeat.checking': 'Checking real bot status…',
    'ui.scrolltop': 'Scroll to top',
    'heartbeat.now': 'Last online: just now',
    'heartbeat.ago': 'Last online: {since} ({time})',
    'heartbeat.off': 'Bot is currently offline',
    'heartbeat.up': 'Bot started {since} · last ping: {time}',

    'nav.changelog': 'Changelog',
    'cl.tag': 'CHANGELOG',
    'cl.title1': 'Version',
    'cl.title2': 'history',
    'cl.new': 'NEW',
    'cl.fix': 'FIXED',
    'cl.v24_t': 'v2.4 — Reaction roles &amp; Auto-moderation',
    'cl.v24_d': 'Emoji-reaction role system (`/rr setup`), anti-spam, anti-link, anti-raid protection (`/automod`), rotating presence with language-aware member count.',
    'cl.v23_t': 'Full dark/light theme',
    'cl.v23_d': 'Website now has complete dark/light modes, new logo and favicon set, OG banner. i18n 217 keys (MN = EN).',
    'cl.v22_t': 'Mobile fully polished',
    'cl.v22_d': 'Command cards, badges, and search input look clean on 390px phones. All 118 commands have MN/EN descriptions.',
    'cl.v21_t': 'Website launch',
    'cl.v21_d': '3D animated hero, command catalog (search, filter, modal), live Online/Offline status, staff and rules section.',
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
    /* Placeholder-уудыг мөн солих */
    document.querySelectorAll('[data-i18n-ph]').forEach(el => {
      const v = dict[el.getAttribute('data-i18n-ph')];
      if (v !== undefined) el.setAttribute('placeholder', v);
    });
    /* aria-label атрибутуудыг хэл солих (data-i18n-attr) */
    document.querySelectorAll('[data-i18n-attr]').forEach(el => {
      const v = dict[el.getAttribute('data-i18n-attr')];
      if (v !== undefined) el.setAttribute('aria-label', v);
    });
    document.querySelectorAll('.lang-btn').forEach(b => {
      b.classList.toggle('active', b.getAttribute('data-lang') === lang);
    });
    try { localStorage.setItem('aether-lang', lang); } catch {}
    // Heartbeat статусын текстүүдийг одоогийн төлөвөөр дахин зурна
    if (window.__aetherLang === 'en' || window.__aetherLang === 'mn') {
      // status нь аль хэдийн тогтсон байвал last-seen-ийг зөвхөн шалгах текстээр
      const ls = document.getElementById('last-seen');
      if (ls && !ls.textContent.includes('…') && ls.dataset.ok !== '1') {
        ls.textContent = dict['heartbeat.checking'];
      }
    }
    window.__aetherLang = lang;
    /* Нээлттэй modal байвал хэл солихын дагуу дахин render */
    const modal = document.getElementById('cmd-modal');
    if (modal && modal.classList.contains('open') && modal.__cmdName) {
      const c = window.COMMAND_LIST?.find(x => x.name === modal.__cmdName);
      if (c) openModal(c);
    }
    /* Командын карт болон категорын шошгыг дахин зурна */
    if (typeof window.__aetherRender === 'function') window.__aetherRender();
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

/* ---------------- Command detail modal (click a card) ---------------- */
(() => {
  const openModal = (c) => {
    let modal = document.getElementById('cmd-modal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'cmd-modal';
      modal.className = 'cmd-modal';
      modal.innerHTML = `
        <div class="cmd-modal-backdrop"></div>
        <div class="cmd-modal-box" role="dialog" aria-modal="true">
          <button class="cmd-modal-close" aria-label="Close">✕</button>
          <div class="cmd-modal-head"></div>
          <div class="cmd-modal-body"></div>
        </div>`;
      document.body.appendChild(modal);
      modal.querySelector('.cmd-modal-close').addEventListener('click', closeModal);
      modal.querySelector('.cmd-modal-backdrop').addEventListener('click', closeModal);
    }
    const dict = AETHER_I18N[window.__aetherLang || 'mn'] || AETHER_I18N.mn;
    const m = window.CAT_META?.[c.cat] || { label: c.cat, color: '#89B4FA', icon: '🔧' };
    const catLabel = (window.__aetherLang === 'en' && m.labelEN) || m.label;
    const prefix = c.type === 'slash' ? '/' : 'A!';
    const args = Array.isArray(c.args) && c.args.length ? c.args : null;
    modal.querySelector('.cmd-modal-head').innerHTML = `
      <span class="cmd-modal-icon">${c.icon}</span>
      <div>
        <div class="cmd-modal-name">${prefix}${c.name}</div>
        <div class="cmd-modal-cat">${m.icon} ${catLabel} · <span class="cmd-type ${c.type}">${c.type === 'slash' ? 'SLASH' : 'TEXT'}</span></div>
      </div>`;
    const desc = (window.__aetherLang === 'en' && (dict[`cmd.${c.name}.desc`])) || c.desc;
    modal.querySelector('.cmd-modal-body').innerHTML = `
      <p class="cmd-modal-desc">${desc}</p>
      ${args ? `<div class="cmd-modal-row">
        <div class="cmd-modal-label">${dict['modal.args']}</div>
        <div class="cmd-modal-args">${args.map(a => `<span class="cmd-arg ${a.req ? 'req' : 'opt'}">${a.key} <small>${dict[a.req ? 'modal.required' : 'modal.optional']}</small></span>`).join('')}</div>
      </div>` : ''}
      ${c.example ? `<div class="cmd-modal-row">
        <div class="cmd-modal-label">${dict['modal.example']}</div>
        <div class="cmd-modal-example"><code>${c.example}</code><button class="cmd-copy-btn" type="button">📋</button></div>
      </div>` : ''}`;
    const copyBtn = modal.querySelector('.cmd-copy-btn');
    if (copyBtn) {
      copyBtn.addEventListener('click', () => {
        navigator.clipboard?.writeText(c.example).then(() => {
          copyBtn.textContent = '✅';
          setTimeout(() => { copyBtn.textContent = '📋'; }, 1500);
        });
      });
    }
    modal.__cmdName = c.name;
    modal.classList.add('open');
    document.body.style.overflow = 'hidden';
  };
  const closeModal = () => {
    const modal = document.getElementById('cmd-modal');
    if (modal) {
      modal.classList.remove('open');
      document.body.style.overflow = '';
    }
  };
  window.closeCmdModal = closeModal;
  document.addEventListener('click', (e) => {
    const card = e.target.closest('.cmd-card');
    if (!card) return;
    /* Хэрэв карт доторх link/badge дээр дарсан бол modal нээхгүй */
    if (e.target.closest('a, .cmd-type')) return;
    /* Нэмэгдсэн args/example өгөгдөлтэй командыг тохируулна */
    const nameMatch = card.querySelector('.cmd-name')?.textContent?.replace(/^\/|^A!/, '');
    const c = window.COMMAND_LIST?.find(x => x.name === nameMatch);
    if (c) openModal(c);
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });
})();

/* ============================================================
   JS Error capture — алдааг localStorage-д хадгалж,
   footer-д badge харагдаж, дэлгэрэнгүй modal-оор харна
   ============================================================ */
(() => {
  'use strict';
  const KEY = 'aether_js_errors';
  const MAX = 50;

  const loadErrors = () => {
    try { return JSON.parse(localStorage.getItem(KEY)) || []; } catch { return []; }
  };
  const saveErrors = (arr) => {
    try { localStorage.setItem(KEY, JSON.stringify(arr.slice(-MAX))); } catch { /* quota */ }
  };

  const pushError = (type, msg, src, line) => {
    const arr = loadErrors();
    arr.push({ t: Date.now(), type, msg: String(msg), src: src || '', line: line || 0 });
    saveErrors(arr);
    renderBadge(arr.length);
  };

  window.addEventListener('error', (e) => {
    if (e.filename && /vortex\.github\.io|localhost/.test(e.filename)) {
      pushError('error', e.message, e.filename, e.lineno);
    }
  });
  window.addEventListener('unhandledrejection', (e) => {
    pushError('promise', String(e.reason), '', 0);
  });

  const renderBadge = (n) => {
    const badge = document.getElementById('err-badge');
    if (!badge) return;
    badge.textContent = `⚠ ${n}`;
    badge.classList.toggle('show', n > 0);
  };

  document.addEventListener('DOMContentLoaded', () => {
    const footer = document.querySelector('.footer-links') || document.querySelector('.footer');
    if (!footer) return;
    const badge = document.createElement('button');
    badge.id = 'err-badge';
    badge.type = 'button';
    badge.setAttribute('aria-label', 'Site errors');
    footer.appendChild(badge);
    renderBadge(loadErrors().length);
    badge.addEventListener('click', () => openErrModal());
  });

  const openErrModal = () => {
    let modal = document.getElementById('err-modal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'err-modal';
      modal.className = 'err-modal';
      modal.innerHTML = `
        <div class="err-modal-backdrop"></div>
        <div class="err-modal-box">
          <div class="err-modal-head">
            <span>🛠 Site error log</span>
            <button type="button" class="err-modal-close">✕</button>
          </div>
          <div class="err-modal-body"></div>
          <div class="err-modal-foot">
            <button type="button" class="err-clear-btn">🧹 Clear log</button>
          </div>
        </div>`;
      document.body.appendChild(modal);
      modal.querySelector('.err-modal-close').addEventListener('click', closeErrModal);
      modal.querySelector('.err-modal-backdrop').addEventListener('click', closeErrModal);
      modal.querySelector('.err-clear-btn').addEventListener('click', () => {
        try { localStorage.removeItem(KEY); } catch { /* */ }
        closeErrModal();
        renderBadge(0);
      });
    }
    const arr = loadErrors();
    modal.querySelector('.err-modal-body').innerHTML = arr.length
      ? arr.slice().reverse().map(e => `
        <div class="err-entry">
          <span class="err-type">${e.type === 'promise' ? 'PROMISE' : 'ERR'}</span>
          <span class="err-time">${new Date(e.t).toLocaleString()}</span>
          <span class="err-msg">${e.msg.replace(/</g, '&lt;')}</span>
          ${e.src ? `<span class="err-src">${e.src}:${e.line}</span>` : ''}
        </div>`).join('')
      : '<div class="err-empty">✅ No errors recorded.</div>';
    modal.classList.add('open');
    document.body.style.overflow = 'hidden';
  };
  const closeErrModal = () => {
    const modal = document.getElementById('err-modal');
    if (!modal) return;
    modal.classList.remove('open');
    document.body.style.overflow = '';
  };
  window.closeErrModal = closeErrModal;
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeErrModal(); });
})();
