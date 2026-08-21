# 𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹 — Website

Ботын албан ёсны вэбсайт. **Хүснэгт бүхий backend шаардлагагүй** — цэвэр статик (HTML/CSS/JS). Vercel, Netlify, GitHub Pages, Cloudflare Pages гэх мэт дурын статик hosting дээр шууд ажиллана.

## Хэсгүүд

| Хэсэг | Тайлбар |
|---|---|
| Hero | 3D orb + floating feature cards + canvas particle фон |
| Онцлогууд | Ботын 8 үндсэн ангилал (Economy, Leveling, Гэр бүл, Shop & Stock, Casino, Mafia, Модерац, Fun) |
| Командууд | 94 slash командыг хайлт болон ангиллын фильтрээр |
| Статистик | 29 cog · 77+ slash команд · 57 database таблиц · 24/7 (count-up animation) |
| Статус | Ботын технологийн стек (Python 3.12, discord.py 2.7, Supabase) |
| About Us | Ботын тухай, технологи, чанарын тестийн мэдээлэл |
| Premium | 3 төлөвлөгөөний үнэ (Free / Premium / Server) |
| Invite CTA | Ботыг server-тээ нэмэх даралт |

## Тохиргоо (заавал хийх)

`js/config.js` файлаас invite холбоосоо тохируулна:

```js
window.AETHER_CONFIG = {
  INVITE_URL: 'https://discord.com/oauth2/authorize?client_id=ТӨРИЙН_CLIENT_ID&permissions=8&scope=bot%20applications.commands',
};
```

Client ID-ээ [Discord Developer Portal](https://discord.com/developers/applications)-оос аваарай. `permissions=8` нь administrator эрх — бусад эрх хэрэгтэй бол OAuth2 permissions calculator-аар солино уу.

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
