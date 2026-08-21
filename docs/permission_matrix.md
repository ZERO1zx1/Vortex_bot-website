# 𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹 — Админ / Модератор командуудын эрхийн матриц

**Огноо:** 2026-08-16 · **Commit:** `3e8d37a` (main) · **Git:** https://github.com/ZERO1zx1/gurtendev

Энэ баримт бичигт ботын бүх админ болон модератор командуудын эрхийн тохиргоог нэгтгэсэн. Audit-ын явцад бүх 29 cog-ийг шалгаж, дутуу байсан 3 командыг засварласан.

---

## 1. Эрхийн ангилал

Дискорд дээр админistrate-ийн эрхийг хоёр түвшинд хянадаг:

| Түвшин | Декоратор | Юу хийдэг |
|---|---|---|
| Text командиуд (`!command`) | `@commands.has_permissions(...)` | Команд ажиллуулах үед Python-оор шалгана, эрхгүй бол алдаа буцаана |
| Slash командиуд (`/command`) | `@app_commands.default_permissions(...)` | Discord UI дээр командиуд **хийн** харагдахгүй (зөвхөн эрхтэй хүнд) |

Ботын бүх команд `hybrid_command` (slash + text хоёулаа) эсвэл `app_commands` (slash зөвхөн) хэлбэртэй тул **хоёр түвшний шалгалт хоёулаа** байх ёстой гэсэн стандартыг хэрэглэсэн.

---

## 2. Админ эрх (Эзэмшигч)

`/addmoney`, `/removemoney` нь text + slash хоёулаа ажилладаг.

| Команд | Текст | Slash | Нэмэлт хамгаалалт |
|---|---|---|---|
| `admin.addmoney` (`!am`) | administrator ✅ | administrator ✅ | + runtime: зөвхөн bot эзэмшигч/co-owner (`owner_ids`) |
| `admin.removemoney` (`!rm`) | administrator ✅ | administrator ✅ | + runtime: зөвхөн bot эзэмшигч/co-owner |
| `admin.rolelist` | administrator ✅ | administrator ✅ | — |
| `economy.admin-panel` (`!admin-panel`) | administrator ✅ | text зөвхөн — Discord-рүү бүртгэгдэхгүй | — |
| `economy.workphrase` | administrator ✅ | administrator ✅ | — |
| `avatar_check` (admin cmds) | administrator ✅ | administrator ✅ | — |
| `confessions` (3 admin cmd) | slash зөвхөн | administrator ✅ | — |
| `counting` (admin cmd) | slash зөвхөн | administrator ✅ | — |
| `mafia` (create/start/end) | administrator ✅ | administrator ✅ | — |
| `marriage.market` (admin) | slash зөвхөн | administrator ✅ | — |
| `stock` (5 admin cmd: toggle, restock) | administrator ✅ | administrator ✅ | — |
| `tempvoice` (admin cmd) | slash зөвхөн | administrator ✅ | — |
| `announcement.announce` | slash зөвхөн | administrator ✅ | + modal payload validation |

---

## 3. Модератор эрх (Модератор)

