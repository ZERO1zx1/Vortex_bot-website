# 𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹 — Website Backend API (FastAPI)

Firebase дээрх static сайтад зориулсан API сервис. Discord бот Supabase-д
бичдэг (heartbeat, levels, giveaways), энэ backend тэдгээрийг уншиж
сайт руу CORS-оор өгдөг. **Discord-тай огт холбогддоггүй** тул хөнгөн,
тусдаа deploy хийгдэнэ.

## Endpoints

| Method | Path | Тайлбар |
|--------|------|---------|
| GET | `/`, `/health` | Health check |
| GET | `/api/status` | Бот online/offline + uptime (`bot_status` хүснэгт) |
| GET | `/api/leaderboard?guild_id=...&limit=10` | XP топ жагсаалт (`levels`) |
| GET | `/api/giveaways?guild_id=...&active=1` | Giveaway жагсаалт (`giveaways`) |
| GET | `/api/commands?cat=Economy&q=...` | Командын каталог (153 команд) |

Interactive docs: `/docs` (Swagger UI).

## Локал ажиллуулах

```powershell
cd backend
pip install -r requirements.txt
$env:SUPABASE_URL = "https://onpxpvemmjesobxpilgd.supabase.co"
$env:SUPABASE_KEY = "<anon эсвэл service key>"
uvicorn main:app --reload --port 8080
```

Шалгах: http://localhost:8080/health ба http://localhost:8080/docs

## Railway дээр deploy (боттой ижил project)

1. Railway project дотроо **New Service → GitHub Repo** сонгоно
2. **Settings → Build → Root Directory: `backend`** гэж тохируулна
   (backend/Dockerfile автоматаар ашиглагдана)
3. **Variables** хэсэгт нэмнэ:
   - `SUPABASE_URL` — боттой ижил
   - `SUPABASE_KEY` — боттой ижил (anon key хангалттай)
   - `ALLOWED_ORIGINS` — нэмэлт домэйн байвал (таслалаар)
4. **Settings → Networking → Generate Domain** — жишээ:
   `https://aether-backend.up.railway.app`

## Сайттай холбох (website/js/config.js)

```js
window.AETHER_CONFIG = {
  // ...одоогийнхоо доор нэмнэ:
  API_BASE_URL: 'https://aether-backend.up.railway.app',
};
```

Жишээ fetch (app.js):

```js
const res = await fetch(`${AETHER_CONFIG.API_BASE_URL}/api/status`);
const { online, uptime_secs } = await res.json();
```

## Env хувьсагчид

| Нэр | Заавал | Default | Тайлбар |
|-----|--------|---------|---------|
| `SUPABASE_URL` | ✅ | — | Supabase project URL |
| `SUPABASE_KEY` | ✅ | — | anon/service key |
| `ALLOWED_ORIGINS` | — | Firebase + localhost | CORS нэмэлт origin-ууд |
| `HEARTBEAT_FRESH_SECS` | — | `120` | Бот offline гэж тооцох босго |
| `STATUS_CACHE_TTL` | — | `20` | Status cache (сек) |
| `LIST_CACHE_TTL` | — | `60` | Leaderboard/giveaway cache (сек) |
| `PORT` | — | `8080` | Railway автоматаар өгнө |

## Тэмдэглэл

- `data/commands.json` нь `website/js/commands.js`-ээс үүсгэгдсэн.
  Команд нэмэх бүрд дахин generate хийнэ (tools/sync_website_commands.py
  ажиллуулсны дараа).
- Бүх endpoint зөвхөн **уншдаг** (GET only) — бичилт, auth одохондоо байхгүй.
