# Aether — Бүрэн код шалгалтын тайлан (2026-09-19)

## Шалгалтын хүрээ

| Давхарга | Файлууд | Шалгасан арга |
|---|---|---|
| Discord бот (`src/`) | 36 cog + core/database/utils | `compileall`, `pyflakes`, pytest (123), offline cog probe |
| Backend API (`backend/`) | FastAPI (3 файл) | Syntax + логикийн уншилт |
| Вэб (`website/`) | index.html, app.js, commands.js, config.js, style.css | `node --check`, JSON parse, каталог diff |
| Tools/Tests | 15+ скрипт | Шууд ажиллуулалт |

## Илэрсэн бөгөөд зассан алдаанууд (6 файл)

### 1. `src/cogs/tempvoice.py:250` — `TypeError: 'NoneType' object is not iterable`
`fetch_safe("tempvoice_setup_msg")` нь хүснэгт дутуу/эрхгүй (PGRST205/404/42501) үед
`None` буцаадаг ч `for row in rows:` шууд давталт хийдэг байсан.
**Үр дагавар:** cog_load дэх background task унаж, persistent view-үүд сэргэдэггүй.
**Засвар:** `for row in rows or []:`

### 2. `src/cogs/roles.py:347` — ижил `TypeError` (`temprole_loop`)
`fetch_safe("temproles")` → `None` буцаахад `tasks.loop` бүрэн унаж дахин ажилладаггүй
(discord.py loop нэг exception дээр зогсдог). Түр үүргүүд хэзээ ч цуцлагдахгүй байх эрсдэлтэй байсан.
**Засвар:** `for r in (rows or [])`

### 3. `src/cogs/casino.py:120` — үхэж хоцорсон `status` хувьсагч (Blackjack UI баг)
Split хийсэн гаруудыг харуулахдаа `status` тооцогдож байгаа ч embed-д оруулаагүй —
"✋ Гар 2: 18" гэж л гардаг, тоглож буй/үр дүнтэйгүйгээр ижил харагдана.
**Засвар:** `f"✋ Гар {i+1} ({status}): ..."`

### 4. `tools/diff_catalog_check.py:53` — `cogs.{name}` → `src.cogs.{name}`
`src/` refactor-ын дараа зам хуучирч бүх 36 cog "LOAD FAIL" болж, дүгнэлт
бүрэн буруу гардаг байсан ("205 documented-but-unregistered" хуурамч дохио).
**Засвар:** зөв package зам. Одоо: 205/205 бүртгэл COMMAND_INFO-той таарч байна, зөрүү 0.

### 5. `tools/probe_load_all_cogs.py` — `StubDB.fetch_safe` жинхэнэ семантик биш
Stub `fetch_safe` үргэлж `None` буцаадаг байсан → жинхэнэ `fetch_safe` (multi = `[]`)-ийн
`or []` дутагдлыг барихгүй өнгөрүүлдэг байсан (1, 2-р багийн регресс хамгаалалт).
**Засвар:** `single=True → None`, multi → `[]` гэх жинхэнэ гэрээг тусгасан.

### 6. `tools/test_help_embeds.py` — 2 засвар
- Харьцангуй зам `src/cogs/help.py` (cwd-ээс хамаарч FileNotFoundError өгдөг) → absolute зам.
- Хуучирсан `HelpView.build_embed()` → одоогийн `build_category_embed()`.
Одоо: **15/15 ангилалын embed + 205/205 командын embed Discord-ын хязгаарлалтанд багтаж байна.**

## Баталгаажуулалт (засварын дараа)

- `pytest tests` — **123/123 PASS**
- 36/36 cog offline load — **алдаагүй, "Task exception was never retrieved" арилсан**
- Help-каталог ↔ бүртгэгдсэн команд: **205/205 таарна**, undocumented = зөвхөн alias (70, норм)
- `website/js/commands.js` ↔ `backend/data/commands.json`: **205/205 нийцтэй**
- Бүх `.json` parse OK, `node --check` 3 JS файл OK

## Нэмэлт засвар (үнэлгээний дараа хийгдсэн)

### 7. Бүх `src/` дэх bare `except:` → `except Exception:` (103 ширхэг, 21 файл)
Bare `except:` нь `KeyboardInterrupt`/`SystemExit`-ийг ч залгилж, Ctrl+C болон
graceful shutdown-ыг эвддэг байв. Одоо зөвхөн ердийн Exception барина —
"үл тоомсорлох" UX-ийн зорилго хэвээр, гэхдээ зогсоолт ажиллана.
Шалгасан: `pytest 123/123 PASS`, 36/36 cog load OK, compileall/pyflakes цэвэр.

## Анхаарах (засаагүй — загварын сонголт)

- `website/js/config.js`-ийн `GITHUB: 'null'` — магадгүй санаатай "placeholder".
- `.firebase/` cache, `__pycache__/` repo дотор байна (`.gitignore`-д бүртгэлтэй — истори үлдсэн).
- Pyflakes-ийн үлдсэн "unused local variable" анхааруулгууд (`except ... as e:` доторх
  `e` г.м.) — санамсаргүй биш, зөвхөн стилийн анхааруулга; устгавал log-ийн
  ирээдүйн өргөтгөлд төвөгтэй тул хэвээр үлдээв.