| Команд | Текст | Slash | Discord-ийн бааз эрх |
|---|---|---|---|
| `moderation.lock` / `unlock` | manage_channels ✅ | *тохиргоо нь text-д* | manage_channels |
| `moderation.kick` | kick_members ✅ | default: kick_members ✅* | kick_members |
| `moderation.ban` / `unban` / `banlist` | ban_members ✅ | default: ban_members ✅* | ban_members |
| `moderation.clear` (`!purge`) | manage_messages ✅ | default: manage_messages ✅* | manage_messages |
| `moderation.timeout` / `untimeout` | moderate_members ✅ | default: moderate_members ✅* | moderate_members |
| `moderation.warn` / `unwarn` | kick_members ✅ | default: kick_members ✅* | kick_members |
| `moderation.warnings` / `warnedusers` | kick_members ✅ | default: kick_members ✅* | kick_members |
| `giveaway.*` (6 cmd) | slash зөвхөн | manage_guild ✅ | manage_guild |
| `greetings.*` (10 cmd) | slash зөвхөн | manage_guild ✅ (нэг нь administrator) | manage_guild |
| `invite_tracker.*` (3 cmd) | slash зөвхөн | manage_guild / administrator ✅ | — |
| `roles.*` (5 cmd: add/remove/give/list/config) | manage_roles ✅ | administrator (config) ✅ | manage_roles + ботын manage_roles ба бот тухайн ролыг удирдах эсэх шалгалт |
| `leveling` admin (grank admin path) | runtime: admin эсвэл allowlist ✅ | — | allowlist-ийг DB `leveling_exceptions`-с уншина |
| `stick` (2 cmd) | manage_channels ✅ | — | manage_channels |

\* `default_permissions` нь Discord-ийн slash UI дээрхи харагдах эрх; `has_permissions` нь text командад нэмэлт Python шалгалт. Бүх moderate командыг мөн **ботын өөрийн эрх** (`guild.me.guild_permissions`) эсэхийг нэмэлт шалгадаг — жишээ нь ботонд kick эрх байхгүй бол зөв тайлбар бүхий алдаа буцаана.

---

## 4. Нийтийн командууд (эрх шаардахгүй)

Эдийн засаг, тоглоом, café, shop, marriage (member), help, status, info, giveaway оролцох командууд гэх мэт бүх ердийн командуудад эрхийн шалгалт байхгүй — бүх гишүүн ашиглах боломжтой. `status` болон `info` нь серверийн нийтийн мэдээлэл харуулдаг учраас зориудаар нээлттэй орхисон.

---

## 5. Энэ шалгалтын явцад хийсэн засварууд

| Файл | Өөрчлөлт |
|---|---|
| `cogs/admin.py` | `addmoney`, `removemoney`-д `has_permissions(administrator)` + `default_permissions(administrator)` нэмсэн. Runtime эзэмшигчийн шалгалт хэвээрээ — давхар хамгаалалт |
| `cogs/economy.py` | `workphrase`-д `default_permissions(administrator)` нэмсэн (text тал нь аль хэдийн has_permissions-тай байсан) |

Бусад бүх admin/moderator командууд аль хэдийн зөв тохируулагдсан байсан — нэмэлт засвар шаардлагагүй.

---

## 6. Discord сервер дээр эрх тохируулах

Discord сервер дээрх үүргүүдэд эдгээр эрхүүдийг өгөхөд командууд автоматаар нээгдэнэ:

| Үүрэг | Өгөх эрхүүд |
|---|---|
| **Администратор** | Administrator (бүх эрх) — эсвэл зөвхөн дээрх командуудад Manage Server |
| **Модератор** | Manage Channels, Kick Members, Ban Members, Manage Messages, Moderate Members, Manage Roles (хайрцаглах) |

**Анхааруулга:** `Administrator` эрхтэй үүрэг бүх дээрх шалгалтыг автоматаар давна — ямар ч команд ашиглах боломжтой болно. `Manage Server` эрх нь мөн Administrator flag-тэй тэнцүү ажиллана (Discord-ийн дүрэм).

---

## 7. Таны PC дээр шинэчлэх

```powershell
cd C:\Users\hotar\OneDrive\Desktop\gurtendev
git pull origin main
py -3.12 main.py
```

(Локал `database/migrations/000_complete_schema.sql` файлд өөрчлөлттэй бол эхлээд `git checkout -- database/migrations/000_complete_schema.sql`.)

Шинэчлэсний дараа `/addmoney`, `/removemoney`, `/workphrase` командууд эрхгүй хүний slash жагсаалтад хийн болж, эрхгүй хүн ашиглах гэж оролдвол Discord шууд "You cannot use this command" гэж харуулна.
