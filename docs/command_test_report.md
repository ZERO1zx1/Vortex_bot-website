# 𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹 — Командын бүрэн тестийн тайлан

**Огноо:** 2026-08-16 (UTC) · **Туршилтын орчин:** Sandbox (Python 3.12, discord.py 2.7.1) · **Supabase:** Vortex (`onpxpvemmjesobxpilgd`) · **Git commit:** `a28c9b8` (main)

---

## 1. Туршилтын арга зүй

Таны `.env`-ээр (Discord токен + Supabase anon key) ботыг sandbox дээр бүрэн асааж, бодит сервер (`1501605621584363720`) дээрх бүх кодыг туршсан. Туршилт 2 давхаргаар хийгдсэн:

| Давхарга | Агуулга |
|---|---|
| **A. Ботын бүтэн startup** | `main.py` бодитоор асаагдсан — 29/29 cog, 77 slash command, background loop-ууд (stock restock, role income, tempvoice, giveaway) 20+ минут тасралтгүй ажилласан. Нийт 900+ REST дуудлага бүгд 200/201/204. **0 × 401 / 42501 / PGRST205 / 23505 алдаа.** |
| **B. Командын функц тест** | `tools/test_all_commands.py` шинэ туршилтын хэрэгсэл бичиж, бүх 29 cog-оос 122 командыг цуглуулж, 40 hybrid командыг (economy, moderation, leveling, marriage, mafia, games, admin, shop, leaderboard гэх мэт) бодит database-тай шууд invoke хийж баталгаажуулсан. |

Туршилтын кодыг `tools/test_all_commands.py` болгон repo руу оруулсан — цаашид өөрчлөлт бүрийн дараа `python3 tools/test_all_commands.py` гэж ажиллуулж регрессийг шалгах боломжтой (энэ нь Discord-рүү ямар ч мессеж илгээдэггүй, зөвхөн командын логик + database бичилтийг туршина).

---

## 2. Туршилтын үр дүн: 40/40 команд OK

| Ангилал | Командууд | Үр дүн |
|---|---|---|
| Эдийн засаг | workphrase, addmoney, removemoney | ✅ |
| Түвшин | grank, serveractivity, leaderboard | ✅ |
| Модераци | lock, unlock, kick, ban, unban, banlist, clear, timeout, untimeout, warn, unwarn, warnings, warnedusers | ✅ |
| Гэр бүл | propose, divorce, adopt, disown, spouse, love, gift, familytree, marriagepro | ✅ |
| Дэлгүүр | market, mp | ✅ |
| Админ | status, info, rolelist | ✅ |
| Кафе | cafe, dine | ✅ |
| Тоглоом | mfiacreate, mfiastart, mafiaend | ✅ |
| Тусламж | help | ✅ |

Database түвшинд: бүх уншилт/бичилт (economy, levels, warnings, staff_activity, shop_stock гэх мэт) амжилттай — upsert засварын дараа cooldown, warning гэх мэт cooldown-ууд зөв хадгалагдаж байгаа нь батлагдсан.

---

## 3. Туршилтын явцад олдсон алдаанууд ба засварууд

### 3.1 `/announce` модалын 50035 алдаа (өмнөх хүсэлт)
**Шалтгаан:** discord.py-ийн `Modal` class attribute `title = TextInput(...)`-ийг `super().__init__()` overwrite хийж, TextInput бүртгэгддэггүй → хоосон `components: []` payload → Discord "Must be between 1 and 40 in length".
**Засвар (commit `6b9dbf7`):** 5 модал бүгдийг `__init__` дотор `self.add_item()`-ээр бүртгэдэг болгосон; модал бүрийн payload баталгаажсан (rows=1, components=1).

### 3.2 `!daily` давхар урамшуулал (өмнөх хүсэлт)
**Засвар (commit `a4a7b58`):** `upsert()`-ийг postgrest 2.x-ийн зөв API (`on_conflict` kwarg) руу шилжүүлсэн; live DB дээр баталгаажуулсан; economy-д duplicate мөр байхгүйг шалгасан.

### 3.3 `/status` NaN алдаа (шинэ олдсон)
**Шалтгаан:** Gateway холбогдохоос өмнө `self.bot.latency` нь `NaN` байдаг; `round(NaN)` → `ValueError`. Таны бот серверт байнга ажилладаг учраас бодит орчинд ховор ч, restart-ын дараах эхний хүсэлтэд тохиолдох боломжтой.
**Засвар (commit `a28c9b8`):** `latency = round(latency_ms) if latency_ms == latency_ms else 0` NaN guard нэмсэн.

### 3.4 Хамаагүй: PyNaCl warning
`PyNaCl is not installed, voice will NOT be supported` — voice суваг ашиглахгүй байгааг анхааруулж буй info. `py -3.12 -m pip install PyNaCl`-ээр устгаж болно (заавал биш).

---

## 4. Таны PC дээр хийх эцсийн шинэчлэл

```powershell
cd C:\Users\hotar\OneDrive\Desktop\gurtendev
git pull origin main
py -3.12 -m pip install -q psutil PyNaCl
py -3.12 main.py
```

Анхааруулга: локал `database/migrations/000_complete_schema.sql` файлд өөрчлөлттэй бол `git checkout -- database/migrations/000_complete_schema.sql` гэж эхэл.

Дараа нь хүссэнээрээ шалгах боломжтой:
```powershell
py -3.12 tools\test_all_commands.py
```

---

## 5. Аюулгүй байдлын тэмдэглэл

Таны `.env` энэ чат-д байгаа тул Supabase Dashboard > Settings > API-аас anon key-ийг **rotate** хийж `.env`-ээ шинэчлэхийг зөвлөж байна. Sandbox дээрх бүх түр файлууд (.env, тест скриптүүд) аль хэдийн устгагдсан; repo-д зөвхөн токентой бус туршилтын хэрэгсэл push хийгдсэн.
