# Aether website

Aether bot-ын Монгол хэл дээрх anime/cyberpunk танилцуулга болон command catalog.
React 19 + Vite дээр байгуулсан SPA.

## Бүтэц

```
website/
├── index.html            # Vite entry (head, SEO meta, theme bootstrap)
├── src/
│   ├── main.jsx          # React root
│   ├── App.jsx           # section composition + global effects
│   ├── components/       # one file per section, plus shared primitives
│   ├── hooks/            # theme, lang, heartbeat, catalog, motion, background
│   ├── i18n/             # MN/EN UI copy
│   ├── data/             # generated catalog + site config
│   └── styles/style.css  # the full design system (single file, as before)
├── public/               # static assets, copied verbatim by Vite
└── tools/                # catalog generators and browser checks
```

## Хөгжүүлэх

```powershell
cd website
npm install
npm run dev      # http://localhost:5173
npm run build    # -> website/dist
npm run preview  # serves dist on http://localhost:4173
```

`npm run build` үргэлж `website/dist` руу бичнэ. Firebase Hosting мөн `website/dist`-ийг
нийлүүлдэг тул deploy хийхийн өмнө build заавал авах шаардлагатай.

## Deploy

```powershell
npm --prefix website run build
firebase deploy --only hosting:aether
```

## Catalog шинэчлэх

Bot-д command нэмсэн эсвэл active cog өөрчлөгдсөн үед:

```powershell
python website/tools/sync_website_commands.py
node website/tools/validate_commands.mjs
```

Файл өөрчлөхгүйгээр sync шаардлагатай эсэхийг шалгах:

```powershell
python website/tools/sync_website_commands.py --check
python website/tools/sync_cmd_i18n.py --check
```

`--check` нь файл бичихгүй; drift байвал exit code 1 буцаана. Танихгүй
аргументыг parser шууд алдаа болгоно. `--check`-гүй sync нь generated файлд
өөрчлөлт оруулдаг тул diff-ийг commit хийхээс өмнө шалгана.

- `tools/sync_website_commands.py` — `src/cogs/help.py`-ийн `COMMAND_INFO`-г
  уншан `src/data/commands.js` ES module-ыг үүсгэнэ. `desc` нь Монгол,
  `descEN` нь Англи текст.
- `tools/catalog_source.py` — JS файлыг ажиллуулахгүйгээр унших туслах.
- `tools/sync_cmd_i18n.py` — catalog дахь орчуулгын дутуу/согдсон утгыг шалгана.
- `tools/validate_commands.mjs` — catalog-ийн бүтэц, `type`, `args`,
  `desc`/`descEN` оршихыг шалгана.

Command-ийн нийт тоо, slash/text задаргаа нь `src/data/commands.js`-ээс
web дээр автоматаар гардаг. Иймээс HTML дотор гараар тоо солих шаардлагагүй.

## Browser шалгалт

```powershell
python website/tools/render_check.py --url http://localhost:4173 --shots
python website/tools/interaction_check.py --url http://localhost:4173
```

`render_check.py` — desktop/mobile render, console алдаа, overflow, asset ачаалалт.
`interaction_check.py` — хэл солих, theme, command хайх/шүүх, modal focus trap,
mobile цэс.

## Үндсэн системүүд

Economy, Games & Casino, Level/Ranking/Profile, Shop/Inventory, Giveaway, Ticket,
Moderation & Statistics, Webhook Automation, Marriage, Fun, Confessions.