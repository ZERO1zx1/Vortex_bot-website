# Gurtendev — Cog Audit болон Supabase Migration Баталгаажуулалтын Тайлан

**Огноо:** 2026-08-15 | **Repository:** ZERO1zx1/gurtendev (`main`, commit `a92b200`) | **Supabase project:** Vortex (`onpxpvemmjesobxpilgd`)

Энэхүү тайланы зорилго нь бүх 29 cog файлыг бүрэн шалгаж, кодод байгаа жинхэнэ алдаануудыг тодорхойлох, мөн Supabase дээр schema migration ажилласан эсэхийг баталгаажуулах юм.

## 1. Cog файлуудын шалгалтын үр дүн

Бүх cog файлыг Python compile шалгалт, абстракт синтаксийн модны нэр хяналт (static name analysis), мөн unittest suite-ээр шалгалаа. Compile алдаа, unittest-ийн алдаа, эсвэл import-ын асуудал **аль нь ч олдсонгүй**; бүх 41 unittest амжилттай дууссан.

Статик шинжилгээний үр дүнд олон тооны "undefined name" илэрсэн ч тэдгээрийн дийлэнх нь функцын параметр (`ctx`, `interaction`, `self.x`, `member`, `guild_id` гэх мэт), list comprehension-ийн хувьсагч, эсвэл `from discord import ...`-ээр импортлогдсон нэрс байсан тул жинхэнэ алдаа биш юм.

### Жинхэнэ олдсон алдаа: `cogs/games.py`

`games.py` файлын 195–257 мөрөнд тодорхойлогдоогүй 9 view class болон 1 хувьсагчийг ашигласан байна. Эдгээр нь команд ажиллуулах үед `NameError` үүсгэнэ (бот асахад алдаа гарахгүй, харин командаар тоглох үед задарна):

| Байрлал | Дутуу нэр | Төлөв |
|---|---|---|
| `gamble`, `coinflipgame`, `slot`, `roulettegame`, `dice`, `rps` командууд | `GambleView`, `CoinflipView`, `SlotsView`, `RouletteView`, `DiceView`, `RPSView` | Class нь repo-д огт тодорхойлогдоогүй |
| `numberguess` команд | `NumberGuessView` | Мөн адил |
| `trivia` команд (257 мөр) | `TRIVIA_QUESTIONS` | Асуултын жагсаалт байхгүй |
| 43–47 мөрөнд | `BlackjackView`, `HighCardView`, `CrashView`, `HighLowView` | Комментарииор "хэмжээ хязгаартай тул оруулаагүй" гэж бичсэн байдаг ч кодын 195–249 мөрөнд эдгээрийг ашигласан |

Харин `cogs/casino.py` дотор `BlackjackView` бодитоор тодорхойлогдсон (31 мөр) бөгөөд үүнийг games.py-рүү импортлон оруулах боломжтой.

Командын нэрийн давхцал шалгахад хоёр файлыг ялгасан байна: `games.py` нь `gamble`, `coinflipgame`, `slot`, `roulettegame`, `dice`, `rps`, `numberguess`, `highcard`, `crash`, `trivia`, `gamestats`; `casino.py` нь `blackjack`, `rob`, `hack`, `cgive`, `highlow`. Аль нэг ч давхцал байхгүй тул Discord sync-д мөн алдаа гарахгүй.

**Зөвлөмж:** `cogs/casino.py`-аас `BlackjackView` гэх мэт view-үүдийг өргөтгөж games.py-ийн бүх тоглоомын view-ийг гүйцэтгэн оруулж, `TRIVIA_QUESTIONS`-д жинхэнэ асуултын жагсаалт нэмэх шаардлагатай. Хүсвэл би энэ засварыг хийж болно.

## 2. Supabase migration-ийн баталгаажуулалт

Би таны Supabase account-тай холбогдох зөвшөөрөгдсөн удирдлагын API-аар (read-only) Vortex project-ийг шалгалаа. Үр дүн тодорхой:

| Шалгалт | Үр дүн |
|---|---|
| Project төлөв | ACTIVE_HEALTHY (ap-northeast-1) |
| `list_migrations` | Хоосон — ямар ч SQL migration ажиллаагүй |
| `information_schema.tables` (public schema) | **0 хүснэгт** — database нь бүрэн хоосон |

Өөрөөр хэлбэл, **schema migration-ийг Supabase-д огт ажиллуулаагүй** байна. Bot-ын log дээрх бүх `404 Not Found` ба `PGRST205` алдаанууд үүнээс гарч байгаа бөгөөд code-д биш.

### Хийх ёстой алхмууд (таны PC дээр)

1. Supabase Dashboard-д [Vortex project](https://supabase.com/dashboard/project/onpxpvemmjesobxpilgd) руу нэвтрэх
2. Зүүн цэснээс **SQL Editor → New query**
3. Repository-ийн `database\migrations\000_complete_schema.sql` файлыг нээж бүх агуулгыг (578 мөр) copy хийнэ
4. SQL Editor дээр paste хийж **Run** дарна
5. Дараа нь `check_migration_applied.py` скриптийг ажиллуулж баталгаажуулна:

```powershell
cd C:\Users\hotar\OneDrive\Desktop\gurtendev
py -3.12 check_migration_applied.py
```

Энэ скрипт нь таны `.env`-ээс `SUPABASE_URL` болон `SUPABASE_KEY`-ийг автоматаар уншиж, 57 хүснэгтийн аль нь байгаа/байхгүйг мөчлөгт шалгана. Read-only учраас database-д өөрчлөлт оруулахгүй.

6. Эцэст нь bot-оо дахин асаана: `py -3.12 main.py`

Migration амжилттай болсны дараа startup-ын `Required Supabase table ... is missing` warning-ууд болон background task-уудын `PGRST205` алдаанууд бүгд арилах ёстой.
