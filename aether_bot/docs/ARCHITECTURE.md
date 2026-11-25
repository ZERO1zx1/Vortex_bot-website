# Aether — Architecture, Schema & Data Flow

> Энэ баримт бичиг нь **хэрэгжүүлэлтийн** үнэн эх сурвалж.
> `aether_context.md` нь санаа/стандартыг, энэ файл нь бодит бүтэц, SQL схемийн
> тайлбар, модуль хоорондын урсгалыг тодорхойлно. SQL-ийн цорын ганц эх нь
> `migrations/NNN_*.sql` (connect хийх бүрд version + SHA-256-аар ажиллана).

---

## 1. Folder structure

```text
aether-bot/
├── bot.py                     # ✅ entry point, DB + cogs + HTTP guard
├── config.py                  # ✅ typed env, өнгө, тэнцвэрийн тогтмолууд
├── migrations/
│   └── 001_baseline.sql       # ✅ PostgreSQL schema + seed + RLS
├── requirements.txt           # ✅ pinned runtime deps
├── requirements-dev.txt       # ✅ pinned test/lint deps
├── README.md                  # ✅ setup, commands, checks
├── .env.example               # ✅
├── core/
│   ├── database.py            # ✅ asyncpg pool, transactions, migrations
│   ├── locks.py               # ✅ reentrant per-user / multi-key locks
│   ├── rate_limiter.py        # ✅ 45 req/s global + route bucket, HTTP guard
│   ├── event_bus.py           # ✅ typed async pub/sub
│   ├── exceptions.py          # ✅ Mongolian user_message-тэй домайн алдаанууд
│   └── skill_catalog.py       # ✅ 3 path, 7 skill
├── utils/
│   └── time_utils.py          # ✅ UTC ↔ PostgreSQL timestamp, humanize
├── repositories/
│   ├── user_repo.py           # ✅ users CRUD + atomic SP хасалт
│   └── skill_repo.py          # ✅ user_skills (түвшин, cooldown, active)
├── services/
│   └── rpg/skill_service.py   # ✅ get_modifiers / upgrade / activate / reset
├── ui/
│   └── embeds.py              # ✅ balance / skill tree embed + progress bar
├── cogs/
│   ├── health.py              # ✅ /ping
│   ├── economy.py             # ✅ /balance
│   ├── skills.py              # ✅ /skills /upgrade /activate
│   └── admin.py               # ✅ /setprefix /settings
└── tests/                     # ✅ 67 regression tests
```

Хамаарлын дүрэм: `cogs/ → ui/ → services/ → repositories/ → core/database.py`.
`services/` нь `discord` импортлохгүй; `cogs/ui` нь SQL бичихгүй.

---

## 2. Database schema

Supabase PostgreSQL-д TLS Session pooler-оор холбогдоно. Timestamp баганууд
`TIMESTAMPTZ`, metadata/detail баганууд `JSONB`, Discord ID-ууд `BIGINT` байна.

| Хүснэгт | Түлхүүр | Үүрэг |
| :--- | :--- | :--- |
| `users` | `user_id` PK | Wallet/Bank/XP/Level/SP, streak, `shield_until`, цол, bio, `casino_net` (leaderboard) |
| `user_skills` | (`user_id`, `skill_id`) PK | Түвшин, `last_used_at` (cooldown), `active_until` (эффект) |
| `shop_items` | `item_id` PK | Дэлгүүрийн каталог + эффектийн төрөл/утга |
| `inventory` | (`user_id`, `item_id`) PK | Эзэмшил, тоо ширхэг |
| `user_effects` | `effect_id` PK | Item-ээр олгогдсон түр эффект (XP booster, Shield) |
| `cooldowns` | (`user_id`, `action_key`) PK | `/work`, `/rob`, `/adventure`, `xp_chat` |
| `transactions` | `tx_id` PK | Мөнгөний append-only бүртгэл (`balance_after`-той) |
| `casino_logs` | `log_id` PK | Тоглоом, бооцоо, payout, outcome, detail JSON |
| `game_logs` | `log_id` PK | `/duel`, `/adventure`, hunt/fish/boss-ийн үр дүн |
| `guild_settings` | `guild_id` PK | Сервер бүрийн prefix, татвар |
| `schema_migrations` | `version` PK | Migration tracker + SHA-256 checksum |

