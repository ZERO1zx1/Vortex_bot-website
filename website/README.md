# 𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹 — Website

Ботын албан ёсны статик HTML/CSS/JS вэбсайт. UI болон командын каталог нь дурын статик hosting дээр ажиллана. Live status-д Supabase key-г browser-т гаргахгүйн тулд `backend/` FastAPI сервисийн `API_BASE_URL` шаардлагатай.

## Хэсгүүд

| Хэсэг | Тайлбар |
|---|---|
| Hero | 3D orb + floating feature cards + canvas particle фон |
| Онцлогууд | Ботын 8 үндсэн ангилал (Economy, Leveling, Гэр бүл, Shop & Stock, Casino, Mafia, Модерац, Fun) |
| Командууд | 201 командыг (83 slash / 118 text) хайлт болон ангиллын фильтрээр |
| Статистик | 35 cog · 201 команд · 61 database хүснэгт · 24/7 (count-up animation) |
| Статус | Ботын технологийн стек (Python 3.13, discord.py 2.6, Supabase) |
| About Us | Ботын тухай, технологи, чанарын тестийн мэдээлэл |
| Premium | 3 төлөвлөгөөний үнэ (Free / Premium / Server) |
| Invite CTA | Ботыг server-тээ нэмэх даралт |

## Тохиргоо (заавал хийх)

`js/config.js` файлаас invite холбоосоо тохируулна:

```js
window.AETHER_CONFIG = {
  BOT_INVITE_URL: 'https://discord.com/oauth2/authorize?client_id=ТӨРИЙН_CLIENT_ID&permissions=0&scope=bot%20applications.commands',
};
```

Мөн backend-ээ deploy хийсний дараа `API_BASE_URL`-г тохируулна. Хоосон үед сайт database руу fallback хийхгүй бөгөөд status-ийг offline/unavailable гэж үзнэ.

Client ID-ээ Discord Developer Portal-оос аваарай. Invite холбоос нь серверийн эрх автоматаар шаардахгүй. Серверийн эзэмшигч зөвхөн ашиглах feature-д хэрэгтэй эрхийг ботын role-д өгнө.

## Local-д турших

```bash
cd website
python3 -m http.server 8080
# http://localhost:8080
```

## Hosting-д нийтлэх

- **Vercel/Netlify/Cloudflare Pages:** `website/` хавтсыг publish directory болгож сонгох. Ямар ч тохиргоо шаардлагагүй.
- **GitHub Pages:** Repo settings > Pages > Source: GitHub Actions эсвэл `website/` хавтас.
- Файлууд шууд `index.html` → бүх asset харьцангуй замаар холбогдсон тул subdirectory-д ч ажиллана.

## Өөрчлөх боломжтой зүйлс

- Өнгөний схем: `css/style.css`-ийн `:root` хувьсагчид (`--accent` г.м.)
- Командын жагсаалт: `js/commands.js` (`COMMANDS` массив)
- Premium үнэ: `index.html`-ийн `#premium` хэсэг
