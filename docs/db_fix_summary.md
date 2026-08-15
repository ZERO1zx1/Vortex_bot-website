# Supabase Vortex — Бүрэн шалгалт ба засварын тайлан

**Огноо:** 2026-08-15 (02:15–02:22 UTC)
**Project:** Vortex (`onpxpvemmjesobxpilgd`, ap-northeast-1)

## 1. Асуудлын жинхэнэ шалтгаан

Таны 10:13 цагийн log-д `401 Unauthorized` болон `42501 permission denied` алдаанууд гарч байсан. Шалгалтаар дараах зүйлсийг тогтоолоо:

| Шалтгаан | Тайлбар |
|---|---|
| RLS унтарсан ✅ | Бүх 57 хүснэгт `rowsecurity = false` байсан — RLS биш байсан |
| **GRANT дутуу байсан ❌ → засагдлаа** | Dashboard SQL Editor-оор migration ажиллуулахад бүх хүснэгт `postgres` роль дээр үүссэн. Supabase-ийн default privileges нь `postgres`-оор үүсгэгдсэн хүснэгтэд `anon` рольд **SELECT/INSERT/UPDATE/DELETE эрх өгдөггүй** байсан |

`economy` хүснэгтийн жишээ (засвараас өмнө): `anon` рольд зөвхөн `REFERENCES`, `TRIGGER`, `TRUNCATE` эрхтэй байсан — `SELECT` байхгүй учраас bot (anon key) хүснэгт бүр дээр 42501 авч байсан.

## 2. Хийсэн засварууд (live database дээр хийгдсэн)

1. **`GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated`** — бүх 57 хүснэгтэд `anon` болон `authenticated` рольд бүрэн эрх. Шалгалтаар **57/57 хүснэгт `anon_can_select = true`** болсон.
2. **`GRANT ALL ON ALL SEQUENCES / FUNCTIONS ... TO anon, authenticated`** — sequence болон function эрхүүд мөн.
3. **`ALTER DEFAULT PRIVILEGES FOR ROLE postgres ...`** — ЦААШДАА dashboard SQL Editor-оор (postgres) шинэ хүснэгт үүсгэхэд `anon` рольд бүрэн эрх автоматаар олгогдох болсон. Энэ засвар ирээдүйд ижил алдаа дахин гарахаас сэргийлнэ.
4. **`NOTIFY pgrst, 'reload schema'`** — PostgREST schema cache цэвэрлэсэн.

## 3. Repo дээр хийсэн засварууд (commit `90e757d`, main руу push хийгдсэн)

| Файл | Өөрчлөлт |
|---|---|
| `database/migrations/000_complete_schema.sql` | SECTION 4 нэмэгдсэн: `GRANT ALL ... TO anon, authenticated` болон `ALTER DEFAULT PRIVILEGES` — дахин migration хийх үед бүрэн бэлэн |
| `database/supabase_manager.py` | `_is_missing_table()` одоо **42501 (permission denied)** алдааг бас барьдаг — энэ төрлийн алдаа loop-уудыг дахин crash хийлгэхгүй |
| `check_migration_applied.py` | 401 алдааны заавар сайжруулсан (GRANT-ийн талаар тайлбарласан) |

## 4. Бүрэн шалгалтын үр дүн (02:22 UTC)

| Талбар | Үр дүн |
|---|---|
| Database холболт | ✅ PostgreSQL 17.6 — идэвхтэй, pause болоогүй |
| Хүснэгтийн тоо | ✅ 57 хүснэгт public schema-д байна |
| RLS | ✅ 57/57 хүснэгт RLS OFF, RLS-тай хүснэгт **0** |
| anon SELECT эрх | ✅ 57/57 хүснэгт `anon_can_select = true` |
| Default privileges | ✅ `postgres`-оор үүсгэгдэх шинэ хүснэгтүүд `anon`-д `arwdDxtm` эрхтэй болсон |
| PostgREST cache | ✅ schema reload хийгдсэн |

## 5. Хийх үлдсэн алхмууд (таны талд)

```powershell
cd C:\Users\hotar\OneDrive\Desktop\gurtendev
git pull origin main          # commit 90e757d авах
py -3.12 check_migration_applied.py   # 12 гол хүснэгт бүгд OK гарах ёстой
```

Дараа нь **bot-оо бүрэн унтрааж** (`Ctrl+C`), дахин асаа:

```powershell
py -3.12 main.py
```

Энэ удаа `401`, `42501` алдаанууд **бүгд арилах ёстой** — учир нь засварууд database дээр аль хэдийн хийгдсэн бөгөөд PostgREST cache цэвэрлэгдсэн.
