"""Render the built site and report console errors, layout overflow and a11y basics.

Usage:
  python website/tools/render_check.py [--url http://127.0.0.1:4173] [--out DIR]
"""
import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

VIEWPORTS = {
    'desktop': (1440, 900),
    'mobile': (390, 844),
}

PROBE = """
() => {
  const de = document.documentElement;
  const vw = de.clientWidth;

  // Only report elements that genuinely escape the viewport. Decorative
  // glows are clipped by their own container and are not a layout fault.
  const escaping = [...document.querySelectorAll('body *')]
    .filter((el) => {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return false;
      const cs = getComputedStyle(el);
      if (cs.position === 'fixed' && r.width <= 1) return false;
      return r.right > vw + 2 || r.left < -2;
    })
    .slice(0, 12)
    .map((el) => {
      const r = el.getBoundingClientRect();
      return `${el.tagName.toLowerCase()}.${(el.className?.baseVal ?? el.className ?? '')
        .toString().trim().split(/\\s+/).slice(0, 2).join('.')} [${Math.round(r.left)}..${Math.round(r.right)}]`;
    });

  const imgs = [...document.images]
    .filter((i) => !i.complete || i.naturalWidth === 0)
    .map((i) => i.getAttribute('src'));

  const nav = document.querySelector('.navbar');
  const burger = document.querySelector('.nav-burger');

  return {
    title: document.title,
    lang: document.documentElement.lang,
    theme: document.documentElement.getAttribute('data-theme'),
    scrollW: de.scrollWidth,
    clientW: vw,
    horizontalScroll: de.scrollWidth > vw,
    docHeight: de.scrollHeight,
    sections: [...document.querySelectorAll('section[id]')].map((s) => s.id),
    navLinks: [...document.querySelectorAll('.nav-links a')].map((a) => a.getAttribute('href')),
    langBtns: [...document.querySelectorAll('.lang-btn')].map((b) => b.textContent.trim()),
    langSwitchVisible: [...document.querySelectorAll('.lang-switch')]
      .filter((e) => e.getBoundingClientRect().width > 0)
      .map((e) => e.className),
    burgerRect: burger && burger.getBoundingClientRect().width
      ? [Math.round(burger.getBoundingClientRect().left), Math.round(burger.getBoundingClientRect().right)]
      : null,
    navbarRect: nav ? [Math.round(nav.getBoundingClientRect().left), Math.round(nav.getBoundingClientRect().right)] : null,
    cmdCards: document.querySelectorAll('.cmd-card').length,
    cmdPanels: document.querySelectorAll('.cmd-panel').length,
    searchHasLabel: !!document.querySelector('label[for="cmd-search"]'),
    filterPressed: document.querySelector('.filter[aria-pressed="true"]')?.textContent.trim(),
    staffBios: [...document.querySelectorAll('.staff-desc p')].map((p) => p.textContent.slice(0, 40)),
    escaping,
    unloadedImages: imgs,
    focusables: document.querySelectorAll('a[href],button:not([disabled]),input,summary,[tabindex="0"]').length,
  };
}
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:4173')
    parser.add_argument('--out', default=str(Path.home() / 'AppData/Local/Temp/opencode/aether-shots'))
    parser.add_argument('--shots', action='store_true')
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    report = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, args=['--no-sandbox'])

        for name, (w, h) in VIEWPORTS.items():
            ctx = browser.new_context(viewport={'width': w, 'height': h},
                                      device_scale_factor=1)
            page = ctx.new_page()
            errors, console_errors, failed = [], [], []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('console', lambda m: console_errors.append(m.text) if m.type == 'error' else None)
            page.on('requestfailed', lambda r: failed.append(f'{r.url} :: {r.failure}'))

            page.goto(args.url, wait_until='networkidle')
            page.wait_for_timeout(1500)

            # Walk the page so lazy-loaded images and reveal animations
            # actually run, then return to the top before probing.
            # `behavior: instant` is required: the site sets
            # `scroll-behavior: smooth`, which would animate each hop and
            # never actually reach the bottom within the delay.
            page.evaluate(
                """async () => {
                    const de = document.documentElement;
                    const step = window.innerHeight * 0.75;
                    for (let y = 0; y < de.scrollHeight; y += step) {
                        window.scrollTo({ top: y, behavior: 'instant' });
                        await new Promise(r => setTimeout(r, 120));
                    }
                    window.scrollTo({ top: de.scrollHeight, behavior: 'instant' });
                    await new Promise(r => setTimeout(r, 600));
                    window.scrollTo({ top: 0, behavior: 'instant' });
                    await new Promise(r => setTimeout(r, 400));
                }"""
            )
            page.wait_for_timeout(1500)

            report[name] = page.evaluate(PROBE)
            report[name]['pageErrors'] = errors
            report[name]['consoleErrors'] = console_errors
            report[name]['failedRequests'] = failed[:8]

            if args.shots:
                page.screenshot(path=str(out / f'{name}-top.png'))
                for sec in ('commands', 'community', 'premium'):
                    page.evaluate(f"document.getElementById('{sec}')?.scrollIntoView()")
                    page.wait_for_timeout(700)
                    page.screenshot(path=str(out / f'{name}-{sec}.png'))

            ctx.close()

        browser.close()

    print(json.dumps(report, indent=2, ensure_ascii=False))
    bad = any(v.get('pageErrors') for v in report.values())
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())