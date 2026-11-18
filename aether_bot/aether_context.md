# AETHER DISCORD BOT — PROJECT CONTEXT & ARCHITECTURE

> Энэхүү файл нь **Aether** Discord ботыг хөгжүүлэхэд ашиглах үндсэн контекст, архитектурын дүрэм, өгөгдлийн сангийн схем, команд хоорондын холболт, Шорон (Jail) систем болон Skills логикийн техникийн баримт бичиг юм. Төслийн санааг [DarkMooN-SYS/MongolBot](https://github.com/DarkMooN-SYS/MongolBot)-ийн модульчлагдсан бүтцээс уламжлан авч, орчин үеийн Layered Architecture + Atomic Service Layer + Interactive UI болгон шинэчилсэн.

## 1. ТӨСЛИЙН ЕРӨНХИЙ МЭДЭЭЛЭЛ

* **Ботын нэр:** Aether

* **Сэдэв / Харагдах байдал:** Anime / Cyber-Fantasy RPG & Economy

* **Хэл:** Хэрэглэгчийн бүх UI текст нь цэвэрхэн, загварлаг Монгол хэл дээр (техникийн болон RPG нэршил хосолсон).

* **Командын дүрэм (Prefix vs. Slash):**

  * **Энгийн хэрэглэгчийн командууд:** Бүгд **Prefix** команд байна (Өгөгдмөл угтвар: `a!`, сервер бүрээр өөрчлөх боломжтой, товч alias-тай: `a!bal`, `a!bj`, `a!s` г.м.). `discord.Intents.message_content = True` заавал идэвхтэй байна.

  * **Админ командууд:** Бүгд **Slash Command (`/`)** хэлбэртэй байна (`app_commands`, зөвхөн Administrator / Bot Owner эрхтэй).

* **Технологийн стек:**

  * **Runtime:** Python 3.11+

  * **Discord API:** `discord.py` 2.4+ (Prefix Commands + `discord.ui.View`, `Button`, `StringSelect`, `Modal` + Admin Slash Commands)

  * **Database:** `aiosqlite` (WAL mode + Foreign Keys идэвхжүүлсэн). Одоогийн SQL нь SQLite-д тусгайлагдсан (`?` placeholder, `INSERT OR IGNORE`, `lastrowid`, PRAGMA) тул PostgreSQL руу шилжихэд Repository давхаргад dialect layer нэмэх шаардлагатай.

  * **Concurrency & Rate Limit:** `asyncio.Lock` (хэрэглэгч тус бүр дээр race condition хаах), Global Rate Limiter (Discord-ийн 50 req/s хязгаараас сэргийлж **45 req/s** дээр хязгаарлана).

## 2. ХАВТАСНЫ БҮТЭЦ (DOMAIN-BASED FOLDER STRUCTURE)

```text
aether-bot/
├── bot.py                          # Entry point, Dynamic Prefix, Cogs auto-loader
├── config.py                       # Өнгөний палитр, тогтмолууд, .env уншигч
├── requirements.txt                # discord.py, aiosqlite, python-dotenv, pytest
├── README.md                       # Суулгах заавар, ботын танилцуулга
├── .env                            # DISCORD_TOKEN, DB_PATH, DEFAULT_PREFIX, LOG_LEVEL
├── .gitignore                      # .env, data/db/*.db, logs/, __pycache__/
│
├── assets/                         # Визуал медиа файлууд
│   ├── banners/                    # Casino, Shop, Duel, Jail embed баннерууд
│   └── thumbnails/                 # Aether систем болон NPC дүрийн зургууд
│
├── data/                           # Статик тохиргоо ба Өгөгдлийн сан (Ангиллаар)
│   ├── db/
│   │   └── aether.db               # SQLite өгөгдлийн сан (WAL mode)
│   ├── economy/
│   │   ├── jobs.json               # Ажлын жагсаалт, шаардагдах level, цалин
│   │   └── crimes.json             # Гэмт хэргийн төрлүүд, эрсдэл, шоронгийн хугацаа
│   ├── rpg/
│   │   ├── skills.json             # 3 салбарын Skill Tree, max level, modifier
│   │   ├── shop_items.json         # Дэлгүүрийн бараанууд (seed data)
│   │   ├── dungeons.json           # Adventure өрөөнүүд, унах олз
│   │   └── bosses.json             # World Boss-ийн HP, дайралт, шагнал
│   └── ui/
│       ├── anime_quotes.json       # Embed footer болон NPC ишлэлүүд
│       └── banners.json            # Embed зураг/GIF URL-ууд
│
├── core/                           # Системийн дэд бүтэц (Infrastructure)
│   ├── __init__.py
│   ├── database.py                 # aiosqlite connection manager, WAL mode, migrations
│   ├── locks.py                    # Per-user asyncio.Lock manager (Race condition хаах)
│   ├── rate_limiter.py             # Global 45 req/s rate limiter & stats monitor
│   ├── event_bus.py                # Async EventBus (XP, LevelUp, Jail, Transaction)
│   ├── checks.py                   # @not_jailed(), @is_admin(), @has_cooldown()
│   └── exceptions.py               # InsufficientFundsError, CooldownError, JailedError
│
├── utils/                          # Ерөнхий туслах функцүүд (Pure helpers)
│   ├── __init__.py
│   ├── logger.py                   # Rotating file & console logging
│   ├── formatters.py               # Тоо форматлах (1,000,000), progress bar (▰▱)
│   ├── time_utils.py               # Cooldown ба шоронгийн үлдсэн хугацаа форматлах
│   └── validators.py               # Бооцооны дүн ("all", "half", "10k") задлагч
│
├── repositories/                   # Өгөгдлийн сангийн давхарга (Зөвхөн SQL)
│   ├── __init__.py
│   ├── user_repo.py                # users хүснэгтийн CRUD, atomic balance/xp/jail
│   ├── skill_repo.py               # user_skills хүснэгтийн CRUD
│   ├── shop_repo.py                # shop_items, inventory хүснэгтүүд
│   ├── cooldown_repo.py            # cooldowns хүснэгтийн удирдлага
│   ├── guild_repo.py               # guild_settings (prefix, tax_rate, log_channel)
│   └── log_repo.py                 # transactions, casino_logs, duel_logs
│
├── services/                       # Бизнес логик (Ангиллаар, Discord обьектгүй)
│   ├── __init__.py
│   ├── economy/
│   │   ├── wallet_service.py       # Balance, Deposit, Withdraw, Transfer, Tax, Escrow
│   │   ├── income_service.py       # Daily Streak, Work
│   │   ├── crime_service.py        # Crime, Rob магадлал ба тооцоо
│   │   └── jail_service.py         # Шоронд оруулах, хугацаа шалгах, батлан даалт
│   ├── rpg/
│   │   ├── level_service.py        # XP тооцоо, Level-up шалгалт, SP олголт
│   │   ├── skill_service.py        # Skill Tree, get_modifiers(), Active skill & Cooldown
│   │   ├── shop_service.py         # Дэлгүүрийн үнэ, Merchant's Eye хөнгөлөлт, Худалдан авалт
│   │   └── inventory_service.py    # Item ашиглах (Booster, Shield, Scroll), Title зүүх
│   ├── casino/
│   │   ├── slots_service.py        # Slots магадлал, үржүүлэгч, Lucky Star cashback
│   │   ├── blackjack_service.py    # Хөзрийн тавцан, Dealer логик, Escrow
│   │   ├── roulette_service.py     # Roulette хүрд ба төлөлт
│   │   ├── minefield_service.py    # Бөмбөгний байрлал, алхмын үржүүлэгч
│   │   ├── crash_service.py        # Crash муруй ба санамсаргүй цэг
│   │   └── lottery_service.py      # Тасалбар, Jackpot сан, тохирол
│   └── games/
│       ├── duel_service.py         # 1v1 PvP ээлжит тулааны тооцоо
│       ├── adventure_service.py    # Dungeon өрөө, сонголт, олз
│       ├── hunt_fish_service.py    # Ан ба загасчлалын олз, tool нөлөө
│       └── boss_service.py         # World Boss Raid HP ба шагнал хуваарилалт
│
├── ui/                             # Anime-Style UI (Ангиллаар)
│   ├── __init__.py
│   ├── common/
│   │   ├── base.py                 # AetherView (author_id шалгалт, timeout disable)
│   │   ├── embeds.py               # Anime-style Embed builder, Quote & Color helper
│   │   ├── modals.py               # DepositModal, WithdrawModal, TransferModal, BetModal, BioModal
│   │   └── paginator.py            # Олон хуудастай жагсаалтын View
│   ├── economy/
│   │   ├── balance_view.py         # Wallet/Bank товч ба Modal дуудагч
│   │   ├── work_view.py            # Ажлын сонголтын StringSelect
│   │   ├── crime_view.py           # Гэмт хэргийн сонголтын StringSelect
│   │   └── jail_view.py            # Шоронгийн статус болон [Батлан даалт] товч
│   ├── rpg/
│   │   ├── profile_view.py         # Adventurer Card + [Inventory] [Skills] [Bio]
│   │   ├── skill_view.py           # Skill Tree Branch Select + Upgrade/Use товч
│   │   ├── shop_view.py            # Ангилал Select, Pagination, Buy Modal
│   │   └── inventory_view.py       # Item Select + [Ашиглах / Зүүх] товч
│   ├── casino/
│   │   ├── slots_view.py           # [Дахин], [2x], [Бооцоо (Modal)]
│   │   ├── blackjack_view.py       # [Hit], [Stand], [Double Down]
│   │   ├── roulette_view.py        # Бооцооны төрөл Select & Spin товч
│   │   ├── minefield_view.py       # 4x4 эсвэл 5x4 Grid Button + [Cashout]
│   │   └── crash_view.py           # Амьд үржүүлэгч ба [Cashout] товч
│   └── games/
│       ├── duel_view.py            # [Зөвшөөрөх/Татгалзах] + [Довтлох/Skill/Хамгаалах]
│       ├── adventure_view.py       # Өрөөний сонголтын товчнууд
│       ├── hunt_fish_view.py       # Мини-тоглоомын товчнууд
│       └── boss_view.py            # Нийтийн Raid Boss [Довтлох] товч
│
├── cogs/                           # Discord командууд (Ангиллаар, нэг файл = нэг үүрэг)
│   ├── __init__.py
│   ├── system/
│   │   ├── help.py                 # a!help (Category SelectMenu), a!ping, a!tutorial
│   │   ├── events.py               # on_message (XP), on_command_error (Jailed/Cooldown)
│   │   └── admin.py                # /admin_economy, /admin_jail, /admin_shop, /admin_skill, /admin_config
│   ├── economy/
│   │   ├── wallet.py               # a!bal, a!dep, a!wd, a!pay
│   │   ├── income.py               # a!daily, a!work
│   │   ├── crime.py                # a!crime, a!rob
│   │   └── jail.py                 # a!jail, a!bail
│   ├── rpg/
│   │   ├── profile.py              # a!profile, a!rank, a!lb
│   │   ├── skills.py               # a!skills
│   │   ├── shop.py                 # a!shop, a!buy
│   │   └── inventory.py            # a!inv, a!use, a!equip
│   ├── casino/
│   │   ├── slots.py                # a!slots (s)
│   │   ├── blackjack.py            # a!blackjack (bj)
│   │   ├── roulette.py             # a!roulette (r)
│   │   ├── minefield.py            # a!minefield (mf)
│   │   ├── coinflip.py             # a!coinflip (cf)
│   │   ├── crash.py                # a!crash (cr)
│   │   └── lottery.py              # a!lottery (lot)
│   └── games/
│       ├── duel.py                 # a!duel
│       ├── adventure.py            # a!adventure (adv)
│       ├── hunt.py                 # a!hunt
│       ├── fish.py                 # a!fish
│       └── boss.py                 # a!boss
│
└── tests/                          # Тест ба Эдийн засгийн баланс симулятор
    ├── test_economy.py             # Atomic transaction & race condition тест
    ├── test_skills.py              # Skill modifier & cooldown тест
    ├── test_jail.py                # Crime/Rob шорон ба bail хөнгөлөлтийн тест
    └── test_casino_sim.py          # 10,000+ тоглолтын offline магадлал/баланс шалгагч
```

## 3. АРХИТЕКТУРЫН ХАТУУ ДҮРМҮҮД (CRITICAL RULES)

1. **Давхаргат тусгаарлалт:**

   * `cogs/` болон `ui/` дотор **SQL бичихгүй**, бизнес логик бодож болохгүй. Тэд зөвхөн `services/`-ийг дуудна.

   * `services/` нь `discord` обьекттой шууд харьцахгүй (зөвхөн Python дата бүтэц буцаана).

2. **Prefix + Interactive Modal холболт:**

   * Prefix команд нь `Modal`-ийг шууд нээж чаддаггүй тул prefix команд эхлээд Anime-style Embed + `Button`/`StringSelect`-тэй мессеж илгээнэ. Хэрэглэгч товч дарахад (`Button.callback`) `interaction.response.send_modal()`-аар 3 секундийн дотор (`defer()` хийлгүйгээр) `Modal` нээнэ.

   * Database шалгалтыг `Modal.on_submit()` дотор хийнэ.

3. **Атомик Гүйлгээ ба Escrow:**

   * Мөнгө хасах/нэмэх бүх үйлдэл `async with user_lock(user_id):` болон `BEGIN IMMEDIATE` SQL транзакци дотор хийгдэнэ.

   * Казино болон `a!duel` эхлэхэд бооцоог эхлээд **Escrow** хэлбэрээр суутгаж, тоглоом дуусахад хожигчид шилжүүлнэ.

4. **Шоронгийн (Jail) хамгаалалт:**

   * `@not_jailed()` check нь `work`, `crime`, `rob`, бүх `casino` болон `games` командуудын өмнө ажиллана. Хэрэв хэрэглэгч шоронд байвал үлдсэн хугацаа болон `[Батлан даалтаар гарах]` товчийг харуулна.

5. **UI Хамгаалалт:**

   * Бүх `discord.ui.View` нь `author_id`-г хадгалж, өөр хэрэглэгч товч дарвал `ephemeral=True`-аар `"✦ Энэ цэс зөвхөн эзэндээ нээлттэй."` гэж хариулна.

   * `on_timeout()` үед бүх товч болон select-ийг `disabled=True` болгож мессежийг шинэчилнэ.

## 4. ӨГӨГДЛИЙН САНГИЙН СХЕМ (SQLITE SCHEMA)

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id         INTEGER PRIMARY KEY,
    wallet          INTEGER NOT NULL DEFAULT 500 CHECK (wallet >= 0),
    bank            INTEGER NOT NULL DEFAULT 0 CHECK (bank >= 0),
    xp              INTEGER NOT NULL DEFAULT 0 CHECK (xp >= 0),
    level           INTEGER NOT NULL DEFAULT 1 CHECK (level >= 1),
    skill_points    INTEGER NOT NULL DEFAULT 0 CHECK (skill_points >= 0),
    daily_streak    INTEGER NOT NULL DEFAULT 0,
    last_daily_at   TIMESTAMP,
    shield_until    TIMESTAMP,
    jail_until      TIMESTAMP,
    jail_bail_cost  INTEGER NOT NULL DEFAULT 0,
    active_title    TEXT DEFAULT 'Wanderer',
    bio             TEXT DEFAULT 'Aether ертөнцийн аялагч.',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_skills (
    user_id         INTEGER NOT NULL,
    skill_id        TEXT NOT NULL,
    skill_level     INTEGER NOT NULL DEFAULT 0,
    last_used_at    TIMESTAMP,
    active_until    TIMESTAMP,
    PRIMARY KEY (user_id, skill_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS shop_items (
    item_id         TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    category        TEXT NOT NULL, -- 'defense', 'booster', 'title', 'scroll', 'tool'
    price           INTEGER NOT NULL CHECK (price > 0),
    description     TEXT NOT NULL,
    effect_type     TEXT NOT NULL,
    effect_value    REAL NOT NULL DEFAULT 0,
    duration_sec    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS inventory (
    user_id         INTEGER NOT NULL,
    item_id         TEXT NOT NULL,
    quantity        INTEGER NOT NULL DEFAULT 1 CHECK (quantity >= 0),
    PRIMARY KEY (user_id, item_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES shop_items(item_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cooldowns (
    user_id         INTEGER NOT NULL,
    action_key      TEXT NOT NULL, -- 'work', 'crime', 'rob', 'hunt', 'fish', 'adv', 'xp_chat'
    expires_at      TIMESTAMP NOT NULL,
    PRIMARY KEY (user_id, action_key)
);

CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id        INTEGER PRIMARY KEY,
    prefix          TEXT NOT NULL DEFAULT 'a!',
    tax_rate        REAL NOT NULL DEFAULT 0.05,
    log_channel_id  INTEGER
);

CREATE TABLE IF NOT EXISTS transactions (
    tx_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    amount          INTEGER NOT NULL, -- + орлого, - зарлага
    source          TEXT NOT NULL,    -- 'daily', 'work', 'crime', 'rob', 'bail', 'casino', 'shop'
    metadata        TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 5. КОМАНД БҮРИЙН ҮҮРЭГ БА ХОЛБОЛТ

### А. Эдийн засаг, Гэмт хэрэг ба Шорон (Prefix: `a!`)

| Команд (Aliases) | UI Компонент | Холбогдох Сервисүүд | Үндсэн үүрэг ба Өгөгдлийн урсгал | 
| ----- | ----- | ----- | ----- | 
| `a!balance` (`bal`) | `Button`, `Modal` | `WalletService`, `LevelService` | Wallet, Bank, Net Worth харуулна. `[Хийх]`, `[Авах]`, `[Шилжүүлэх]` товч нь `Modal` нээж дүн авна. | 
| `a!deposit <дүн/all>` (`dep`) | `Button` | `WalletService` | Wallet-аас Bank руу шууд мөнгө хийнэ. | 
| `a!withdraw <дүн/all>` (`wd`) | `Button` | `WalletService` | Bank-аас Wallet руу шууд мөнгө авна. | 
| `a!transfer @user <дүн>` (`pay`) | `Button` (Confirm) | `WalletService` | Өөр тоглогч руу татвартай (`tax_rate`) мөнгө шилжүүлнэ. | 
| `a!daily` | `Button` | `IncomeService`, `SkillService`, `LevelService` | 24 цагийн шагнал + Streak. `Level` болон `Golden Touch` skill-ээс хамаарч өснө. | 
| `a!work` | `StringSelect`, `Button` | `IncomeService`, `SkillService`, `LevelService` | Сонгосон ажлаар Coin болон XP олно (`Golden Touch` ба `Astral Resonance` нөлөөлнө). | 
| `a!crime` | `StringSelect`, `Button` | `CrimeService`, `JailService`, `SkillService` | Эрсдэлтэй гэмт хэрэг (Хакдах, Хулгай, Контрабанд). Амжилттай бол өндөр шагнал, **бүтэлгүйтвэл торгууль + Шоронд орно**. | 
| `a!rob @user` | `Button` | `CrimeService`, `JailService`, `SkillService` | Зорилтот хэрэглэгчийн Wallet-аас дээрэмдэнэ. `Aether Shield` эсвэл `shield_until` шалгана. **Бүтэлгүйтвэл шоронд орно**. | 
| `a!jail` | `Button` (`[Батлан даалт]`) | `JailService` | Шоронгийн үлдсэн хугацаа болон батлан даалтын үнийг харуулна. | 
| `a!bail` | `Button` (Confirm) | `JailService`, `WalletService`, `SkillService` | Батлан даалтын мөнгө төлж шоронгоос хугацаанаасаа өмнө гарна (`Shadow Step` хөнгөлөлт өгнө). | 

### Б. Профайл, Level, Skills & Дэлгүүр (Prefix: `a!`)

| Команд (Aliases) | UI Компонент | Холбогдох Сервисүүд | Үндсэн үүрэг ба Өгөгдлийн урсгал | 
| ----- | ----- | ----- | ----- | 
| `a!profile [@user]` (`p`) | `Button`, `Modal` | `LevelService`, `SkillService`, `WalletService` | Anime Adventurer Card. `[Inventory]`, `[Skills]`, `[Bio засах (Modal)]` товчнуудтай. | 
| `a!rank [@user]` | — | `LevelService` | Түвшин, XP progress bar болон дараагийн түвшний шагналыг харуулна. | 
| `a!leaderboard` (`lb`) | `StringSelect` | `WalletService`, `LevelService` | Ангилал: `Хамгийн баян`, `Өндөр Level`, `Шоронгийн ахлагч`. | 
| `a!skills` (`sk`) | `StringSelect`, `Button` | `SkillService`, `LevelService` | 3 салбарын Skill Tree. `[+1 Сайжруулах]` болон Active skill `[Ашиглах]` товчтой. | 
| `a!shop` | `StringSelect`, `Button`, `Modal` | `ShopService`, `WalletService`, `SkillService` | Ангилал шүүх, хуудаслах. `Merchant's Eye` хямдрал харуулна. Тоо ширхэгээр авахад `Modal` нээнэ. | 
| `a!buy <item> [тоо]` | `Button` | `ShopService`, `WalletService` | Дэлгүүрээс шууд нэрээр нь худалдаж авах. | 
| `a!inventory` (`inv`) | `StringSelect`, `Button` | `InventoryService`, `LevelService`, `SkillService` | Item жагсаалт болон `[Ашиглах / Зүүх]` товч. | 
| `a!use <item>` / `a!equip <title>` | — | `InventoryService`, `SkillService` | Booster, Shield, Skill Reset Tome эсвэл Anime цолыг шууд идэвхжүүлэх. | 

### В. Казиногийн бие даасан командууд (Prefix: `a!`, `@not_jailed()`)

| Команд (Aliases) | UI Компонент | Холбогдох Сервисүүд | Үндсэн үүрэг ба Өгөгдлийн урсгал | 
| ----- | ----- | ----- | ----- | 
| `a!slots <бооцоо>` (`s`) | `Button` (`[Дахин]`, `[2x]`, `[Бооцоо (Modal)]`) | `SlotsService`, `WalletService`, `SkillService` | Anime/Cyber тэмдэгтүүдтэй 3x3 Slot машин. Хожигдвол `Lucky Star` Cashback буцаана. | 
| `a!blackjack <бооцоо>` (`bj`) | `Button` (`[Hit]`, `[Stand]`, `[Double Down]`) | `BlackjackService`, `WalletService`, `SkillService` | Сонгодог Blackjack. Бооцоо Escrow-д түгжигдэнэ. | 
| `a!roulette <бооцоо> <сонголт>` (`r`) | `StringSelect`, `Button` | `RouletteService`, `WalletService`, `SkillService` | Улаан/Хар, Тэгш/Сондгой эсвэл Тоо (0-36) дээр бооцоо тавих. | 
| `a!minefield <бооцоо>` (`mf`) | `Button` (5x4 эсвэл 4x4 Grid) | `MinefieldService`, `WalletService`, `SkillService` | Тэсрэх бөмбөггүй нүд нээх бүрд үржүүлэгч өснө, `[Cashout]` товчоор мөнгөө авна. | 
| `a!coinflip <бооцоо> <h/t>` (`cf`) | `Button` (`[Дахин эргүүлэх]`) | `SlotsService` / `WalletService` | Хурдан зоос шидэлт (Heads/Tails). | 
| `a!crash <бооцоо>` (`cr`) | `Button` (`[Cashout]`) | `CrashService`, `WalletService`, `SkillService` | Үржүүлэгч өсөж байгаад санамсаргүй цэгт унахаас өмнө Cashout хийнэ. | 
| `a!lottery [тоо]` (`lot`) | `Button` (`[Тасалбар авах (Modal)]`) | `LotteryService`, `WalletService` | Серверийн эсвэл глобал сугалааны сан (Jackpot pool). | 

### Г. Тоглоом ба RPG командууд (Prefix: `a!`, `@not_jailed()`)

| Команд (Aliases) | UI Компонент | Холбогдох Сервисүүд | Үндсэн үүрэг ба Өгөгдлийн урсгал | 
| ----- | ----- | ----- | ----- | 
| `a!duel @user <бооцоо>` | `Button` (Accept + Turn-based Combat) | `DuelService`, `WalletService`, `SkillService` | 1v1 Anime тулаан (`[Довтлох]`, `[Skill ашиглах]`, `[Хамгаалах]`). Бооцоо Escrow-д түгжигдэнэ. | 
| `a!adventure` (`adv`) | `Button` (Choice-based Story) | `AdventureService`, `LevelService`, `InventoryService` | RPG Dungeon даалгавар. Төгсгөлд нь Coin, XP болон ховор Item унагана. | 
| `a!hunt` | `Button` | `HuntFishService`, `WalletService`, `LevelService` | Ан хийж олз (материал/мөнгө/XP) олох (Cooldown-тай, Tool item нөлөөлнө). | 
| `a!fish` | `Button` | `HuntFishService`, `WalletService`, `LevelService` | Загас барих мини-тоглоом (Хорвоогийн ховор олз, мөнгө, XP). | 
| `a!boss` | `Button` (Co-op Raid) | `BossService`, `SkillService`, `LevelService` | Серверийн нийтийн Raid Boss. Олон тоглогч `[Довтлох]` товчоор оролцож шагнал хуваана. | 

### Д. Админ командууд (Зөвхөн Slash Command: `/`)

| Команд | Эрх | Үндсэн үүрэг | 
| ----- | ----- | ----- | 
| `/admin_economy` | Administrator | Тоглогчид мөнгө/XP нэмэх, хасах, бүртгэл шалгах | 
| `/admin_jail` | Administrator | Тоглогчийг шоронд хийх эсвэл шоронгоос суллах (`unjail`) | 
| `/admin_shop` | Administrator | Дэлгүүрт шинэ Item нэмэх, үнэ засах, устгах | 
| `/admin_skill` | Administrator | Тоглогчийн SP нэмэх эсвэл Skill reset хийх | 
| `/admin_config` | Administrator | Серверийн угтвар (`prefix`), татварын хувь (`tax_rate`), log суваг тохируулах | 

## 6. SKILLS & JAIL СИСТЕМИЙН ЛОГИК БА БАЛАНС

* **Level & SP томьёо:**

  * Дараагийн түвшинд шаардагдах XP: `required_xp(level) = int(100 * (level ** 1.5))`

  * Түвшин ахих бүрд: **+2 Skill Point (SP)** болон `level * 200` Aether Coin олгоно.

* **Шоронгийн (Jail) томьёо:**

  * `a!crime` бүтэлгүйтвэл: `10–25 минут` шорон + батлан даалт `500 + (level * 100)` Coin.

  * `a!rob` бүтэлгүйтвэл: `15–40 минут` шорон + батлан даалт `800 + (level * 150)` Coin.

  * `Shadow Step` skill нь шоронд орох хугацаа болон батлан даалтын үнийг түвшин бүрд `5%` (дээд тал нь `25%`) бууруулна.

* **`SkillService.get_modifiers(user_id)` буцаах бүтэц:**

  * `work_income_mult`: `1.0 + (golden_touch_lv * 0.06)` *(Max +30%)*

  * `casino_cashback_pct`: `lucky_star_lv * 0.02` *(Max 10% cashback; хожих магадлалд нөлөөлөхгүй)*

  * `shop_discount_pct`: `merchants_eye_lv * 0.05` *(Max 15%)*

  * `rob_success_bonus`: `shadow_step_lv * 0.04` *(Max +20%)*

  * `jail_reduction_pct`: `shadow_step_lv * 0.05` *(Max 25%)*

  * `xp_gain_mult`: `1.0 + (astral_resonance_lv * 0.05)` *(Max +25%)*

  * `crit_active`: `bool` (`Critical Strike` идэвхтэй эсэх — `1.5x` damage, 2 цагийн cooldown)

  * `shield_active`: `bool` (`Aether Shield` идэвхтэй эсэх — 3 цаг дээрмээс хамгаална, 6 цагийн cooldown)

## 7. ANIME-STYLE EMBED СТАНДАРТ

* **Өнгөний палитр (`config.py`):**

  * `PRIMARY = 0x8A2BE2` (Aether Violet)

  * `CYAN = 0x00E5FF` (Cyber Cyan)

  * `SUCCESS = 0x2ECC71` (Emerald)

  * `DANGER = 0xFF4757` (Crimson — Алдаа болон Шоронгийн анхааруулга)

  * `GOLD = 0xFFD700` (Astral Gold — Jackpot болон Level Up)

* **Progress Bar функц:** `render_bar(current, total, length=10)` → жишээ нь: `▰▰▰▰▰▰▱▱▱▱ 60%`.

* **Уур амьсгал:** Бүх embed-ийн footer дээр Aether ертөнцийн богино ишлэл эсвэл хэрэглэгчийн идэвхтэй цолыг харуулна (жишээ нь: `✦ Aether System • [Cyber Ronin]`).