### Foreign key холболт

```text
users 1 ──< user_skills      (ON DELETE CASCADE)
users 1 ──< inventory        (ON DELETE CASCADE)
users 1 ──< user_effects     (ON DELETE CASCADE)
users 1 ──< cooldowns        (ON DELETE CASCADE)
users 1 ──< transactions     (ON DELETE RESTRICT)
users 1 ──< casino_logs      (ON DELETE RESTRICT)
users 1 ──< game_logs.user_id       (ON DELETE RESTRICT)
users 1 ──< game_logs.opponent_id   (ON DELETE SET NULL)
shop_items 1 ──< inventory   (ON DELETE CASCADE)
```

`transactions`, `casino_logs`, `game_logs` нь **append-only**: `UPDATE`/`DELETE`
trigger-ээр хориотой, хэрэглэгчийг устгахад `RESTRICT` тул санхүүгийн түүх
устахгүй. `user_skills.skill_id` нь **FK биш** — skill тодорхойлолт код дотор
(`core/skill_catalog.py`) амьдардаг тул тэнцвэр өөрчлөхөд migration шаардахгүй.
`users.wallet/bank/xp` дээр `CHECK (>= 0)` — сөрөг баланс DB түвшинд хориотой.

Гүйцэтгэлийн индексүүд: `users(level DESC, xp DESC)`, `users(casino_net DESC)`,
`transactions(user_id, created_at DESC)`, `casino_logs(user_id, ...)`,
`game_logs(user_id, kind, ...)`, `user_effects(user_id, effect_type)`.

---

## 3. Модуль хоорондын өгөгдлийн урсгал

### 3.1 Ерөнхий дүрэм

```text
Slash command (cog)
   ↓ 1. defer / send_modal (3 сек дүрэм)
   ↓ 2. per-user lock + PostgreSQL транзакц (service дотор)
Service  ── SkillService.get_modifiers(user_id) ──→ Modifiers (1 удаа, кэш 15с)
   ↓
Repository (SQL) → Database (commit)
   ↓
EventBus.publish(...)  →  LevelService (XP), Quest систем, Log
   ↓
UI (embed + View) — зөвхөн үр дүнг харуулна
```

Бүх мөнгө хөдөлгөх service дараах дарааллыг баримтална:

1. `validate` (дүн, эрх, cooldown)
2. `async with user_lock(user_id):` / `multi_user_lock(a, b):`
3. `async with db.transaction():` (нэг asyncpg connection)
4. `SkillService.get_modifiers()` — бонусийг нэг л удаа уншина
5. `EconomyService`-ээр мөнгө хөдөлгөх + `transactions` бичих
6. commit → `EventBus.publish(MoneyChanged / XPGained / CasinoResolved)`

### 3.2 `/casino` (Slots жишээ)

1. **Lobby** — `SkillService.get_modifiers()` дуудаж, бооцооны лимит болон
   `Lucky Star` cashback %-ийг embed-д харуулна (мэдээллийн зорилго).
2. **Bet Modal** — `send_modal()` шууд (defer хийхгүй). `on_submit` дотор:
   `CASINO_MIN_BET ≤ bet ≤ CASINO_MAX_BET` ба `wallet ≥ bet` шалгана.
3. `CasinoService.play_slots(user_id, bet)`:
   1. `user_lock(user_id)` авна.
   2. `db.transaction()` → `EconomyService.escrow(user_id, bet)`:
      wallet-оос хасаж, `transactions`-д `casino_escrow` бичнэ.
   3. RNG (house edge 4%) → payout тооцно.
   4. `payout > 0` бол `EconomyService.credit(user_id, payout, source="casino_win")`;
      `payout == 0` бол `mods.cashback(bet)`-ийг `casino_cashback` эх сурвалжтай нэмнэ.
   5. `casino_logs` + `users.casino_net` шинэчилнэ.
   6. commit.
4. `EventBus.publish(CasinoResolved)` → `LevelService` XP өгнө
   (`mods.apply_xp(...)`), quest систем ахина.
5. UI: `[Дахин тоглох]`, `[Бооцоо 2x]` товчнууд. Дахин тоглох нь шинэ
   `play_*` дуудлага — escrow дахин хийгдэнэ. Timeout үед бүх товч disabled.

