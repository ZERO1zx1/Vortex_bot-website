"""Exercise the site's interactive behaviour in a real browser.

Covers the flows the unit-level checks cannot: language switching, theme
toggle, command search/filter/URL sync, the command modal (focus trap +
Escape), and the mobile navigation menu.

Usage:
  python website/tools/interaction_check.py [--url http://localhost:4173]
"""
import argparse
import sys

from playwright.sync_api import sync_playwright, expect

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

results = []


def check(name, condition, detail=''):
    results.append((name, bool(condition), detail))
    print(f"{'PASS' if condition else 'FAIL'}  {name}" + (f'  — {detail}' if detail else ''))


def run(page, results):
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(page.url or 'about:blank', wait_until='load')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://localhost:4173')
    args = parser.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, args=['--no-sandbox'])
        ctx = browser.new_context(viewport={'width': 1440, 'height': 900})
        page = ctx.new_page()
        page_errors = []
        page.on('pageerror', lambda e: page_errors.append(str(e)))
        page.goto(args.url, wait_until='load')
        page.wait_for_timeout(1500)

        # ---------- language switcher ----------
        before = page.locator('.nav-links a').first.inner_text()
        page.click('.lang-switch-bar .lang-btn[data-lang="en"]')
        page.wait_for_timeout(400)
        after = page.locator('.nav-links a').first.inner_text()
        check('language switch changes nav labels', before != after, f'{before!r} -> {after!r}')
        check('html[lang] updates', page.get_attribute('html', 'lang') == 'en',
              page.get_attribute('html', 'lang'))
        check('EN button pressed', page.get_attribute(
            '.lang-switch-bar .lang-btn[data-lang="en"]', 'aria-pressed') == 'true')

        # A staff bio must survive the switch (it used to be clobbered by the
        # role-name dictionary entries).
        bio = page.locator('.staff-desc p').first.inner_text()
        check('staff bio not replaced by role name',
              'Founder' not in bio and 'Moderator' not in bio, bio[:60] + '...')

        # Persistence across reload
        page.reload(wait_until='load')
        page.wait_for_timeout(1200)
        check('language persists across reload',
              page.get_attribute('html', 'lang') == 'en')
        check('command descriptions translated',
              page.locator('.cmd-card .cmd-desc').first.inner_text() != '')

        # Back to Mongolian
        page.click('.lang-switch-bar .lang-btn[data-lang="mn"]')
        page.wait_for_timeout(300)

        # ---------- theme toggle ----------
        theme_before = page.get_attribute('html', 'data-theme')
        page.click('#theme-toggle')
        page.wait_for_timeout(400)
        theme_after = page.get_attribute('html', 'data-theme')
        check('theme toggles', theme_before != theme_after, f'{theme_before} -> {theme_after}')
        page.click('#theme-toggle')
        page.wait_for_timeout(300)

        # ---------- command search ----------
        total = page.locator('.cmd-card').count()
        check('all commands rendered', total == 187, f'{total} cards')
        check('no horizontal overflow',
              page.evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth'))

        page.fill('#cmd-search', 'daily')
        page.wait_for_timeout(600)
        found = page.locator('.cmd-card').count()
        check('search narrows results', 0 < found < total, f'{found} of {total}')
        check('search reflected in URL', 'q=daily' in page.url, page.url.split('#')[-1])
        check('result count announced', page.locator('.cmd-result-count').inner_text().strip() != '')

        page.fill('#cmd-search', 'zzzznotacommand')
        page.wait_for_timeout(600)
        check('empty state shown', page.locator('.cmd-empty').count() == 1)
        check('no cards on empty search', page.locator('.cmd-card').count() == 0)

        page.click('.cmd-reset')
        page.wait_for_timeout(600)
        check('reset clears search', page.locator('.cmd-card').count() == total)

        # ---------- category filter ----------
        page.click('.filter[data-cat="Games"]')
        page.wait_for_timeout(500)
        panels = page.locator('.cmd-panel').count()
        check('filter shows one panel', panels == 1, f'{panels} panel(s)')
        check('filter URL synced', 'cat=Games' in page.url, page.url.split('#')[-1])
        check('filter aria-pressed set', page.get_attribute(
            '.filter[data-cat="Games"]', 'aria-pressed') == 'true')
        page.click('.filter[data-cat="all"]')
        page.wait_for_timeout(500)
        check('all filter restores panels', page.locator('.cmd-panel').count() == 7)

        # ---------- command modal ----------
        page.locator('.cmd-card').first.click()
        page.wait_for_timeout(500)
        modal = page.locator('.cmd-modal-box')
        check('modal opens', modal.count() == 1 and modal.is_visible())
        check('modal is a dialog', modal.get_attribute('role') == 'dialog')
        check('modal has accessible name', bool(modal.get_attribute('aria-labelledby')))
        focus_in_modal = page.evaluate(
            "() => document.getElementById('cmd-modal')?.contains(document.activeElement)")
        check('focus moves into modal', focus_in_modal)

        page.keyboard.press('Escape')
        page.wait_for_timeout(400)
        check('Escape closes modal', page.locator('.cmd-modal-box').count() == 0)
        check('body scroll restored',
              page.evaluate("() => document.body.style.overflow") == '')

        # ---------- deep link ----------
        page.goto(args.url + '#commands?q=balance', wait_until='load')
        page.wait_for_timeout(1600)
        check('deep link prefills search',
              page.input_value('#cmd-search') == 'balance', page.input_value('#cmd-search'))
        check('deep link filters results', 0 < page.locator('.cmd-card').count() < 187)

        ctx.close()

        # ---------- mobile nav ----------
        mctx = browser.new_context(viewport={'width': 390, 'height': 844})
        mpage = mctx.new_page()
        merr = []
        mpage.on('pageerror', lambda e: merr.append(str(e)))
        mpage.goto(args.url, wait_until='load')
        mpage.wait_for_timeout(1500)

        burger = mpage.locator('#nav-burger')
        check('burger visible on mobile', burger.is_visible())
        check('burger starts collapsed', mpage.get_attribute('#nav-burger', 'aria-expanded') == 'false')
        check('nav links hidden initially', not mpage.locator('#primary-nav a').first.is_visible())

        burger.click()
        mpage.wait_for_timeout(400)
        check('menu opens', mpage.get_attribute('#nav-burger', 'aria-expanded') == 'true')
        check('nav links visible when open', mpage.locator('#primary-nav a').first.is_visible())
        check('language switcher reachable in menu',
              mpage.locator('.nav-links-footer .lang-btn').first.is_visible())

        mpage.keyboard.press('Escape')
        mpage.wait_for_timeout(400)
        check('Escape closes menu', mpage.get_attribute('#nav-burger', 'aria-expanded') == 'false')

        burger.click()
        mpage.wait_for_timeout(300)
        premium_link = mpage.locator('#primary-nav a[href="#premium"]')
        premium_link.wait_for(state='visible', timeout=10000)
        premium_link.click()
        mpage.wait_for_timeout(1200)
        check('menu closes on link click',
              mpage.get_attribute('#nav-burger', 'aria-expanded') == 'false')
        check('nav scrolled to section',
              mpage.evaluate("() => window.scrollY") > 500,
              f'scrollY={mpage.evaluate("() => window.scrollY")}')

        mctx.close()
        browser.close()

    check('no runtime errors (desktop)', not page_errors, '; '.join(page_errors[:3]))
    check('no runtime errors (mobile)', not merr, '; '.join(merr[:3]))

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())