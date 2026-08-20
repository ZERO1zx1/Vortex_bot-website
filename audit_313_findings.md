# Python 3.13 (docs.python.org/3.13/) аудит — олдвор

## Стандартын мэдлэг (3.13 docs-оос)
- `datetime.datetime.utcnow()` deprecated 3.12, REMOVAL: remove_in 3.14 (docs.python.org/3/deprecations)
  → `datetime.now(timezone.utc)` ашиглах.
- `asyncio.get_event_loop()` (sync context) deprecated 3.10+, removal 3.14; 3.13-д DeprecationWarning гаргаж эхэлнэ
  → `asyncio.get_running_loop()` хэрэглэх (sync-с дуудахад RuntimeError → fallback).
- `asyncio.iscoroutinefunction()` deprecated 3.15-д авах — 3.13-д бус (skip)
- Removed modules 3.13 (PEP 594): aifc, audioop, cgi, cgitb, chunk, crypt, imghdr, mailcap, msilib, nis, nntplib, ossaudiodev, pipes, sndhdr, spwd, sunau, telnetlib, uu, xdrlib → бидний код эдгээрийг ашиглахгүй.
- `typing.NamedTuple` kwargs syntax deprecated 3.13 → бидэнд байхгүй (verify).
- `warnings.deprecated()` 3.13-д шинэ — хэрэглэх шаардлагагүй (бог кодууд).

## discord.utils.utcnow()
discord.py 2.x-ийн `discord.utils.utcnow()` нь `datetime.now(timezone.utc)` RETURN — ALREADY AWARE. 3.13-д safe. Үлдэх.

## ЗАСВАРЛАХ (3.13 стандартын дагуу)
1. cogs/moderation.py:200 `datetime.datetime.utcnow()` → `datetime.datetime.now(datetime.timezone.utc)` (weekly_task)
   - line 704, automod 228/278, greetings 326: `discord.utils.utcnow()` — aware, ХЭВЭЭР үлдээнэ (discord.py 2.x албан ёсны helpers)
2. database/supabase_manager.py:311 `datetime.utcnow().isoformat() + "Z"` → `datetime.now(timezone.utc).isoformat() + "Z"`
3. cogs/invite_tracker.py:464 `datetime.datetime.now(datetime.timezone.utc)` — OK (already aware)
4. utils/i18n.py:240, 256 `loop = asyncio.get_event_loop()` → `loop = asyncio.get_running_loop()`
5. cogs/automod.py:103 `asyncio.get_event_loop()` (fallback) → get_running_loop() зөвхөн; call_later хэрэглээнд loop.get_event_loop_policy хэрэггүй
6. tools/test_all_commands.py:181 sync context: `asyncio.get_event_loop()` → new_event_loop fallback (тест файл — зөөлөн засах)
7. cogs/presence.py:46 `asyncio.new_event_loop()` + `run_until_complete` в to_thread wrapper — энэ нь to_thread (threading)-д зориулсан, зөв (thread-д running loop байхгүй) → ХЭВЭЭР
8. Наив timestamp сайтууд (confessions/marriage/stock/moderation 752/828/860): int(timestamp) DB storage → UTC-aware болгох нь цэвэрхэн: `datetime.now(timezone.utc).timestamp()` — энэ нь 3.13 deprecation-тай шууд хамааралгүй ч "utcnow deprecation" spirit-д нийцнэ. Засах (consistent).
9. greetings.py:293 `now = datetime.now()` placeholder only (local display) → зориудаар SKIP гэж audit_notes-д байсан; ГЭВЧ 3.13 spirit: aware болгох = энгийн засах. Хийх: `datetime.now(timezone.utc)` — placeholder цаг UTC болно, MN серверийн хувьд -8 зөрүү гарна → SKIP (user intention: local time display). Тэмдэглэх.
10. admin.py:24 `datetime.fromtimestamp(self.start_time)` — aware хийх: `datetime.fromtimestamp(self.start_time, timezone.utc)` → энгийн, 3.13 spirit. Хийх.

## Хийхгүй (skip, шалтгаантай)
- greeting placeholder local time, marriage .date() date-math, stock int(ts) already consistent → stock/marriage/confessions: consistency төлөө засах (3.13 spirit "stop naive UTC") → ACTUALLY засах нь дээр (consistent UTC).
- Discord API requires aware datetimes; our aware usage is already correct.