> Escrow нь «мөнгө хоёр дор зэрэг байхгүй» баталгаа болно: хасалт, нэмэлт
> хоёулаа нэг транзакцад байх тул crash үед ч үлдэгдэл буруу болохгүй.

### 3.3 `/duel @user`

1. Cog: `GameService.create_duel(challenger, opponent, bet)` →
   `multi_user_lock(a, b)` дор хоёр талын wallet шалгаж, бооцоог escrow-д түгжинэ.
   `duel_sessions` (санах ой, TTL 120с) -д session үүсгэнэ.
2. Хүлээн авагч `[Зөвшөөрөх]` → `GameService.accept()`; `[Татгалзах]` →
   escrow буцаана (`refund`).
3. Тулаан эхлэхэд `get_modifiers()` хоёр тоглогчид тусдаа уншигдана:
   `crit_active` бол `SkillService.consume_charge(user, "critical_strike")` —
   цэнэг зарцуулагдаж, тухайн раундын хохирол 1.5x.
4. Раунд бүр: `[Довтлох] / [Skill ашиглах] / [Хамгаалах]` → `GameService.resolve_round()`
   (damage = f(level, skill, random)). Session-д ээлж хадгална; буруу тоглогч
   товч дарвал `ephemeral` анхааруулга.
5. Ялалт: escrow хоёулаа хожигчид; `game_logs` хоёр мөр; `EconomyService`
   `transactions` (`duel_win`, `duel_loss`); `EventBus` → XP + Level.
6. Timeout/abort: escrow буцаана, session устна.

### 3.4 `/daily`

1. `EconomyService.claim_daily(user_id)`:
   `user_lock` → транзакц → `cooldowns`/`users.last_daily_at` шалгах.
2. `LevelService`-ээс `level`, `SkillService.get_modifiers()`-ээс
   `work_income_mult` авч:
   `reward = (DAILY_BASE + level*50) * (1 + streak*5%, max 50%) * work_income_mult`.
3. Wallet кредит + `transactions` (`daily`) + streak/`last_daily_at` шинэчлэл.
4. `EventBus.publish(XPGained(amount=mods.apply_xp(DAILY_XP)))` →
   `LevelService` шаардлагатай XP хүрвэл `LevelUp` нийтэлнэ →
   `SkillService`-ээс гадна `users.skill_points += 2`, `level*200` coin.

### 3.5 `/skills` (upgrade / activate)

- `upgrade` — `user_lock` → транзакц → `users.level ≥ skill.unlock_level`
  шалгах → `UPDATE users SET skill_points = skill_points - 1 WHERE skill_points >= 1`
  (атомик) → `user_skills.skill_level + 1 WHERE skill_level < max_level` →
  кэш invalidate → `SkillUpgraded` event.
- `activate` — `last_used_at + cooldown > now` бол `CooldownError`;
  эс бөгөөс `last_used_at = now`, `active_until = now + duration`
  (`Critical Strike` 1ц цэнэг / 2ц cooldown, `Aether Shield` 3ц / 6ц).
- `reset` — зөвхөн `ShopService` (Tome of Rebirth зарцуулсны дараа) дуудна:
  бүх мөр устгаж, `SUM(skill_level)`-ийг SP болгон буцаана.
- `get_modifiers` кэш 15 секунд; upgrade/activate/consume/reset бүрд invalidate.

### 3.6 `/rob`

`mods.rob_success_chance()` = `0.35 + shadow_step*0.04` (max 0.92).
Хамгаалалт: зорилтын `users.shield_until` **эсвэл** `mods.shield_active` →
`rob_blocked` (мөнгө хөдлөхгүй). Баригдвал торгууль =
`wallet * 0.15 * mods.rob_fine_mult`, зорилт руу шилжинэ.

---

## 4. Дараагийн шат

1. `economy_service.py` + `level_service.py` (escrow, daily/work/rob, XP→level)
2. `shop_service.py`, `casino_service.py`, `game_service.py`
3. `ui/skill_views.py`, `shop_views.py`, `casino_views.py`, `game_views.py`
4. `cogs/shop.py`, `casino.py`, `games.py`, `profile.py`

Одоо ажиллаж буй: `bot.py`, `cogs/health.py`, `cogs/economy.py`,
`cogs/skills.py`, `cogs/admin.py`, `ui/embeds.py`.
