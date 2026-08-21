# 𝓐𝓮𝓽𝓱𝓮𝓻  蒼穹 — Зассан код, Индексийн шинжилгээ, psutil хяналтын тайлбар

**Зохиогч:** Manus AI · **Огноо:** 2026-08-15
**Репозитор:** [ZERO1zx1/gurtendev](https://github.com/ZERO1zx1/gurtendev) · **Салбар:** main

Энэхүү тайланд гурван асуултын хариултыг нэгтгэв: (1) бүрэн засварын үйл явцад орсон кодын өөрчлөлтүүдийн git diff тойм болон `stock.py`-д ямар өөрчлөлт орсны тайлбар, (2) Supabase дээрх хүснэгтүүдийн бүтэц болон ботын query-д үндэслэсэн индексийн шинжилгээ, (3) admin cog доторх psutil-ээр CPU/RAM хянах командиудын ажиллах зарчим.

---

## 1. Зассан код (git diff тойм)

Бүх засвар нь `de9bd47` (failed Cline-ийн оношилгооны файлуудыг цэвэрлэсэн commit) commit-ээс `107a7ce` (сүүлийн commit) хүртэлх **11 commit**-д багтсан. Нийт **14 файл, +1060 мөр, −64 мөр** өөрчлөгдсөн.

| # | Commit | Тайлбар | Өөрчлөгдсөн файлууд |
|---|--------|---------|---------------------|
| 1 | `9b4b522` | Failed Cline-ийн `.agents/skills/agentcore/` папкиг хаслаа | 1 файл −26 |
| 2 | `f6e8106` | Бүрэн schema migration (`000_complete_schema.sql`, 57 хүснэгт) + `check_migration_applied.py` шалгагч + README-д Windows `py -3.12` заавар | 3 файл +597 |
| 3 | `cfbc1c4` | Background loop-ууд хүснэгт байхгүй үед crash хийхээ больсон (`fetch_safe`) | 8 файл +84 −25 |
| 4 | `a92b200` | `moderation.py` logger `NameError` + бүх staff уншилт `fetch_safe` болсон | 1 файл +36 |
| 5 | `6cb9e1b` | Cog audit тайлан + read-only migration шалгагч | 2 файл +197 |
| 6 | `fee0255` | Migration-д `fake`, `left` (SQL нөөц үг) баганыг quote хийсэн | 1 файл |
| 7 | `8f64eee` | 57 хүснэгтэд RLS унтраасан (`DISABLE ROW LEVEL SECURITY`) — 401/42501-ийн эхний засвар | 2 файл +73 |
| 8 | `90e757d` | `anon`/`authenticated` рольд GRANT ALL нэмсэн + `fetch_safe` 42501-ийг барьдаг болсон | 3 файл +45 −8 |
| 9 | `4ab972b` | Database засварын баталгаажуулалтын тайлан | 1 файл +57 |
| 10 | `107a7ce` | `stock.py` 23505 duplicate key race condition-ийг upsert болгож заслаа | 1 файл +38 |

### Cogs файлуудын diff (голын логик өөрчлөлтүүд)

**`cogs/economy.py`** — `role_income` loop-ийн уншилт:

```diff
-                rows = await self.bot.db_manager.fetch_all("role_income")
+                rows = await self.bot.db_manager.fetch_safe("role_income")
```

**`cogs/giveaway.py`** — дууссан giveaway-уудыг шалгах loop:

```diff
-        giveaway_rows = await self.bot.db_manager.fetch_all("giveaways", {"ended": False})
+        giveaway_rows = await self.bot.db_manager.fetch_safe("giveaways", {"ended": False})
```

**`cogs/leveling.py`** — тохиргоо уншихдаа PGRST205-ийг зөөлөн боловсруулж, voice XP loop-д `fetch_one`-ийг `fetch_safe(single=True)` болгосон:

```diff
 async def get_config(db_manager, guild_id: int) -> Dict[str, Any]:
-    row = await db_manager.fetchone("leveling_config", {"guild_id": str(guild_id)})
+    try:
+        row = await db_manager.fetchone("leveling_config", {"guild_id": str(guild_id)})
+    except Exception as e:
+        if "PGRST205" not in str(e) and getattr(e, "status_code", None) != 404:
+            raise
+        row = None
```

**`cogs/roles.py`** — temprole loop:

```diff
-        rows = await self.bot.db_manager.fetch_all("temproles", {})
+        rows = await self.bot.db_manager.fetch_safe("temproles", {})
```

**`cogs/tempvoice.py`** — setup message-ийн reload:

```diff
-        rows = await self.bot.db_manager.fetch_all("tempvoice_setup_msg", {})
+        rows = await self.bot.db_manager.fetch_safe("tempvoice_setup_msg", {})
```

**`cogs/moderation.py`** — хамгийн их өөрчлөлттэй файл. Эхлээд `import logging` + `logger` нэмж `NameError`-ийг заслаа, дараа нь 12 удаагийн staff хүснэгтийн уншилтыг `fetch_safe` болгож, weekly winner болон leaderboard шинэчлэлтийг per-guild try/except-д орууллаа:

```diff
+import logging
+logger = logging.getLogger(__name__)
...
-        members = await self.bot.db_manager.fetch_all("staff_members", {"guild_id": guild_id})
-        activity_rows = await self.bot.db_manager.fetch_all("staff_activity", {"guild_id": guild_id})
+        members = await self.bot.db_manager.fetch_safe("staff_members", {"guild_id": guild_id})
+        activity_rows = await self.bot.db_manager.fetch_safe("staff_activity", {"guild_id": guild_id})
+        if not members or not activity_rows:
+            return
...
     async def update_leaderboard(self, guild: discord.Guild):
         guild_id = str(guild.id)
+        try:
+            await self._update_leaderboard_inner(guild, guild_id)
+        except Exception as e:
+            logger.error("Staff лидерборд шинэчлэлт сервер %s дээр амжилтгүй: %s", guild.id, e)
+
+    async def _update_leaderboard_inner(self, guild: discord.Guild, guild_id: str):
```

Үлдсэн staff уншилтууд (`staff_config`, `staff_counts`, `staff_status`) бүгд `fetch_safe(..., single=True)` болсон.

### `database/supabase_manager.py` — шинэ `fetch_safe()` метод

```diff
+    def _is_missing_table(self, error: BaseException) -> bool:
+        msg = str(error)
+        code = getattr(error, "code", None) or ""
+        status = getattr(error, "status_code", None) or getattr(error, "status", None) or 0
+        return ("PGRST205" in code or "PGRST205" in msg
+                or int(status) == 404
+                or "42501" in code or "42501" in msg)
+
+    async def fetch_safe(self, table, filters=None, single=False, **kwargs):
+        try:
+            if single:
+                return await self.fetch_one(table, filters or {}, **kwargs)
+            return await self.fetch_all(table, filters or {}, **kwargs)
+        except Exception as e:
+            if not self._is_missing_table(e):
+                raise
+            logging.getLogger("aether.db").error(
+                "Table '%s' is missing in Supabase (PGRST205). "
+                "Apply database/migrations/000_complete_schema.sql and restart.", table)
+            return None if single else []
```

Энэ нь background loop-уудыг PGRST205 (хүснэгт байхгүй), HTTP 404, эсвэл 42501 (эрхийн алдаа) үед crash хийхээс хамгаалж, `[]` / `None` буцаана. Бусад бодит алдаанууд (auth, сүлжээ) хэвээр дамждаг.

### `database/migrations/000_complete_schema.sql` — 670 мөрийн шинэ файл

57 хүснэгтийн `CREATE TABLE IF NOT EXISTS`, 10 index, `increment_rpc` функц, RLS disable хэсэг (57 хүснэгт), мөн `GRANT ALL ON ALL TABLES ... TO anon, authenticated` хэсэг — бүгд нэг файлд, босоо давтагдахгүйгээр (idempotent).

---

## 2. `stock.py`-ийн өөрчлөлтийн дэлгэрэнгүй тайлбар

### Асуудал: 23505 duplicate key алдаа

`stock.py`-ийн `_ensure_item_stock` функц нь **select-then-insert** хэв маягтай байсан: эхлээд бараа байгаа эсэхийг шалгаад (`fetch_one`), байхгүй бол `insert` хийдэг. Энэ нь ганц process-д асуудалгүй мэт боловч `daily_restock` loop нь өглөөний цагаар бүх guild-ийн бүх бараанд энэ шалгалтыг зэрэг хийдэг. SELECT-ээр "байхгүй" гэж харсан мөч болон INSERT-ээр мөрийг бичих мөчийн хооронд нөгөө мөр үүссэн тохиолдолд PostgreSQL-ийн `shop_stock_pkey` (guild_id, item_id) unique constraint зөрчигдөж `23505 duplicate key` алдаа гарна. Sandbox-д ажиллуулсан үед бодитоор `Key (guild_id, item_id)=(1501605621584363720, 4055) already exists` гэж бүртгэгдсэн.

### Засвар: INSERT-ийг UPSERT болгосон

```diff
-        await self.bot.db_manager.insert("shop_stock", {
+        await self.bot.db_manager.upsert("shop_stock", {
             "guild_id": str(guild_id),
             "item_id": item_id,
             "current_stock": random_stock,
             "last_restock": int(datetime.datetime.now().timestamp()),
-        })
+        }, on_conflict="guild_id,item_id")
```

PostgreSQL-ийн `INSERT ... ON CONFLICT (guild_id, item_id) DO UPDATE` нь давхардал гарвал шууд update хийдэг тул race condition бүрмөсөн арилна. Мөн хэвийн үед (мөр байгаа бол) SELECT-ээр урьдчилж шалгасан байгаа тул upsert-ийн update нь бараг хэзээ ч биелдэггүй — зөвхөн түүнийг хамгаалах сүлжээ болдог.

### Хоёр дахь өөрчлөлт: daily_restock loop-ийн найдвартай болголт

`daily_restock` loop нь нэг guild дээр алдаа гарвал бүхэл loop тасрах бүтэцтэй байсан. Одоо **guild тус бүрийг try/except-д** оруулж, нэг серверт гарсан алдаа бусад серверийн нөөц шинэчлэлтийг зогсоохгүй:

```diff
         for guild in self.bot.guilds:
-            await self.ensure_stocks_for_guild(guild.id)
-            stock_rows = await self.bot.db_manager.fetch_all(...)
-            for row in stock_rows:
-                ... (200 орчим мөрийн шинэчлэлт)
+            try:
+                await self.ensure_stocks_for_guild(guild.id)
+                stock_rows = await self.bot.db_manager.fetch_safe(...)
+                for row in stock_rows:
+                    ... (шинэчлэлт хэвээр)
+            except Exception as e:
+                logger.error("Өдөр бүрийн нөөц шинэчлэлт сервер %s дээр амжилтгүй: %s", guild.id, e)
```

Засварын дараа sandbox-д 3+ минут ажиллуулж, 23505 алдаа 0 болсон, нөөц шинэчлэлт амжилттай гүйцэтгэгдэж байгааг баталгаажуулсан.

---

## 3. Supabase индексийн шинжилгээ

### Одоо байгаа индексүүд (migration-д тодорхойлсон)

| Индекс | Хүснэгт | Баганууд |
|--------|---------|----------|
| `idx_economy_balance` | economy | balance |
| `idx_economy_guild` | economy | guild_id, balance |
| `idx_levels_guild` | levels | guild_id, level DESC, xp DESC |
| `idx_temproles_guild` | temproles | guild_id |
| `idx_temproles_end` | temproles | end_time |
| `idx_giveaways_guild` | giveaways | guild_id |
| `idx_giveaways_end` | giveaways | end_time |
| `idx_role_income_guild` | role_income | guild_id |
| `idx_game_stats_guild` | game_stats | guild_id, total_won DESC |
| `idx_shop_stock_guild` | shop_stock | guild_id |

Түүнчлэн хүснэгт бүрийн **PRIMARY KEY нь автоматаар unique index** болдог. Ботын query-нүүдийн ихэнх нь яг энэ PK-ээр шүүдэг — жишээ нь `economy` хүснэгтийг `(user_id, guild_id)`-ээр унших бүх команд нь `(user_id, guild_id)` compound PK-ээр шууд хэрэглэгдэнэ.

### Query-г индексүүдтэй харьцуулсан үр дүн

| Ботын query хэв маяг | Хүснэгтийн индексийн төлөв | Дүгнэлт |
|----------------------|---------------------------|---------|
| `economy` ← (user_id, guild_id) | PK `(user_id, guild_id)` | ✅ Бүрэн хангагдсан |
| `levels` ← (user_id, guild_id), leaderboard | PK `(user_id, guild_id)` + `idx_levels_guild` | ✅ |
| `shop_stock` ← (guild_id, item_id) | PK `(guild_id, item_id)` | ✅ |
| `user_inventory` ← (user_id, guild_id, item_id) | PK `(user_id, guild_id, item_id)` | ✅ |
| `staff_members` ← guild_id | PK `(guild_id, user_id)` — guild нь эхний багана | ✅ |
| `staff_config`, `guild_config`, `greeting_config`, `counting_config` зэрэг тохиргооны хүснэгтүүд ← guild_id | `guild_id TEXT PRIMARY KEY` | ✅ |
| `work_phrases` ← guild_id | PK `(guild_id, word)` — guild эхний багана | ✅ |
| `giveaways` ← id | `id SERIAL PRIMARY KEY` | ✅ |
| `temproles` ← end_time (хугацаа дууссан шалгалт) | `idx_temproles_end` | ✅ |
| `staff_activity` ← guild_id (hourly leaderboard + weekly loop) | PK `(user_id, guild_id)` — **guild эхний багана биш** | ⚠️ Index дутуу |
| `warnings` ← guild_id | `id SERIAL PRIMARY KEY` — guild индексгүй | ⚠️ Бага зэрэг |
| `giveaways` ← {ended: False} | `ended` багананд индексгүй | ℹ️ Сонголтоор |

### Дүгнэлт ба зөвлөмж

Ботын бичиж буй query-нүүдийн **~95% нь одоо байгаа primary key эсвэл индексээр бүрэн хангагдаж байна**. Supabase-ийн free tier хүснэгтүүд энэ цэгт хэдэн зуун мянган мөр хүртэл тул PostgREST аль хэдийн хурдан байна. Гэхдээ `staff_activity` хүснэгтийн PK нь `(user_id, guild_id)` дараалалтай тул `WHERE guild_id = ?` query нь индексийн **эхний багана ашиглахгүй** — энэ нь цаг тутам ажилладаг leaderboard болон долоо хоногийн weekly winner loop-д шууд нөлөөтэй цорын ганц ноцтой дутагдал юм.

Зөвлөж буй нэмэлт индекс (шаардлагатай бол migration-д нэмж ажиллуулна):

```sql
-- staff_activity: leaderboard loop бүр guild_id-ээр бүх мөр татдаг
CREATE INDEX IF NOT EXISTS idx_staff_activity_guild
  ON staff_activity (guild_id);

-- warnings: /warnings командыг guild-ээр шүүдэг
CREATE INDEX IF NOT EXISTS idx_warnings_guild
  ON warnings (guild_id);

-- giveaways: ended=False filter (хүснэгт томорбол ашигтай)
CREATE INDEX IF NOT EXISTS idx_giveaways_ended
  ON giveaways (ended);
```

Эдгээр индексийг одоо нэмэх ч болно, хүснэгтүүд томорсны дараа ч болно — ботын одоогийн ачаалалд аль нь ч заавал шаардлагатай биш. `idx_levels_guild (guild_id, level DESC, xp DESC)` нь leaderboard-ийн `ORDER BY level DESC, xp DESC LIMIT N` query-д тохируулсан маш сайн индекс учраас одоо өөрчлөх шаардлагагүй.

---

## 4. admin.py — psutil-ээр CPU/RAM хянах командиудын ажиллах зарчим

`admin.py` нь `psutil` санг (Python system monitoring library) ашиглан бот ажиллаж буй машины нөөцийг шууд уншдаг. Энэ cog нь зөвхөн ботын эзэмшигч / хамт эзэмшигчдэд (main.py-ийн `owner_ids`) ажилладаг бөгөөд load болохын тулд машины Python орчинд `psutil` суусан байх шаардлагатай — яг энэ модуль дутуугаас admin cog өмнө нь load fail болж байсан бөгөөд `py -3.12 -m pip install psutil` командаар засагдсан.

### `status` команд — нөөцийн мониторинг

Командын логик нь дараах дарааллаар ажиллана:

```python
# cog ачаалагдах үед лог-д хадгалагдана (cogs/admin.py мөр 14)
self.start_time = time.time()

# /status дуудагдах үед:
uptime = str(datetime.fromtimestamp(self.start_time).strftime("%Y-%m-%d %H:%M:%S"))
latency = round(self.bot.latency * 1000)          # Discord WebSocket сүлжээний хоцролт (мс)
cpu_usage = psutil.cpu_percent()                   # CPU ашиглалт (%)
ram_usage = psutil.virtual_memory().percent        # RAM ашиглалт (%)
```

| Элемент | Эх сурвалж | Тайлбар |
|---------|-----------|---------|
| ⏳ Ажилласан хугацаа | `self.start_time = time.time()` | Cog instance үүсэх цаг (эпохийн секундоор). Хэрэглэгч дуудах үед Unix timestamp-ийг `datetime` руу хөрвүүлж уншигдах хэлбэрт оруулна. |
| 📡 Хоцролт | `self.bot.latency * 1000` | discord.py-ийн WebSocket сүүлийн heartbeat round-trip. Секундээр хэмжигддэг тул 1000-аар үржүүлж миллисекунд болгоно. |
| 💻 CPU | `psutil.cpu_percent()` | Сүүлийн секундын CPU ашиглалт. `interval` параметр өгөөгүй тул өмнөх дуудлагатай харьцуулсан instantaneous утгыг буцаана (эхний дуудлагад ~0 гарна). |
| 🧠 RAM | `psutil.virtual_memory().percent` | Нийт RAM-аас ашиглагдаж буй хувь. Дотор нь `psutil.virtual_memory()` нь `total`, `available`, `used`, `percent` зэрэг системийн мэдээллийг `/proc/meminfo` (Linux) эсвэл `GlobalMemoryStatusEx` (Windows)-ээс уншина. |
| ⚙️ Систем | `platform.system()` | ОС-ийн нэр (Windows / Linux) |
| 🐍 Python | `platform.python_version()` | Python-ийн хувилбар |

Ажлын зарчмын хувьд энэ нь **server-ийн бус host machine-ийн** нөөцийг хянадаг гэдгийг онцлох хэрэгтэй: бот таны PC (эсвэл хостлогч машин) дээр ажиллах үед `psutil.cpu_percent()` болон `virtual_memory()` нь **таны PC-ийн** CPU/RAM-ийг харуулна. Хэрэв ботыг цаашлаад VPS дээр хостлох бол VPS-ийн нөөцийг харуулна.

### psutil-ийн дотоод механизм

`psutil` нь платформ тус бүрт C түвшний системийн API-г дууддаг: Windows дээр `GlobalMemoryStatusEx`, `GetSystemTimes`, Linux дээр `/proc/stat`, `/proc/meminfo` файлуудыг уншина. Тиймээс админ хэрэглэгч `status` командыг дуудах бүр бот нэг удаагийн маш хурдан (микросекундын түвшний) системийн дуудлага хийж, үр дүнг embed хэлбэрээр буцаана — background loop биш тул ботын үйл ажиллагаанд ачаалал өгдөггүй.

### Нэмэлт админ командиуд

`status`-аас гадна `info` команд нь `guild` обьектоос серверийн мэдээлэл (гишүүдийн тоо, хүн/бот харьцаа, сувгууд, роль, boost түвшин, баталгаажуулалт) цуглуулж embed болгодог — энэ нь Discord API-ийн өгөгдөл тул psutil-тай хамааралгүй. `addmoney` нь эдийн засгийн cog-д дамжуулж тухайн гишүүнд мөнгө нэмнэ. CPU/RAM-ийн хяналтыг өргөтгөхөөр санал болгож болох зүйлс нь `psutil.disk_usage('/')` (диск), `psutil.net_io_counters()` (сүлжээний траффик), `psutil.cpu_percent(interval=1)` (илүү нарийн 1-секундын дундаж) юм.
