# Aether website

Aether bot-ын Монгол хэл дээрх anime/cyberpunk танилцуулга болон command catalog.

## Бүтэц

- `index.html` — нүүр, 11 үндсэн систем, статус, community, changelog, FAQ
- `js/commands.js` — active bot cogs-оос автоматаар үүссэн command catalog
- `js/app.js` — хайлт, filter, modal, theme, animation, live status
- `tools/sync_website_commands.py` — `ACTIVE_COGS` болон `COMMAND_INFO`-г тулгаж catalog sync хийнэ
- `tools/catalog_source.py` — catalog literal-уудыг JavaScript ажиллуулахгүй унших туслах
- `tools/sync_cmd_i18n.py` — command нэр/тайлбарын орчуулгын дутуу key-г нэмнэ
- `tools/validate_commands.js` — catalog-ийн бүтэц, duplicate, command type шалгана

## Catalog шинэчлэх

Bot-д command нэмсэн эсвэл active cog өөрчлөгдсөн үед:

```powershell
python website/tools/sync_website_commands.py
node website/tools/validate_commands.js
```

Файл өөрчлөхгүйгээр sync шаардлагатай эсэхийг шалгах:

```powershell
python website/tools/sync_website_commands.py --check
python website/tools/sync_cmd_i18n.py --check
```

`--check` нь файл бичихгүй; drift байвал exit code 1 буцаана. Танихгүй
аргументыг parser шууд алдаа болгоно. `--check`-гүй sync нь generated файлд
өөрчлөлт оруулдаг тул diff-ийг commit хийхээс өмнө шалгана.

Command-ийн нийт тоо, slash/text задаргаа нь `commands.js`-ээс web дээр автоматаар гардаг. Иймээс HTML дотор гараар тоо солих шаардлагагүй.

## Үндсэн системүүд

Economy, Games & Casino, Level/Ranking/Profile, Shop/Inventory, Giveaway, Ticket,
Moderation & Statistics, Webhook Automation, Marriage, Fun, Confessions.

Firebase Hosting нь `website/` хавтсыг publish хийдэг.
