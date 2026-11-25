# AETHER DISCORD BOT — PROJECT CONTEXT, AUDIT & IMPLEMENTATION PROMPT

> Энэхүү баримт бичиг нь `aether_bot.zip` архивын бодит кодын аудит, одоогийн хэрэгжсэн суурь (Baseline v2), дутуу байгаа модулиудын жагсаалт болон үргэлжлүүлэн хөгжүүлэхэд зориулсан **Master Continuation Prompt**-ийг агуулна. Төслийн санааг [DarkMooN-SYS/MongolBot](https://github.com/DarkMooN-SYS/MongolBot)-ийн модульчлагдсан бүтцээс уламжлан авч, орчин үеийн Layered Architecture + Atomic Service Layer + Interactive UI болгон шинэчилсэн.

> **Одоогийн төлөв (2026-11-25):** Доорх Gap Analysis нь анхны архивын
> түүхэн аудит. Түүний Economy, Jail, RPG, Casino, Games, UI болон Cog үе
> шатууд одоо хэрэгжсэн. Production database нь Supabase PostgreSQL болсон;
> шинэ schema `migrations/001_baseline.sql`-д бүрэн агуулагдана. Бодит
> Supabase validation нь disposable `AETHER_TEST_DATABASE_URL` өгөх хүртэл
> хийгдээгүй.

---

## 1. `aether_bot.zip` КОДЫН АУДИТ (ОДОО БАЙГАА БАЙДАЛ БА ЗӨРҮҮ)

### А. Бүрэн хэрэгжсэн, чанартай суурь (Production-Ready Foundation — 71 тесттэй)
Архив доторх суурь дэд бүтэц маш сайн бичигдсэн бөгөөд дараах файлуудыг **эвдэхгүйгээр** шууд залгуулан ашиглана:

| Модуль / Файл | Статус | Хэрэгжсэн онцлог |
| :--- | :--- | :--- |
| `core/database.py` | ✅ Бэлэн | WAL горим, тусдаа `_read_conn` (`query_only=ON`) ба `_write_lock`-той бичих холболт, `BEGIN IMMEDIATE` транзакц, ContextVar leak хамгаалалт, SHA-256 checksum-тай migration runner. |
| `migrations/001` & `002` | ✅ Бэлэн | `users`, `user_skills`, `shop_items`, `inventory`, `user_effects`, `cooldowns`, `transactions`, `casino_logs`, `game_logs`, `guild_settings` хүснэгтүүд + Append-only (`BEFORE UPDATE/DELETE RAISE(ABORT)`) триггерүүд. |
| `core/locks.py` | ✅ Бэлэн | Reentrant `PerUserLockManager` (`user_lock`, `multi_user_lock` эрэмбэлэлттэй deadlock хамгаалалт). |
| `core/rate_limiter.py` | ✅ Бэлэн | 45 req/s глобал sliding-window лимитер + `RouteLimiter` (5 req / 2s) + `install_http_guard`. |
| `core/event_bus.py` | ✅ Бэлэн | Async pub/sub (`XPGained`, `LevelUp`, `MoneyChanged`, `SkillUpgraded`, `SkillActivated`, `CasinoResolved`, `QuestProgress`). |
| `core/skill_catalog.py` | ✅ Бэлэн | 3 салбар (`Fortune`, `Shadow`, `Wisdom`), 7 skill (`golden_touch`, `lucky_star`, `merchants_eye`, `shadow_step`, `critical_strike`, `astral_resonance`, `aether_shield`). |
| `services/rpg/skill_service.py` | ✅ Бэлэн | 15с кэштэй `get_modifiers()`, атомик `upgrade()`, `activate()`, `consume_charge()`, `reset()`. |
| `repositories/user_repo.py` & `skill_repo.py` | ✅ Бэлэн | `UserRow`, `SkillRow` CRUD ба атомик SP зарцуулалт. |

### Б. Илэрсэн зөрүү болон Дутуу зүйлс (Gap Analysis)
Архивыг задлан шалгахад дараах **6 гол зөрүү ба дутуу хэсгүүд** илэрлээ:

1. **Командын төрлийн зөрүү (`hybrid_command` vs. Prefix / Slash ялгалт):**
   * Одоогийн `cogs/economy.py`, `cogs/skills.py`, `cogs/health.py`, `cogs/admin.py` нь бүгд `@commands.hybrid_command` ашигласан байна.
   * **Шаардлага:** Энгийн тоглогчийн бүх команд **зөвхөн Prefix (`@commands.command`, `a!`)** байх ёстой. Харин Админ командууд **зөвхөн Slash (`@app_commands.command`, `/admin_*`)** байх ёстой.
2. **Архитектурын дүрмийн зөрчил (`cogs/admin.py` ба `bot.py`):**
   * `cogs/admin.py` болон `bot.py` дотор `self.bot.db.execute(...)` / `fetchone(...)` гэж **Cog дотроос шууд SQL бичсэн** нь *"cogs дотор SQL бичихгүй"* гэсэн дүрмийг зөрчсөн. Үүнийг `GuildRepository` руу шилжүүлэх ёстой.
3. **Шоронгийн (Jail) систем DB болон Service дээр огт байхгүй:**
   * `001_baseline.sql` болон `002_hardening.sql` дээр `users` хүснэгтэд `jail_until`, `jail_bail_cost` баганууд **байхгүй** байна.
   * **Шийдэл:** `001`, `002`-ийг засах хориотой тул (SHA-256 checksum шалгадаг) шинээр **`migrations/003_jail_and_features.sql`** үүсгэж `jail_until`, `jail_bail_cost`, `log_channel_id` болон сугалааны хүснэгтийг нэмнэ. Мөн `JailedError` болон `@not_jailed()` check декоратор (`core/checks.py`) дутуу байна.
4. **Интерактив UI (`Button`, `StringSelect`, `Modal`) огт бичигдээгүй:**
   * `ui/` хавтас дотор зөвхөн `embeds.py` байна. `AetherView` (author_id шалгалт + timeout auto-disable), `Modal`-ууд болон цэсүүд огт хийгдээгүй; `a!upgrade`, `a!activate` зэрэг нь текст аргументаар ажиллаж байна.
5. **Хоосон хавтаснууд ба Огт бичигдээгүй Сервисүүд:**
   * `services/economy/`, `services/casino/`, `services/games/`, `data/economy/`, `data/rpg/`, `data/ui/` хавтаснууд **0 файлтай хоосон** байна.
   * `shop_repo.py`, `cooldown_repo.py`, `guild_repo.py`, `log_repo.py` байхгүй.
6. **Багцын жин:**
   * `aether_bot.zip` дотор `.venv/`, `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/` болон `.env` орсон байгааг `.gitignore`-оор цэвэрлэх шаардлагатай.

---

## 2. ЗОРИЛТОТ ХАВТАСНЫ БҮТЭЦ (DOMAIN-BASED STRUCTURE)

Одоо байгаа `core/` болон `migrations/` суурийг хэвээр хадгалж, дутуу файлуудыг дараах ангиллаар гүйцээнэ:

```text
aether_bot/
├── bot.py                          # [ЗАСАХ] Dynamic Cog loader, GuildRepo prefix, EventBus холболт
├── config.py                       # [ЗАСАХ] CRIME/JAIL/GAME тогтмолууд нэмэх
├── migrations/
│   ├── 001_baseline.sql            # [ХӨНДӨХГҮЙ] SHA-256 checksum-тай
│   ├── 002_hardening.sql           # [ХӨНДӨХГҮЙ] SHA-256 checksum-тай
│   └── 003_jail_and_features.sql   # [ШИНЭ] users.jail_until, jail_bail_cost, lottery_tickets, log_channel_id
│
├── data/                           # [ШИНЭ] Статик тохиргооны JSON файлууд
│   ├── economy/
│   │   ├── jobs.json               # Ажлын жагсаалт, шаардагдах level, цалин
│   │   └── crimes.json             # Гэмт хэргийн төрлүүд, эрсдэл, шоронгийн хугацаа
│   ├── rpg/
│   │   ├── dungeons.json           # Adventure өрөөнүүд, сонголт, олз
│   │   └── bosses.json             # World Boss-ийн HP, дайралт, шагнал
│   └── ui/
│       └── banners.json            # Embed баннер/thumbnail URL-ууд
│
├── core/
│   ├── database.py                 # [БЭЛЭН]
│   ├── locks.py                    # [БЭЛЭН]
│   ├── rate_limiter.py             # [БЭЛЭН]
│   ├── event_bus.py                # [ЗАСАХ] UserJailed, UserReleased event нэмэх
│   ├── skill_catalog.py            # [БЭЛЭН]
│   ├── exceptions.py               # [ЗАСАХ] JailedError, ItemNotFoundError нэмэх
│   └── checks.py                   # [ШИНЭ] @not_jailed(), @is_admin() декораторууд
│
├── utils/
│   ├── time_utils.py               # [БЭЛЭН]
│   └── validators.py               # [ШИНЭ] "all", "half", "10k", "1.5m" дүн задлагч
│
├── repositories/
│   ├── user_repo.py                # [ЗАСАХ] wallet/bank/xp/level/jail atomic update методууд нэмэх
│   ├── skill_repo.py               # [БЭЛЭН]
│   ├── shop_repo.py                # [ШИНЭ] shop_items, inventory, user_effects CRUD
│   ├── cooldown_repo.py            # [ШИНЭ] cooldowns хүснэгт шалгах/тохируулах
│   ├── guild_repo.py               # [ШИНЭ] guild_settings (prefix, tax_pct, log_channel_id)
│   └── log_repo.py                 # [ШИНЭ] transactions, casino_logs, game_logs бичих/унших
│
├── services/
│   ├── economy/
│   │   ├── wallet_service.py       # [ШИНЭ] Balance, Deposit, Withdraw, Transfer (tax_pct), Escrow
│   │   ├── income_service.py       # [ШИНЭ] Daily Streak, Work
│   │   ├── crime_service.py        # [ШИНЭ] Crime, Rob (Shield шалгах, бүтэлгүйтвэл Jail)
│   │   └── jail_service.py         # [ШИНЭ] Шоронд хийх, хугацаа шалгах, Bail (Shadow Step хөнгөлөлт)
│   ├── rpg/
│   │   ├── skill_service.py        # [ЗАСАХ] Modifiers дээр jail_reduction_pct нэмэх
│   │   ├── level_service.py        # [ШИНЭ] XPGained сонсох, Level-up тооцоо (+2 SP, level*200 coin)
│   │   ├── shop_service.py         # [ШИНЭ] Merchant's Eye хямдрал, худалдан авалт
│   │   └── inventory_service.py    # [ШИНЭ] Item хэрэглэх (Shield, XP Boost, Stamina, Tome of Rebirth, Title)
│   ├── casino/
│   │   ├── slots_service.py        # [ШИНЭ] 3x3 Slots, Escrow, Lucky Star cashback
│   │   ├── blackjack_service.py    # [ШИНЭ] Blackjack state machine (Hit/Stand/Double)
│   │   ├── roulette_service.py     # [ШИНЭ] Улаан/Хар, Тэгш/Сондгой, Тоо (0-36)
│   │   ├── minefield_service.py    # [ШИНЭ] 4x4 бөмбөгтэй талбай, Cashout үржүүлэгч
│   │   ├── coinflip_service.py     # [ШИНЭ] Heads/Tails
│   │   ├── crash_service.py        # [ШИНЭ] Crash үржүүлэгч ба Cashout
│   │   └── lottery_service.py      # [ШИНЭ] Сугалааны тасалбар ба Jackpot
│   └── games/
│       ├── duel_service.py         # [ШИНЭ] 1v1 PvP ээлжит тулаан (Critical Strike цэнэг ашиглана)
│       ├── adventure_service.py    # [ШИНЭ] Dungeon өрөөний сонголт ба олз
│       ├── hunt_fish_service.py    # [ШИНЭ] Hunt ба Fish мини-тоглоом
│       └── boss_service.py         # [ШИНЭ] Нийтийн Raid Boss
│
├── ui/
│   ├── embeds.py                   # [ЗАСАХ] Бүх модулийн Anime-style embed функцүүд нэмэх
│   ├── common/
│   │   ├── base.py                 # [ШИНЭ] AetherView (author_id хамгаалалт + on_timeout auto-disable)
│   │   ├── modals.py               # [ШИНЭ] AmountModal, TransferModal, BetModal, BuyQuantityModal, BioModal
│   │   └── paginator.py            # [ШИНЭ] Хуудаслагч View
│   ├── economy/                    # [ШИНЭ] balance_view.py, work_view.py, crime_view.py, jail_view.py
│   ├── rpg/                        # [ШИНЭ] profile_view.py, skill_view.py, shop_view.py, inventory_view.py
│   ├── casino/                     # [ШИНЭ] slots_view.py, blackjack_view.py, roulette_view.py, minefield_view.py, crash_view.py
│   └── games/                      # [ШИНЭ] duel_view.py, adventure_view.py, boss_view.py
│
└── cogs/
    ├── system/                     # [ШИНЭ] help.py (a!help, a!ping), events.py (XP & Error handler), admin.py (/admin_*)
    ├── economy/                    # [ШИНЭ] wallet.py, income.py, crime.py, jail.py
    ├── rpg/                        # [ШИНЭ] profile.py, skills.py, shop.py, inventory.py
    ├── casino/                     # [ШИНЭ] slots.py, blackjack.py, roulette.py, minefield.py, coinflip.py, crash.py, lottery.py
    └── games/                      # [ШИНЭ] duel.py, adventure.py, hunt.py, fish.py, boss.py
```

---

## 3. MIGRATION 003 СХЕМ (`migrations/003_jail_and_features.sql`)

Шинэ Supabase database-ийн бүрэн PostgreSQL схемийг
`migrations/001_baseline.sql` нэг дор үүсгэнэ. Jail, guild log channel болон
lottery хүснэгтүүд baseline-д багтсан; migration runner нь SHA-256 checksum-ээр
хэрэглэгдсэн файлыг дахин өөрчлөхөөс хамгаална.

---

## 4. АРХИТЕКТУР БА КОМАНДЫН ХАТУУ ДҮРМҮҮД

1. **Prefix vs. Slash хатуу ялгалт:**
   * Тоглогчийн бүх команд (`economy`, `rpg`, `casino`, `games`, `help`, `ping`) нь `@commands.command(...)` буюу **Prefix (`a!`)** команд байна (`hybrid_command` ашиглахгүй).
   * Админ командууд (`cogs/system/admin.py`) нь `@app_commands.command(...)` буюу **Slash (`/admin_*`)** команд байна (`@app_commands.default_permissions(administrator=True)`).
2. **Давхаргат тусгаарлалт ба Одоогийн SQL-ийн дүрэм:**
   * `cogs/` болон `ui/` нь SQL бичихгүй, зөвхөн `services/` дуудна.
   * Гүйлгээ бүрд `transactions` хүснэгтийн **`balance_after`** баганыг заавал бөглөнө (`001_baseline.sql` ба `002_hardening.sql`-ийн дагуу).
   * `transactions`, `casino_logs`, `game_logs` хүснэгтүүд нь append-only тул хэзээ ч `UPDATE` эсвэл `DELETE` хийхгүй.
3. **Interactive UI (`Button`, `StringSelect`, `Modal`) & 3 секундийн дүрэм:**
   * Prefix команд нь `Modal` шууд нээж чадахгүй тул эхлээд Anime-style Embed + `AetherView` (Button/Select)-ийг илгээнэ.
   * Хэрэглэгч товч дарахад `interaction.response.send_modal(...)`-ийг `defer()` хийлгүйгээр шууд дуудна. Бүх DB болон баланс шалгалтыг `Modal.on_submit()` дотор гүйцэтгэнэ.
   * `AetherView` (`ui/common/base.py`) нь `interaction_check` дотор `interaction.user.id == self.author_id` эсэхийг шалгаж, өөр хүн дарвал `ephemeral=True`-аар `"✦ Энэ цэс зөвхөн эзэндээ нээлттэй."` гэж хариулна.
4. **Шоронгийн (`Jail`) логик:**
   * `@not_jailed()` декоратор нь `work`, `crime`, `rob`, бүх `casino` болон `games` командуудыг хамгаална.
   * `a!crime` эсвэл `a!rob` бүтэлгүйтвэл торгууль суутгаад, `JailService.imprison(user_id, minutes, bail_cost)` дуудаж шоронд хийнэ (`Shadow Step` skill нь шоронгийн хугацаа болон батлан даалтын үнийг түвшин бүрд `5%`, дээд тал нь `25%` бууруулна).

---

## 5. КОМАНД БҮРИЙН БҮРЭН ЖАГСААЛТ БА ХОЛБОЛТ

| Бүлэг | Командууд (Prefix `a!` + Aliases) | Холбогдох Сервисүүд | Интерактив UI (`ui/`) |
| :--- | :--- | :--- | :--- |
| **Economy (Wallet)** | `a!balance` (`bal`), `a!deposit` (`dep`), `a!withdraw` (`wd`), `a!transfer` (`pay`) | `WalletService`, `SkillService` | `BalanceView` (`[Хийх]`, `[Авах]`, `[Шилжүүлэх]` → `Modal`) |
| **Economy (Income)** | `a!daily`, `a!work` | `IncomeService`, `SkillService`, `LevelService` | `WorkView` (`StringSelect`-ээр ажил сонгох) |
| **Economy (Crime & Jail)** | `a!crime`, `a!rob @user`, `a!jail`, `a!bail` | `CrimeService`, `JailService`, `WalletService`, `SkillService` | `CrimeView` (`StringSelect`), `JailView` (`[Батлан даалтаар гарах]` Button) |
| **RPG (Profile & Level)** | `a!profile` (`p`), `a!rank`, `a!leaderboard` (`lb`) | `LevelService`, `WalletService`, `SkillService` | `ProfileView` (`[Inventory]`, `[Skills]`, `[Bio засах (Modal)]`), `LeaderboardView` (`StringSelect`) |
| **RPG (Skills)** | `a!skills` (`sk`), `a!upgrade`, `a!activate` | `SkillService` | `SkillTreeView` (`StringSelect`-ээр салбар ба skill сонгож `[+1 Сайжруулах]`, `[Идэвхжүүлэх]` Button) |
| **RPG (Shop & Inv)** | `a!shop`, `a!buy`, `a!inventory` (`inv`), `a!use`, `a!equip` | `ShopService`, `InventoryService`, `WalletService`, `SkillService` | `ShopView` (`StringSelect` ангилал, хуудаслагч, `BuyQuantityModal`), `InventoryView` (`[Ашиглах/Зүүх]`) |
| **Casino** | `a!slots` (`s`), `a!blackjack` (`bj`), `a!roulette` (`r`), `a!minefield` (`mf`), `a!coinflip` (`cf`), `a!crash` (`cr`), `a!lottery` (`lot`) | Тус бүрийн `CasinoService` + `WalletService` (Escrow) + `SkillService` (`Lucky Star`) | Тоглоом бүрийн интерактив товчнууд (`[Hit]`, `[Stand]`, `[Cashout]`, `[Дахин]`, `[Бооцоо (Modal)]`, 4x4 Grid) |
| **Games & PvP** | `a!duel @user <bet>`, `a!adventure` (`adv`), `a!hunt`, `a!fish`, `a!boss` | Тус бүрийн `GameService` + `WalletService` + `SkillService` (`Critical Strike`) + `LevelService` | `DuelView` (Accept/Decline + Turn-based `[Довтлох]`, `[Skill]`, `[Хамгаалах]`), `AdventureView`, `BossView` |
| **System & Help** | `a!help`, `a!ping`, `a!settings` | `GuildRepository` | `HelpView` (`StringSelect` категори сонгогч) |
| **Admin (Зөвхөн `/`)** | `/admin_economy`, `/admin_jail`, `/admin_shop`, `/admin_skill`, `/admin_config` | Бүх сервис + `GuildRepository` | Ephemeral баталгаажуулалт ба Embed |

---

## 6. AI ХӨГЖҮҮЛЭГЧИД ӨГӨХ MASTER CONTINUATION PROMPT

Доорх промптыг хуулж аваад `aether_bot` хавтас дотор ажиллаж буй AI хөгжүүлэгч (Cursor / Claude Code / AgentCore) руу шууд өгөөрэй:

```markdown
Бид `aether_bot` төсөл дээр үргэлжлүүлэн ажиллаж байна. Одоогийн байдлаар `core/` (`database.py`, `locks.py`, `rate_limiter.py`, `event_bus.py`, `skill_catalog.py`, `exceptions.py`), `migrations/001_baseline.sql`, `migrations/002_hardening.sql`, `repositories/user_repo.py`, `repositories/skill_repo.py`, `services/rpg/skill_service.py` болон 71 unit тест бүрэн ажиллаж байгаа.

### ХАТУУ АНХААРУУЛГА (DO NOT BREAK):
1. `migrations/001_baseline.sql` болон `migrations/002_hardening.sql` файлуудыг ОГТ ЗАСАЖ БОЛОХГҮЙ (SHA-256 checksum шалгадаг). Шинэ багана, хүснэгтийг зөвхөн `migrations/003_jail_and_features.sql` файлаар нэмнэ.
2. `transactions`, `casino_logs`, `game_logs` хүснэгтүүд нь append-only триггертэй тул зөвхөн `INSERT` хийнэ (`balance_after` баганыг заавал тооцож бичнэ).
3. `cogs/` болон `ui/` дотор SQL бичихгүй, бизнес логик бодохгүй. `services/` дотор `discord` импортлохгүй.
4. Энгийн хэрэглэгчийн бүх команд **Prefix (`@commands.command`, `a!`)** байна (`hybrid_command` биш). Зөвхөн Админ командууд (`cogs/system/admin.py`) **Slash (`@app_commands.command`, `/admin_*`)** байна.
5. Бүх UI нь Anime/Cyber-Fantasy стилийн Embed + `AetherView` (`Button`, `StringSelect`, `Modal`) ашиглана. `Modal` нь заавал товч дарахад `interaction.response.send_modal()`-аар (`defer()` хийлгүйгээр) нээгдэнэ.
6. Бүх тест (`pytest -q -W error`), `ruff check .`, `mypy` алдаагүй давдаг хэвээр байх ёстой.

### ГҮЙЦЭТГЭХ ҮЕ ШАТУУД (ШАТ ДАРААЛАН БИЧИЖ ТЕСТЛЭХ):

#### Ээлж 1: Схем өргөтгөл, Repositories & Core Checks
1. `migrations/003_jail_and_features.sql` үүсгэ (`users.jail_until`, `users.jail_bail_cost`, `guild_settings.log_channel_id`, `lottery_tickets`).
2. `core/exceptions.py` дээр `JailedError`, `ItemNotFoundError`, `InvalidBetError` нэм; `core/checks.py` дээр `@not_jailed()` декоратор бич.
3. `utils/validators.py` (дүн болон бооцоо задлагч: `"all"`, `"half"`, `"10k"`).
4. `repositories/user_repo.py`-г өргөтгөж (wallet/bank/xp/level/jail_until/casino_net атомик шинэчлэлт), `shop_repo.py`, `cooldown_repo.py`, `guild_repo.py`, `log_repo.py` файлуудыг бүрэн бич.
5. `services/rpg/skill_service.py`-ийн `Modifiers` дээр `jail_reduction_pct` нэм.

#### Ээлж 2: Economy, Jail & RPG Services
1. `services/economy/wallet_service.py` (deposit, withdraw, transfer + `guild_settings.tax_pct`, escrow lock/release/refund).
2. `services/economy/income_service.py` (`daily` streak + `work` + `Golden Touch` bonus + `XPGained` event).
3. `services/economy/jail_service.py` & `crime_service.py` (`crime`, `rob` — зорилтын `shield_until` болон `Aether Shield` шалгах, бүтэлгүйтвэл торгууль + шоронд хийх, `bail`-ээр гарах).
4. `services/rpg/level_service.py` (`EventBus` дээр `XPGained` сонсож `required_xp = int(100 * (level ** 1.5))` шалгах, түвшин ахихад +2 SP болон `level * 200` Coin өгч `LevelUp` нийтлэх).
5. `services/rpg/shop_service.py` & `inventory_service.py` (`Merchant's Eye` хөнгөлөлт, item худалдаж авах, `Aether Shield Charm`, `Astral XP Elixir`, `Tome of Rebirth` -> `skill_service.reset()`, `Shadowstep Elixir`, `Title` зүүх).

#### Ээлж 3: Casino & Games Services
1. `services/casino/`: `slots_service.py`, `blackjack_service.py`, `roulette_service.py`, `minefield_service.py`, `coinflip_service.py`, `crash_service.py`, `lottery_service.py` (бүгд Escrow + 4% House Edge + `Lucky Star` cashback + `casino_logs`).
2. `services/games/`: `duel_service.py` (1v1 turn-based + `multi_user_lock` + `Critical Strike` consume), `adventure_service.py`, `hunt_fish_service.py`, `boss_service.py`.

#### Ээлж 4: Interactive Anime UI (`ui/`) & Cogs (`cogs/`)
1. `ui/common/base.py` (`AetherView`), `ui/common/modals.py` (`AmountModal`, `TransferModal`, `BetModal`, `BuyQuantityModal`, `BioModal`), `ui/common/paginator.py`.
2. Модуль тус бүрийн View болон Cog-уудыг (`cogs/economy/*`, `cogs/rpg/*`, `cogs/casino/*`, `cogs/games/*`, `cogs/system/*`) үүсгэж `bot.py` дээр ачаал. Хуучин давхардсан `cogs/economy.py`, `cogs/skills.py`, `cogs/admin.py`, `cogs/health.py`-г шинэ ангилсан бүтэц рүү шилжүүл.
3. Шинэ сервис болон командуудад зориулсан `pytest` тестүүдийг нэмж, бүх шалгалтыг (`pytest`, `ruff`, `mypy`) ажиллуулж баталгаажуул.
```
