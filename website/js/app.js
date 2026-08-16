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
          <div class="panel-count">${list.length} команд</div>
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
        <span class="cmd-name">/${c.name}</span>
        <span class="cmd-desc">${c.desc}</span>
      </div>
      <span class="cmd-cat">${m.icon} ${m.label}</span>
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
    if (a.id === 'invite-btn') a.href = INVITE_URL;
    if (a.id === 'invite-btn') a.setAttribute('target', '_blank');
    if (a.id === 'invite-btn') a.setAttribute('rel', 'noopener');
  });
})();

/* ---------------- Bot heartbeat: жинхэнэ Online / Offline ---------------- */
(() => {
  const cfg = window.AETHER_CONFIG || {};
  const HEARTBEAT_URL = cfg.HEARTBEAT_URL || '';
  const TIMEOUT_MS = cfg.HEARTBEAT_TIMEOUT_MS || 6000;
  const POLL_MS = cfg.HEARTBEAT_POLL_MS || 60000;

  const dot = document.getElementById('status-dot');
  const text = document.getElementById('online-text');
  if (!dot || !text) return;

  const setOnline = () => {
    dot.className = 'status-dot online';
    text.textContent = 'Online';
  };
  const setOffline = () => {
    dot.className = 'status-dot offline';
    text.textContent = 'Offline';
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
      const res = await fetch(HEARTBEAT_URL, { signal: ctrl.signal, cache: 'no-store' });
      clearTimeout(t);
      if (res.ok) setOnline(); else setOffline();
    } catch {
      setOffline();
    }
  };
  check();
  setInterval(check, POLL_MS);
})();
